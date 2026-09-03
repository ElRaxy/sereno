#!/usr/bin/env python3
"""`todos.py --rapido` salta exactamente los lentos, y ni uno de mas ni de menos.

El flag existe para el loop local: la carpeta entera tarda ~360s porque los tres tests
que abren un pseudo-terminal y la bateria de mutantes se comen casi todo el reloj. Con
`--rapido` se saltan esos cuatro y el resto corre en segundos; la CI sigue corriendo la
carpeta completa, sin el flag.

Se prueba la funcion pura `seleccion(ficheros, rapido)`, no el subprocess: correr
`todos.py --rapido` de verdad meteria aqui todos los demas tests. Y el control que hace
que esto proteja algo: cada nombre de `LENTOS` tiene que existir como fichero. Si alguien
renombra un pty y no toca `LENTOS`, `--rapido` saltaria un fantasma —seguiria corriendo el
test lento con otro nombre— y el flag dejaria de servir en silencio. Ese es justo el fallo
que este test caza.
"""
import importlib.util, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent


def carga():
    spec = importlib.util.spec_from_file_location("todos_mod", RAIZ / "todos.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cuerpo(fallos):
    mod = carga()
    ficheros = sorted(RAIZ.glob("test_*.py"))

    # Sin el flag no se toca nada.
    if mod.seleccion(ficheros, False) != ficheros:
        fallos.append("sin --rapido la seleccion no es la carpeta entera")

    # Con el flag, fuera LENTOS y NADA mas.
    rapidos = {p.name for p in mod.seleccion(ficheros, True)}
    for n in mod.LENTOS:
        if n in rapidos:
            fallos.append(f"--rapido no saltó {n!r}")
    esperado = {p.name for p in ficheros} - mod.LENTOS
    if rapidos != esperado:
        sobra = rapidos - esperado
        falta = esperado - rapidos
        fallos.append(f"--rapido dejó una seleccion torcida (sobra={sobra}, falta={falta})")

    # Cada lento nombrado existe de verdad: si no, --rapido salta un fantasma.
    for n in mod.LENTOS:
        if not (RAIZ / n).exists():
            fallos.append(f"LENTOS nombra un fichero que no existe: {n!r}")


def main():
    fallos = []
    cuerpo(fallos)
    if fallos:
        print("FALLA todos_rapido:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: --rapido salta exactamente los cuatro lentos (3 pty + mutantes) y todos "
          "existen; sin el flag corre la carpeta entera")
    return 0


if __name__ == "__main__":
    sys.exit(main())
