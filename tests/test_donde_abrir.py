#!/usr/bin/env python3
"""`r` pregunta EN QUE terminal abrir, cuando hay mas de una.

Hasta la 1.25.0 el sitio lo elegia el programa —el primero de `LANZADORES`— y la unica
forma de cambiarlo era una variable de entorno. Es la misma pega que se le puso al relevo
y se arreglo con su cuadro: una variable de entorno no es una forma de ofrecer algo.

Lo que se vigila:

  1. con dos o mas sitios, `r` abre el cuadro y lo elegido llega a quien abre;
  2. con uno solo NO lo abre — un cuadro de una opcion es una tecla de mas — salvo
     que haya modelo que elegir: entonces el cuadro es el unico sitio del `[m]`;
  3. una tecla cualquiera cancela y no abre nada;
  4. el cuadro cabe en pantallas pequenas, que es donde curses se calla;
  5. y el `ejecutar` de la demo aguanta el parametro nuevo. Ese lambda tenia dos
     parametros y el selector pasa tres: sin esto, `r` en modo demo revienta.
"""
import contextlib, io, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
os.environ.pop("SERENO_LANZADOR", None)
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

ESPACIO, R, UNO, DOS, TRES, Q = 32, ord("r"), ord("1"), ord("2"), ord("3"), ord("q")


def corre(teclas, disponibles, h=30, w=150, con_modelo=False):
    """(llamadas a ejecutar, celdas fuera de marco).

    Las filas de la demo no saben recibir modelo (no son sesiones paradas de Claude ni
    de Codex); `con_modelo` les pone un id de Claude para que el `[m]` tenga sentido."""
    # Las preferencias a un temporal: recordar la ultima eleccion cambia el ORDEN de los
    # sitios, asi que sin aislarlas un caso contamina al siguiente. Y un test no escribe
    # en el HOME de nadie.
    import tempfile
    ns["PREFS"] = pathlib.Path(tempfile.mkdtemp()) / "prefs.json"

    import curses as real
    llamadas, cajon = [], []
    ns["lanzadores_disponibles"] = lambda: list(disponibles)

    def ejecutar(verbo, sel, donde=None, modelo=None):
        llamadas.append({"verbo": verbo, "n": len(sel), "donde": donde, "modelo": modelo})
        return "ok", ns["sesiones_demo"]()
    # Sin esto no se prueba nada: `r` descarta las que YA tienen pestana abierta, y en
    # la demo la primera fila la tiene. La seleccion se quedaba vacia y no se llamaba a
    # nadie — que es justo lo que este test cree estar midiendo.
    filas = ns["sesiones_demo"]()
    for f in filas:
        f["attached"] = False
        if con_modelo:
            f["meta"] = dict(f.get("meta") or {}, id="demo-id-" + f["name"])
    sys.modules["curses"] = espia(real, h, w, list(teclas), cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](filas, ejecutar=ejecutar)
    finally:
        sys.modules["curses"] = real
    return llamadas, (cajon[0].fuera if cajon else [("sin pintar",)])


def main():
    fallos = []
    tres = ["warp", "tmux", "terminal"]

    # 1. Con tres sitios, el elegido llega hasta quien abre. Se prueban el primero y el
    #    tercero: con uno solo, un bug que devuelva siempre `lanzadores[0]` pasaria.
    for tecla, esperado in ((UNO, "warp"), (TRES, "terminal")):
        llam, fuera = corre([ESPACIO, R, tecla, Q], tres)
        abrir = [l for l in llam if l["verbo"] == "reopen"]
        if not abrir:
            fallos.append(f"con [{chr(tecla)}] no se abrio nada")
        elif abrir[0]["donde"] != esperado:
            fallos.append(f"[{chr(tecla)}] eligio {abrir[0]['donde']!r}, no {esperado!r}")
        if fuera:
            fallos.append(f"el cuadro se sale del marco: {fuera[:2]}")

    # 2. Con uno solo y sin modelos que ofrecer no hay cuadro: la primera tecla
    #    despues de `r` NO se come el cuadro, se va al selector. Se comprueba porque
    #    `reopen` ocurre igualmente y con ese unico lanzador. El catalogo se vacia con
    #    una coma: `_env` trata la cadena vacia como "sin variable".
    os.environ["SERENO_MODELOS"] = ","
    try:
        llam, _f = corre([ESPACIO, R, Q], ["tmux"], con_modelo=True)
    finally:
        os.environ.pop("SERENO_MODELOS", None)
    abrir = [l for l in llam if l["verbo"] == "reopen"]
    if not abrir:
        fallos.append("con un solo lanzador `r` no abre: hay un cuadro donde no toca")
    elif abrir[0]["donde"] != "tmux":
        fallos.append(f"con uno solo no se usa ese: {abrir[0]['donde']!r}")

    # 2b. Con uno solo PERO con modelos que elegir, el cuadro si se abre: es el unico
    #     sitio donde vive el `[m]`. `1` abre con ese unico lanzador; `m` y luego `1`
    #     abre con el primer modelo del catalogo.
    llam, fuera = corre([ESPACIO, R, UNO, Q], ["tmux"], con_modelo=True)
    abrir = [l for l in llam if l["verbo"] == "reopen"]
    if not abrir or abrir[0]["donde"] != "tmux":
        fallos.append(f"con un lanzador y modelos, [1] no abre con ese lanzador: {abrir!r}")
    elif abrir[0]["modelo"] is not None:
        fallos.append(f"sin tocar [m] llega un modelo: {abrir[0]['modelo']!r}")
    if fuera:
        fallos.append(f"el cuadro de un lanzador se sale del marco: {fuera[:2]}")
    llam, _f = corre([ESPACIO, R, ord("m"), UNO, Q], ["tmux"], con_modelo=True)
    abrir = [l for l in llam if l["verbo"] == "reopen"]
    if not abrir or abrir[0]["modelo"] != ns["modelos_catalogo"]()[0]:
        fallos.append(f"con un lanzador, [m] no llega a quien abre: {abrir!r}")

    # 2c. Y con filas que admiten modelo pero sin filas que lo pidan (sin `con_modelo`)
    #     tampoco hay cuadro: `r` abre directo con el unico lanzador.
    llam, _f = corre([ESPACIO, R, Q], ["tmux"])
    abrir = [l for l in llam if l["verbo"] == "reopen"]
    if not abrir or abrir[0]["donde"] != "tmux":
        fallos.append(f"con un lanzador y filas sin modelo aparece un cuadro: {abrir!r}")

    # 3. Una tecla cualquiera cancela.
    llam, _f = corre([ESPACIO, R, ord("z"), Q], tres)
    if [l for l in llam if l["verbo"] == "reopen"]:
        fallos.append("una tecla cualquiera abrio igual")

    # 4. Un numero sin lanzador detras tampoco abre nada.
    llam, _f = corre([ESPACIO, R, ord("9"), Q], tres)
    if [l for l in llam if l["verbo"] == "reopen"]:
        fallos.append("un numero sin lanzador detras abrio algo")

    # 5. Cabe en pantallas pequenas.
    for h, w in ((12, 40), (18, 62), (24, 112)):
        _l, fuera = corre([ESPACIO, R, UNO, Q], tres, h, w)
        if fuera:
            fallos.append(f"[{w}x{h}] el cuadro se sale: {fuera[:2]}")

    # 6. El `ejecutar` de la demo acepta el parametro nuevo. Es el de `--demo`, que se
    #    monta en `main()` y no en el selector: tenia dos parametros y ahora recibe tres.
    import inspect
    fuente = (RAIZ / "sereno").read_text()
    if "ejecutar=lambda verbo, sel, donde=None, modelo=None:" not in fuente:
        fallos.append("el ejecutar de la demo no acepta `donde` y `modelo`: "
                      "`r` revienta en --demo")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_donde_abrir" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
