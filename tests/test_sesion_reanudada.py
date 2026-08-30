#!/usr/bin/env python3
"""Una sesion reanudada se sigue hasta el fichero que escribe AHORA.

El registro guarda el sessionId de arranque. Al reanudar (`--continue`, `--resume`),
Claude Code empieza un transcript NUEVO con otro id y el registro no se entera: la fila
se quedaba congelada en la ultima actividad del fichero viejo. Visto el 2026-08-26 en
tres sesiones a la vez; una llevaba seis minutos trabajando y figuraba parada desde
hacia tres horas, con el contexto al 12% mientras el propio CLI mostraba 41%.

El enlace es exacto: el transcript nuevo copia las lineas del viejo y esas lineas
conservan su `session_id` original, aunque el `sessionId` de la linea ya sea el nuevo.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
VIEJO = "aaaaaaaa-1111-2222-3333-444444444444"
NUEVO = "bbbbbbbb-5555-6666-7777-888888888888"
OTRO = "cccccccc-9999-0000-1111-222222222222"


def linea(session_id, texto, heredada_de=None):
    """Una linea del transcript. `heredada_de` reproduce lo que hace el CLI al
    reanudar: la linea viaja al fichero nuevo con su `session_id` original dentro."""
    j = {"type": "assistant", "sessionId": session_id, "cwd": "/home/u/proyecto",
         "message": {"role": "assistant", "model": "claude-opus-5",
                     "usage": {"cache_read_input_tokens": 1000},
                     "content": [{"type": "text", "text": texto}]}}
    if heredada_de:
        j["session_id"] = heredada_de
    return json.dumps(j)


def escribe(p, lineas, edad=0):
    p.write_text("\n".join(lineas) + "\n")
    if edad:
        os.utime(p, (time.time() - edad, time.time() - edad))


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-home-u-proyecto"
        proy.mkdir(parents=True)
        reg = casa / "reg"
        (reg / "live").mkdir(parents=True)   # el registro cuelga de `live/`

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_REGISTRY"] = str(reg)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        vivo, VIVA = ns["transcript_vivo"], ns["VIVA"]

        entrada = {"id": VIEJO, "project_dir": str(proy), "cwd": "/home/u/proyecto"}
        viejo_p, nuevo_p, otro_p = (proy / f"{s}.jsonl" for s in (VIEJO, NUEVO, OTRO))

        # 1. Mientras el registrado siga escribiendo, no se busca nada.
        escribe(viejo_p, [linea(VIEJO, "trabajando")])
        if vivo(entrada) != viejo_p:
            fallos.append("con el registrado fresco deberia devolverlo tal cual")

        # 2. Registrado rancio y sin sucesor: se queda con el registrado.
        escribe(viejo_p, [linea(VIEJO, "hace rato")], edad=VIVA + 600)
        ns["_SUCESOR"].clear()
        if vivo(entrada) != viejo_p:
            fallos.append("sin sucesor deberia devolver el registrado, no None")

        # 3. Hay sucesor: se sigue la cadena.
        escribe(nuevo_p, [linea(NUEVO, "vieja", heredada_de=VIEJO),
                          linea(NUEVO, "y sigo trabajando")])
        ns["_SUCESOR"].clear()
        if vivo(entrada) != nuevo_p:
            fallos.append(f"no sigue al sucesor: devuelve {vivo(entrada)}")

        # 4. Un transcript ajeno y mas nuevo NO se roba la sesion: sin la firma, no
        #    hay parentesco, por reciente que sea.
        escribe(otro_p, [linea(OTRO, "otra sesion cualquiera")])
        ns["_SUCESOR"].clear()
        if vivo(entrada) != nuevo_p:
            fallos.append("se lleva un transcript ajeno solo por ser mas reciente")

        # 5. Cadena de dos saltos: gana el ultimo, no el intermedio.
        escribe(nuevo_p, [linea(NUEVO, "vieja", heredada_de=VIEJO)], edad=VIVA + 300)
        tercero = proy / "dddddddd-3333-4444-5555-666666666666.jsonl"
        escribe(tercero, [linea("dddddddd-3333-4444-5555-666666666666", "v", heredada_de=VIEJO),
                          linea("dddddddd-3333-4444-5555-666666666666", "lo ultimo")])
        ns["_SUCESOR"].clear()
        if vivo(entrada) != tercero:
            fallos.append(f"con dos saltos deberia ganar el ultimo, da {vivo(entrada)}")

        # 6. Y la fila que sale del registro apunta ya al fichero resuelto.
        (reg / "live" / "1234-1000.env").write_text(
            f"id={VIEJO}\nproject_dir={proy}\ncwd=/tmp/proyecto\npid=1234\n"
            f"title=X\ntmux_session=cc-X-{VIEJO[:8]}\ntmux_socket=no-existe\n")
        ns["_SUCESOR"].clear()
        metas = ns["meta_by_tmux"]()
        e = next(iter(metas.values()), {})
        if e.get("_transcript") != tercero:
            fallos.append(f"meta_by_tmux no resuelve: {e.get('_transcript')}")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: sigue la reanudacion, y no se lleva transcripts ajenos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
