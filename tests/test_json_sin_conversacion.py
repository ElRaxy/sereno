#!/usr/bin/env python3
"""`--json` no saca ni una linea de conversacion, y sus campos son de tipo cerrado.

Un `--json` acaba en barras de estado, en scripts de terceros y en pipes que nadie
previo. El panel puede ensenar el ultimo prompt porque lo esta mirando una persona
delante de su propia pantalla; una salida canalizable, no. Este test es lo que sostiene
esa promesa cuando alguien anada un campo mas dentro de seis meses.

Y sostiene la otra mitad del contrato: `schema`. La version del programa no sirve para
saber si los campos siguen ahi —sube por un color o por un texto—, asi que quien
consume esto necesita un numero que solo se mueva cuando algo deja de estar. La lista
de abajo ES el esquema 1: quitar un campo o cambiarle el tipo sin subir el numero
rompe a un tercero en silencio, y aqui se para antes.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

SECRETO = "CANARIO-CONVERSACION-QUE-NO-DEBE-SALIR"
CAMPOS = {
    # `id` es la clave de la fila (nombre de tmux en una viva, uuid en una del
    # historial) y `session_id` es el id de la sesion de Claude, el que se le pasa a
    # `--resume`. Van los dos porque no son lo mismo, y confundirlos era un bug.
    "id": str, "session_id": str,
    "title": str, "project": str, "branch": str, "source": str,
    "state": str, "writing": bool, "tool_pending": bool, "turn_closed": bool,
    "idle_seconds": int,
    "attached": bool, "cwd_exists": bool,
    "memory_mb": int, "context_tokens": int, "context_max": int,
    "model": str, "pid": str,
    # El acumulado. `null` sin `--usage`, que es como corre este test.
    "input_tokens": int, "output_tokens": int, "cache_write_tokens": int,
    "cache_read_tokens": int, "assistant_turns": int, "compactions": int,
    "peak_context_tokens": int,
    "working_seconds": int, "api_cost_usd": float,
    # Con quien choca y cuanto, en cifras. Nunca la RUTA: un path de cliente
    # dice tanto como una frase de la conversacion, y esto se canaliza.
    "clash_level": int, "clash_with": str, "clash_files": int,
    "clash_command": str,
    # Enum cerrado y en ingles. Nunca el comando que se atasca, que si sale en el panel.
    "stuck": list,
}
ESTADOS = {"writing", "in_command", "waiting", "stopped", "unknown"}

# Version del contrato que describe la tabla CAMPOS de arriba. Si este test falla por
# un campo que falta o cambia de tipo, el arreglo no es tocar la tabla y ya: es subir
# `ESQUEMA_JSON` en `sereno` y aqui, porque alguien ahi fuera lee esos campos.
ESQUEMA = 1
# Lo que envuelve a las filas. Ni una clave mas: un consumidor que haga
# `for s in d["sessions"]` no puede encontrarse otra cosa donde no la espera.
SOBRE = {"sereno": str, "schema": int, "sessions": list}


def main():
    fallos = []
    fila = {
        "name": "una-sesion", "title": "t", "title_full": "t", "idle": 12.7,
        "attached": True, "mem_mb": 512.4, "pid": "999", "proyecto": "p", "rama": "b",
        "fuente": "claude", "created": 0, "meta": {"cwd": "/x", "lastPrompt": SECRETO},
        "pulso": {"escribe": False, "herramienta": False, "ctx": 176_000,
                  "modelo": "claude-opus-5", "lastPrompt": SECRETO, "aiTitle": "t"},
        # Lo que `detalles()` deja pegado a la fila cuando ya se ha mirado el panel.
        "_det": {"lastPrompt": SECRETO, "resp": SECRETO, "tool": SECRETO,
                 # El recorrido lleva comandos dentro: que no se escape por --json.
                 "ruta": [{"res": SECRETO}]},
    }
    (salida,) = ns["filas_json"]([fila])

    if SECRETO in str(salida):
        fallos.append("el JSON lleva conversacion dentro")
    sobran = set(salida) - set(CAMPOS)
    if sobran:
        fallos.append(f"campos no declarados: {sorted(sobran)} "
                      "(anadelos a este test y confirma que no llevan conversacion)")
    faltan = set(CAMPOS) - set(salida)
    if faltan:
        fallos.append(f"campos que desaparecieron: {sorted(faltan)} — eso ROMPE a "
                      f"quien lea el esquema {ESQUEMA}: sube ESQUEMA_JSON en `sereno` "
                      "y aqui, y dilo en el CHANGELOG")
    for k, tipo in CAMPOS.items():
        v = salida.get(k)
        if v is not None and not isinstance(v, tipo):
            fallos.append(f"{k} es {type(v).__name__}, se esperaba {tipo.__name__} o null")
    if salida.get("state") not in ESTADOS:
        fallos.append(f"estado fuera del enum: {salida.get('state')!r}")

    # ── el sobre: lo que envuelve a las filas, y el numero de contrato ──────
    if ns["ESQUEMA_JSON"] != ESQUEMA:
        fallos.append(f"el programa dice esquema {ns['ESQUEMA_JSON']} y este test "
                      f"describe el {ESQUEMA}: uno de los dos se quedo atras")
    import io, json as _json, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["print_json"]([fila])
    try:
        sobre = _json.loads(buf.getvalue())
    except Exception as e:
        sobre = None
        fallos.append(f"lo que imprime --json no es JSON: {e}")
    if sobre is not None:
        if set(sobre) != set(SOBRE):
            fallos.append(f"el sobre de --json cambio: sobran "
                          f"{sorted(set(sobre) - set(SOBRE))}, faltan "
                          f"{sorted(set(SOBRE) - set(sobre))}")
        for k, tipo in SOBRE.items():
            if k in sobre and not isinstance(sobre[k], tipo):
                fallos.append(f"sobre.{k} es {type(sobre[k]).__name__}, se esperaba "
                              f"{tipo.__name__}")
        if sobre.get("schema") != ESQUEMA:
            fallos.append(f"--json anuncia esquema {sobre.get('schema')!r} y no "
                          f"{ESQUEMA}")
        if SECRETO in buf.getvalue():
            fallos.append("lo que imprime --json lleva conversacion dentro")

    # Y sobre las filas de la demo, que pasan por todas las ramas de estado.
    for r in ns["sesiones_demo"]():
        e = ns["estado_estable"](r)
        if e not in ESTADOS:
            fallos.append(f"demo {r['name']}: estado {e!r} fuera del enum")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"ok: esquema {ESQUEMA}, {len(CAMPOS)} campos tipados, enum cerrado, "
          "cero conversacion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
