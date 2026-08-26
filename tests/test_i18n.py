#!/usr/bin/env python3
"""Cada clave que pasa por `_()` tiene traduccion, y con los mismos huecos.

El ingles es la clave, asi que una clave sin traducir no revienta: sale en ingles en
mitad de una interfaz en castellano y nadie se entera hasta que lo ve un usuario. Y un
`{n}` que se pierde al traducir si revienta, pero solo cuando se pinta ese mensaje.
"""
import ast, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text()
# Palabras que en castellano SIEMPRE llevan tilde o ene. No van las ambiguas ("como",
# "que", "esta", "solo", "tu"), que tambien existen sin ella: aqui solo entra lo que
# escrito asi esta mal seguro. Si alguna vez hace falta una de estas sin tilde, se
# quita de la lista a mano y se dice por que.
SIN_TILDE = re.compile(r"\b(?:estan|sesion|numero|aqui|tambien|segun|pestana|pestanas|"
                       r"raton|opcion|opciones|seleccion|confirmacion|huerfana|huerfanas|"
                       r"titulo|ultimo|ultima|ultimos|ultimas|volvera|volveran|quitalas|"
                       r"cuales|mas|asi|despues|ademas|informacion|accion|version|"
                       r"ningun|algun|facil|dificil|rapido|alli|codigo|linea|lineas)\b")

HUECOS = re.compile(r"\{(\w+)\}")


def claves_usadas(arbol):
    for n in ast.walk(arbol):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_" and n.args):
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                yield a.value, {k.arg for k in n.keywords if k.arg}


# Un literal que parece una frase: al menos ocho caracteres utiles y dos palabras con
# letras. Deja fuera claves de diccionario ("aiTitle"), codigos ANSI y separadores.
_FRASE = re.compile(r"[A-Za-z].*\s+.*[A-Za-z]")
_ANSI = ("\x1b[1m", "\x1b[0m", "\x1b[2m")
# Sitios donde una frase acaba viendola el usuario. `aviso` y `cabecera` son las dos
# variables que se pintan tal cual.
_DESTINOS = ("aviso", "cabecera", "msg")


def _literales_sueltos(nodo):
    """Cadenas del arbol que NO vienen de una llamada a `_()`."""
    fuera = []

    class V(ast.NodeVisitor):
        def visit_Call(self, c):
            if isinstance(c.func, ast.Name) and c.func.id == "_":
                return              # traducido: no hay que bajar
            self.generic_visit(c)

        def visit_Constant(self, c):
            if isinstance(c.value, str):
                fuera.append(c.value)

        def visit_JoinedStr(self, j):
            for v in j.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    fuera.append(v.value)
                elif isinstance(v, ast.FormattedValue):
                    self.visit(v)

    V().visit(nodo)
    return fuera


def sin_traducir(arbol):
    """Frases que llegan al usuario sin pasar por `_()`.

    Existe por un caso real: la rama de recuperacion tras un apagon estaba entera en
    castellano —"Hay N sesion(es) que murieron sin dejar proceso"— y el resto del test
    no lo veia, porque solo mira las claves que SI pasan por `_()`. Un usuario en
    ingles se encontraba con eso y con dos mensajes que ademas nombraban un alias que
    no es el del programa.
    """
    def frase(t):
        limpio = t
        for a in _ANSI:
            limpio = limpio.replace(a, "")
        return len(limpio.strip()) >= 8 and bool(_FRASE.search(limpio))

    for n in ast.walk(arbol):
        pinta = (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "print")
        if pinta:
            for t in _literales_sueltos(n):
                if frase(t):
                    yield n.lineno, t
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name) and tg.id in _DESTINOS:
                    for t in _literales_sueltos(n.value):
                        if frase(t):
                            yield n.lineno, t


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile(FUENTE, "sereno", "exec"), ns)
    es = ns["TEXTOS"]["es"]
    fallos, vistas = [], set()

    for ln, txt in sin_traducir(ast.parse(FUENTE)):
        fallos.append(f"L{ln}: frase que se pinta sin pasar por _(): "
                      f"{' '.join(txt.split())[:70]!r}")

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

    # Y que el castellano ESTE en castellano. De 245 cadenas, una sola llevaba tilde:
    # la interfaz entera estaba escrita como si el teclado no tuviera acentos, y eso
    # se lee como una traduccion a medio hacer, no como un idioma soportado.
    for clave, texto in sorted(es.items()):
        for palabra in SIN_TILDE.findall(texto.lower()):
            fallos.append(f"falta la tilde en {palabra!r}: {texto!r}")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: {len(vistas)} claves, todas traducidas" if not fallos
          else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
