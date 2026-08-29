#!/usr/bin/env python3
"""`--watch` avisa cuando el contexto de una sesion cruza un escalon, y solo entonces.

El aviso llega tarde o no llega: las dos formas de fallar son silenciosas. Por eso esto
no se conforma con probar la funcion pura — monta un transcript de verdad en un HOME de
mentira y comprueba que el porcentaje sale de los MISMOS campos que pinta la lista. Si
`filas_json` renombra `context_max`, el aviso deja de existir sin que nada se queje, y
es este bloque el que lo caza.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID = "0123abcd-4567-89ef-0123-456789abcdef"


def escribe(t, leidos):
    """Un transcript minimo cuyo ultimo turno declara `leidos` tokens de contexto."""
    lineas = [
        {"type": "user", "cwd": "/tmp/proyecto", "gitBranch": "main",
         "message": {"role": "user", "content": "haz algo"}},
        {"type": "assistant", "message": {
            "role": "assistant", "model": "claude-opus-5",
            "usage": {"cache_read_input_tokens": leidos, "input_tokens": 20},
            "content": [{"type": "text", "text": "ya esta"}]}},
    ]
    t.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-tmp-proyecto"
        proy.mkdir(parents=True)
        t = proy / f"{UUID}.jsonl"
        escribe(t, leidos=185_000)          # 185.020 de 200.000 = 92,5%

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ["SERENO_LANG"] = "en"     # el aviso se compara en ingles, no en el
                                             # idioma que tenga puesto quien lo ejecute
        for v in ("SERENO_DEMO", "SERENO_CTX_MAX", "SERENO_CTX_AVISO"):
            os.environ.pop(v, None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        filas_json, live = ns["filas_json"], ns["live_sessions"]
        nivel, nuevos, esc = ns["nivel_ctx"], ns["contextos_nuevos"], ns["escalones_ctx"]

        # ── la cadena entera: disco -> pulso -> filas_json -> escalon ──────────
        filas = filas_json(live(fino=True, solo_activas=False))
        if len(filas) != 1:
            print(f"FALLA: el HOME de mentira no da 1 sesion, da {len(filas)}")
            return 1
        if filas[0]["context_max"] != 200_000:
            fallos.append(f"tope {filas[0]['context_max']}, se esperaba 200000")
        if nivel(filas[0]) != 90:
            fallos.append(f"al 92,5% el escalon es {nivel(filas[0])}, se esperaba 90")

        # ── el bucle de verdad: la primera vuelta calla y la segunda avisa ────
        # Se corre `watch()` entero con la lista pinchada, en vez de fiarse de que
        # alguien recuerde envolver la llamada en el guarda de la primera vuelta.
        import contextlib, io

        vueltas, dormidas, TOPE_VUELTAS = [], [], [2]

        class _Reloj:
            strftime = staticmethod(time.strftime)

            @staticmethod
            def sleep(_s):
                dormidas.append(1)
                if len(dormidas) >= TOPE_VUELTAS[0]:    # y fuera del bucle
                    raise KeyboardInterrupt

        guardado = (ns["filas_json"], ns["live_sessions"], ns["time"], ns["notifica"])
        ns["filas_json"] = lambda rows: rows
        ns["live_sessions"] = lambda **kw: vueltas[-1]
        ns["time"] = _Reloj
        ns["notifica"] = lambda *a: None
        salida = io.StringIO()
        vueltas.append(filas)                     # ya cruzada desde el principio
        try:
            with contextlib.redirect_stdout(salida):
                ns["watch"](cada=0)
        except KeyboardInterrupt:
            pass
        if "% of its context" in salida.getvalue():
            fallos.append("la primera vuelta avisa del contexto, y no debe")

        vueltas.clear()
        dormidas.clear()
        vueltas.append([dict(filas[0], context_tokens=100_000)])   # 50%: nada que decir
        salida = io.StringIO()

        def _siguiente(**kw):
            v = vueltas[-1]
            vueltas.append(filas)                 # la segunda vuelta ya va al 92,5%
            return v

        ns["live_sessions"] = _siguiente
        try:
            with contextlib.redirect_stdout(salida):
                ns["watch"](cada=0)
        except KeyboardInterrupt:
            pass
        if "92" in salida.getvalue():
            fallos.append("el aviso dice el porcentaje exacto, no el escalon cruzado")
        if "90% of its context" not in salida.getvalue():
            fallos.append(f"el bucle no avisa al cruzar: {salida.getvalue()!r}")

        # Y lo que solo se ve corriendo el bucle: una sesion que compacta y vuelve a
        # llenarse avisa DOS veces. Si el nivel guardado fuera el maximo historico en
        # vez del de ahora, el segundo aviso no llegaria nunca y nada mas lo notaria.
        TOPE_VUELTAS[0] = 3
        secuencia = [filas,                                        # 92,5%: avisa
                     [dict(filas[0], context_tokens=60_000)],      # compacta: calla
                     filas]                                        # otra vez: avisa
        dormidas.clear()
        salida = io.StringIO()
        ns["live_sessions"] = lambda **kw: secuencia[min(len(dormidas), 2)]
        try:
            with contextlib.redirect_stdout(salida):
                ns["watch"](cada=0)
        except KeyboardInterrupt:
            pass
        if salida.getvalue().count("% of its context") != 1:
            fallos.append("tras compactar y volver a llenarse no avisa otra vez: "
                          f"{salida.getvalue()!r}")
        ns["filas_json"], ns["live_sessions"], ns["time"], ns["notifica"] = guardado

        # ── el flanco, sobre filas sinteticas: lo que se prueba es cuando avisa ──
        def fila(ctx, tope=200_000, ident=UUID):
            return {"id": ident, "title": "t", "project": "p",
                    "context_tokens": ctx, "context_max": tope}

        justa = [fila(170_000)]            # 85% -> ha pasado el 80
        muy_justa = [fila(190_000)]        # 95% -> ha pasado el 90
        holgada = [fila(100_000)]          # 50% -> ningun escalon

        if nivel(holgada[0]) != 0:
            fallos.append("una sesion al 50% ya cuenta como cruzada")
        salta = nuevos({}, justa)
        if [p for _r, p in salta] != [80]:
            fallos.append(f"no avisa del primer escalon: {salta!r}")
        # Media hora al 85% es UN aviso, no uno por vuelta del bucle.
        if nuevos({UUID: 80}, justa):
            fallos.append("repite el aviso mientras sigue en el mismo escalon")
        # Pero subir del 80 al 90 si es noticia nueva.
        salta = nuevos({UUID: 80}, muy_justa)
        if [p for _r, p in salta] != [90]:
            fallos.append(f"no avisa al subir de escalon: {salta!r}")
        # Y compactar baja el nivel solo, asi que el siguiente cruce vuelve a avisar.
        if nivel(holgada[0]) != 0:
            fallos.append("tras compactar el nivel no vuelve a cero")
        if [p for _r, p in nuevos({UUID: 0}, justa)] != [80]:
            fallos.append("tras compactar no vuelve a avisar al cruzar otra vez")

        # ── lo que no consta no avisa: `None` es "no se midio", no cero ────────
        if nivel(fila(190_000, tope=None)) != 0:
            fallos.append("avisa de una sesion cuyo tope no consta")
        if nivel(fila(None)) != 0:
            fallos.append("avisa de una sesion cuyo contexto no consta")

        # ── los escalones son configurables, y se pueden apagar ────────────────
        casos = {"": (80, 90), "70,85": (70, 85), "0": (), "off": (),
                 "95": (95,), "90,70": (70, 90), "150,60": (60,)}
        for crudo, espera in casos.items():
            esc.__dict__.pop("_v", None)
            if crudo:
                os.environ["SERENO_CTX_AVISO"] = crudo
            else:
                os.environ.pop("SERENO_CTX_AVISO", None)
            if esc() != espera:
                fallos.append(f"SERENO_CTX_AVISO={crudo!r} da {esc()}, se esperaba {espera}")
        os.environ["SERENO_CTX_AVISO"] = "0"
        esc.__dict__.pop("_v", None)
        if nivel(fila(199_000)) != 0 or nuevos({}, [fila(199_000)]):
            fallos.append("apagado con SERENO_CTX_AVISO=0 y sigue avisando")
        os.environ.pop("SERENO_CTX_AVISO", None)
        esc.__dict__.pop("_v", None)

        # La frase existe en los dos idiomas: sin ella el aviso reventaria al salir.
        clave = "{hora}  ▰ {t} is at {p}% of its context{d}"
        if clave not in ns["TEXTOS"]["es"]:
            fallos.append("falta la traduccion del aviso de contexto")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: avisa al cruzar el escalon, calla dentro de el y se puede apagar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
