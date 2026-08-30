#!/usr/bin/env python3
"""`--hoy` cuenta lo tocado desde que empezo el dia, y el dia no empieza a medianoche.

Dos cosas se rompen aqui sin hacer ruido. Una: el corte. A la una y media de la manana,
un dia que empezara a las 00:00 contestaria "nada tocado hoy" justo cuando acabas de
trabajar seis horas — el fallo se ve como una respuesta plausible, no como un error. Dos:
el filtro por mtime, que es lo que hace el comando barato; si deja pasar los transcripts
viejos, `--hoy` cuenta la vida entera y ademas tarda.

Se prueban las dos con relojes y mtimes puestos a mano, que es la unica forma: esperar a
que sean las 04:59 no es un test.
"""
import datetime, json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def escribe(t, texto="haz algo", leidos=40_000, cwd="/tmp/proyecto"):
    lineas = [{"type": "user", "cwd": cwd, "gitBranch": "main",
               "message": {"role": "user", "content": texto}},
              {"type": "assistant", "message": {
                  "role": "assistant", "model": "claude-opus-5",
                  "usage": {"cache_read_input_tokens": leidos, "input_tokens": 20},
                  "content": [{"type": "text", "text": "ya esta"}]}}]
    t.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")


def epoch(dia, hora, minuto=0):
    return datetime.datetime(2026, 8, dia, hora, minuto).timestamp()


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-tmp-proyecto"
        otro = casa / ".claude/projects/-tmp-otro"
        proy.mkdir(parents=True); otro.mkdir(parents=True)
        hoy = proy / "0123abcd-4567-89ef-0123-456789abcdef.jsonl"
        vieja = proy / "1123abcd-4567-89ef-0123-456789abcdef.jsonl"
        lejana = otro / "2123abcd-4567-89ef-0123-456789abcdef.jsonl"
        escribe(hoy); escribe(vieja)
        # El proyecto sale del `cwd` del transcript, no de la carpeta: dos ficheros con
        # el mismo cwd son el MISMO proyecto por mucho que esten en directorios distintos.
        escribe(lejana, cwd="/tmp/otro")

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        for v in ("SERENO_DEMO", "SERENO_JORNADA"):
            os.environ.pop(v, None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        corte_jornada, jornada = ns["corte_jornada"], ns["jornada"]

        # ── 1. el corte: el dia empieza a las cinco, no a medianoche ──────────
        casos = [
            ((20, 13, 0), (20, 5)),      # a mediodia, el dia es el de hoy
            ((20, 1, 30), (19, 5)),      # a la una y media, el dia sigue siendo el de ayer
            ((20, 5, 0), (20, 5)),       # justo a las cinco, ya es hoy
            ((20, 4, 59), (19, 5)),      # un minuto antes, todavia no
        ]
        for (d, h, m), (ed, eh) in casos:
            got = corte_jornada(epoch(d, h, m))
            if got != epoch(ed, eh):
                fallos.append(f"a las {h}:{m:02d} el corte es "
                              f"{time.strftime('%d %H:%M', time.localtime(got))}, "
                              f"se esperaba dia {ed} a las {eh}:00")
        # Y la hora se puede mover.
        os.environ["SERENO_JORNADA"] = "9"
        if corte_jornada(epoch(20, 8, 0)) != epoch(19, 9):
            fallos.append("SERENO_JORNADA=9 no mueve el corte")
        os.environ["SERENO_JORNADA"] = "no-es-una-hora"
        if corte_jornada(epoch(20, 13, 0)) != epoch(20, 5):
            fallos.append("una SERENO_JORNADA invalida no cae a la hora de casa")
        os.environ.pop("SERENO_JORNADA")

        # ── 2. lo que entra y lo que no ───────────────────────────────────────
        ahora = time.time()
        corte = corte_jornada(ahora)
        os.utime(hoy, (corte + 60, corte + 60))          # dentro
        os.utime(vieja, (corte - 3600, corte - 3600))    # justo antes: fuera
        os.utime(lejana, (ahora - 120, ahora - 120))     # dentro, y recien tocada
        ns["_CACHE_DISCO"].clear()
        j = jornada(ahora=ahora)
        if j["n_sesiones"] != 2:
            fallos.append(f"cuenta {j['n_sesiones']} sesiones, se esperaban 2 "
                          "(la de antes del corte no entra)")
        ids = {s["id"] for s in j["sesiones"]}
        if vieja.stem in ids:
            fallos.append("una sesion anterior al corte entra en la jornada")
        if j["n_proyectos"] != 2:
            fallos.append(f"agrupa en {j['n_proyectos']} proyectos, se esperaban 2")
        if j["primera"] is None or j["ultima"] is None or j["primera"] > j["ultima"]:
            fallos.append(f"las horas del dia no cuadran: {j['primera']} {j['ultima']}")

        # ── 3. sin --usage, lo que no se midio es None y NO cero ──────────────
        for s in j["sesiones"]:
            for campo in ("turnos", "activo", "compacta"):
                if s[campo] is not None:
                    fallos.append(f"sin --usage, {campo} vale {s[campo]} y deberia ser None")
        if any(d["turnos"] is not None for d in j["por_proyecto"]):
            fallos.append("sin --usage, el total por proyecto no es None")

        # ── 4. "a medias" es lo que sigue colgando, no todo lo del dia ────────
        # El corte es el MISMO que usa la interfaz (`estado_estable`: te espera hasta las
        # seis horas, parada despues), no uno propio de este comando.
        # El corte de la jornada se pasa a mano (`corte=0`) para que la sesion entre
        # SIEMPRE: si no, una parada de siete horas cae antes del corte por la mañana y
        # el caso no llegaria a probar lo que dice probar.
        for horas, deberia in ((0.03, True), (5, True), (7, False)):
            os.utime(hoy, (ahora - horas * 3600,) * 2)
            ns["_CACHE_DISCO"].clear()
            colgando = {s["id"] for s in jornada(corte=0, ahora=ahora)["a_medias"]}
            if (hoy.stem in colgando) != deberia:
                fallos.append(f"parada hace {horas}h "
                              f"{'no sale' if deberia else 'sale'} como 'a medias'")

        # ── 5. y el comando pinta sin reventar, en los dos idiomas ───────────
        import contextlib, io
        for lang in ("en", "es"):
            ns["LANG_UI"] = lang
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = ns["cmd_hoy"]()
            if codigo != 0:
                fallos.append(f"cmd_hoy sale con {codigo} en {lang}")
            if not salida.getvalue().strip():
                fallos.append(f"cmd_hoy no pinta nada en {lang}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_hoy" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
