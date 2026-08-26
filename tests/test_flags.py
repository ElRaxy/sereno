#!/usr/bin/env python3
"""Un flag que no existe se dice, no se traga.

Antes, `sereno --jsonn` hacia lo mismo que `sereno` a secas: abrir el selector. En un
script eso es peor que un error, porque no se ve — crees estar pidiendo JSON y recibes
un TUI esperando teclas. Este test tambien fija lo contrario: que ningun flag real, ni
sus valores, se confundan con un flag desconocido.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
desconocidos, parecido, FLAGS = (ns["flags_desconocidos"], ns["_parecido"], ns["_FLAGS"])

VALIDOS = [
    [], ["--json"], ["--json", "--all"], ["--list"], ["--hook"], ["--version"],
    ["--watch"], ["--watch", "--every", "30"],
    ["--find", "algo"], ["--find", "algo", "--all"], ["--find", "algo", "--list"],
    ["--close-sel", "1,4-6"], ["--stop-sel", "idle"],
    ["--add", "un-id", "--cwd", "/tmp", "--title", "un titulo"],
    ["--yes"], ["--dismiss"], ["-h"], ["--help"],
    # El valor de un flag no se valida aunque parezca uno: buscar la cadena "--json"
    # es raro pero legitimo, y ahogarlo seria peor que dejarlo pasar.
    ["--find", "--json"], ["--title", "--que-sea"],
]
INVALIDOS = ["--jsonn", "--frobnicate", "-x", "--wach", "--al", "--Json", "--find-all"]
SUGERENCIAS = {"--jsonn": "--json", "--wach": "--watch", "--al": "--all",
               "--lst": "--list", "--frobnicate": ""}


def main():
    fallos = []
    for argv in VALIDOS:
        malos = desconocidos(argv)
        if malos:
            fallos.append(f"{argv} rechaza {malos}, y es valido")
    for f in INVALIDOS:
        if desconocidos([f]) != [f]:
            fallos.append(f"{f} pasa como valido")
    for malo, esperado in SUGERENCIAS.items():
        dado = parecido(malo)
        if dado != esperado:
            fallos.append(f"{malo}: sugiere {dado!r}, se esperaba {esperado!r}")

    # Todo flag documentado en el docstring tiene que estar en la tabla, o el aviso
    # rechazaria algo que la propia ayuda anuncia.
    ayuda = (ns["__doc__"] or "")
    import re
    for f in set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", ayuda)):
        if f not in FLAGS:
            fallos.append(f"{f} sale en --help y no esta en _FLAGS")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"ok: {len(VALIDOS)} combinaciones validas, {len(INVALIDOS)} rechazadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
