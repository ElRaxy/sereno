#!/usr/bin/env python3
"""`--watch` avisa en el flanco, no por el estado, y la primera vuelta calla.

El fallo de un vigilante es silencioso por definicion: si no avisa, no pasa nada
visible y te enteras cuando ya llevabas media hora sin mirar. Asi que esto recorre la
cadena entera —transcript en disco -> pulso -> estado -> transicion— sobre un HOME de
mentira, en vez de fiarse de que las piezas encajan.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID = "0123abcd-4567-89ef-0123-456789abcdef"


def escribe(t, pendiente):
    """Un transcript minimo. `pendiente=True` deja un tool_use sin su tool_result:
    eso es "corriendo un comando", que es justo lo que el mtime NO distingue."""
    lineas = [
        {"type": "user", "cwd": "/home/u/proyecto", "gitBranch": "main",
         "message": {"role": "user", "content": "haz algo"}},
        {"type": "assistant", "message": {
            "role": "assistant", "model": "claude-opus-5",
            "usage": {"cache_read_input_tokens": 120000, "input_tokens": 20},
            "content": [{"type": "tool_use", "id": "tu_1", "name": "Bash",
                         "input": {"command": "pytest"}}]}},
    ]
    if not pendiente:
        lineas += [
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"}]}},
            {"type": "assistant", "message": {
                "role": "assistant", "model": "claude-opus-5",
                "usage": {"cache_read_input_tokens": 140000, "input_tokens": 30},
                "content": [{"type": "text", "text": "ya esta"}]}},
        ]
    t.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-home-u-proyecto"
        proy.mkdir(parents=True)
        t = proy / f"{UUID}.jsonl"
        escribe(t, pendiente=True)

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        filas_json, live, trans = ns["filas_json"], ns["live_sessions"], ns["transiciones"]

        v1 = filas_json(live(fino=True, solo_activas=False))
        if len(v1) != 1:
            print(f"FALLA: el HOME de mentira no da 1 sesion, da {len(v1)}")
            return 1
        if v1[0]["state"] != "in_command":
            fallos.append(f"con un tool_use sin resultado el estado es "
                          f"{v1[0]['state']!r}, se esperaba 'in_command'")
        if v1[0]["context_tokens"] != 120020:
            fallos.append(f"contexto {v1[0]['context_tokens']}, se esperaba 120020")

        # La primera vuelta no avisa aunque haya sesiones: solo fija la linea base.
        if trans({}, v1):
            fallos.append("la primera vuelta avisa, y no debe")

        # Termina el comando, contesta, y pasa un rato sin escribir nada.
        escribe(t, pendiente=False)
        viejo = time.time() - 300
        os.utime(t, (viejo, viejo))
        ns["_CACHE_DISCO"].clear()
        v2 = filas_json(live(fino=True, solo_activas=False))
        if v2[0]["state"] != "waiting":
            fallos.append(f"tras contestar el estado es {v2[0]['state']!r}, "
                          "se esperaba 'waiting'")

        antes = {r["id"]: r["state"] for r in v1}
        salta = trans(antes, v2)
        if len(salta) != 1:
            fallos.append(f"el flanco no se detecta: {len(salta)} avisos")
        elif salta[0]["id"] != UUID:
            fallos.append(f"avisa de otra sesion: {salta[0]['id']}")

        # Y no se repite en la vuelta siguiente: el aviso es del cambio, no del estado.
        if trans({r["id"]: r["state"] for r in v2}, v2):
            fallos.append("repite el aviso mientras la sesion sigue esperando")

        # ── el tercer flanco: que una sesion empiece a dar vueltas ─────────────
        # No hace falta un transcript atascado de verdad: `atascos_nuevos` es pura y lo
        # que se prueba es el flanco, no la deteccion (esa la cubre test_recorrido).
        an = ns["atascos_nuevos"]
        limpia = [dict(v2[0], stuck=[])]
        con_bucle = [dict(v2[0], stuck=["loop"])]
        con_las_dos = [dict(v2[0], stuck=["loop", "sweep"])]
        if an({}, limpia):
            fallos.append("avisa de una sesion que no esta atascada")
        salta = an({UUID: []}, con_bucle)
        if [a for _r, a in salta] != ["loop"]:
            fallos.append(f"el flanco del atasco no se detecta: {salta!r}")
        # Veinte minutos dando vueltas son UN aviso, no uno por vuelta del bucle.
        if an({UUID: ["loop"]}, con_bucle):
            fallos.append("repite el aviso mientras la sesion sigue en bucle")
        # Pero empezar ADEMAS a barrer si es nuevo, y se dice.
        salta = an({UUID: ["loop"]}, con_las_dos)
        if [a for _r, a in salta] != ["sweep"]:
            fallos.append(f"no avisa del aviso nuevo que se suma: {salta!r}")
        # Cada clave del enum publico tiene su frase, o el aviso reventaria al salir.
        for clave in ("loop", "sweep"):
            if clave not in ns["_AVISO_WATCH"]:
                fallos.append(f"falta la frase de --watch para {clave!r}")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: avisa en el flanco, calla en la primera vuelta y no repite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
