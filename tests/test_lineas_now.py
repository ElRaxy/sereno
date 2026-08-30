#!/usr/bin/env python3
"""La vista de todas: UN solo compositor, y lo que dice cada linea.

`lineas_now` lo pintan dos sitios —`--now` por la terminal y la pantalla `n` del
selector— para que no acaben diciendo cosas distintas de los mismos hechos.
`test_vista_now.py` comprueba que esa pantalla se abre, pinta y se cierra, tambien en
una ventana pequena. Lo que el texto DICE no lo miraba nadie: de los cambios minimos
probados sobre este compositor, todos pasaban los 53 tests en verde.

Y el texto es lo unico que queda cuando esto sale por una tuberia: el color se pierde,
asi que un estado que solo viviera en el par de color dejaria nueve lineas identicas.
Por eso el estado va escrito, y por eso se comprueba aqui.
"""
import os
import pathlib
import sys

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_LANG"] = "en"
RAIZ = pathlib.Path(__file__).resolve().parent.parent


def fila(estado="waiting", titulo="una sesion", proyecto="", idle=None,
         eventos=(), atasco=(), sintomas=None):
    return {"estado": estado, "titulo": titulo, "id": "id-largo-de-sesion",
            "proyecto": proyecto, "idle": idle, "eventos": list(eventos),
            "atasco": list(atasco),
            "sintomas": sintomas or {"fallos_seguidos": 3,
                                     "busquedas_sin_resultado": 2}}


def evento(res="git status", dur=4.0, pend=False, err=False, vacio=False):
    return {"res": res, "dur": dur, "pend": pend, "err": err, "vacio": vacio,
            "t0": None}


def textos(lineas):
    return [t for t, _par in lineas]


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ln = ns["lineas_now"]
    fallos = []

    def comprueba(que, cond, extra=""):
        if not cond:
            fallos.append(que + (": " + extra if extra else ""))

    # ── control positivo: si el compositor devolviera vacio, media prueba de
    #    abajo —"esto NO aparece"— pasaria sola ────────────────────────────────
    base = textos(ln([fila(titulo="la sesion de prueba")], 40))
    if not any("la sesion de prueba" in t for t in base):
        print("FALLO: el titulo de la sesion no aparece: %r" % (base,))
        return 1

    # ── la cabecera reparte: cuantas trabajan y cuantas te esperan ────────────
    # Es la unica linea que se lee de un vistazo desde otra ventana. Invertida, dice
    # que puedes irte a comer cuando en realidad hay tres esperandote.
    tres = textos(ln([fila("writing"), fila("in_command"), fila("waiting")], 40))[0]
    comprueba("la cabecera no cuenta bien las vivas", "3 live" in tres, tres)
    comprueba("la cabecera no cuenta bien las que trabajan",
              "2 working" in tres, tres)
    comprueba("la cabecera no cuenta bien las que te esperan",
              "1 waiting" in tres, tres)
    solo_parada = textos(ln([fila("stopped")], 40))[0]
    comprueba("una sesion parada cuenta como trabajando",
              "0 working" in solo_parada and "1 waiting" in solo_parada, solo_parada)

    # ── el estado va en TEXTO, no solo en color ──────────────────────────────
    largo = ns["ESTADO_LARGO"]
    for estado in ("writing", "in_command", "waiting", "stopped"):
        t = " ".join(textos(ln([fila(estado)], 40)))
        comprueba("el estado %r no se escribe en ninguna linea" % estado,
                  largo(estado) in t)
    dos = {largo(e) for e in ("writing", "waiting")}
    comprueba("dos estados distintos se escriben igual", len(dos) == 2)

    # ── el 'hace tanto' solo tiene sentido en la que NO trabaja ──────────────
    parada = " ".join(textos(ln([fila("waiting", idle=3600)], 40)))
    trabaja = " ".join(textos(ln([fila("writing", idle=3600)], 40)))
    comprueba("una sesion parada no dice desde cuando",
              ns["_hace"](3600) in parada, parada[:80])
    comprueba("una sesion que trabaja dice 'hace tanto', que ahi no significa nada",
              ns["_hace"](3600) not in trabaja, trabaja[:80])

    # ── titulo y proyecto en la MISMA linea, y recortados al ancho ───────────
    ancho = 30
    con_proy = textos(ln([fila(titulo="t" * 200, proyecto="VanguardIA")], ancho))
    cuerpo = [t for t in con_proy if "tt" in t]
    comprueba("el titulo no se pinta", cuerpo)
    if cuerpo:
        comprueba("el proyecto gasta un renglon propio", len(cuerpo) == 1,
                  "%d lineas lo llevan" % len(cuerpo))
        comprueba("el titulo se sale del ancho pedido",
                  cuerpo[0].index("  ") <= ancho,
                  "la parte de titulo mide %d" % cuerpo[0].index("  "))
    corto = textos(ln([fila(titulo="corto", proyecto="VanguardIA")], ancho))
    comprueba("el proyecto no aparece junto al titulo",
              any("corto" in t and "VanguardIA" in t for t in corto), repr(corto))

    # ── una sesion sin llamadas lo DICE, no se queda muda ────────────────────
    muda = textos(ln([fila()], 40))
    comprueba("una sesion sin llamadas no dice que no las tiene",
              any("no tool calls" in t for t in muda), repr(muda))
    con_una = textos(ln([fila(eventos=[evento("git status")])], 40))
    comprueba("la llamada no se pinta", any("git status" in t for t in con_una))
    comprueba("se dice 'sin llamadas' habiendolas",
              not any("no tool calls" in t for t in con_una))

    # ── el atasco se avisa, y con su cifra ───────────────────────────────────
    # Es lo unico de esta pantalla que pide hacer algo. Callarlo la deja en un informe.
    at = textos(ln([fila(atasco=["bucle"],
                         sintomas={"fallos_seguidos": 3,
                                   "busquedas_sin_resultado": 2})], 40))
    comprueba("el atasco de bucle no se avisa",
              any("failed 3 times" in t for t in at), repr(at))
    at2 = textos(ln([fila(atasco=["barrido"],
                          sintomas={"fallos_seguidos": 3,
                                    "busquedas_sin_resultado": 2})], 40))
    comprueba("el atasco de barrido no se avisa",
              any("2 searches in a row" in t for t in at2), repr(at2))
    comprueba("se avisa de un atasco que no consta",
              not any("failed" in t for t in textos(ln([fila()], 40))))

    for f in fallos:
        print("FALLO:", f)
    print("ok" if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
