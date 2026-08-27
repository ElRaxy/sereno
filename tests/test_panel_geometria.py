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


def _CAJA(ch):
    return "\u2500" <= ch <= "\u257f"


class Pantalla:
    """El doble del terminal. Solo lo que `run()` llama de verdad."""

    def __init__(s, h, w, teclas):
        s.h, s.w, s.teclas = h, w, list(teclas)
        s.celdas, s.solapes, s.fuera, s.fotogramas = {}, [], [], []
        s.fotograma = 0

    # ── lo que se mide ──────────────────────────────────────────────────────
    def addnstr(s, y, x, texto, n, attr=0):
        if not isinstance(texto, str):
            texto = str(texto)
        if y < 0 or x < 0 or y >= s.h or x >= s.w:
            s.fuera.append((s.fotograma, y, x, texto[:20]))
            return
        col = x
        for ch in texto[:max(0, n)]:
            paso = ns["ancho"](ch)
            if col + paso > s.w:
                # curses recorta aqui; que llegue hasta aqui ya es lo que se vigila.
                s.fuera.append((s.fotograma, y, col, texto[:20]))
                break
            previo = s.celdas.get((y, col))
            if (previo is not None and previo != ch
                    and previo.strip() and ch.strip()
                    # El marco si se pisa a proposito: la junta `┬` se dibuja encima de
                    # la linea `─` que ya estaba. Dos caracteres de caja en la misma
                    # celda son un dibujo, no un accidente.
                    and not (_CAJA(previo) and _CAJA(ch))):
                s.solapes.append((s.fotograma, y, col, previo, ch, texto[:30]))
            s.celdas[(y, col)] = ch
            col += paso

    def erase(s):
        # El ultimo fotograma no es el unico que cuenta: un solape puede darse en
        # cualquiera, asi que cada uno se guarda antes de borrarlo.
        if s.celdas:
            s.fotogramas.append(dict(s.celdas))
        s.celdas.clear()
        s.fotograma += 1

    def getmaxyx(s):
        return (s.h, s.w)

    def getch(s):
        return s.teclas.pop(0) if s.teclas else ord("q")

    # ── lo que hay que aceptar y no mide nada ───────────────────────────────
    def __getattr__(s, _n):
        return lambda *a, **k: 0


def espia(real, h, w, teclas, cajon):
    """Un modulo `curses` de mentira, para `sys.modules`.

    `pick_ui()` hace `import curses` DENTRO de la funcion, asi que no basta con tocar
    el espacio de nombres del modulo: lo que resuelve ese import es `sys.modules`.
    Todo lo que no sea `wrapper` se deja pasar al real si es una constante y se
    convierte en un no-op si es una llamada — aqui no se prueba curses, se prueban las
    coordenadas que le pasa el programa.
    """
    class Falso:
        def __getattr__(s, n):
            v = getattr(real, n)
            return v if not callable(v) else (lambda *a, **k: 0)

        def wrapper(s, func, *a, **k):
            pantalla = Pantalla(h, w, list(teclas))
            cajon.append(pantalla)
            return func(pantalla, *a, **k)

    # `COLORS` y `has_colors()` solo existen de verdad tras `start_color()` en un
    # terminal real. Se dan a mano y en su valor mas exigente: con 256 colores el
    # programa pinta la rama larga, que es la que puede descuadrar columnas.
    Falso.COLORS = 256
    Falso.COLOR_PAIRS = 65536
    Falso.has_colors = lambda s: True
    Falso.can_change_color = lambda s: False
    # Las que devuelven tuplas: un 0 en su sitio revienta al desempaquetar.
    Falso.mousemask = lambda s, *a: (1, 0)
    Falso.getmouse = lambda s: (0, 0, 0, 0, 0)
    Falso.pair_content = lambda s, *a: (0, 0)
    Falso.color_content = lambda s, *a: (0, 0, 0)
    f = Falso()
    for cte in dir(real):
        if cte.isupper() or cte == "error":
            try:
                setattr(Falso, cte, getattr(real, cte))
            except Exception:
                pass
    return f


def main():
    import curses as real
    fallos = []
    for h, w in TAMANOS:
        cajon = []
        teclas = [TECLAS["abajo"], TECLAS["abajo"], TECLAS["q"]]
        sys.modules["curses"] = espia(real, h, w, teclas, cajon)
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
