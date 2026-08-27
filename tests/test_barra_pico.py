#!/usr/bin/env python3
"""La barra de contexto recuerda lo que la sesion LLEGO a tener.

Compactar borra la prueba: el contexto cae y la barra baja con el. Una sesion de 700
turnos que ha compactado dos veces marca un 11% y se lee como la mas fresca de la lista
justo cuando es la mas gastada. El pico ya se calculaba desde v1.8.0 —sobrevive a
compactar porque sale del `preTokens` de cada compactacion— pero solo se veia entrando
en el panel.

Dos capas, porque se rompen por separado:

1. `barra()` / `_celdas()` en aislado. Es aritmetica pura y ahi vive la regla.
2. El CABLEADO, con el doble de `stdscr`: que el pico llegue de la fila a la barra que
   se pinta. Sin esta capa, borrar `pico=alto_pico` de la llamada no rompe nada.

El caso de la capa 2 esta elegido para que TODAS las vias alternativas apunten a lo
contrario de lo correcto: la fila compactada tiene MENOS contexto que la de al lado, asi
que sin el cableado saldria con MENOS celdas llenas. Que salga con mas solo puede venir
del pico. Un caso donde la compactada ya fuera la mas llena no distinguiria nada.
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

barra, _celdas = ns["barra"], ns["_celdas"]
LLENA, HUECA = "▰", "▱"
M = 1_000_000
Q = ord("q")


def llenas(cad):
    return cad.count(LLENA)


# ── 1. la aritmetica ────────────────────────────────────────────────────────────
def aritmetica(f):
    # Sin pico, exactamente lo de siempre. Es la garantia de que esto no cambia lo que
    # ya se veia en las sesiones que nunca han compactado, que son la mayoria.
    # Ojo con el medio exacto: `round()` de Python redondea al par, asi que 500k de un
    # millon son 2 celdas y no 3, y 900k son 4 y no 5. No es un fallo —una celda arriba
    # o abajo en el medio no cambia nada— pero clavarlo aqui evita "arreglarlo" luego.
    for v, esperadas in ((0, None), (1_000, 1), (100_000, 1), (300_000, 2),
                         (500_000, 2), (900_000, 4), (M, 5), (2 * M, 5)):
        cad = barra(v, M)
        if esperadas is None:
            f(cad == " " * 5, "sin contexto la barra va en blanco, no a cero: %r" % cad)
            continue
        f(llenas(cad) == esperadas,
          "%d de un millon -> %d celdas, esperaba %d" % (v, llenas(cad), esperadas))
        f(len(cad) == 5, "la barra siempre mide 5: %r" % cad)

    # Un hilo de contexto no puede desaparecer: redondearia a cero y la sesion se leeria
    # como sin estrenar.
    f(llenas(barra(1, M)) == 1, "1 token de un millon tiene que pintar una celda")

    # Con pico: manda el pico, y siempre en llenas.
    cad = barra(115_901, M, pico=522_036)
    f(llenas(cad) == 3, "11%% con pico del 52%% -> 3 celdas, salieron %d" % llenas(cad))
    f(len(cad) == 5, "con pico tambien mide 5: %r" % cad)
    f(cad == LLENA * 3 + HUECA * 2, "las del pico van LLENAS, no huecas: %r" % cad)

    # El pico nunca resta. Es monotono por construccion, pero una lectura a medias puede
    # dejarlo por debajo del contexto de ahora y ahi no debe tocar nada.
    for pico in (0, None, 1, 100_000, 300_000):
        f(barra(300_000, M, pico=pico) == barra(300_000, M),
          "un pico de %r por debajo del contexto no puede cambiar la barra" % (pico,))

    # Ni pasarse del ancho, ni pintar nada donde no hay contexto que pintar.
    f(barra(10_000, M, pico=5 * M) == LLENA * 5, "el pico se acota al ancho de la barra")
    f(barra(0, M, pico=900_000) == " " * 5,
      "sin contexto de ahora no se pinta pico: seria una barra de una sesion vacia")
    f(barra(500_000, 0, pico=900_000) == " " * 5, "sin tope no hay barra")

    # `_celdas` es la que comparten las dos medidas, y por eso existe: si cada una
    # redondeara por su cuenta, el pico podria caer por debajo del contexto de ahora.
    for v in (0, 1, 99_999, 100_001, 300_000, 499_999, 999_999, M):
        f(_celdas(v, M) <= 5, "%d se pasa de 5 celdas" % v)
        f(_celdas(v, M) >= _celdas(max(0, v - 1), M),
          "_celdas tiene que crecer con el valor, y en %d no crece" % v)


# ── 2. el cableado ──────────────────────────────────────────────────────────────
def sesion(fila, ctx, pico):
    """Una fila con el contexto y el pico puestos a mano.

    Los dos NO viven en el mismo sitio y descubrirlo costo un falso verde: lo que la
    barra mide sale de `r["pulso"]["ctx"]`, y el pico de `r["_uso"]["pico"]`. Fijar solo
    `_uso` dejaba el contexto en el que trae la demo, asi que el test pasaba con un
    escenario que no era el que decia su nombre.
    """
    r = dict(fila)
    r["pulso"] = dict(r.get("pulso") or {}, ctx=ctx, modelo="claude-opus-5",
                      ventana_1m=True)
    r["_uso"] = {"in": ctx, "out": 0, "cw": 0, "cr": 0, "turnos": 40, "compacta": 0,
                 "ctx": ctx, "pico": pico, "modelo": "claude-opus-5",
                 "ventana_1m": True, "activo": 600.0, "usd": None, "completo": True}
    return r


def pinta(filas, h=32, w=170):
    import curses as real
    cajon, guardado = [], ns["uso_de"]
    ns["uso_de"] = lambda r, tope=None: r.get("_uso")
    sys.modules["curses"] = espia(real, h, w, [Q], cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](filas)
    finally:
        sys.modules["curses"] = real
        ns["uso_de"] = guardado
    p = cajon[0]
    celdas = p.celdas or p.fotogramas[-1]
    return ["".join(celdas.get((y, x), " ") for x in range(w)).rstrip()
            for y in range(h)]


def cableado(f):
    base = [r for r in ns["sesiones_demo"]() if r.get("fuente", "claude") == "claude"][:2]
    if len(base) < 2:
        f(False, "la demo tiene que dar al menos dos filas de claude")
        return
    # 11% ahora, 52% en su dia (compacto dos veces). La de al lado: 36% y sin compactar,
    # que es por que su pico es su contexto — el contexto solo crece hasta que compactas.
    compactada = sesion(base[0], 115_901, 522_036)
    virgen = sesion(base[1], 358_990, 358_990)

    pantalla = pinta([compactada, virgen])
    filas = [l for l in pantalla if LLENA in l or HUECA in l]
    f(len(filas) >= 2, "esperaba dos filas con barra, salieron %d" % len(filas))
    if len(filas) < 2:
        return

    def celdas_de(linea):
        i = min(linea.index(c) for c in (LLENA, HUECA) if c in linea)
        return linea[i:i + 5]

    a, b = celdas_de(filas[0]), celdas_de(filas[1])
    f(llenas(a) == 3, "la compactada (11%% con pico 52%%) tiene que pintar 3 celdas, "
                      "pinto %d (%r)" % (llenas(a), a))
    f(llenas(b) == 2, "la virgen (36%%) tiene que pintar 2 celdas, pinto %d (%r)"
                      % (llenas(b), b))
    # Y el porcentaje sigue siendo el de AHORA: el pico llena celdas, no infla la cifra.
    # Si se colara al porcentaje, la sesion se leeria como llena y es justo lo contrario.
    f(" 12%" in filas[0], "la compactada tiene que seguir marcando 12%%: %r" % filas[0])
    f(" 36%" in filas[1], "la virgen tiene que marcar 36%%: %r" % filas[1])
    # El veredicto que solo puede dar el cableado: la de MENOS contexto sale con MAS
    # celdas. Sin el pico esto seria imposible.
    f(llenas(a) > llenas(b),
      "la compactada tiene menos contexto y aun asi tiene que salir mas llena: "
      "%r vs %r" % (a, b))


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    aritmetica(f)
    cableado(f)
    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos else "ok: la barra recuerda el pico")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
