#!/usr/bin/env python3
"""Medir texto en COLUMNAS y no en caracteres, que es de lo que va una tabla.

Todo el pintado descansa en tres funciones —`ancho`, `recorta`, `rellena`— y en una
propiedad que ninguna dice en voz alta: **lo recortado a N columnas nunca puede medir
mas de N**. Si falla una sola vez, la fila se sale de la ventana; y curses no avisa
cuando eso pasa, se pierde el texto y ya.

`len()` no vale porque un ideograma o un emoji ocupan dos columnas. Eso ya estaba
resuelto con `east_asian_width`, pero se le escapaba una familia entera: los emoji que
se forman con el selector de variacion U+FE0F. `⚠` es 'N' —una columna— y
`⚠️` se pinta a dos, asi que cada ⚠️ ❤️ ▶️ ☑️ de un titulo desplazaba la fila
una columna a la derecha.

Aviso de alcance: eso NO se observo en esta maquina. Se busco en sus 605 titulos y en
las primeras 60 lineas de 250 transcripts y no aparece ni uno. Se arregla igual, porque
los titulos los escribe el CLI con lo que diga cada cual y esto lo instala gente que no
conocemos.
"""
import pathlib
import random
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Un alfabeto con todo lo que descuadra una tabla: ancho doble, combinantes, invisibles
# y los emoji de dos piezas.
ALFABETO = ["a", "b", "X", " ", "-", "ñ", "á",
            "日", "本",                      # CJK, dos columnas
            "\U0001f600", "✨",                  # emoji 'W'
            "́", "​",                       # combinante y ancho cero
            "⚠️", "❤️",           # emoji con selector
            "…", "·"]


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ancho, recorta, rellena = ns["ancho"], ns["recorta"], ns["rellena"]
    fallos = []

    def comprueba(que, cond, extra=""):
        if not cond:
            fallos.append(que + (": " + extra if extra else ""))

    # ── control positivo: en ASCII, columnas y caracteres son lo mismo ───────
    # Sin esto, una funcion que devolviera 0 siempre pasaria todas las cotas de abajo.
    if ancho("hola mundo") != 10:
        print("FALLO: ancho('hola mundo') = %r, y en ASCII tiene que ser 10"
              % ancho("hola mundo"))
        return 1

    # ── lo que mide dos columnas ────────────────────────────────────────────
    comprueba("un ideograma no mide dos columnas", ancho("日") == 2)
    comprueba("un emoji no mide dos columnas", ancho("\U0001f600") == 2)
    # El selector de variacion: la pieza que faltaba.
    for base, nombre in (("⚠", "aviso"), ("❤", "corazon"),
                         ("▶", "play"), ("☑", "casilla")):
        comprueba("%s + selector de variacion no mide dos columnas" % nombre,
                  ancho(base + "️") == 2,
                  "mide %d" % ancho(base + "️"))
    comprueba("el selector de variacion suelto no mide cero",
              ancho("️") == 0)

    # ── lo que no ocupa nada ────────────────────────────────────────────────
    comprueba("una tilde combinante ocupa columna", ancho("é") == 1)
    comprueba("un espacio de ancho cero ocupa columna", ancho("​") == 0)

    # ── LA propiedad: lo recortado cabe. Sobre un corpus, no sobre un caso ──
    random.seed(11)
    corpus = ["", " ", "hola", "⚠️ deploy", "日本語",
              "\U0001f600\U0001f600\U0001f600"]
    for _ in range(3000):
        corpus.append("".join(random.choice(ALFABETO)
                              for _ in range(random.randint(0, 24))))
    malos = anchos_mal = 0
    for s in corpus:
        for cols in (1, 2, 3, 5, 12, 30, 44):
            r = recorta(s, cols)
            if ancho(r) > cols:
                malos += 1
                if malos <= 3:
                    fallos.append("recorta(%r, %d) mide %d columnas"
                                  % (s, cols, ancho(r)))
            p = rellena(s, cols)
            if ancho(p) != max(cols, ancho(s)):
                anchos_mal += 1
                if anchos_mal <= 3:
                    fallos.append("rellena(%r, %d) mide %d y deberia medir %d"
                                  % (s, cols, ancho(p), max(cols, ancho(s))))
    comprueba("hay %d recortes que se salen del ancho pedido" % malos, malos == 0)
    comprueba("hay %d rellenos con el ancho equivocado" % anchos_mal, anchos_mal == 0)

    # ── recortar no puede alargar, y lo que ya cabe se queda igual ──────────
    comprueba("un texto que ya cabe se toca al recortarlo",
              recorta("hola", 10) == "hola")
    comprueba("recortar no deja marca de que se corto",
              recorta("hola mundo entero", 8).endswith("…"))

    for f in fallos:
        print("FALLO:", f)
    print("ok: %d cadenas por 7 anchos, y lo recortado siempre cabe" % len(corpus)
          if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
