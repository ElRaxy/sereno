#!/usr/bin/env python3
"""Lo que nacio en un directorio temporal no cuenta como trabajo — y se dice.

En la maquina donde se escribio esto, 46 de las 200 filas del historial no eran sesiones
de nadie: eran un optimizador de skills lanzandose a si mismo, veintidos veces "Score how
well the response satisfies…" y veintidos "Complete the following task…". Ocupaban el
tope de la lista, salian en `--hoy` y metian proyectos como `skillopt_sleep_claude_ylulwmwr`
en el reparto de `--disk`.

Lo que se prueba aqui es el CRITERIO, que es lo unico que puede envenenarse: se miran por
donde nacieron —su `cwd` cuelga del temporal del sistema— y no por lo que dicen. Filtrar
por el titulo seria adivinar, y cambiaria con cada version del script que las lanza.

Y el reverso, que importa igual: una sesion de verdad NO puede desaparecer por esto. El
caso del final monta las dos y comprueba que solo se cae la desechable.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID_REAL = "0123abcd-4567-89ef-0123-456789abcdef"
UUID_TIRAR = "9923abcd-4567-89ef-0123-456789abcdef"


def escribe(t, cwd):
    lineas = [{"type": "user", "cwd": cwd, "gitBranch": "main",
               "message": {"role": "user", "content": "haz algo"}},
              {"type": "assistant", "message": {
                  "role": "assistant", "model": "claude-opus-5",
                  "usage": {"cache_read_input_tokens": 1000, "input_tokens": 20},
                  "content": [{"type": "text", "text": "ya esta"}]}}]
    t.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        # El proyecto se aplana sustituyendo `/` por `-`: asi es como el CLI nombra la
        # carpeta, y es lo que el filtro mira sin abrir el fichero.
        real = casa / ".claude/projects/-home-u-proyecto"
        tirar = casa / ".claude/projects/-private-var-folders-c6-x-T-skillopt-sleep-claude-x"
        real.mkdir(parents=True); tirar.mkdir(parents=True)
        escribe(real / f"{UUID_REAL}.jsonl", "/home/u/proyecto")
        escribe(tirar / f"{UUID_TIRAR}.jsonl",
                "/private/var/folders/c6/x/T/skillopt_sleep_claude_x")

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        tirable = ns["de_usar_y_tirar"]

        # ── 1. el criterio, ruta a ruta ───────────────────────────────────────
        casos = [
            ("/private/var/folders/c6/x/T/skillopt_x", True),
            ("/tmp/lo-que-sea", True),
            ("/var/folders/abc/T/algo", True),
            ("/Users/alex/Desktop/VanguardIA", False),
            ("/home/u/proyecto", False),
            ("", False),                       # no consta no es "temporal"
            ("/var/folders2/no-es-temporal", False),   # el prefijo no basta: va por tramo
            ("/tmpfs/proyecto", False),
        ]
        for ruta, espera in casos:
            if tirable(ruta) != espera:
                fallos.append(f"de_usar_y_tirar({ruta!r}) = {tirable(ruta)}, "
                              f"se esperaba {espera}")
        # `TMPDIR` cuenta aunque no sea ninguno de los fijos: en macOS es una carpeta
        # por usuario dentro de /var/folders, y en otra maquina puede ser cualquier cosa.
        os.environ["TMPDIR"] = "/mi/temporal/raro"
        ns["_raices_temporales"].__dict__.pop("_v", None)
        if not tirable("/mi/temporal/raro/una-sesion"):
            fallos.append("TMPDIR no cuenta como temporal")
        if tirable("/mi/temporal"):
            fallos.append("el padre de TMPDIR cuenta como temporal, y no lo es")
        os.environ.pop("TMPDIR")
        ns["_raices_temporales"].__dict__.pop("_v", None)

        # ── 2. la cadena entera: historial, jornada y peso ────────────────────
        filas = ns["sesiones_de_disco"](limite=40)
        ids = {f["name"] for f in filas}
        if UUID_TIRAR in ids:
            fallos.append("una sesion nacida en un temporal se ofrece para reanudar")
        if UUID_REAL not in ids:
            fallos.append("el filtro se llevo por delante una sesion de verdad")

        j = ns["jornada"](corte=0)
        if any(s["id"] == UUID_TIRAR for s in j["sesiones"]):
            fallos.append("una sesion de usar y tirar cuenta como trabajo del dia")
        if not any(s["id"] == UUID_REAL for s in j["sesiones"]):
            fallos.append("la sesion de verdad no cuenta en la jornada")

        h = ns["peso_historial"]()
        if h["de_usar_y_tirar"] != 1:
            fallos.append(f"--disk cuenta {h['de_usar_y_tirar']} desechables, se esperaba 1")
        if h["sesiones"] != 1:
            fallos.append(f"--disk cuenta {h['sesiones']} sesiones, se esperaba 1")
        if not h["bytes_de_usar_y_tirar"]:
            fallos.append("--disk no dice lo que pesan las desechables")
        # Y no ensucian el reparto por proyecto con nombres que no son de nadie.
        if any("skillopt" in e["proyecto"] for e in h["por_proyecto"]):
            fallos.append("un proyecto temporal entra en el reparto de --disk")

        # ── 3. --find las salta, y lo DICE (callar seria lo de siempre) ───────
        res = ns["buscar"]("haz algo")
        if any(r["name"] == UUID_TIRAR for r, _a in res):
            fallos.append("--find busca en las de usar y tirar sin --all")
        if not any(r["name"] == UUID_REAL for r, _a in res):
            fallos.append("--find deja de encontrar lo que si es trabajo")
        res_todo = ns["buscar"]("haz algo", todo=True)
        if not any(r["name"] == UUID_TIRAR for r, _a in res_todo):
            fallos.append("--find --all sigue sin mirarlas, y --all es 'mira todo'")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_de_usar_y_tirar" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
