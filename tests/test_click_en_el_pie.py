#!/usr/bin/env python3
"""Pinchar una pastilla del pie hace lo que hace su tecla, en la interfaz de verdad.

`test_zonas_del_pie.py` prueba las dos piezas puras: donde cae cada pastilla y como se
resuelve un punto contra la tabla. Lo que no puede ver es el **cableado** — que lo que
`pastillas_pie` calcula sea lo mismo que se pinta, que sus zonas acaben en la tabla, y
que el codigo que devuelve `zona_en` se ejecute como si lo hubieras tecleado. Las tres
cosas se rompen sin que ningun test puro se entere: la pieza sigue en verde y el boton
deja de funcionar.

Asi que aqui se abre un pseudo-terminal, se arranca el programa y se le escribe un click
SGR como lo escribiria el terminal — sobre la pastilla `? help`, que abre un cuadro que
se ve desde fuera y no toca ninguna sesion.

Y con su reverso: un click en el HUECO entre dos pastillas no puede abrir nada. Sin ese
caso, unas zonas que cubrieran toda la fila pasarian igual, que es justo el fallo que
`- 1` por `+ 1` produce.

La fila del pie depende del alto util, asi que se barren las tres ultimas en vez de
calcularla aqui: un test que repite la aritmetica del programa no prueba la aritmetica
del programa.
"""
import os
import pathlib
import pty
import re
import select
import signal
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
H, W = 30, 150
FILAS_DEL_PIE = (27, 28, 29)           # 1-based, como las manda el terminal
COL_AYUDA = 46                         # dentro de ` ? help `, que a 150 va de la 41 a la 48
# El hueco va a la DERECHA de la pastilla de la ayuda, no a la izquierda: si se busca
# el de antes, ampliar las zonas lo tapa la pastilla ` x close `, que abre otra cosa, y
# el caso pasa en verde sin haber comprobado nada. A la derecha lo tapa la de la ayuda,
# que es la que este test sabe ver.
COL_HUECO = 50                         # entre ` ? help ` (acaba en la 48) y ` / filter `
# Palabras que solo salen con el cuadro de ayuda abierto, en ingles.
DE_LA_AYUDA = ("wheel", "mouse", "keys")


def click(col, fila):
    """Pulsar y soltar el boton izquierdo. SGR cuenta desde uno."""
    return ("\x1b[<0;%d;%dM\x1b[<0;%d;%dm" % (col, fila, col, fila)).encode()


def corre(teclas, tope=25):
    entorno = dict(os.environ, SERENO_DEMO="1", SERENO_LANG="en",
                   TERM="xterm-256color", SERENO_DEBUG="1",
                   SERENO_TMUX_SOCK="no-existe", LINES=str(H), COLUMNS=str(W))
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(sys.executable, [sys.executable, str(RAIZ / "sereno")], entorno)
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", H, W, 0, 0))
    except Exception:
        pass
    salida, t0, fin, pend = b"", time.time(), time.time() + tope, list(teclas)
    vivo = True
    while time.time() < fin:
        r, _, _ = select.select([fd], [], [], 0.25)
        if r:
            try:
                trozo = os.read(fd, 65536)
            except OSError:
                break
            if not trozo:
                break
            salida += trozo
        pasado = time.time() - t0
        while pend and pasado > pend[0][0]:
            _, k = pend.pop(0)
            os.write(fd, k)
        hijo, _st = os.waitpid(pid, os.WNOHANG)
        if hijo:
            vivo = False
            break
    if vivo:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
    texto = salida.decode("utf-8", "replace")
    return texto, re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto).lower()


def abre_ayuda(col):
    """¿Pinchar esa columna abre el cuadro de ayuda en alguna de las filas del pie?"""
    for fila in FILAS_DEL_PIE:
        crudo, limpio = corre([(5, click(col, fila)), (8, b"q"), (11, b"q")])
        if "Traceback" in crudo:
            return None, "el programa revento:\n" + crudo[crudo.find("Traceback"):][:700]
        if any(p in limpio for p in DE_LA_AYUDA):
            return fila, None
    return False, None


def main():
    fallos = []

    fila, revento = abre_ayuda(COL_AYUDA)
    if revento:
        fallos.append(revento)
    elif fila is False:
        fallos.append("pinchar la pastilla ` ? help ` no abre la ayuda en ninguna de las "
                      "filas del pie: lo que se pinta y lo que se puede pinchar no "
                      "coinciden, o el codigo de la zona no se ejecuta")

    hueco, revento = abre_ayuda(COL_HUECO)
    if revento:
        fallos.append(revento)
    elif hueco is not False:
        fallos.append("pinchar el hueco ENTRE dos pastillas (columna %d, fila %s) abre "
                      "la ayuda: las zonas se estan comiendo la separacion"
                      % (COL_HUECO, hueco))

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: la pastilla del pie se pincha y hace lo suyo, y el hueco de al lado no")
    return 0


if __name__ == "__main__":
    sys.exit(main())
