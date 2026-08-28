#!/usr/bin/env python3
"""`--list` no rellena con un interrogante lo que no sabe.

Una sesion que no arranco por el alias no tiene entrada de tmux, asi que no consta cuando
se abrio. El panel deja ese campo en blanco; `--list` escribia "open for ?" — el mismo
hecho contado de dos formas, y la fea afirma el dato y lo rellena con un simbolo. No es un
caso raro: le pasa a todas las que el selector lee de `~/.claude/projects`.
"""
import contextlib, io, pathlib, re, sys, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def fila(**kw):
    base = dict(name="cc-x-1", title="una sesion", attached=False, created=None,
                idle=5, mem_mb=None, colision=None,
                pulso={"escribe": True, "herramienta": False, "cerrado": False})
    base.update(kw)
    return base


def main():
    fallos = []
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

    con = fila(name="cc-x-2", title="con hora", created=time.time() - 3600)
    sin = fila(name="8e3a6684-96ed-451f-aab2-b57c6eee2bfe", title="sin hora")

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        ns["print_live"]([con, sin])
    lineas = [l for l in out.getvalue().splitlines() if l.strip()]
    conh = next((l for l in lineas if "con hora" in l), "")
    sinh = next((l for l in lineas if "sin hora" in l), "")

    if not conh or not sinh:
        print(f"FALLA: no salen las dos filas:\n{out.getvalue()[:300]}")
        return 1

    # 1. La que no consta no inventa un valor.
    if "?" in sinh:
        fallos.append(f"la fila sin hora sigue trayendo un '?': {sinh.strip()!r}")
    # 2. Y tampoco pinta la etiqueta sola, que seria igual de raro.
    if re.search(r"open for\s*$|abierta hace\s*$", sinh):
        fallos.append("la etiqueta se pinta sin valor detras")
    # 3. Control: la que SI consta la sigue pintando. Sin esto, borrar el campo entero
    #    para todas dejaria este test en verde.
    if "1h" not in conh:
        fallos.append(f"la fila con hora ha perdido el dato: {conh.strip()!r}")
    # 4. Ni una cola de espacios: las columnas van rellenadas a ancho fijo.
    for l in lineas:
        if l != l.rstrip():
            fallos.append(f"linea con espacios al final: {l!r}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_lista_sin_hora" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
