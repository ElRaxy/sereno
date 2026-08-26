#!/usr/bin/env python3
"""`--find` busca en lo que se DIJO, no en el fichero.

Medido sobre 506 transcripts reales: buscando una palabra, 287 ficheros la contenian y
solo 25 la tenian en algo dicho por alguien. La diferencia son volcados de `tool_result`
y el CLAUDE.md que el CLI inyecta en cada sesion — con esos dentro, cualquier palabra
del proyecto casa siempre y la busqueda no distingue nada. Este test fija esa frontera.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
AGUJA = "murcielago"
UUID = "0123abcd-4567-89ef-0123-456789abcdef"

LINEAS = [
    # SI: lo tecleo una persona.
    {"type": "user", "cwd": "/tmp/proyecto",
     "message": {"role": "user", "content": f"revisa el {AGUJA} del informe"}},
    # NO: salida de un comando. No lo dijo nadie.
    {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1",
         "content": f"grep: encontrado {AGUJA} en 400 ficheros"}]}},
    # NO: contexto que pega el CLI. Aparece en TODAS las sesiones del proyecto.
    {"type": "user", "message": {"role": "user", "content":
        f"<system-reminder>el proyecto trata sobre el {AGUJA}</system-reminder>"}},
    # NO: un subagente. Su conversacion no es la de esta sesion.
    {"type": "assistant", "isSidechain": True, "message": {
        "role": "assistant", "content": [{"type": "text", "text": f"del {AGUJA} nada"}]}},
    # SI: lo contesto el agente.
    {"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5",
        "usage": {"cache_read_input_tokens": 1000},
        "content": [{"type": "text", "text": f"el {AGUJA} estaba mal contado"}]}},
    # NO: una llamada a herramienta, aunque lleve la palabra en el comando.
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t2", "name": "Bash",
         "input": {"command": f"grep {AGUJA} ."}}]}},
]


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-tmp-proyecto"
        proy.mkdir(parents=True)
        t = proy / f"{UUID}.jsonl"
        t.write_text("\n".join(json.dumps(x) for x in LINEAS) + "\n")

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

        res = ns["buscar"](AGUJA, todo=True)
        if len(res) != 1:
            print(f"FALLA: {len(res)} sesiones, se esperaba 1")
            return 1
        fila, aciertos = res[0]
        quienes = [q for q, _f in aciertos]
        if len(aciertos) != 2:
            fallos.append(f"{len(aciertos)} aciertos, se esperaban 2 "
                          f"(el prompt y la respuesta): {aciertos}")
        if quienes != ["user", "assistant"]:
            fallos.append(f"atribucion mal: {quienes}")
        for _q, frag in aciertos:
            for basura in ("grep:", "<system-reminder>", "nada"):
                if basura in frag:
                    fallos.append(f"se ha colado {basura!r} en un fragmento")

        # Una palabra que SOLO esta en la basura no puede devolver nada.
        if ns["buscar"]("400 ficheros", todo=True):
            fallos.append("encuentra texto que solo esta en un tool_result")
        if ns["buscar"]("trata sobre", todo=True):
            fallos.append("encuentra texto que solo esta en un system-reminder")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: encuentra lo dicho y descarta tool_result, system-reminder y sidechain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
