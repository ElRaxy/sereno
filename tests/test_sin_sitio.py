#!/usr/bin/env python3
"""Una sesion cuyo directorio de trabajo ya no existe cae al fondo de la lista.

Es la gemela de `test_sesion_vacia.py` y responde a la misma pregunta —¿se puede volver
aqui?— por el otro lado: aquellas son sesiones que nunca contestaron, estas contestaron
de sobra pero reanudarlas te deja en un `cd` a un sitio que no esta.

En la maquina donde se escribio esto eran **40 de las 46 filas** del historial. Quitando
las 53 sesiones que un optimizador dejo esa manana —para que la cifra no la inflara el
propio trabajo del dia— seguian siendo **28 de 37**, de dos clases concretas: worktrees
ya borradas (10 de 15) y directorios temporales (18 de 18, todos).

Cuatro capas, que se rompen por separado:

1. `hay_sitio()` en aislado, contra directorios de verdad: existe, no existe, revive, y
   las dos formas de "no consta" que NO pueden contar como ausencia.
2. `sin_sitio()`: el hecho, y que una viva no se marca nunca.
3. `ordena()`: cae al fondo en los CINCO modos, debajo de los huecos y ENCIMA de las
   vacias — no tener nada es peor que no tener donde.
4. El cableado, con el doble de `stdscr`: que la fila gris se pinte abajo del todo.

El caso esta elegido para que todas las vias alternativas apunten a lo contrario: la
fila sin sitio es la MAS RECIENTE (`idle=0`), asi que el orden por actividad —el de por
defecto— la pondria la PRIMERA, y su nombre es el primero alfabeticamente, que es el
desempate. Que salga la ultima solo puede venir de `sin_sitio`.
"""
import contextlib, io, os, pathlib, shutil, sys, tempfile

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_DEBUG"] = "1"
os.environ["SERENO_LANG"] = "es"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

hay_sitio, sin_sitio, ordena = ns["hay_sitio"], ns["sin_sitio"], ns["ordena"]
Q = ord("q")


def uso(pico=200_000):
    return {"in": pico, "out": 0, "cw": 0, "cr": 0, "turnos": 40, "compacta": 0,
            "ctx": pico, "pico": pico, "modelo": "claude-opus-5", "ventana_1m": True,
            "activo": 600.0, "usd": None, "completo": True}


def fila(name, fuente="historial", sitio=True, idle=100, u=None):
    return {"name": name, "title": name, "title_full": name, "fuente": fuente,
            "idle": idle, "attached": False, "mem_mb": 100, "proyecto": "p", "rama": "",
            "created": 0, "working": False, "meta": {}, "pid": "", "_sitio": sitio,
            "pulso": {"escribe": False, "herramienta": False,
                      "ctx": (u or uso()).get("ctx"),
                      "modelo": "claude-opus-5", "ventana_1m": True},
            "_uso": u or uso()}


def el_disco(f):
    """`hay_sitio` contra el disco de verdad, que es lo unico que puede decir la verdad."""
    d = tempfile.mkdtemp()
    try:
        ns["_CACHE_SITIO"].clear()
        f(hay_sitio(d) is True, "un directorio que existe tiene que dar True")

        # El cache es por RUTA y con TTL. Sin limpiarlo, el borrado no se ve todavia —y
        # eso es lo correcto: es el precio de no hacer un `stat` cuatro veces por segundo.
        shutil.rmtree(d)
        f(hay_sitio(d) is True, "dentro del TTL sigue valiendo lo ultimo que se vio")
        ns["_CACHE_SITIO"].clear()
        f(hay_sitio(d) is False, "pasado el TTL, un directorio borrado da False")

        # Y revive: una worktree que vuelves a crear vuelve a la lista sin reiniciar nada.
        os.makedirs(d)
        ns["_CACHE_SITIO"].clear()
        f(hay_sitio(d) is True, "si el directorio vuelve, la sesion vuelve a tener sitio")

        # Las dos formas de "no consta". Ninguna puede contar como ausencia: marcar una
        # sesion por un dato que falta es el error contrario al que esto arregla.
        f(hay_sitio("") is True, "sin ruta no se puede afirmar que no exista")
        f(hay_sitio(None) is True, "un cwd ausente tampoco afirma nada")

        # Un fichero NO es un directorio al que volver.
        fich = os.path.join(d, "x.txt")
        open(fich, "w").close()
        ns["_CACHE_SITIO"].clear()
        f(hay_sitio(fich) is False, "un fichero no es un sitio al que volver")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def el_hecho(f):
    f(sin_sitio(fila("a", sitio=False)) == 1, "historial + directorio ausente = sin sitio")
    f(sin_sitio(fila("a", sitio=True)) == 0, "con directorio, la fila es normal")

    # Sin el campo no se marca: un dato que falta no es un dato malo.
    sin_campo = fila("a")
    del sin_campo["_sitio"]
    f(sin_sitio(sin_campo) == 0, "sin el dato no se puede afirmar que no exista")

    # Las vivas no se marcan NUNCA: su proceso corre dentro de ese directorio.
    for fuente in ("claude", "codex", "gemini", "antigravity"):
        f(sin_sitio(fila("a", fuente=fuente, sitio=False)) == 0,
          "una fila de %s no se marca: su proceso esta dentro de ese directorio" % fuente)


def el_orden(f):
    # `z-normal` va DESPUES alfabeticamente y tiene MAS idle: las dos vias alternativas
    # la ponen detras. Si sale delante es por `sin_sitio` y solo por eso.
    s = fila("a-sin-sitio", sitio=False, idle=0)
    normal = fila("z-normal", idle=900, u=uso(300_000))
    hueco = fila("m-hueco", idle=400, u=None)
    hueco["_uso"] = None
    hueco["pulso"]["ctx"] = None
    hueco["mem_mb"] = None
    hueco["proyecto"] = ""

    for modo in ns["MODOS_ORDEN"]:
        for invertido in (False, True):
            out = ordena([s, normal, hueco], modo, invertido)
            f(out[-1] is s, "modo %s%s: la sin sitio tiene que quedar la ultima, quedo %r"
                            % (modo, " invertido" if invertido else "",
                               [r["name"] for r in out]))

    # Por DEBAJO del hueco: un hueco es una sesion real cuyo dato no consta.
    out = ordena([s, normal, hueco], "context")
    f(out.index(hueco) < out.index(s),
      "un hueco va por encima de una sin sitio: %r" % [r["name"] for r in out])

    # Y por ENCIMA de una vacia: no tener nada es peor que no tener donde.
    v = fila("b-vacia", idle=0)
    v["_uso"] = dict(uso(), pico=0, turnos=1)
    v["pulso"]["ctx"] = 0
    out = ordena([s, v, normal], "activity")
    f(out.index(s) < out.index(v),
      "una sin sitio va por encima de una vacia: %r" % [r["name"] for r in out])

    # CONTROL POSITIVO: sin la marca, el orden por actividad la pondria la PRIMERA. Sin
    # esto, un `ordena` que hundiera cualquier cosa pasaria todo lo de arriba.
    f(ordena([dict(s, _sitio=True), normal, hueco], "activity")[0]["name"] == "a-sin-sitio",
      "con su directorio en pie, la mas reciente vuelve a ir la primera")


def el_cableado(f):
    import curses as real
    base = [r for r in ns["sesiones_demo"]() if r.get("fuente", "claude") == "claude"][:2]
    if len(base) < 2:
        f(False, "la demo tiene que dar dos filas de claude")
        return
    s = dict(base[0]); s["fuente"] = "historial"; s["idle"] = 0; s["_sitio"] = False
    s["_uso"] = uso()
    otra = dict(base[1]); otra["idle"] = 900; otra["_uso"] = uso(300_000)

    cajon, guardado = [], ns["uso_de"]
    ns["uso_de"] = lambda r, tope=None: r.get("_uso")
    sys.modules["curses"] = espia(real, 32, 170, [Q], cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"]([s, otra], vista_inicial="todas")
    finally:
        sys.modules["curses"] = real
        ns["uso_de"] = guardado
    p = cajon[0]
    celdas = p.celdas or p.fotogramas[-1]
    pantalla = ["".join(celdas.get((y, x), " ") for x in range(170)).rstrip()
                for y in range(32)]
    filas = [l for l in pantalla if s["title"][:12] in l or otra["title"][:12] in l]
    if len(filas) < 2:
        f(False, "esperaba las dos filas pintadas, salieron %d" % len(filas))
        return
    f(otra["title"][:12] in filas[0], "arriba va la que si tiene sitio: %r" % filas[0][:60])
    f(s["title"][:12] in filas[1],
      "la sin sitio va debajo aunque sea la mas reciente: %r" % filas[1][:60])

    # Y la cabecera lo DICE, que es la mitad del trato: hundirlas sin contarlas seria
    # esconderlas.
    cab = " ".join(pantalla[:3])
    f("sin sitio al que volver" in cab,
      "la cabecera tiene que contarlas aparte. Decia: %r" % cab[:120])


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    el_disco(f)
    el_hecho(f)
    el_orden(f)
    el_cableado(f)
    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos
          else "ok: las que ya no tienen directorio caen al fondo, la cabecera las cuenta "
               "aparte, y vuelven solas si el directorio vuelve")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
