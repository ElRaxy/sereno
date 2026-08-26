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

    # La propiedad que de verdad importa, sobre todo el rango: pase lo que pase, la
    # barra no puede pasar del 100%. Si algun dia se anade un tope intermedio, esto
    # sigue vigilando el invariante sin tener que reescribir los casos de arriba.
    for modelo in ("claude-opus-5", "claude-opus-5[1m]", "claude-sonnet-5", ""):
        for ctx in (1, 1_000, 199_999, 200_001, 560_080, 999_999):
            pct = 100 * ctx / tope(modelo, ctx)
            if pct > 100:
                fallos.append(f"{modelo or 'sin modelo'} con {ctx:,} pinta {pct:.0f}%")

    # Y en la lista, las filas de la demo tampoco.
    for r in ns["sesiones_demo"]():
        pu = r["pulso"]
        ctx = pu.get("ctx")
        if ctx and 100 * ctx / tope(pu.get("modelo"), ctx) > 100:
            fallos.append(f"demo {r['name']} pinta mas del 100%")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: el tope sale de la cascada y ninguna fila pasa del 100%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
