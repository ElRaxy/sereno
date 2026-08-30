#!/usr/bin/env python3
"""Lo tecleado en el cuadro de cerrar se traduce a las filas correctas, o a nada.

`parse_sel` decide que sesiones se van a MATAR, asi que sus dos fallos posibles son
caros y opuestos: entender de menos deja sesiones vivas que el usuario queria cerrar,
y entender de mas cierra una que estaba trabajando. Por eso lo que devuelve distingue
`None` ("no te he entendido, no toco nada") de una lista ("cierra exactamente estas"),
y una palabra que no es atajo NUNCA se adivina.

Ademas vigila el coste: `1-50000000` sobre tres filas daba el resultado correcto
tras 2,8 s y 2,3 GB de RAM, porque materializaba el rango entero antes de recortarlo.
En un equipo de 8 GB eso es la interfaz colgada por un dedo torpe.
"""
import os
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def filas(n, trabajando=True, con_pestana=True):
    return [{"working": trabajando, "attached": con_pestana} for _ in range(n)]


def main():
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ps = ns["parse_sel"]

    fallos = []
    tres = filas(3)

    def caso(texto, filas_, esperado, por_que):
        real = ps(texto, filas_)
        if real != esperado:
            fallos.append("%s: %r dio %r, se esperaba %r" % (por_que, texto, real, esperado))

    # ── lo que se entiende ────────────────────────────────────────────────────
    caso("2", tres, [1], "la cuenta es de uno, no de cero")
    caso("1,3", tres, [0, 2], "lista suelta")
    caso("1-3", tres, [0, 1, 2], "rango")
    caso("3-1", tres, [0, 1, 2], "un rango al reves es el mismo rango")
    caso("1,1,1", tres, [0], "repetir una fila no la cierra tres veces")
    caso("3 1", tres, [0, 2], "el espacio tambien separa, y sale ordenado")
    caso("todas", tres, [0, 1, 2], "atajo de todas")
    caso("*", tres, [0, 1, 2], "el asterisco es todas")

    # ── lo que NO se entiende, que debe ser None y no lista vacia ─────────────
    for texto, por_que in (
        ("xyz", "una palabra que no es atajo no se adivina"),
        ("1,xyz", "un termino malo invalida la seleccion entera"),
        ("", "vacio"),
        ("   ", "solo espacios"),
        ("0", "no hay fila cero"),
        ("9", "fuera de rango"),
        ("5-9", "rango entero fuera de rango"),
    ):
        real = ps(texto, tres)
        if real is not None:
            fallos.append("%s: %r dio %r, se esperaba None" % (por_que, texto, real))

    # `None` y `[]` no son lo mismo y el codigo que llama los trata distinto.
    if ps("xyz", tres) == []:
        fallos.append("una entrada incomprensible se confunde con 'ninguna fila'")

    # ── los atajos por estado, en los dos idiomas ─────────────────────────────
    mezcla = [
        {"working": True, "attached": True},     # 0: trabajando, con pestana
        {"working": False, "attached": True},    # 1: parada, con pestana
        {"working": False, "attached": False},   # 2: parada y suelta
        {"working": None, "attached": True},     # 3: no se pudo observar
    ]
    for texto in ("espera", "esperando", "paradas", "idle", "waiting", "stopped"):
        caso(texto, mezcla, [1, 2], "atajo de paradas (%s)" % texto)
    for texto in ("sueltas", "sin-pestana", "sinpestana", "detached", "loose", "no-tab"):
        caso(texto, mezcla, [2], "atajo de sueltas (%s)" % texto)

    # Lo que no se pudo observar no es "parada": `None` no cuenta como False, o se
    # cerraria una sesion sobre la que no se sabe nada.
    if 3 in (ps("paradas", mezcla) or []):
        fallos.append("una fila con `working` desconocido cuenta como parada y se cerraria")

    # ── el coste, no solo el resultado ────────────────────────────────────────
    # Sin recortar el rango antes de generarlo, esto son 50 millones de enteros en
    # memoria para quedarse con tres. Medido: 2,8 s y 2,3 GB.
    t0 = time.time()
    r = ps("1-50000000", tres)
    tardo = time.time() - t0
    if r != [0, 1, 2]:
        fallos.append("un rango enorme deberia recortarse a las filas que hay, dio %r" % (r,))
    if tardo > 1.0:
        fallos.append("un rango enorme tarda %.1f s: se esta materializando entero "
                      "antes de recortarlo" % tardo)

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: lo tecleado se traduce a las filas correctas, o a None, y sin reventar la RAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
