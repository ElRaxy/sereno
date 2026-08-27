#!/usr/bin/env python3
"""La tecla `s` llega hasta `gasto` y la lista sale ordenada por lo consumido.

`tests/test_orden.py` prueba `ordena()` en aislado, que es donde vive la regla. Lo que
no prueba —y es la mitad que se rompe— es el CABLEADO: que la tecla recorra los cinco
modos, que el modo llegue a `ordena()` y que alguien haya pasado antes por `carga_uso()`.
Sin esa ultima llamada `spend` no revienta: deja la lista tal cual, que desde fuera se
lee como "la tecla no hace nada" y ningun test en aislado lo ve.

Se mira la matriz de celdas del doble, no un volcado del terminal: curses manda diffs y
un pty leido a pelo mezcla dos fotogramas (ver `doble_curses.py`).
"""
import contextlib, io, os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

S = ord("s")
Q = ord("q")


def gasto(r):
    u = r.get("_uso") or {}
    return (u.get("in") or 0) + (u.get("cw") or 0) + (u.get("out") or 0)


def lineas(celdas, h, w):
    out = []
    for y in range(h):
        out.append("".join(celdas.get((y, x), " ") for x in range(w)).rstrip())
    return out


def pinta(teclas, h=32, w=170):
    """Pinta una vez, con el consumo VACIADO de las filas y detras de `uso_de`.

    La demo trae `_uso` precocinado, asi que pasarla tal cual dejaria el cableado sin
    probar: comprobado, quitar `carga_uso()` del bucle no rompia nada. Aqui las filas
    entran sin el dato y solo lo reciben si alguien pasa por `uso_de`, que es lo que
    `carga_uso()` hace y solo en el modo que lo necesita.
    """
    import curses as real
    tabla = {r["name"]: r.get("_uso") for r in ns["sesiones_demo"]()}
    filas = [dict(r, _uso=None) for r in ns["sesiones_demo"]()]

    def uso_falso(r):
        if r.get("_uso") is None:
            r["_uso"] = tabla.get(r.get("name"))
        return r["_uso"]

    cajon, guardado = [], ns["uso_de"]
    ns["uso_de"] = uso_falso
    sys.modules["curses"] = espia(real, h, w, teclas, cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](filas)
    finally:
        sys.modules["curses"] = real
        ns["uso_de"] = guardado
    p = cajon[0]
    # El ultimo fotograma es el que quedo en pantalla al pulsar `q`: `erase()` guarda
    # el anterior antes de borrar, asi que el vivo esta en `celdas` y no en la lista.
    return lineas(p.celdas or p.fotogramas[-1], h, w)


def main():
    fallos = []
    demo = [r for r in ns["sesiones_demo"]() if r.get("fuente", "claude") == "claude"]
    esperado = [r["title"].rstrip("…")[:14]
                for r in sorted(demo, key=lambda r: -gasto(r))]

    # 1. Cuatro `s` desde `actividad` tienen que llegar a `gasto`, que es el quinto y
    #    ultimo modo. Si alguien anade un sexto delante, este numero deja de cuadrar y
    #    el test lo dice en vez de pasar por otro modo cualquiera.
    pantalla = pinta([S, S, S, S, Q])
    cabecera = pantalla[0] + " " + pantalla[1]
    if "orden: gasto" not in cabecera:
        fallos.append(f"la cabecera no dice el modo: {cabecera.strip()[:90]!r}")

    # 2. Y la lista sale en ese orden. Se busca cada titulo por pantalla y se compara
    #    la posicion VERTICAL: es lo que ve quien mira, y no depende de en que columna
    #    empiece la lista ni de cuanto se recorte el titulo.
    filas = {}
    for t in esperado:
        for y, linea in enumerate(pantalla):
            if t and t in linea:
                filas.setdefault(t, y)
                break
    faltan = [t for t in esperado if t not in filas]
    if faltan:
        fallos.append(f"no se ven en pantalla: {faltan}")
    else:
        salida = sorted(esperado, key=lambda t: filas[t])
        if salida != esperado:
            fallos.append(f"orden en pantalla {salida} != por gasto {esperado}")

    # 3. Control positivo: sin pulsar nada, la lista NO sale en ese orden. Sin esto el
    #    test pasaria igual si `s` no hiciera nada y el orden por defecto coincidiera.
    base = pinta([Q])
    pos = {}
    for t in esperado:
        for y, linea in enumerate(base):
            if t and t in linea:
                pos.setdefault(t, y)
                break
    if len(pos) == len(esperado) and sorted(esperado, key=lambda t: pos[t]) == esperado:
        fallos.append("el orden por defecto ya es el de gasto: el test no prueba nada")

    for f in fallos:
        print("FALLO:", f)
    print("ok: `s` llega a gasto y la lista se pinta ordenada por lo consumido"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
