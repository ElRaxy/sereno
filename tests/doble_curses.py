#!/usr/bin/env python3
"""Un terminal de mentira que apunta cada escritura en una matriz de celdas.

Vive aparte porque lo usan dos tests que miran cosas distintas de la misma pantalla:
`test_panel_geometria.py` mira las COORDENADAS (nada se pisa, nada se sale) y
`test_orden_en_pantalla.py` mira el CONTENIDO (que la tecla cambia el orden que se
pinta). Duplicarlo era garantizar que se arreglara en uno solo.

No es un emulador de terminal: no interpreta secuencias de escape ni sabe de diffs. Es
justo lo que `run()` llama, y el veredicto lo compone quien lo usa a partir de las
celdas.
"""
import sys


def _CAJA(ch):
    return "\u2500" <= ch <= "\u257f"


class Pantalla:
    """El doble del terminal. Solo lo que `run()` llama de verdad."""

    def __init__(s, h, w, teclas, ancho):
        # `ancho` es la funcion del programa, no `len`: un glifo de ancho doble ocupa
        # dos celdas y contarlo como una descuadra la matriz entera y con ella el
        # veredicto. Se pasa desde fuera para que este fichero no tenga que cargar
        # `sereno` por su cuenta.
        s.h, s.w, s.teclas, s.ancho = h, w, list(teclas), ancho
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
            paso = s.ancho(ch)
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


def espia(real, h, w, teclas, cajon, ancho):
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
            pantalla = Pantalla(h, w, list(teclas), ancho)
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
