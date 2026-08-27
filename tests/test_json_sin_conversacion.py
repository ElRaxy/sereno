#!/usr/bin/env python3
"""`--json` no saca ni una linea de conversacion, y sus campos son de tipo cerrado.

Un `--json` acaba en barras de estado, en scripts de terceros y en pipes que nadie
previo. El panel puede ensenar el ultimo prompt porque lo esta mirando una persona
delante de su propia pantalla; una salida canalizable, no. Este test es lo que sostiene
esa promesa cuando alguien anada un campo mas dentro de seis meses.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

SECRETO = "CANARIO-CONVERSACION-QUE-NO-DEBE-SALIR"
CAMPOS = {
    "id": str, "title": str, "project": str, "branch": str, "source": str,
    "state": str, "writing": bool, "tool_pending": bool, "idle_seconds": int,
    "attached": bool, "memory_mb": int, "context_tokens": int, "context_max": int,
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
        fallos.append(f"campos que desaparecieron: {sorted(faltan)}")
    for k, tipo in CAMPOS.items():
        v = salida.get(k)
        if v is not None and not isinstance(v, tipo):
            fallos.append(f"{k} es {type(v).__name__}, se esperaba {tipo.__name__} o null")
    if salida.get("state") not in ESTADOS:
        fallos.append(f"estado fuera del enum: {salida.get('state')!r}")

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
    print(f"ok: {len(CAMPOS)} campos tipados, enum cerrado, cero conversacion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
