#!/usr/bin/env python3
"""`r` reabre TODAS las marcadas, incluidas las que ya se ven en otra ventana.

El bug que lo trajo: se marcaban seis sesiones, cuatro estaban abiertas en otro Warp y
solo se abrian dos — y si las seis lo estaban, ninguna, con un "esas ya tienen pestana
abierta" que sonaba a error del usuario. `r` filtraba por `attached` antes de abrir.

Nadie lo cazo porque **toda la bateria marcaba una sola fila**: `test_donde_abrir.py` y
compania pulsan `[ESPACIO, r]` y ademas ponen `attached = False` en todas para que la
seleccion no salga vacia. Con una marca y sin nadie enganchado, el filtro nunca se veia.

Lo que se vigila:

  1. marcar N manda N a quien abre, para N = 1, 2 y 3 (el caso multiple, que faltaba);
  2. una fila con `attached` NO se cae de la seleccion;
  3. el comando de una sesion viva lleva `attach -d`, que es lo que la MUDA aqui;
  4. y el hecho de tmux en el que se apoya el `-d`, medido contra tmux de verdad: sin
     el, la sesion acaba con dos clientes —y tmux la encoge al mas pequeno—; con el,
     con uno. Sin esta ultima parte el punto 3 seria una preferencia de estilo.

Si no hay tmux esto FALLA en vez de saltarse, igual que `test_tmux_de_verdad.py`: un
test que se calla cuando le falta la dependencia no protege nada.
"""
import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
os.environ.pop("SERENO_LANZADOR", None)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

ESPACIO, ABAJO, R, UNO, Q = 32, 258, ord("r"), ord("1"), ord("q")
SOCK = "sereno-tests-marcadas"


def corre(n_marcas, attached=()):
    """Marca `n_marcas` filas y pulsa `r`. Devuelve las llamadas a `ejecutar`.

    `attached` son los indices de las filas que ya se ven en otra ventana.
    """
    ns["PREFS"] = pathlib.Path(tempfile.mkdtemp()) / "prefs.json"
    import curses as real
    llamadas, cajon = [], []
    ns["lanzadores_disponibles"] = lambda: ["warp", "tmux", "terminal"]

    def ejecutar(verbo, sel, donde=None, modelo=None):
        llamadas.append({"verbo": verbo, "n": len(sel), "donde": donde})
        return "ok", ns["sesiones_demo"]()

    filas = ns["sesiones_demo"]()
    for i, f in enumerate(filas):
        f["attached"] = i in attached

    # El cursor avanza de una en una; las filas de la demo se marcan de dos en dos
    # porque entre ellas hay separadores, y por eso el ABAJO va entre marca y marca.
    teclas = []
    for i in range(n_marcas):
        teclas.append(ESPACIO)
        if i < n_marcas - 1:
            teclas.append(ABAJO)
    teclas += [R, UNO, Q]

    sys.modules["curses"] = espia(real, 40, 160, teclas, cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](filas, ejecutar=ejecutar)
    finally:
        sys.modules["curses"] = real
    return [l for l in llamadas if l["verbo"] == "reopen"]


def tmux(*args):
    return subprocess.run(["tmux", "-L", SOCK, *args], capture_output=True, text=True)


def clientes_tras_attach(con_d):
    """Cuantos clientes le quedan a una sesion tras engancharla una segunda vez.

    Se levanta un servidor propio (`-L`) para no abrir ventanas en las sesiones de quien
    corra la bateria dentro de tmux, que es justo el publico de este programa.
    """
    tmux("kill-server")
    time.sleep(0.5)
    tmux("new-session", "-d", "-s", "diana", "sleep 60")
    tmux("new-session", "-d", "-s", "casa", "sleep 60")
    # `unset TMUX` porque desde dentro de tmux el attach se niega a anidar. Es lo mismo
    # que hace el guion de `_guion`, y sin ello la ventana muere sin engancharse.
    for i, extra in enumerate(("", "-d " if con_d else "")):
        tmux("new-window", "-t", "casa", "-n", "c%d" % i,
             "unset TMUX; exec tmux -L %s attach %s-t diana" % (SOCK, extra))
        time.sleep(1.5)
    n = tmux("display-message", "-p", "-t", "diana", "#{session_attached}").stdout.strip()
    tmux("kill-server")
    return int(n or 0)


def main():
    fallos = []

    # 1. N marcadas -> N abiertas. Con una sola marca ya pasaba; el caso que faltaba
    #    es el de varias, que es el que Alex reporto.
    for n in (1, 2, 3):
        abrir = corre(n)
        if not abrir:
            fallos.append("con %d marcadas no se abrio nada" % n)
        elif abrir[0]["n"] != n:
            fallos.append("marcadas %d, abiertas %d" % (n, abrir[0]["n"]))

    # 2. Las que ya tienen pestana en otra ventana siguen dentro. La demo marca las
    #    filas 0, 2 y 4, asi que se enganchan esas.
    abrir = corre(3, attached=(0, 2))
    if not abrir:
        fallos.append("con dos ya enganchadas no se abrio ninguna")
    elif abrir[0]["n"] != 3:
        fallos.append("dos enganchadas se cayeron: se abrieron %d de 3" % abrir[0]["n"])

    # 2b. Y el caso extremo: TODAS enganchadas. Antes salia "esas ya tienen pestana
    #     abierta" y no se abria nada.
    abrir = corre(3, attached=(0, 2, 4))
    if not abrir or abrir[0]["n"] != 3:
        fallos.append("con las tres enganchadas no se reabren: %r" % (abrir,))

    # 3. El comando de una sesion viva la MUDA, no la duplica.
    cmd, _cwd = ns["_comando_de"]({"name": "cc-loquesea", "meta": {"cwd": str(RAIZ)}})
    if " attach -d -t " not in cmd:
        fallos.append("el attach de una sesion viva no lleva -d: %r" % cmd)

    # 4. El hecho de tmux en que se apoya el `-d`.
    if not shutil.which("tmux"):
        fallos.append("no hay tmux: la mitad de este test no se ha ejecutado")
    else:
        sin_d = clientes_tras_attach(con_d=False)
        con_d = clientes_tras_attach(con_d=True)
        if sin_d != 2:
            fallos.append("sin -d se esperaban 2 clientes y hubo %d" % sin_d)
        if con_d != 1:
            fallos.append("con -d se esperaba 1 cliente y hubo %d" % con_d)

    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("ok: `r` reabre todas las marcadas y el attach las muda con -d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
