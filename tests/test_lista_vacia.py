#!/usr/bin/env python3
"""Con la lista filtrada a cero, las teclas de seleccion no tienen a que agarrarse.

Cuando el filtro no casa con nada, la lista no se queda sin filas: se pinta UNA fila de
mentira que dice "(nada coincide)". Es lo que evita dividir por cero al mover el cursor
y lo que da algo que mirar, pero tambien pone al alcance del dedo una fila que no es una
sesion — con el `name` vacio. Marcarla mete una cadena vacia en la seleccion: a partir
de ahi el programa cree que tienes algo marcado, deja de avisarte de que marques, y los
contadores cuentan un fantasma.

La guarda que lo impide descarta las teclas mientras esa fila es lo unico que hay. Y
tiene dos lados, porque descartar de mas es igual de malo:

  · **de menos** — el ESPACIO o la `a` marcan la fila que no es una sesion;
  · **de mas** — se come la `q` y te deja encerrado en una lista sin nada, o se come el
    borrar y no puedes deshacer el filtro que te dejo ahi. La unica salida seria matar
    el proceso.

Romper esa guarda dejaba los 65 tests en verde, que es como se descubrio que le faltaba
red. Se prueba mirando la pantalla, no el estado interno: lo que decide es lo que ve
quien esta delante.
"""
import contextlib
import io
import os
import pathlib
import signal
import sys

os.environ["SERENO_DEMO"] = "1"        # nunca sesiones reales: esto se pinta y se mira
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

SLASH, ENTER, ESPACIO, Q, A, BORRAR = ord("/"), 10, ord(" "), ord("q"), ord("a"), 127
NADA_CASA = [ord(c) for c in "zzzznocasa"]
FILTRO = [SLASH] + NADA_CASA + [ENTER]      # deja la lista en "(nada coincide)"
MARCADA = "▌"                          # la barra de canal de una fila marcada
H, W = 32, 170


class SeColgo(Exception):
    pass


def pinta(teclas, tope=10):
    """Devuelve (lineas de la pantalla final, teclas que no se llegaron a consumir).

    Con reloj, y no por prurito: el doble devuelve `q` cuando se le acaban las teclas,
    asi que un fallo que se coma esa tecla deja el bucle dando vueltas para siempre.
    Sin la alarma eso lo cazaba el TOPE de 300 s del catalogo de mutantes —muere, pero
    tarda cinco minutos, y eso lo pagan doce jobs en cada pull request—. Con ella el
    mismo fallo se cuenta en diez segundos y ademas dice que se colgo, que es un
    diagnostico distinto de "no marco lo que debia".
    """
    import curses as real
    cajon = []
    sys.modules["curses"] = espia(real, H, W, teclas, cajon, ns["ancho"])
    anterior = signal.signal(signal.SIGALRM,
                             lambda *a: (_ for _ in ()).throw(SeColgo()))
    signal.setitimer(signal.ITIMER_REAL, tope)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](ns["sesiones_demo"]())
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, anterior)
        sys.modules["curses"] = real
    p = cajon[0]
    celdas = p.celdas or p.fotogramas[-1]
    lineas = ["".join(celdas.get((y, x), " ") for x in range(W)).rstrip()
              for y in range(H)]
    return lineas, len(p.teclas)


def main():
    fallos = []

    # ── control positivo: en una lista normal, ESPACIO SI marca ───────────────
    # Sin esto, todo lo de abajo pasaria igual si el ESPACIO no marcara nunca nada.
    normal, _ = pinta([ESPACIO, Q])
    if not any(MARCADA in l for l in normal):
        print("FALLA: el control positivo no marca — este test no esta midiendo nada")
        return 1

    # ── de menos: la fila que no es una sesion no se puede marcar ─────────────
    for teclas, que in ((FILTRO + [ESPACIO, Q], "ESPACIO"),
                        (FILTRO + [A, Q], "`a` (marcar todas)")):
        pantalla, _ = pinta(teclas)
        if not any("nada coincide" in l for l in pantalla):
            fallos.append("%s: el caso no llego a dejar la lista vacia" % que)
        elif any(MARCADA in l for l in pantalla):
            fallos.append("%s marca la fila de '(nada coincide)': la seleccion se queda "
                          "con una cadena vacia dentro" % que)

    # ── de mas: salir y deshacer el filtro siguen funcionando ─────────────────
    # Si la guarda se come la `q`, las teclas que van detras se consumen tambien y el
    # bucle no vuelve nunca: el doble sigue dandole `q` y se las sigue comiendo.
    try:
        _, sin_consumir = pinta(FILTRO + [Q, ESPACIO, ESPACIO])
        if sin_consumir != 2:
            fallos.append("con la lista vacia, `q` no sale del selector: se quedaron %d "
                          "teclas sin consumir en vez de 2" % sin_consumir)
    except SeColgo:
        fallos.append("con la lista vacia, `q` no sale del selector y el bucle no "
                      "vuelve: la unica salida seria matar el proceso")

    pantalla, _ = pinta(FILTRO + [BORRAR, Q])
    if any("nada coincide" in l for l in pantalla):
        fallos.append("con la lista vacia, borrar no deshace el filtro: no hay forma de "
                      "volver a ver las sesiones")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: la fila de '(nada coincide)' no se marca, y salir y borrar siguen vivos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
