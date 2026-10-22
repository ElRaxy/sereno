#!/usr/bin/env python3
"""El programa no puede abrir una conexion, y aqui se demuestra.

Es la pregunta razonable de cualquiera que se plantee instalarlo: esto lee tus
prompts y las respuestas de tu agente. La respuesta no deberia ser "confia en mi",
asi que el test recorre el AST y falla si aparece un import de red, y ademas fija
la lista COMPLETA de programas externos que se lanzan.
"""
import ast, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text()

RED = {"socket", "ssl", "http", "urllib", "urllib2", "requests", "httpx", "ftplib",
       "smtplib", "telnetlib", "asyncio", "xmlrpc", "webbrowser", "poplib",
       "imaplib", "aiohttp", "websockets"}

# Todo binario externo que puede ejecutar. Si aparece uno nuevo, este test obliga a
# anadirlo aqui a mano — que es justo el momento de preguntarse si debe estar.
# Cada uno de estos esta aqui porque hace falta y porque no sale de la maquina:
#   ps        -> RAM por arbol de procesos          defaults -> el idioma en macOS
#   tmux      -> las sesiones vivas                 open     -> reabrir una pestana
#   osascript -> el aviso de escritorio en macOS    notify-send -> el mismo en Linux
# Anadir uno nuevo obliga a pasar por aqui, que es justo lo que se pretende.
PERMITIDOS = {"ps", "open", "defaults", "tmux", "/bin/sh", "osascript", "notify-send"}


def imports_del_fuente(arbol):
    """Los modulos que el programa importa de verdad, de primer nivel y sin repetir."""
    fuera = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            fuera.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            fuera.add(n.module.split(".")[0])
    return fuera


def main():
    arbol = ast.parse(FUENTE)
    fallos = []

    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in RED:
                    fallos.append(f"import de red en la linea {n.lineno}: {a.name}")
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in RED:
                fallos.append(f"import de red en la linea {n.lineno}: {n.module}")

    externos = set()
    for n in ast.walk(arbol):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("run", "Popen", "call", "check_output") and n.args):
            continue
        arg = n.args[0]
        elems = arg.elts if isinstance(arg, ast.List) else [arg]
        if not elems:
            continue
        p = elems[0]
        if isinstance(p, ast.Constant) and isinstance(p.value, str):
            externos.add(p.value.rsplit("/", 1)[-1] if p.value.startswith("/") else p.value)
        elif isinstance(p, ast.Name):
            externos.add(f"<variable {p.id}>")

    # TMUX_BIN es una variable, pero su valor esta fijado en el fuente y se comprueba
    concretos = {e for e in externos if not e.startswith("<")}
    nuevos = concretos - PERMITIDOS
    if nuevos:
        fallos.append(f"programas externos no declarados: {sorted(nuevos)}")
    if "<variable TMUX_BIN>" in externos and 'shutil.which("tmux")' not in FUENTE:
        fallos.append("TMUX_BIN ya no sale de shutil.which('tmux')")

    # La promesa de privacidad del README nombra la lista ENTERA de imports, asi que es
    # una afirmacion verificable y no un adjetivo. Se comprobo por las malas: `base64`
    # entro con OSC 52 en la 1.13.0 y la lista siguio diciendo "entera" sin el, o sea que
    # el parrafo que promete que nada sale de la maquina llevaba semanas incompleto.
    reales = imports_del_fuente(arbol) - {"curses"}      # curses se nombra aparte
    for doc in ("README.md", "README.es.md"):
        texto = (RAIZ / doc).read_text()
        # Se extrae la lista del propio README y se comparan conjuntos, en vez de buscar
        # cada nombre por separado: los saltos de linea del parrafo daban falsos positivos
        # segun donde partiera la linea, y un test que falla por como esta maquetado un
        # parrafo se acaba silenciando.
        # Se localiza por `shlex` y se expande a los backticks que lo rodean. Emparejar
        # todos los backticks del fichero NO vale: los bloques ``` del README desalinean
        # los pares y la lista cae fuera de uno.
        i = texto.find("shlex")
        ini, fin = texto.rfind("`", 0, i), texto.find("`", i)
        if i < 0 or ini < 0 or fin < 0:
            fallos.append(f"{doc}: no encuentro la lista de imports que promete ser entera")
            continue
        prometidos = {x.strip() for x in texto[ini + 1:fin].replace("\n", " ").split(",")}
        faltan = sorted(reales - prometidos)
        if faltan:
            fallos.append(f"{doc} promete la lista entera de imports y le faltan: {faltan}")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: cero imports de red; solo lanza {sorted(concretos)}"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
