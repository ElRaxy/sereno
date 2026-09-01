#!/usr/bin/env python3
"""Lo que el programa ve de tmux: la lista de sesiones, y la guarda de antes de pedirla.

`tmux_list` es la unica fuente de las sesiones VIVAS. Si devuelve una lista vacia el
selector no ensena ninguna, y eso no se lee como un fallo: se lee como "hoy no tienes
nada abierto". Un fallo mudo con la forma de una respuesta razonable.

Lo que no tenia test es lo que hace con la respuesta: **el parseo de `list-panes`**.
`test_tmux_de_verdad` levanta un servidor y comprueba que se ABREN ventanas, que es el
otro camino; nadie miraba que la lista se lea bien. (La guarda de una linea que lleva
delante —si el binario no esta, ni se intenta— si tiene red alli: invertirla lo pone
rojo. Aqui se cubre igual, y a los dos les viene bien.)

Se le inyecta la salida en vez de levantar un servidor: lo que se prueba es el parseo,
no tmux. Y va con la salida real de la maquina, que es la que trae las trampas — un
panel sin titulo propio se queda con el hostname, y un `.local` no identifica ninguna
sesion.
"""
import pathlib
import sys
import types

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# session_name, session_created, session_attached, pane_title, pane_pid
SALIDA = (
    "claude-strev\t1756600000\t1\tArreglar el panel\t4321\n"
    "claude-web\t1756600100\t0\tmac-de-alex.local\t4322\n"     # titulo generico
    "claude-web\t1756600100\t0\totro panel de la misma\t9999\n"  # 2o panel: se ignora
    "claude-api\t1756600200\t0\t✳ Con adorno delante\t4323\n"
    "linea rota sin columnas\n"
)


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    fallos = []

    class Sub:
        """Un `subprocess` que devuelve lo que se le diga, y apunta si le llamaron."""

        def __init__(s, stdout="", rc=0, revienta=False):
            s.stdout, s.rc, s.revienta, s.veces = stdout, rc, revienta, 0

        def run(s, *a, **k):
            s.veces += 1
            if s.revienta:
                raise OSError("aqui no hay tmux")
            return types.SimpleNamespace(stdout=s.stdout, returncode=s.rc)

    def con(binario, **kw):
        ns["TMUX_BIN"] = binario
        sub = Sub(**kw)
        ns["subprocess"] = sub
        return sub

    # ── la lista, con el binario donde tiene que estar ────────────────────────
    # `sys.executable` existe seguro y en cualquier sistema: lo que importa de esa ruta
    # es que exista, porque a quien se llama es al doble.
    sub = con(sys.executable, stdout=SALIDA)
    filas = ns["tmux_list"]()

    if not filas:
        fallos.append("con el binario en su sitio y tmux respondiendo, no devuelve nada")
    nombres = [f[0] for f in filas]
    if nombres != ["claude-strev", "claude-web", "claude-api"]:
        fallos.append("las sesiones salen mal: %r" % (nombres,))
    if sub.veces != 1:
        fallos.append("se llama a tmux %d veces para una lista" % sub.veces)

    por_nombre = {f[0]: f for f in filas}
    if por_nombre.get("claude-strev", ("",))[3] != "Arreglar el panel":
        fallos.append("se pierde el titulo del panel: %r" % (por_nombre.get("claude-strev"),))
    if por_nombre.get("claude-web", (None,) * 4)[3] != "":
        fallos.append("un panel que aun no tiene titulo se queda con el hostname: %r"
                      % (por_nombre.get("claude-web", (None,) * 4)[3],))
    if por_nombre.get("claude-api", (None,) * 4)[3] != "Con adorno delante":
        fallos.append("el adorno del principio del titulo no se quita: %r"
                      % (por_nombre.get("claude-api", (None,) * 4)[3],))
    if por_nombre.get("claude-strev", (None, None, None, None))[2] is not True:
        fallos.append("no se distingue una sesion enganchada de una suelta")
    if por_nombre.get("claude-strev", (None,) * 5)[4] != "4321":
        fallos.append("se pierde el pid del panel")

    # ── la guarda: sin binario no se pregunta ────────────────────────────────
    sub = con(str(RAIZ / "no-existe-este-binario"), stdout=SALIDA)
    if ns["tmux_list"]() != []:
        fallos.append("sin el binario de tmux devuelve sesiones: se esta preguntando "
                      "igual, o inventandoselas")
    if sub.veces:
        fallos.append("sin el binario de tmux se llama igual al proceso: la guarda no "
                      "esta guardando nada")

    # ── y lo que sale mal por debajo no puede tumbar el programa ─────────────
    # Con salida Y codigo de error a la vez, que es el caso que distingue: tmux escribe
    # en stdout aunque acabe mal, asi que un test con la salida vacia da lista vacia
    # por las dos razones y no prueba nada. Con esto, si se deja de mirar el codigo de
    # error, el programa se cree las sesiones de una llamada que fallo.
    con(sys.executable, stdout=SALIDA, rc=1)
    if ns["tmux_list"]() != []:
        fallos.append("una llamada a tmux que devolvio error se toma por buena y sus "
                      "sesiones acaban en la lista")
    con(sys.executable, revienta=True)
    if ns["tmux_list"]() != []:
        fallos.append("si el proceso revienta deberia dar lista vacia, no propagar")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: las sesiones de tmux se leen enteras, y sin tmux ni se pregunta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
