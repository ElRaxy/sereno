#!/usr/bin/env python3
"""Un click en una pastilla del pie ejecuta SU tecla, y no la de al lado.

Las pastillas de abajo (`ENTER abrir`, `x cerrar`, `q salir`…) no son texto: son
botones, se pinchan y hacen lo que su tecla. Cada una apunta una zona clicable en una
tabla, y `zona_en` traduce despues "donde has pinchado" a "que has pinchado".

El fallo que persigue esto no da error ni se ve en la pantalla: **dos zonas que se
solapan**. La ultima columna de una pastilla se calcula restando uno; sumarlo la mete
dos columnas dentro de la vecina, todo se sigue pintando igual, y un click en ese borde
ejecuta la tecla de al lado. Entre esas teclas esta cerrar sesiones.

Hasta la 1.37.0 no habia forma de probarlo: la tabla de zonas vivia dentro de `pick_ui`
y no se podia mirar desde fuera. Medido, ademas: cambiar ese `- 1` por un `+ 1` pasaba
los 66 tests en verde.

`zona_en` se prueba aparte y con una tabla escrita a mano, porque es la otra mitad —
unas zonas perfectas con un resolutor que se equivoca de fila dan el mismo click en el
sitio que no era.
"""
import os
import pathlib
import sys

os.environ["SERENO_LANG"] = "en"       # las etiquetas cambian de ancho con el idioma
os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
RAIZ = pathlib.Path(__file__).resolve().parent.parent

ANCHOS = (200, 150, 120, 80, 60, 40, 30, 20, 12, 8, 4)


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    pastillas_pie, zona_en, ancho = ns["pastillas_pie"], ns["zona_en"], ns["ancho"]
    fallos = []

    for w in ANCHOS:
        ps = pastillas_pie(w)

        # ── ninguna pisa a la siguiente ───────────────────────────────────────
        for (t1, _x1, _c1, a1, b1), (t2, _x2, _c2, a2, _b2) in zip(ps, ps[1:]):
            if a2 <= b1:
                fallos.append("w=%d: la zona de %r acaba en la columna %d y la de %r "
                              "empieza en la %d: un click ahi ejecuta la tecla que no es"
                              % (w, t1, b1, t2, a2))
            elif a2 <= b1 + 1:
                # Pegadas no se pisan, pero dejan de leerse como botones: el fondo de
                # una entra en el de la siguiente y el pie parece una barra continua.
                # La separacion es parte del dibujo, no un margen que sobre.
                fallos.append("w=%d: %r y %r se pintan pegadas (%d y %d): el pie deja "
                              "de leerse como botones" % (w, t1, t2, b1, a2))

        # ── cada una cubre exactamente lo que ocupa, ni una columna de mas ────
        for tecla, txt, _cod, a, b in ps:
            pintado = ancho(" %s %s " % (tecla, txt))
            if b - a + 1 != pintado:
                fallos.append("w=%d: %r se pinta en %d columnas y su zona mide %d"
                              % (w, tecla, pintado, b - a + 1))
            if b >= w - 1:
                fallos.append("w=%d: la zona de %r llega a la columna %d y la pantalla "
                              "acaba en la %d" % (w, tecla, b, w - 1))

        # ── y un click en CUALQUIER columna suya devuelve su tecla ───────────
        zonas = [(9, a, b, "tecla", cod) for _t, _x, cod, a, b in ps]
        for tecla, _txt, cod, a, b in ps:
            for mx in (a, (a + b) // 2, b):
                golpe = zona_en(zonas, mx, 9)
                if golpe is None:
                    fallos.append("w=%d: la columna %d de %r no cae en ninguna zona"
                                  % (w, mx, tecla))
                elif golpe[4] != cod:
                    fallos.append("w=%d: pinchar la columna %d de %r ejecuta la tecla %r"
                                  % (w, mx, tecla, chr(golpe[4]) if golpe[4] > 31 else golpe[4]))

    # ── caben las que caben, y en el orden que importa ───────────────────────
    if [p[2] for p in pastillas_pie(200)] != [10, 32, ord("x"), ord("?"), ord("/"),
                                              ord("s"), 9, ord("q")]:
        fallos.append("con sitio de sobra no salen las ocho en su orden: %r"
                      % ([p[0] for p in pastillas_pie(200)],))
    if len(pastillas_pie(80)) < 5:
        fallos.append("a 80 columnas —media flota— salen %d pastillas y tienen que "
                      "caber cinco: la de ayuda es la puerta al resto de teclas"
                      % len(pastillas_pie(80)))
    anchas = [len(pastillas_pie(w)) for w in (200, 150, 120, 80, 60, 40, 20)]
    if anchas != sorted(anchas, reverse=True):
        fallos.append("al estrechar la ventana no salen menos pastillas: %r" % (anchas,))
    if pastillas_pie(4):
        fallos.append("en una ventana de 4 columnas se pinta algo: %r" % (pastillas_pie(4),))

    # ── el resolutor, con una tabla escrita a mano ───────────────────────────
    tabla = [(9, 2, 10, "tecla", 10), (9, 13, 22, "tecla", 32),
             (3, 0, 2, "marca", 7), (3, 3, 40, "fila", 7)]
    casos = [((5, 9), 10, "dentro de la primera"),
             ((2, 9), 10, "en su primera columna"),
             ((10, 9), 10, "en su ultima columna"),
             ((13, 9), 32, "en la primera de la siguiente"),
             ((11, 9), None, "en el hueco entre las dos"),
             ((5, 8), None, "la fila de arriba"),
             ((5, 10), None, "la fila de abajo"),
             ((99, 9), None, "pasada la ultima")]
    for (mx, my), esperado, por_que in casos:
        golpe = zona_en(tabla, mx, my)
        dado = golpe[4] if golpe else None
        if dado != esperado:
            fallos.append("zona_en(%d,%d) — %s: dio %r, se esperaba %r"
                          % (mx, my, por_que, dado, esperado))
    # Con dos zonas que se pisan gana la de antes, que es la que se pinto encima.
    if zona_en([(1, 0, 9, "a", "primera"), (1, 5, 9, "b", "segunda")], 7, 1)[4] != "primera":
        fallos.append("con dos zonas solapadas no gana la que se anadio antes")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: las pastillas no se pisan en %d anchos, y el click cae donde se ve"
          % len(ANCHOS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
