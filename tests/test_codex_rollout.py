#!/usr/bin/env python3
"""Relevar DESDE Codex lee su rollout, no se queda en "sin datos".

Codex guarda la sesion en otro formato —`response_item` con `payload`— y en otro sitio
que Claude. Hasta que `detalles()` aprendio a leerlo, relevar una sesion de Codex daba un
briefing vacio: ni lo ultimo que se le pidio, ni lo que respondio, ni que estaba haciendo.
Quien recibia el relevo abria sin nada con que seguir — el fallo que se vio el 2026-09-02
relevando una sesion de Codex a Claude.

El rollout de verdad pesa megas (se han medido 61 MB), asi que se lee SOLO la cola. Aqui
se planta uno pequeno con la MISMA forma —`session_meta`, mensajes de `input_text` /
`output_text`, un `custom_tool_call` con el comando dentro de un trozo de JS— y se
comprueba que el briefing sale con el ultimo intercambio y la traza, en los dos cortes que
importan: por defecto lleva la conversacion, y `SERENO_RELEVO=seco` la quita dejando los
hechos.
"""
import json
import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID = "01a05bac-cd72-7403-8423-7d1ecec1d3b5"        # 36 caracteres, como los de Codex


def escribe_rollout(path, cwd):
    """Un rollout minimo con la forma real: la cabecera trae cwd y rama; luego el ultimo
    intercambio y dos llamadas, una `exec` con su comando y una `function_call`."""
    ev = [
        {"type": "session_meta",
         "payload": {"cwd": cwd, "git": {"branch": "feature/login"}}},
        {"type": "response_item",
         "payload": {"type": "message", "role": "user",
                     "content": [{"type": "input_text",
                                  "text": "arregla el login intermitente"}]}},
        {"type": "response_item",
         "payload": {"type": "message", "role": "assistant",
                     "content": [{"type": "output_text",
                                  "text": "El plan: hacer idempotente el webhook. "
                                          "Siguiente paso F13."}]}},
        {"type": "response_item",
         "payload": {"type": "custom_tool_call", "name": "exec",
                     "input": "const r = await tools.exec_command("
                              "{\"cmd\":\"pytest -q tests/webhooks\"})"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "wait_agent",
                     "arguments": "{\"timeout_ms\":30000}"}},
    ]
    path.write_text("\n".join(json.dumps(e) for e in ev))


def main():
    os.environ["SERENO_DEMO"] = "1"
    os.environ.pop("SERENO_RELEVO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    detalles, briefing = ns["detalles"], ns["briefing"]
    fallos = []

    with tempfile.TemporaryDirectory() as tmp:
        roll = pathlib.Path(tmp) / "rollout.jsonl"
        escribe_rollout(roll, tmp)

        # 1. `detalles()` de una fila de Codex saca del rollout lo mismo que de un
        #    transcript de Claude: rama, ultimo prompt, ultima respuesta y traza.
        fila = {"name": "cx-1", "title": "Retoma B", "title_full": "Retoma B",
                "fuente": "codex",
                "meta": {"cwd": tmp, "_rama": "feature/login", "_rollout": roll}}
        d = detalles(fila)
        if "login intermitente" not in (d.get("lastPrompt") or ""):
            fallos.append(f"no saca el ultimo prompt del rollout: {d.get('lastPrompt')!r}")
        if "idempotente el webhook" not in (d.get("resp") or ""):
            fallos.append(f"no saca la ultima respuesta: {d.get('resp')!r}")
        if d.get("gitBranch") != "feature/login":
            fallos.append(f"no saca la rama: {d.get('gitBranch')!r}")
        ruta = d.get("ruta") or []
        if len(ruta) != 2:
            fallos.append(f"la traza tiene {len(ruta)} eventos, se esperaban 2")
        elif "pytest -q tests/webhooks" not in ruta[0]["res"]:
            fallos.append(f"el comando del exec no sale en la traza: {ruta[0]['res']!r}")

        # 2. El briefing por defecto ES un traspaso: lleva ese intercambio y la traza, para
        #    que la sesion nueva pueda seguir. Y dice que viene de Codex.
        b = briefing(fila)
        for aguja, que in (("login intermitente", "el prompt"),
                           ("idempotente el webhook", "la respuesta"),
                           ("pytest", "la traza"), ("Codex", "de donde viene")):
            if aguja not in b:
                fallos.append(f"el briefing de una fila de Codex no lleva {que}")

        # 3. `SERENO_RELEVO=seco` deja solo hechos: ni prompt ni respuesta, pero la rama y
        #    el proyecto siguen. Es la salida cuando en esa sesion hay trabajo de cliente.
        os.environ["SERENO_RELEVO"] = "seco"
        fila_s = dict(fila, _det=None)
        fila_s.pop("_det")                     # que `detalles` vuelva a mirar
        s = briefing(fila_s)
        os.environ.pop("SERENO_RELEVO", None)
        if "idempotente el webhook" in s or "login intermitente" in s:
            fallos.append("SERENO_RELEVO=seco sigue metiendo la conversacion")
        if "feature/login" not in s:
            fallos.append("SERENO_RELEVO=seco se lleva por delante tambien los hechos")

        # 4. `_cwd_codex` lee cwd Y rama de la cabecera, y trae la ruta del rollout: es lo
        #    que engancha lo de arriba a una fila real. Se apunta CODEX_SESIONES a un arbol
        #    con la forma que glob espera (`*/*/*/rollout-*.jsonl`) y el uuid al final.
        arbol = pathlib.Path(tmp) / "2026" / "01" / "01"
        arbol.mkdir(parents=True)
        dest = arbol / ("rollout-2026-01-01T00-00-00-" + UUID + ".jsonl")
        escribe_rollout(dest, tmp)
        real = ns["CODEX_SESIONES"]
        ns["CODEX_SESIONES"] = pathlib.Path(tmp)
        try:
            info = ns["_cwd_codex"]([UUID]).get(UUID) or {}
        finally:
            ns["CODEX_SESIONES"] = real
        if info.get("cwd") != tmp:
            fallos.append(f"_cwd_codex no saca el cwd de la cabecera: {info.get('cwd')!r}")
        if info.get("rama") != "feature/login":
            fallos.append(f"_cwd_codex no saca la rama de la cabecera: {info.get('rama')!r}")
        if info.get("rollout") != dest:
            fallos.append("_cwd_codex no devuelve la ruta del rollout")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_codex_rollout" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
