#!/usr/bin/env python3
"""El porcentaje de contexto nunca miente por arriba, y el tope sale de un hecho.

Este test existe por un fallo concreto: el tope se derivaba del `model` del transcript
—`claude-opus-5[1m]` seria un millon— pero medido sobre 1.500 respuestas reales el
transcript escribe `claude-opus-5` a secas AUNQUE la sesion corra en la ventana larga.
Resultado: sesiones pintadas al 207%. Un porcentaje por encima de 100 no es un detalle
cosmetico, es la prueba de que el denominador es inventado.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"          # que no lea el settings.json de esta maquina
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
tope, CTX_1M, CTX_STD = ns["tope_contexto"], ns["CTX_1M"], ns["CTX_STD"]


def main():
    fallos = []

    def igual(caso, dado, esperado):
        if dado != esperado:
            fallos.append(f"{caso}: {dado:,} != {esperado:,}")

    igual("sin datos", tope("", 0), CTX_STD)
    igual("modelo normal, contexto normal", tope("claude-opus-5", 150_000), CTX_STD)
    igual("sufijo [1m] explicito", tope("claude-opus-5[1m]", 50_000), CTX_1M)
    # La regla que faltaba: el contexto observado corrige al modelo.
    igual("contexto por encima del estandar", tope("claude-opus-5", 560_080), CTX_1M)
    igual("justo en el borde", tope("claude-opus-5", CTX_STD), CTX_STD)
    igual("un token por encima", tope("claude-opus-5", CTX_STD + 1), CTX_1M)
    igual("modelo desconocido", tope("un-modelo-que-no-existe", 10), CTX_STD)
    igual("modelo ausente", tope(None, 10), CTX_STD)

    # La linea `cost-state` que escribe el propio CLI: su `modelUsage` va indexado por
    # `claude-opus-5[1m]`, con el sufijo que `message.model` no trae. Es el unico hecho
    # de la cascada que habla de ESTA sesion y no de la maquina entera.
    igual("cost-state con sufijo", tope("claude-opus-5", 50_000, True), CTX_1M)
    # Y los dos que no deciden nada: `False` es "la escribio y no llevaba sufijo",
    # `None` es "no la escribio". Ninguno de los dos puede subir el tope, y ninguno
    # puede bajarlo por debajo de lo ya observado.
    igual("cost-state sin sufijo", tope("claude-opus-5", 50_000, False), CTX_STD)
    igual("sin cost-state", tope("claude-opus-5", 50_000, None), CTX_STD)
    igual("cost-state sin sufijo no baja lo observado",
          tope("claude-opus-5", 560_080, False), CTX_1M)

    # ── el orden entre la sesion y la maquina (reordenado el 2026-08-27) ────────
    # Con la config global diciendo un millon, una sesion que el CLI apunto SIN sufijo
    # tiene que poder bajar a la estandar: la config es de la maquina, el `cost-state`
    # es de esta sesion. Mientras la config iba delante, esto era imposible y la barra
    # de una sesion de 200k se pintaba sobre un millon — un 6% donde tocaba un 30%.
    ns["_ctx_max_config"].__dict__["_v"] = CTX_1M       # como un settings.json con [1m]
    try:
        igual("la sesion baja lo que dice la maquina",
              tope("claude-opus-5", 60_000, False), CTX_STD)
        igual("y lo sube igual", tope("claude-opus-5", 60_000, True), CTX_1M)
        igual("sin dato de la sesion, manda la maquina",
              tope("claude-opus-5", 60_000, None), CTX_1M)
        igual("el sufijo del transcript tambien es de la sesion",
              tope("claude-opus-5[1m]", 60_000, None), CTX_1M)
        # Pero la guarda gana a todo lo que no sea el usuario: 400k dentro no caben en
        # 200k, diga lo que diga el `cost-state`.
        igual("la guarda corrige a la sesion",
              tope("claude-opus-5", 400_000, False), CTX_1M)
    finally:
        ns["_ctx_max_config"].__dict__["_v"] = None

    # ── el pico: la guarda con memoria ─────────────────────────────────────────
    # Compactar borra la prueba. El contexto cae a 16k y una sesion de un millon pasa a
    # dibujarse contra la ventana estandar: 171k marcaban 86% —"compacta ya"— cuando
    # eran 171k de un millon, un 17%. Medido sobre los 524 transcripts de esta maquina,
    # el pico corrige 30 y los 30 hacia ese lado.
    igual("pico por encima del estandar", tope("claude-opus-5", 16_000, None, 767_648),
          CTX_1M)
    igual("pico que cabe en la estandar no cambia nada",
          tope("claude-opus-5", 16_000, None, 180_000), CTX_STD)
    igual("pico justo en el borde", tope("claude-opus-5", 10, None, CTX_STD), CTX_STD)
    igual("un token por encima", tope("claude-opus-5", 10, None, CTX_STD + 1), CTX_1M)
    # `0` es "no consta" y no decide nada: es lo que vale mientras nadie haya leido el
    # transcript entero, que es el caso normal de la lista.
    igual("sin pico se comporta como antes", tope("claude-opus-5", 50_000, None, 0),
          CTX_STD)
    # Y gana a un `cost-state` que dice que no: 767k dentro no caben en 200k, lo diga
    # quien lo diga. Es la misma guarda de siempre, solo que con memoria.
    igual("el pico corrige al cost-state",
          tope("claude-opus-5", 16_000, False, 767_648), CTX_1M)

    # Y `SERENO_CTX_MAX` sigue mandando sobre las dos, tambien hacia abajo.
    ns["_ctx_max_env"].__dict__["_v"] = 300_000
    try:
        igual("lo que fija el usuario no se discute",
              tope("claude-opus-5[1m]", 60_000, True), 300_000)
        igual("y tampoco lo discute el pico",
              tope("claude-opus-5", 60_000, None, 900_000), 300_000)
    finally:
        ns["_ctx_max_env"].__dict__["_v"] = None

    # La propiedad que de verdad importa, sobre todo el rango: pase lo que pase, la
    # barra no puede pasar del 100%. Si algun dia se anade un tope intermedio, esto
    # sigue vigilando el invariante sin tener que reescribir los casos de arriba.
    for modelo in ("claude-opus-5", "claude-opus-5[1m]", "claude-sonnet-5", ""):
        for ctx in (1, 1_000, 199_999, 200_001, 560_080, 999_999):
            for v1m in (None, True, False):
                for pico in (0, 1, 180_000, 767_648, 999_999):
                    pct = 100 * ctx / tope(modelo, ctx, v1m, pico)
                    if pct > 100:
                        fallos.append(f"{modelo or 'sin modelo'} con {ctx:,}, "
                                      f"ventana_1m={v1m} y pico {pico:,} "
                                      f"pinta {pct:.0f}%")

    # Y en la lista, las filas de la demo tampoco.
    pico_de = ns["pico_de"]
    for r in ns["sesiones_demo"]():
        pu = r["pulso"]
        ctx = pu.get("ctx")
        if ctx and 100 * ctx / tope(pu.get("modelo"), ctx, None, pico_de(r)) > 100:
            fallos.append(f"demo {r['name']} pinta mas del 100%")
    # Y la demo tiene que ENSENAR el caso: una fila que compacto, marca poco contexto y
    # aun asi se dibuja contra el millon porque llego a tener mas de lo que cabe en la
    # estandar. Sin ella, ni las capturas ni el GIF del README lo muestran nunca.
    ensena = [r for r in ns["sesiones_demo"]()
              if (r.get("_uso") or {}).get("compacta")
              and pico_de(r) > CTX_STD
              and (r["pulso"].get("ctx") or 0) < CTX_STD]
    if not ensena:
        fallos.append("la demo no ensena ninguna sesion compactada con pico de 1M")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: el tope sale de la cascada y ninguna fila pasa del 100%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
