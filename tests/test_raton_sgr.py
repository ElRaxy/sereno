#!/usr/bin/env python3
"""El raton del terminal se entiende a mano, porque el ncurses de macOS no lo entiende.

El que trae macOS es el 6.0 de 2015 y solo conoce el protocolo x11 (`kmous=\\E[M`): un
evento SGR le llega como teclas sueltas —27, 91, 60, 48…— y se pierde entero. El
terminal SI habla SGR, asi que el programa lo pide (`\\033[?1006h`) y lo parsea el.

Se pide SGR y no el viejo por una razon que se ve en pantalla: el protocolo x11 mete la
columna en UN byte y muere en la 223, asi que en una ventana ancha los clicks del panel
derecho llegan a otra parte. Por eso el caso de la columna 120 esta aqui.

Lo que se prueba es que **lo que no es un evento no se inventa**. Esta funcion corre
detras de un ESC, y un ESC es tambien la tecla que cierra un dialogo: si se traga la
tecla siguiente creyendo que era un raton, la interfaz se come pulsaciones; si devuelve
coordenadas de una secuencia a medias, el click cae en la fila equivocada — y en la
lista de sesiones la fila equivocada es la sesion equivocada.

`ungetch` y `espera` entran por parametro. `curses.ungetch` exige un `initscr()` previo,
asi que con la funcion llamandolo por su cuenta este test no podria existir sin arrancar
una interfaz de verdad.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


class Ventana:
    """Lo unico que `leer_sgr` le pide a una ventana de curses."""

    def __init__(s, teclas):
        s.teclas, s.timeouts = list(teclas), []

    def getch(s):
        return s.teclas.pop(0) if s.teclas else -1       # -1 es "no hay nada"

    def timeout(s, v):
        s.timeouts.append(v)


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    leer_sgr = ns["leer_sgr"]
    fallos, ESPERA = [], 2500

    def leer(texto, restaurar=None):
        """Devuelve (lo entendido, lo devuelto al buffer, los timeouts pedidos)."""
        devueltas, win = [], Ventana(ord(c) for c in texto)
        return leer_sgr(win, devueltas.append, ESPERA, restaurar), devueltas, win.timeouts

    def caso(texto, esperado, por_que):
        real = leer(texto)[0]
        if real != esperado:
            fallos.append("%s: %r dio %r, se esperaba %r" % (por_que, texto, real, esperado))

    # ── lo que SI es un evento ────────────────────────────────────────────────
    # `CSI < boton ; columna ; fila M`, y las coordenadas llegan contando desde uno.
    caso("[<0;10;5M", (0, 9, 4, True), "boton izquierdo pulsado")
    caso("[<0;10;5m", (0, 9, 4, False), "la `m` minuscula es soltar")
    caso("[<64;1;1M", (64, 0, 0, True), "la rueda es el bit 64, y la esquina es (0,0)")
    caso("[<32;3;7M", (32, 2, 6, True), "arrastrar es el bit 32")
    # La columna 120 pasa de 223 en el protocolo viejo con solo doblar la ventana: es
    # justo el caso que obliga a pedir SGR.
    caso("[<0;240;30M", (0, 239, 29, True), "una columna que el protocolo viejo no sabe decir")

    # ── lo que NO es un evento, y ademas no puede comerse la tecla ────────────
    for texto, por_que in (("[X", "el segundo caracter no es `<`"),
                           ("[<0;10M", "faltan campos: solo dos"),
                           ("[<0;10;5;9M", "sobran campos: cuatro"),
                           ("[<0;a;5M", "un campo que no es un numero"),
                           ("[<0;10;5X", "no termina en M ni en m"),
                           ("[<;;M", "los tres campos vacios"),
                           ("", "no hay nada que leer"),
                           ("[<" + "9" * 30 + ";1;1M", "un numero interminable")):
        real = leer(texto)[0]
        if real is not None:
            fallos.append("%s: %r dio %r, se esperaba None" % (por_que, texto, real))

    # Un numero interminable no puede dejar la interfaz leyendo: el bucle esta acotado
    # y por eso el caso de arriba corta. Sin el tope, un terminal que escupe basura
    # cuelga el selector en vez de descartar el evento.

    # ── la tecla que no era del raton vuelve al buffer ────────────────────────
    r, devueltas, _ = leer("x")
    if r is not None or devueltas != [ord("x")]:
        fallos.append("una tecla que no abre un evento tiene que volver al buffer: "
                      "dio %r y devolvio %r" % (r, devueltas))
    # Detras de un ESC solo, no hay nada que devolver — y devolver un -1 seria meter
    # una tecla inexistente en la cola.
    r, devueltas, _ = leer("")
    if devueltas:
        fallos.append("sin tecla que leer se devuelve %r al buffer" % (devueltas,))

    # ── el tiempo de espera queda como estaba ────────────────────────────────
    # La secuencia viaja de una pieza, asi que se baja a 30 ms para leerla. Si no se
    # restaura, la lista se queda repintandose cada 30 ms para siempre.
    for texto, que in (("[<0;10;5M", "un evento entero"), ("x", "una tecla cualquiera"),
                       ("[<0;a;5M", "una secuencia rota")):
        _, _, timeouts = leer(texto)
        if timeouts[:1] != [30]:
            fallos.append("%s: no se baja la espera para leer la secuencia (%r)"
                          % (que, timeouts))
        if timeouts[-1:] != [ESPERA]:
            fallos.append("%s: la espera no vuelve a lo que era, queda en %r"
                          % (que, timeouts[-1:]))
    # Y cuando el que llama pide otra espera de vuelta, manda la suya: es lo que usa el
    # camino de los dialogos, que esperan indefinidamente en vez de refrescar solos.
    _, _, timeouts = leer("[<0;1;1M", -1)
    if timeouts[-1:] != [-1]:
        fallos.append("`restaurar` no manda sobre la espera de la lista: %r" % (timeouts,))

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: el evento del raton se entiende, y lo que no es un evento no se inventa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
