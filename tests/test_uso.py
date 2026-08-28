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
        # Y el PICO: lo que la sesion tenia dentro justo antes de compactar. Es el unico
        # rastro que sobrevive —las respuestas de despues ya cuentan la ventana nueva— y
        # es de donde sale el tope de una sesion que ya compacto. Sin leerlo, esa sesion
        # se dibuja contra la ventana estandar aunque haya tenido 400k dentro.
        igual("el pico sale del preTokens mayor", _uso(p)["pico"], 400_000)
        # El `usage` de una respuesta tambien cuenta, y ahi el pico es entrada + cache:
        # la salida no viaja de vuelta al modelo y no ocupa ventana.
        p = d / "pico.jsonl"
        escribe(p, [resp("m1", T(0), out=90_000, cr=120_000, cw=5_000, ent=300)])
        igual("el pico de una respuesta no cuenta la salida", _uso(p)["pico"],
              120_000 + 5_000 + 300)
        # Un `compactMetadata` sin `preTokens`, o con basura dentro, no puede tumbar la
        # lectura ni inventarse un pico: es un fichero que escribe otro programa.
        p = d / "pico_roto.jsonl"
        escribe(p, [json.dumps({"type": "system", "subtype": "compact_boundary"}),
                    json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": {"preTokens": "muchos"}}),
                    json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": None})])
        igual("un preTokens que no es un numero no cuenta", _uso(p)["pico"], 0)
        igual("y las compactaciones se cuentan igual", _uso(p)["compacta"], 3)

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
        for k in ("in", "out", "cw", "cr", "turnos", "compacta", "pico", "activo"):
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

        # 7bis. Leer por TROZOS da exactamente lo mismo que leer de una vez, y lo que
        #       vuelve a medias se distingue: `completo` es False mientras falte algo.
        #       Es lo que permite que el selector no de un tiron de 120 ms al llegar con
        #       el cursor a un transcript de 89 MB.
        p = d / "trozos.jsonl"
        escribe(p, [resp(f"m{i}", T(i), out=10 * i, cr=1_000 * i) for i in range(1, 12)]
                + [json.dumps({"type": "system", "subtype": "compact_boundary",
                               "compactMetadata": {"preTokens": 300_000}})])
        entero = dict(_uso(p))
        if not entero["completo"]:
            fallos.append("una lectura sin tope tiene que quedar completa")
        _CACHE_USO.clear()
        vueltas, parcial = 0, None
        while vueltas < 200:
            parcial = _uso(p, 300)             # trozos pequenos a proposito
            vueltas += 1
            if parcial["completo"]:
                break
        if vueltas < 2:
            fallos.append("el tope no partio la lectura: el caso no se prueba")
        for k in ("in", "out", "cw", "cr", "turnos", "compacta", "pico", "activo"):
            igual(f"por trozos vs de una vez: {k}", parcial[k], entero[k])
        # Y el parcial NO se pinta como total: mientras falta, `completo` es False. El
        # pico es la excepcion y por eso se comprueba aparte — solo puede crecer, asi
        # que a medias se queda corto pero nunca se pasa.
        _CACHE_USO.clear()
        primero = _uso(p, 300)
        if primero["completo"]:
            fallos.append("el primer trozo se declara completo")
        if primero["pico"] > entero["pico"]:
            fallos.append("el pico de un parcial se pasa del real")
        if primero["out"] >= entero["out"]:
            fallos.append("el primer trozo ya trae todo: el tope no corta nada")

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

        # 10. `--json` sin `--usage` deja los nueve campos a null, no a cero.
        fila = {"name": "s", "title_full": "t", "proyecto": "p", "rama": "b",
                "fuente": "claude", "idle": 1.0, "attached": False, "mem_mb": None,
                "pid": "", "meta": {}, "pulso": {"escribe": False, "herramienta": False}}
        (salida,) = ns["filas_json"]([fila])
        for k in ("input_tokens", "output_tokens", "cache_write_tokens",
                  "cache_read_tokens", "assistant_turns", "compactions",
                  "peak_context_tokens",
                  "working_seconds", "api_cost_usd"):
            if k not in salida:
                fallos.append(f"falta el campo {k!r} en --json")
            elif salida[k] is not None:
                fallos.append(f"{k} vale {salida[k]!r} sin --usage: tiene que ser null")
        if "total_tokens" in salida:
            fallos.append("hay un total agregado: la cache leida no se suma con la entrada")

        # 11. El cero del coste que no significa cero. El CLI escribe una linea
        #     `cost-state` al cerrar la sesion, y en una cuenta de suscripcion la escribe
        #     con `totalCostUSD: 0` y `modelUsage: {}` — que no es "esta sesion costo
        #     cero", es que ahi no hay contabilidad. Guardarlo como 0.0 le decia a una
        #     statusline que el trabajo salio gratis.
        #
        #     Medido sobre los 878 transcripts de esta maquina antes de tocar nada: 40
        #     lineas con coste > 0, 8 con ese cero sin desglose, y NINGUNA con un cero
        #     legitimo (0 y `modelUsage` lleno). Distinguirlos no pierde un solo caso real.
        def coste(usd, model_usage):
            return json.dumps({"type": "cost-state", "totalCostUSD": usd,
                               "modelUsage": model_usage})

        for caso, usd, mu, esperado in (
            ("cero sin desglose = no consta", 0, {}, None),
            ("un coste de verdad se relata", 1.23, {"claude-opus-5": {"x": 1}}, 1.23),
            ("un cero CON desglose es un cero de verdad", 0, {"claude-opus-5": {"x": 1}}, 0.0),
            ("y sin la clave modelUsage tampoco consta", 0, None, None),
        ):
            p = d / ("coste-%d.jsonl" % abs(hash(caso)))
            linea = (coste(usd, mu) if mu is not None
                     else json.dumps({"type": "cost-state", "totalCostUSD": usd}))
            escribe(p, [resp("msg_A", T(0)), linea])
            igual(caso, (_uso(p) or {}).get("usd"), esperado)

    for f in fallos:
        print("FALLO:", f)
    print("ok: se deduplica por respuesta, la cache leida va aparte y lo incremental "
          "cuadra con lo completo" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
