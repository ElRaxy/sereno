#!/usr/bin/env python3
"""Corre TODOS los `tests/test_*.py` y falla si alguno falla.

Existe por lo que conto la auditoria del 2026-08-29: `ci.yml` listaba los tests a mano,
un `run:` por fichero, y **de los once escritos entre la 1.22.0 y la 1.29.0 no se cableo
ninguno**. Diecisiete de cuarenta y cuatro no corrian nunca. Los checks salian verdes
igual, que es la peor forma de fallar: un test que se escribe y no se conecta solo
protege el dia que se escribio.

Un recolector no se puede desincronizar. Lo que hay en la carpeta es lo que corre, y
anadir un caso no exige acordarse de tocar el workflow.

Se ejecuta cada fichero en su PROPIO proceso, a proposito: casi todos manipulan `HOME`,
variables de entorno y el `ns` del programa cargado a mano, y compartir intereprete los
contaminaria entre si. Es mas lento y es la unica forma de que el resultado signifique
algo.
"""
import pathlib, subprocess, sys, time

AQUI = pathlib.Path(__file__).resolve().parent
TOPE = 420          # segundos por fichero: uno colgado no puede colgar la CI entera.
                    # La bateria de mutantes (test_mutantes) es la unica larga y crece con
                    # cada guarda; en los runners lentos (macos/ubuntu 3.8) cada mutante que
                    # ancla en test_tui_arranca (~37s) acerca el total a 300. 420 da margen
                    # sin dejar de cazar un test de verdad colgado.

# Los cuatro que se comen casi todo el reloj: los tres que abren un pseudo-terminal
# de verdad y la bateria de mutantes (~300s ella sola). `--rapido` los salta para el
# loop local; la CI corre SIEMPRE la carpeta entera, sin el flag.
LENTOS = {"test_tui_arranca.py", "test_vista_now.py", "test_tmux_de_verdad.py",
          "test_mutantes.py"}


def seleccion(ficheros, rapido):
    """Los ficheros a correr. Con `rapido`, fuera los de `LENTOS`."""
    return [p for p in ficheros if not (rapido and p.name in LENTOS)]


def titulo(p):
    """La primera linea del docstring, que es la frase que decia el `name:` del paso."""
    try:
        for linea in p.read_text("utf-8").splitlines():
            if linea.startswith('"""'):
                return linea.strip('"').strip() or p.stem
    except Exception:
        pass
    return p.stem


def main():
    rapido = "--rapido" in sys.argv[1:]
    todos = sorted(AQUI.glob("test_*.py"))
    if not todos:
        print("FALLA: no hay ni un test que correr")
        return 1
    ficheros = seleccion(todos, rapido)
    saltados = len(todos) - len(ficheros)
    if rapido:
        print(f"MODO RAPIDO: saltados {saltados} ficheros lentos (los 3 pty + mutantes). "
              f"NO sustituye a la bateria completa; la CI corre todo.\n")
    fallados, t0 = [], time.time()
    for p in ficheros:
        marca = time.time()
        try:
            r = subprocess.run([sys.executable, str(p)], timeout=TOPE,
                               capture_output=True, text=True)
            salida, codigo = (r.stdout or "") + (r.stderr or ""), r.returncode
        except subprocess.TimeoutExpired:
            salida, codigo = f"colgado: mas de {TOPE}s sin terminar", 1
        segundos = time.time() - marca
        print(f"{'ok  ' if codigo == 0 else 'FALLA'}  {p.name:<48} {segundos:5.1f}s"
              f"  {titulo(p)}")
        if codigo != 0:
            fallados.append(p.name)
            print("\n".join("      " + l for l in salida.strip().splitlines()[-25:]))
    print(f"\n{len(ficheros) - len(fallados)}/{len(ficheros)} en verde "
          f"({time.time() - t0:.0f}s)"
          f"{f' — MODO RAPIDO, {saltados} lentos sin correr' if rapido else ''}")
    if fallados:
        print("fallan: " + ", ".join(fallados))
    return 1 if fallados else 0


if __name__ == "__main__":
    sys.exit(main())
