#!/usr/bin/env python3
"""Nada del fuente usa sintaxis posterior a Python 3.8, que es el suelo del repo.

El CI ya corre en 3.8, pero avisa tarde: quien escribe el codigo tiene 3.12 o mas y ahi
todo compila. Este test corre en cualquier version y caza la trampa concreta que ya se
colo una vez — una expresion partida en dos lineas DENTRO de un f-string, legal desde
3.12 y `SyntaxError: EOL while scanning string literal` en 3.8.

`ast.parse(..., feature_version=(3, 8))` no sirve para esto: solo cubre features
semanticas, no la gramatica de los f-strings. Verificado.
"""
import io, pathlib, sys, tokenize

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def multilinea_en_fstring(ruta):
    """Las lineas donde un f-string de una sola comilla se parte. Vacio si no hay.

    Necesita el tokenizador de 3.12+, que es el que trocea los f-strings en
    FSTRING_START/MIDDLE/END. En 3.8-3.11 el f-string es un unico STRING y no hay nada
    que mirar — pero es que ahi tampoco compilaria, asi que el aviso llegaria igual.
    """
    if not hasattr(tokenize, "FSTRING_START"):
        return None                       # el tokenizador de esta version no lo ve
    fuera, abierto = [], None
    with ruta.open("rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.FSTRING_START:
                # Un f-string de triple comilla si puede ocupar varias lineas en 3.8.
                abierto = None if tok.string.rstrip("fFrRbB").startswith(("'''", '"""')) \
                    else tok.start[0]
            elif tok.type == tokenize.FSTRING_END and abierto is not None:
                if tok.end[0] != abierto:
                    fuera.append(abierto)
                abierto = None
    return fuera


def main():
    fallos = []
    for ruta in [RAIZ / "sereno"] + sorted((RAIZ / "tests").glob("*.py")):
        lineas = multilinea_en_fstring(ruta)
        if lineas is None:
            print(f"aviso: {sys.version_info[0]}.{sys.version_info[1]} no trocea los "
                  "f-strings; este test solo mira de verdad en 3.12+")
            break
        for n in lineas:
            fallos.append(f"{ruta.name}:{n} parte un f-string en dos lineas "
                          "(SyntaxError en 3.8)")
    for f in fallos:
        print("FALLO:", f)
    print("ok: ningun f-string se parte en dos lineas"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
