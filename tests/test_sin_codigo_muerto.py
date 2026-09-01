#!/usr/bin/env python3
"""Ninguna funcion del programa se queda sin quien la llame.

Una funcion muerta no da error, no sale en la cobertura como hueco —no se ejecuta, pero
tampoco se esperaba que lo hiciera— y no la ve ningun test: lo unico que hace es pedir
que la leas cada vez que buscas algo cerca. En un fichero unico de casi siete mil lineas
eso se paga en cada cambio.

`_fecha_corta` estuvo once lineas ahi desde la 1.0.0 sin un solo llamador, y no la
encontro nadie hasta que se recorrio el arbol de sintaxis a proposito. Esto convierte
ese barrido en red fija.

Cuenta como uso cualquier mencion del nombre fuera de su propia definicion: una llamada,
pasarla como argumento, meterla en una tabla, o nombrarla dentro de una cadena —hay
tablas que despachan por nombre—. Es a proposito laxo: la unica forma de que este test
se equivoque es dando por viva una muerta, nunca al reves, y un test que acusa en falso
se acaba desactivando.

`PERMITIDAS` es para lo que el programa no llama pero existe por algo: hoy, una utilidad
que solo usan los propios tests. Entra con su motivo escrito o no entra.
"""
import ast
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

PERMITIDAS = {
    # La escriben los tests para montar un tmux de mentira; el programa no la llama.
    "write_attach_config": "solo la usan los tests, para preparar el entorno",
}


def main():
    fuente = (RAIZ / "sereno").read_text("utf-8")
    arbol = ast.parse(fuente)
    tests = "\n".join(p.read_text("utf-8") for p in (RAIZ / "tests").glob("*.py"))

    definidas = {}
    for n in ast.walk(arbol):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definidas.setdefault(n.name, n.lineno)

    # Todo nombre que el programa menciona sin estar definiendolo: llamadas, referencias
    # sueltas, atributos y decoradores.
    usados = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Name):
            usados.add(n.id)
        elif isinstance(n, ast.Attribute):
            usados.add(n.attr)

    muertas, coladas = [], []
    for nombre, linea in sorted(definidas.items(), key=lambda kv: kv[1]):
        if nombre in usados:
            continue
        # Despacho por cadena: una tabla que guarda el nombre y lo resuelve luego.
        if re.search(r'["\']%s["\']' % re.escape(nombre), fuente):
            continue
        if nombre in PERMITIDAS:
            if not re.search(r"\b%s\b" % re.escape(nombre), tests):
                coladas.append("%s esta en PERMITIDAS por '%s', pero ya no la usa ningun "
                               "test: quitala de la lista y borra la funcion"
                               % (nombre, PERMITIDAS[nombre]))
            continue
        muertas.append("linea %d: `%s` no la llama nadie" % (linea, nombre))

    if muertas or coladas:
        print("FALLA:")
        for m in muertas:
            print("  -", m)
            print("    borrala, o llamala desde donde deberia usarse. Si existe para los")
            print("    tests, anadela a PERMITIDAS con el motivo escrito.")
        for c in coladas:
            print("  -", c)
        return 1
    print("ok: las %d funciones del programa tienen quien las llame" % len(definidas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
