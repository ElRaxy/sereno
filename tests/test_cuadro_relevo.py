#!/usr/bin/env python3
"""El cuadro que pregunta a donde va el relevo: cabe, elige y no entrega sin permiso.

`c` abria ventanas de otro CLI de un teclazo, sin confirmar y sin decir a cual iba —
cogia el primero del PATH. Y la conversacion del relevo se pedia con una variable de
entorno (`SERENO_RELEVO=completo`) que no descubre nadie que no lea el README.

Lo que se vigila aqui, y por que cada cosa:

  1. **que quepa.** curses no avisa cuando un cuadro no cabe: un `newwin` mas ancho que
     la pantalla y un `addnstr` fuera del borde devuelven bien, y el texto se pierde en
     silencio. Se comprueba con el doble de curses, que apunta lo que cae fuera.
  2. **que la eleccion llegue entera** — destino Y conversacion — a `relevo()`.
  3. **que una tecla cualquiera cancele** sin entregar nada.
"""
import contextlib, io, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
os.environ.pop("SERENO_RELEVO", None)
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

ESPACIO, C, K, UNO, DOS, Q = 32, ord("c"), ord("k"), ord("1"), ord("2"), ord("q")
# En el CI no hay ningun CLI instalado, asi que sin esto `destinos_de_relevo` sale vacio
# y el cuadro no llega a abrirse: el test pasaria sin probar nada.
ns["arneses_disponibles"] = lambda: ["codex", "claude"]


def corre(teclas, h=30, w=150, conserva=False):
    """Conduce el selector con esas teclas. Devuelve (llamadas a relevo, celdas fuera)."""
    # Las preferencias van a un temporal y se borran entre casos: si no, la eleccion de
    # un caso cambia el ORDEN de los destinos del siguiente —que es justo lo que se
    # acaba de anadir— y los casos se contaminan entre si. Ademas, un test no escribe en
    # el HOME de nadie.
    import tempfile
    if not conserva:
        ns["PREFS"] = pathlib.Path(tempfile.mkdtemp()) / "prefs.json"

    import curses as real
    llamadas, cajon = [], []
    def espia_relevo(sel, arnes=None, con_conversacion=None, lanzador=None):
        llamadas.append({"n": len(sel), "arnes": arnes, "conv": con_conversacion,
                         "donde": lanzador})
        return arnes, "ok"
    ns["relevo"] = espia_relevo
    sys.modules["curses"] = espia(real, h, w, list(teclas), cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](ns["sesiones_demo"]())
    finally:
        sys.modules["curses"] = real
    fuera = cajon[0].fuera if cajon else [("sin pintar",)]
    return llamadas, fuera


def main():
    fallos = []

    # 1. Marcar una, abrir el cuadro y elegir el primer destino. Sin tocar `k`, la
    #    conversacion NO viaja: es el corte que hace seguro dejar el YAML en el disco.
    llam, fuera = corre([ESPACIO, C, UNO, Q])
    if len(llam) != 1:
        fallos.append(f"{len(llam)} relevos con [1], se esperaba 1")
    elif llam[0]["arnes"] != "codex" or llam[0]["conv"] is not False:
        fallos.append(f"con [1] se entrego mal: {llam[0]}")
    if fuera:
        fallos.append(f"el cuadro se sale del marco: {fuera[:2]}")

    # 2. El segundo destino es OTRO. Sin este caso, un bug que devuelva siempre el
    #    primero pasaria el caso 1 igual. Los destinos se fijan aqui porque las filas de
    #    la demo son todas de Claude y su propio CLI no se ofrece —eso lo comprueba el
    #    caso 7—: lo que se mira ahora es el mapeo de la tecla al destino.
    real_destinos = ns["destinos_de_relevo"]
    ns["destinos_de_relevo"] = lambda sel: ["codex", "claude"]
    llam, _f = corre([ESPACIO, C, DOS, Q])
    if not llam or llam[0]["arnes"] != "claude":
        fallos.append(f"con [2] no se eligio el segundo destino: {llam}")
    # Una tecla fuera de la lista no elige nada ni revienta: el cuadro sigue abierto.
    llam, _f = corre([ESPACIO, C, ord("9"), UNO, Q])
    if not llam or llam[0]["arnes"] != "codex":
        fallos.append(f"un numero sin destino no deja el cuadro usable: {llam}")
    ns["destinos_de_relevo"] = real_destinos

    # 3. `k` enciende la conversacion, y llega hasta `relevo()`.
    llam, _f = corre([ESPACIO, C, K, UNO, Q])
    if not llam or llam[0]["conv"] is not True:
        fallos.append(f"[k] no enciende la conversacion: {llam}")

    # 4. Y apaga: dos pulsaciones vuelven al principio. Un toggle que solo encendiera
    #    pasaria el caso 3.
    llam, _f = corre([ESPACIO, C, K, K, UNO, Q])
    if not llam or llam[0]["conv"] is not False:
        fallos.append(f"[k] no apaga lo que encendio: {llam}")

    # 5. Cualquier otra tecla cancela y no entrega nada.
    llam, _f = corre([ESPACIO, C, ord("z"), Q])
    if llam:
        fallos.append(f"una tecla cualquiera entrego igual: {llam}")

    # 6. Y cabe en una ventana pequena, que es donde curses se calla.
    for h, w in ((12, 40), (18, 62), (24, 112)):
        _l, fuera = corre([ESPACIO, C, UNO, Q], h, w)
        if fuera:
            fallos.append(f"[{w}x{h}] el cuadro se sale: {fuera[:2]}")

    # 7. `w` rota el sitio donde se abren las ventanas, la misma pregunta que hace `r`.
    #    Solo aparece con dos o mas sitios; con uno, la tecla no hace nada y el cuadro
    #    no la ofrece. Los sitios se fijan aqui porque en el CI no hay ninguno.
    real_lanz = ns["lanzadores_disponibles"]
    ns["lanzadores_disponibles"] = lambda: ["warp", "tmux", "terminal"]
    llam, _f = corre([ESPACIO, C, UNO, Q])
    if not llam or llam[0]["donde"] != "warp":
        fallos.append(f"sin tocar `w` no se usa el primer sitio: {llam}")
    llam, _f = corre([ESPACIO, C, ord("w"), UNO, Q])
    if not llam or llam[0]["donde"] != "tmux":
        fallos.append(f"[w] no rota al segundo sitio: {llam}")
    llam, _f = corre([ESPACIO, C, ord("w"), ord("w"), ord("w"), UNO, Q])
    if not llam or llam[0]["donde"] != "warp":
        fallos.append(f"[w] no vuelve al principio al dar la vuelta: {llam}")
    # Con un solo sitio la tecla no existe: `w` cae en "cualquier otra tecla" y cancela.
    ns["lanzadores_disponibles"] = lambda: ["warp"]
    llam, _f = corre([ESPACIO, C, ord("w"), UNO, Q])
    if llam:
        fallos.append(f"con un solo sitio `w` hace algo en vez de cancelar: {llam}")
    ns["lanzadores_disponibles"] = real_lanz

    # 8. El cuadro RECUERDA. No basta con que el fichero de preferencias funcione —eso
    #    lo prueba `test_prefs_y_ausentes`—: hay que ver que el cuadro lo lee y lo
    #    escribe. Se elige el segundo destino y a la vuelta siguiente ese tiene que ser
    #    el [1]. Y el sitio elegido con `w` tiene que seguir puesto sin volver a tocarlo.
    ns["destinos_de_relevo"] = lambda sel: ["codex", "claude"]
    ns["lanzadores_disponibles"] = lambda: ["warp", "tmux", "terminal"]
    llam, _f = corre([ESPACIO, C, ord("w"), DOS, Q])          # -> claude, en tmux
    if not llam or llam[0]["arnes"] != "claude" or llam[0]["donde"] != "tmux":
        fallos.append(f"la primera eleccion no sale como se pidio: {llam}")
    llam, _f = corre([ESPACIO, C, UNO, Q], conserva=True)     # el [1] ya deberia ser claude
    if not llam or llam[0]["arnes"] != "claude":
        fallos.append(f"el cuadro no recuerda el destino: [1] dio {llam}")
    if not llam or llam[0]["donde"] != "tmux":
        fallos.append(f"el cuadro no recuerda donde abrirlas: {llam}")
    ns["destinos_de_relevo"] = real_destinos
    ns["lanzadores_disponibles"] = real_lanz

    # 9. Y quien decide los destinos: el CLI de origen no se ofrece, pero solo si lo es
    #    de TODAS. Con la seleccion mezclada se ofrecen los dos, porque alguna fila puede
    #    ir a cada uno.
    def fila(fuente):
        return {"name": "n", "title": "t", "fuente": fuente, "meta": {}}
    casos = [(["claude"], ["codex"]),
             (["codex"], ["claude"]),
             (["historial"], ["codex"]),          # historial es Claude parado
             (["claude", "codex"], ["codex", "claude"])]
    for fuentes, esperado in casos:
        sale = real_destinos([fila(f) for f in fuentes])
        if sale != esperado:
            fallos.append(f"destinos de {fuentes}: {sale}, se esperaba {esperado}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_cuadro_relevo" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
