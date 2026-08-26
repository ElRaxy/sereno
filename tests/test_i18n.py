#!/usr/bin/env python3
"""Cada clave que pasa por `_()` tiene traduccion, y con los mismos huecos.

El ingles es la clave, asi que una clave sin traducir no revienta: sale en ingles en
mitad de una interfaz en castellano y nadie se entera hasta que lo ve un usuario. Y un
`{n}` que se pierde al traducir si revienta, pero solo cuando se pinta ese mensaje.
"""
import ast, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text()
HUECOS = re.compile(r"\{(\w+)\}")


def claves_usadas(arbol):
    for n in ast.walk(arbol):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_" and n.args):
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                yield a.value, {k.arg for k in n.keywords if k.arg}


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile(FUENTE, "sereno", "exec"), ns)
    es = ns["TEXTOS"]["es"]
    fallos, vistas = [], set()

    for clave, kwargs in claves_usadas(ast.parse(FUENTE)):
        vistas.add(clave)
        if clave not in es:
            fallos.append(f"sin traducir: {clave!r}")
            continue
        pedidos, dados = set(HUECOS.findall(es[clave])), set(HUECOS.findall(clave))
        if pedidos != dados:
            fallos.append(f"huecos distintos en {clave!r}: en={dados} es={pedidos}")
        if not pedidos <= kwargs and kwargs:
            fallos.append(f"la llamada de {clave!r} pasa {kwargs} y el texto pide {pedidos}")

    # `etiqueta_fuente()` traduce por clave dinamica, asi que el AST no la ve pasar
    # por `_()`. Las etiquetas de fuente se leen del propio modulo.
    vistas |= set(ns["_ETIQUETAS"].values())

    for sobra in sorted(set(es) - vistas):
        fallos.append(f"traduccion huerfana (ya nadie la usa): {sobra!r}")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: {len(vistas)} claves, todas traducidas" if not fallos
          else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
