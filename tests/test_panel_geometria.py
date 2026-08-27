#!/usr/bin/env python3
"""Ninguna celda del panel se pinta dos veces con cosas distintas, y nada sale del marco.

Esto no se puede comprobar mirando un volcado del terminal, y ese fue el problema: curses
manda diffs, asi que un pty leido a pelo mezcla dos fotogramas y ensena solapes que no
existen (y esconde los que si). Este repo ya se comio dos bugs fantasma nacidos de un
volcado sucio.

Asi que el terminal se sustituye por un doble que apunta cada escritura en una matriz.
El veredicto lo compone el codigo a partir de esas celdas: escribir un caracter visible
encima de otro distinto es un solape, y escribir fuera de (h, w) es desbordar. En curses
lo segundo no da error — envuelve el sobrante al principio de la fila siguiente, y el
caracter huerfano aparece lejos de la linea que lo causo.
"""
import contextlib, io, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

os.environ["SERENO_DEMO"] = "1"
# Sin esto `pick_ui` se traga cualquier error de pintado y el test veria una pantalla
# vacia sin saber por que.
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

TAMANOS = ((30, 150), (34, 190), (24, 112), (28, 108))
TECLAS = {"abajo": 258, "q": ord("q")}      # curses.KEY_DOWN


def main():
    import curses as real
    fallos = []
    for h, w in TAMANOS:
        cajon = []
        teclas = [TECLAS["abajo"], TECLAS["abajo"], TECLAS["q"]]
        sys.modules["curses"] = espia(real, h, w, teclas, cajon, ns["ancho"])
        try:
            # El programa escribe a mano las secuencias del raton (1006/1003) fuera de
            # curses. En un terminal de verdad no se ven; aqui saldrian crudas en el
            # log del CI.
            with contextlib.redirect_stdout(io.StringIO()):
                ns["pick_ui"](ns["sesiones_demo"]())
        except Exception as e:
            fallos.append(f"[{w}x{h}] el panel revento: {type(e).__name__}: {e}")
        finally:
            sys.modules["curses"] = real
        if not cajon:
            fallos.append(f"[{w}x{h}] no se llego a pintar")
            continue
        p = cajon[0]
        vistos = set()
        for _f, y, x, prev, ch, txt in p.solapes:
            if (y, x, prev, ch) in vistos or len(vistos) >= 5:
                continue                    # el mismo solape en tres fotogramas es uno
            vistos.add((y, x, prev, ch))
            fallos.append(f"[{w}x{h}] fila {y} col {x}: {ch!r} pisa {prev!r} ({txt!r})")
        for _f, y, x, txt in p.fuera[:5]:
            fallos.append(f"[{w}x{h}] se sale del marco en {y},{x}: {txt!r}")
        if not (p.celdas or p.fotogramas):
            fallos.append(f"[{w}x{h}] no pinto ni una celda")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: el panel no se pisa ni se sale en {len(TAMANOS)} tamanos"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
