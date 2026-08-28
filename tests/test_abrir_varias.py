#!/usr/bin/env python3
"""Abrir varias marcadas escribe el comando de CADA una, no el de la primera.

Habia tres copias del mismo YAML de Warp —abrir una, reabrir varias, y las huerfanas—
y la del medio tenia el comando fijo a `tmux attach`. Con eso, marcar cinco sesiones del
historial y pulsar `r` abria cinco pestanas que fallaban las cinco: `tmux attach -t
<uuid>` no existe, y una pestana que muere al nacer no dice cual era ni por que.

Este test no mira el texto del YAML por gusto: mira que el comando de cada pestana es el
que `_comando_de()` da para ESA fila. Es la unica garantia que se rompio, y se rompe sin
que falle nada visible.
"""
import os, pathlib, re, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def filas():
    """Una de cada tipo, que es donde estaba el fallo: las tres se abren distinto."""
    return [
        {"name": "cc-proyecto-1111aaaa", "title": "una viva", "title_full": "una viva",
         "meta": {"cwd": "/", "id": "1111aaaa-0000-0000-0000-000000000000"}},
        {"name": "2222bbbb-0000-0000-0000-000000000000", "title": "del historial",
         "title_full": "del historial",
         "meta": {"cwd": "/", "id": "2222bbbb-0000-0000-0000-000000000000"}},
        {"name": "3333cccc-0000-0000-0000-000000000000", "title": "de codex",
         "title_full": "de codex", "abrir": ["codex", "resume", "3333cccc"],
         "meta": {"cwd": "/"}},
        # Sin `abrir`, sin nombre de tmux y sin id: no hay forma de abrirla.
        {"name": "4444dddd", "title": "sin forma", "title_full": "sin forma", "meta": {}},
    ]


def main():
    fallos = []
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

    with tempfile.TemporaryDirectory() as tmp:
        ns["LAUNCH"] = pathlib.Path(tmp)
        rows = filas()
        pestanas, sin_forma = ns["pestanas_de"](rows)

        if len(sin_forma) != 1 or sin_forma[0]["name"] != "4444dddd":
            fallos.append(f"la que no se sabe abrir no queda fuera: {len(sin_forma)}")
        if len(pestanas) != 3:
            fallos.append(f"{len(pestanas)} pestanas, se esperaban 3")

        ruta = ns["write_attach_config"](rows)
        ordenes = re.findall(r"^ {12}- exec: (.+)$", ruta.read_text(), re.M)

        if len(ordenes) != 3:
            fallos.append(f"el YAML trae {len(ordenes)} comandos, se esperaban 3")

        # Lo que se rompio: cada pestana lleva el comando de SU fila.
        for r, cmd in zip(rows[:3], ordenes):
            quiere = ns["_comando_de"](r)[0]
            if cmd != quiere:
                fallos.append(f"{r['name']}: el YAML dice {cmd!r} y toca {quiere!r}")

        # Y son tres comandos DISTINTOS: con el bug los tres eran el mismo `tmux attach`,
        # asi que comparar solo el primero habria pasado en verde.
        if len(set(ordenes)) != 3:
            fallos.append(f"los comandos no son distintos entre si: {set(ordenes)}")
        if sum(1 for c in ordenes if "attach" in c) != 1:
            fallos.append("mas de una pestana usa `tmux attach`, que solo vale para la viva")

        # La que no se sabe abrir no se cuela con el comando de otra.
        if "4444dddd" in ruta.read_text():
            fallos.append("la fila sin forma de abrirse ha acabado en el YAML")

        # El tercer sitio que escribe ese YAML: las huerfanas del registro. No son filas
        # de la lista —no tienen `meta` ni pasan por `_comando_de`— asi que componen su
        # orden aparte, y al unificar el escritor se quedaron sin nadie que las mirara.
        huerfanas = [{"id": "aaaa1111", "cwd": "/tmp",
                      "resume_flags__list": ["--model", "opus"], "title": "una huerfana"},
                     {"id": "bbbb2222", "cwd": "/tmp", "resume_flags__list": [],
                      "title": "otra"}]
        # Devuelve (ruta, pestanas) desde la 1.27.0: las pestanas hacen falta para
        # abrir en tmux o Terminal.app, que no leen el YAML de Warp.
        ruta_cfg, _pest = ns["write_launch_config"](huerfanas)
        texto = ruta_cfg.read_text()
        ordenes = re.findall(r"^ {12}- exec: (.+)$", texto, re.M)
        if ordenes != ["claude --resume aaaa1111 --model opus",
                       "claude --resume bbbb2222"]:
            fallos.append(f"las huerfanas ya no se restauran bien: {ordenes}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_abrir_varias" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
