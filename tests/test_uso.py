#!/usr/bin/env python3
"""El acumulado no cuenta dos veces la misma respuesta, y no suma lo que no debe.

Este test existe por dos hechos medidos sobre los transcripts de verdad, no por
prudencia. El primero: una respuesta del agente ocupa VARIAS lineas del jsonl —un
`thinking` y dos `tool_use` van en tres— y las tres repiten el MISMO `usage`. Sumarlas
todas inflaba la salida entre un +49% y un +123% segun la sesion. El segundo:
`cache_read_input_tokens` es cien veces mayor que todo lo demas (300M frente a 3M en una
sesion de ocho horas), asi que cualquier total que lo mezcle con la entrada es un numero
enorme que no significa nada.

Y ademas se comprueba lo que hace barata la feature: leer solo lo nuevo desde el offset
anterior tiene que dar EXACTAMENTE lo mismo que leer el fichero de una vez, incluso si el
ultimo refresco pillo una linea a medio escribir.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
_uso, _CACHE_USO, VIVA = ns["_uso"], ns["_CACHE_USO"], ns["VIVA"]


def resp(mid, ts, out=100, cr=50_000, cw=1_000, ent=2, bloque="text"):
    """Una linea de respuesta del agente, con su `usage`."""
    return json.dumps({
        "type": "assistant", "timestamp": ts,
        "message": {"id": mid, "role": "assistant", "model": "claude-opus-5",
                    "content": [{"type": bloque, "text": "x"}],
                    "usage": {"input_tokens": ent, "output_tokens": out,
                              "cache_creation_input_tokens": cw,
                              "cache_read_input_tokens": cr}}})


def T(mm, ss=0):
    return "2026-08-26T10:%02d:%02dZ" % (mm, ss)


def escribe(p, lineas, final="\n"):
    p.write_bytes(("\n".join(lineas) + final).encode())
    _CACHE_USO.clear()


def main():
    fallos = []

    def igual(caso, dado, esperado):
        if dado != esperado:
            fallos.append(f"{caso}: {dado!r} != {esperado!r}")

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)

        # 1. Tres lineas de la MISMA respuesta cuentan UNA vez. Es el fallo que inflaba
        #    la salida hasta un +123% en los transcripts reales.
        p = d / "dedup.jsonl"
        escribe(p, [resp("msg_A", T(0), bloque="thinking"),
                    resp("msg_A", T(0), bloque="tool_use"),
                    resp("msg_A", T(0), bloque="tool_use"),
                    resp("msg_B", T(1))])
        u = _uso(p)
        igual("turnos con ids repetidos", u["turnos"], 2)
        igual("salida sin duplicar", u["out"], 200)
        igual("cache escrita sin duplicar", u["cw"], 2_000)

        # 2. La cache LEIDA va en su campo y no se mezcla con la entrada. Si algun dia
        #    alguien la suma "para tener un total", esto se cae.
        igual("entrada nueva", u["in"], 4)
        igual("cache leida aparte", u["cr"], 100_000)
        if u["in"] >= u["cr"]:
            fallos.append("la entrada absorbio la cache leida")

        # 3. Los huecos entre respuestas se topan en `VIVA`. Una sesion que estuvo dos
        #    horas parada y volvio NO ha trabajado dos horas.
        p = d / "ritmo.jsonl"
        escribe(p, [resp("m1", T(0)), resp("m2", T(0, 30)), resp("m3", T(50))])
        u = _uso(p)
        igual("trabajo con un hueco corto y otro larguisimo", round(u["activo"]),
              30 + VIVA)

        # 4. Compactaciones: son lo que explica una barra de contexto baja.
        p = d / "compacta.jsonl"
        escribe(p, [resp("m1", T(0)),
                    json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": {"preTokens": 400_000}}),
                    resp("m2", T(1)),
                    json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": {"preTokens": 380_000}})])
        igual("compactaciones contadas", _uso(p)["compacta"], 2)

        # 5. El dinero no se calcula: se relata el que escribio el propio CLI. Y si no
        #    hay linea `cost-state`, es None y no cero.
        p = d / "coste.jsonl"
        escribe(p, [resp("m1", T(0))])
        igual("sin cost-state no hay dinero", _uso(p)["usd"], None)
        escribe(p, [resp("m1", T(0)),
                    json.dumps({"type": "cost-state", "totalCostUSD": 88.5,
                                "modelUsage": {}})])
        igual("cost-state relatado tal cual", _uso(p)["usd"], 88.5)

        # 6. Lectura incremental: leer solo lo nuevo da EXACTAMENTE lo mismo que leer de
        #    una vez. Es lo que hace que el refresco cueste 2,6 ms en vez de 268.
        p = d / "inc.jsonl"
        escribe(p, [resp("m1", T(0)), resp("m2", T(1))])
        _uso(p)                                    # deja el offset puesto
        with p.open("ab") as f:
            f.write((resp("m3", T(2)) + "\n").encode())
        os.utime(p, None)
        incremental = dict(_uso(p))
        _CACHE_USO.clear()
        de_una_vez = dict(_uso(p))
        for k in ("in", "out", "cw", "cr", "turnos", "compacta", "activo"):
            igual(f"incremental vs completo: {k}", incremental[k], de_una_vez[k])

        # 7. La ultima linea a medias NO se consume. Una sesion viva escribe mientras la
        #    lees, y consumir media linea perderia esos tokens para siempre.
        p = d / "medias.jsonl"
        entera = resp("m9", T(3))
        escribe(p, [resp("m1", T(0))], final="\n")
        with p.open("ab") as f:
            f.write(entera[:20].encode())          # media linea, sin salto
        os.utime(p, None)
        _CACHE_USO.clear()
        parcial = dict(_uso(p))
        igual("la linea a medias no cuenta todavia", parcial["turnos"], 1)
        _uso(p)
        with p.open("ab") as f:
            f.write((entera[20:] + "\n").encode())
        os.utime(p, None)
        completado = dict(_uso(p))
        _CACHE_USO.clear()
        igual("al completarse, cuenta una vez", completado["turnos"], 2)
        igual("y coincide con leerlo entero", completado["out"], _uso(p)["out"])

        # 8. Fichero reescrito mas corto: se rehace desde cero. Aqui la cache NO se
        #    limpia a proposito — el caso que se prueba es justamente que el offset
        #    guardado ya no apunta a donde creia.
        p = d / "rehecho.jsonl"
        escribe(p, [resp("m1", T(0)), resp("m2", T(1)), resp("m3", T(2))])
        igual("antes de reescribir", _uso(p)["turnos"], 3)
        time.sleep(0.01)
        p.write_bytes((resp("z1", T(0)) + "\n").encode())   # sin `escribe()`: cache viva
        os.utime(p, None)
        igual("fichero encogido: se rehace", _uso(p)["turnos"], 1)

        # 9. Sin transcript no hay cero: hay None. Una fila de otro CLI no gasto 0 tokens,
        #    es que no lo sabemos, y quien lo lea tiene que poder distinguirlo.
        igual("fichero que no existe", _uso(d / "no-existe.jsonl"), None)
        fila = {"meta": {}}
        igual("fila sin transcript", ns["uso_de"](fila), None)

        # 10. `--json` sin `--usage` deja los ocho campos a null, no a cero.
        fila = {"name": "s", "title_full": "t", "proyecto": "p", "rama": "b",
                "fuente": "claude", "idle": 1.0, "attached": False, "mem_mb": None,
                "pid": "", "meta": {}, "pulso": {"escribe": False, "herramienta": False}}
        (salida,) = ns["filas_json"]([fila])
        for k in ("input_tokens", "output_tokens", "cache_write_tokens",
                  "cache_read_tokens", "assistant_turns", "compactions",
                  "working_seconds", "api_cost_usd"):
            if k not in salida:
                fallos.append(f"falta el campo {k!r} en --json")
            elif salida[k] is not None:
                fallos.append(f"{k} vale {salida[k]!r} sin --usage: tiene que ser null")
        if "total_tokens" in salida:
            fallos.append("hay un total agregado: la cache leida no se suma con la entrada")

    for f in fallos:
        print("FALLO:", f)
    print("ok: se deduplica por respuesta, la cache leida va aparte y lo incremental "
          "cuadra con lo completo" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
