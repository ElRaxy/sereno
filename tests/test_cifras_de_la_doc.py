#!/usr/bin/env python3
"""Los numeros que la documentacion afirma sobre si misma son los de verdad.

Existe porque ya fallo dos veces en el mismo dia: el README anunciaba veintitres tests
cuando habia cuarenta y ocho, y el catalogo de mutantes veinte cuando eran veintiuno.
Nadie miente a proposito — la cifra se escribe una vez y el siguiente test que se anade
la deja atras, y encima esta escrita con letras, donde no la ve ningun grep.

Es la cifra que comprueba en treinta segundos alguien que se plantea contribuir. Que no
cuadre no rompe el programa; rompe la confianza en todo lo demas que dice el fichero.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

UNIDADES_EN = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
               "six": 6, "seven": 7, "eight": 8, "nine": 9}
DECENAS_EN = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
              "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
              "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
              "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
# Del diez al diecinueve llegaron con "ciento diez": hasta entonces el castellano
# empezaba a contar en el veinte, y "ciento diez" no se podia leer aunque "ciento
# nueve" si. Es la misma laguna que tapo "cien" al cruzar los 99, un escalon mas
# arriba.
DECENAS_ES = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
              "quince": 15, "dieciseis": 16, "dieciséis": 16, "diecisiete": 17,
              "dieciocho": 18, "diecinueve": 19,
              "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
              "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
UNIDADES_ES = {"uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
               "seis": 6, "siete": 7, "ocho": 8, "nueve": 9}
VEINTIS = {"veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintidós": 22,
           "veintitres": 23, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25,
           "veintiseis": 26, "veintiséis": 26, "veintisiete": 27, "veintiocho": 28,
           "veintinueve": 29}


def a_numero(txt):
    """"forty-eight" -> 48, "cuarenta y ocho" -> 48, "cien" -> 100. None si no cuela.

    Las centenas llegaron el dia que el catalogo de mutantes paso de 99: hasta entonces
    "cien" no era un numero que este test supiera leer, y la doc quedaba sin vigilante
    justo al cruzar la cifra redonda.
    """
    t = " ".join(txt.strip().lower().split())
    if t in ("cien", "one hundred", "a hundred"):
        return 100
    for cabeza, largo in (("ciento ", 100), ("one hundred and ", 100),
                          ("a hundred and ", 100), ("one hundred ", 100)):
        if t.startswith(cabeza):
            resto = a_numero(t[len(cabeza):])
            return None if resto is None else largo + resto
    if t in VEINTIS:
        return VEINTIS[t]
    if t in UNIDADES_ES:
        return UNIDADES_ES[t]
    if t in UNIDADES_EN:
        return UNIDADES_EN[t]
    if t in DECENAS_EN:
        return DECENAS_EN[t]
    if t in DECENAS_ES:
        return DECENAS_ES[t]
    if "-" in t:                                  # forty-eight
        d, _, u = t.partition("-")
        if d in DECENAS_EN and u in UNIDADES_EN:
            return DECENAS_EN[d] + UNIDADES_EN[u]
    m = re.fullmatch(r"(\w+) y (\w+)", t)         # cuarenta y ocho
    if m and m.group(1) in DECENAS_ES and m.group(2) in UNIDADES_ES:
        return DECENAS_ES[m.group(1)] + UNIDADES_ES[m.group(2)]
    return None


# (fichero · regex con UN grupo que captura el numero en letras · que cuenta · por que)
AFIRMACIONES = [
    ("README.md", r"There are ([\w-]+)\b", "tests",
     "el README ingles anuncia cuantos tests hay"),
    ("README.es.md", r"Hoy son ((?:\w+ y \w+|\w+))\b", "tests",
     "el README castellano anuncia cuantos tests hay"),
    ("CONTRIBUTING.md", r"\b([\w-]+) tests,", "tests",
     "CONTRIBUTING anuncia cuantos tests hay"),
    ("README.md", r"breaks ([\w -]+?) real guards", "mutantes",
     "el README ingles anuncia cuantos mutantes rompe el catalogo"),
    ("README.es.md", r"rompe ((?:\w+ y \w+|\w+ \w+|\w+)) guardas", "mutantes",
     "el README castellano anuncia cuantos mutantes rompe el catalogo"),
    ("CONTRIBUTING.md", r"breaks ([\w -]+?) real guards", "mutantes",
     "CONTRIBUTING anuncia cuantos mutantes rompe el catalogo"),
    ("CONTRIBUTING.md", r"tests, ([\w -]+?) mutants", "mutantes",
     "CONTRIBUTING los repite en la nota sobre codigo asistido"),
]


def main():
    reales = {
        "tests": len(list((RAIZ / "tests").glob("test_*.py"))),
        "mutantes": open(RAIZ / "tests" / "test_mutantes.py", encoding="utf-8")
                    .read().split("MUTANTES = [", 1)[1].split("\n]", 1)[0].count("\n    ("),
    }

    # Control positivo: si el conteo se rompe, el test compararia contra cero y
    # pediria escribir "cero tests" en el README, que es peor que no comprobar nada.
    for que, n in reales.items():
        if n < 5:
            print("FALLA: el conteo de %s da %d, que no puede ser: el test se ha roto, "
                  "no la documentacion" % (que, n))
            return 1
    if a_numero("forty-eight") != 48 or a_numero("cuarenta y ocho") != 48 \
            or a_numero("veinticinco") != 25 or a_numero("fifty") != 50:
        print("FALLA: la conversion de letras a numero no funciona; sin ella este test "
              "no compara nada")
        return 1

    fallos = []
    for fichero, patron, que, por_que in AFIRMACIONES:
        texto = (RAIZ / fichero).read_text(encoding="utf-8")
        m = re.search(patron, texto)
        if not m:
            fallos.append("%s: ya no aparece la frase que anunciaba los %s (patron %r). "
                          "Si se reescribio, actualiza este test" % (fichero, que, patron))
            continue
        dice = a_numero(m.group(1))
        if dice is None:
            fallos.append("%s: %r no es un numero que sepa leer" % (fichero, m.group(1)))
        elif dice != reales[que]:
            fallos.append("%s: %s -> dice %s (%d) y hay %d"
                          % (fichero, por_que, m.group(1), dice, reales[que]))

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: la documentacion dice %d tests y %d mutantes, y eso es lo que hay"
          % (reales["tests"], reales["mutantes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
