#!/usr/bin/env python3
"""Una sesion que nunca recibio una respuesta cae al fondo de la lista.

En esta maquina son 21 de 39 filas del historial —16 de ellas la misma sesion que arranco y murio
en el acto con `API Error: 401 · Please run /login`, cero tokens—, asi que mas de la mitad de la
lista de "a cual vuelvo" eran sesiones a las que no se puede volver, compitiendo por arriba con las
de verdad porque acababan de morir y por tanto eran las mas recientes.

Tres capas, que se rompen por separado:

1. `vacia()` en aislado: el hecho y sus tres formas de NO cumplirse.
2. `ordena()`: caen al fondo en los CINCO modos, y por debajo de los huecos.
3. El cableado, con el doble de `stdscr`: que la fila gris se pinte abajo del todo.

El caso esta elegido para que todas las vias alternativas apunten a lo contrario: la fila vacia es
la MAS RECIENTE de las tres (`idle=0`), asi que el orden por actividad —el de por defecto— la
pondria la PRIMERA. Que salga la ultima solo puede venir de `vacia`. Y su nombre es el primero
alfabeticamente, que es el desempate, para que tampoco explique el resultado.
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

vacia, ordena = ns["vacia"], ns["ordena"]
Q = ord("q")


def uso(turnos=40, pico=200_000, completo=True):
    return {"in": pico, "out": 0, "cw": 0, "cr": 0, "turnos": turnos, "compacta": 0,
            "ctx": pico, "pico": pico, "modelo": "claude-opus-5", "ventana_1m": True,
            "activo": 600.0, "usd": None, "completo": completo}


def fila(name, fuente="historial", u=None, idle=100):
    return {"name": name, "title": name, "title_full": name, "fuente": fuente,
            "idle": idle, "attached": False, "mem_mb": 100, "proyecto": "p", "rama": "",
            "created": 0, "working": False, "meta": {}, "pid": "",
            "pulso": {"escribe": False, "herramienta": False, "ctx": (u or {}).get("ctx"),
                      "modelo": "claude-opus-5", "ventana_1m": True},
            "_uso": u}


def el_hecho(f):
    f(vacia(fila("a", u=uso(turnos=1, pico=0))) == 1,
      "historial + leido entero + cero contexto en toda su vida = vacia")
    f(vacia(fila("a", u=uso(turnos=0, pico=0))) == 1, "ni un turno tambien es vacia")

    # Las tres formas de NO estar vacia. Cada una por su cuenta tiene que bastar.
    f(vacia(fila("a", u=uso(turnos=1, pico=12_000))) == 0,
      "si alguna respuesta consumio tokens, la sesion arranco")
    f(vacia(fila("a", u=uso(turnos=1, pico=0, completo=False))) == 0,
      "a medio leer, un 0 significa 'aun no se sabe', no 'no hay nada'")
    f(vacia(fila("a", u=None)) == 0, "sin transcript que leer no se puede afirmar nada")
    f(vacia(fila("a", u={})) == 0, "un uso vacio tampoco afirma nada")

    # Y la guarda que salva a la sesion que acabas de lanzar. Medido: habia una viva con 23
    # segundos de vida y cero tokens que sin esto se iba al fondo de la lista.
    for fuente in ("claude", "codex", "gemini"):
        f(vacia(fila("a", fuente=fuente, u=uso(turnos=0, pico=0))) == 0,
          "una fila de %s no se marca aunque este a cero: aun no ha contestado" % fuente)


def el_orden(f):
    # `z-viva` va DESPUES alfabeticamente y tiene MAS idle: las dos vias alternativas la
    # ponen detras. Si sale delante es por `vacia` y solo por `vacia`.
    v = fila("a-vacia", u=uso(turnos=1, pico=0), idle=0)
    viva = fila("z-viva", u=uso(turnos=90, pico=300_000), idle=900)
    hueco = fila("m-hueco", u=None, idle=400)
    hueco["pulso"]["ctx"] = None
    hueco["mem_mb"] = None
    hueco["proyecto"] = ""

    for modo in ns["MODOS_ORDEN"]:
        for invertido in (False, True):
            out = ordena([v, viva, hueco], modo, invertido)
            f(out[-1] is v, "modo %s%s: la vacia tiene que quedar la ultima, quedo %r"
                            % (modo, " invertido" if invertido else "",
                               [r["name"] for r in out]))
    # Y por DEBAJO del hueco: un hueco es una sesion real cuyo dato no consta.
    out = ordena([v, viva, hueco], "context")
    f(out.index(hueco) < out.index(v),
      "un hueco va por encima de una vacia: %r" % [r["name"] for r in out])
    # Control positivo: sin la marca, el orden por actividad la pondria la primera.
    f(ordena([dict(v, _uso=uso(turnos=1, pico=1)), viva, hueco], "activity")[0]["name"]
      == "a-vacia", "con un token dentro, la mas reciente vuelve a ir la primera")


def el_cableado(f):
    import curses as real
    base = [r for r in ns["sesiones_demo"]() if r.get("fuente", "claude") == "claude"][:2]
    if len(base) < 2:
        f(False, "la demo tiene que dar dos filas de claude")
        return
    v = dict(base[0]); v["fuente"] = "historial"; v["idle"] = 0
    v["_uso"] = uso(turnos=1, pico=0)
    otra = dict(base[1]); otra["idle"] = 900
    otra["_uso"] = uso(turnos=90, pico=300_000)

    cajon, guardado = [], ns["uso_de"]
    ns["uso_de"] = lambda r, tope=None: r.get("_uso")
    sys.modules["curses"] = espia(real, 32, 170, [Q], cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"]([v, otra])
    finally:
        sys.modules["curses"] = real
        ns["uso_de"] = guardado
    p = cajon[0]
    celdas = p.celdas or p.fotogramas[-1]
    filas = [l for l in ("".join(celdas.get((y, x), " ") for x in range(170)).rstrip()
                         for y in range(32)) if v["title"][:12] in l or otra["title"][:12] in l]
    f(len(filas) >= 2, "esperaba las dos filas pintadas, salieron %d" % len(filas))
    if len(filas) < 2:
        return
    f(otra["title"][:12] in filas[0],
      "arriba va la que si arranco: %r" % filas[0][:60])
    f(v["title"][:12] in filas[1],
      "la vacia va debajo aunque sea la mas reciente: %r" % filas[1][:60])


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    el_hecho(f)
    el_orden(f)
    el_cableado(f)
    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos else "ok: las vacias caen al fondo")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
