#!/usr/bin/env python3
"""Las ordenes que compone Sereno llevan la RUTA del CLI, nunca su nombre pelado.

Sereno no ejecuta lo que compone: la orden acaba dentro de la launch configuration de
Warp, y Warp la escribe en una shell **interactiva**. Ahi mandan los alias del
`.zshrc`, que un `sh -c` no llega a ver — asi que "esto es el binario" comprobado desde
el proceso de Sereno no dice nada sobre lo que se ejecutara alli.

El 2026-09-01 se abrieron tres sesiones del historial con `r` y salieron corriendo con
`--allow-dangerously-skip-permissions`, que Sereno no pide en ningun sitio: `claude`
era un alias a un wrapper que lo anadia. El YAML estaba limpio (`claude --resume <id>`)
y el `ps` no. Un fallo que no se ve en lo que escribe el programa.

Hay TRES sitios que componen ordenes —`_comando_de`, `write_launch_config` y
`ARNESES`— y basta uno con el nombre pelado para que el alias vuelva a colarse, asi que
se comprueban los tres.

**El PATH se falsifica a proposito.** Comparar contra el literal `"claude"` pasaria en
verde en cualquier maquina sin Claude instalada —CI incluido—, donde `bin_cli` devuelve
justo el nombre pelado: el test parece pasar y no ha comprobado nada. Aqui se planta un
`claude` de mentira en un directorio temporal, se pone delante del PATH, y se exige que
la orden salga con ESA ruta.
"""
import os
import pathlib
import re
import shlex
import stat
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CLIS = ("claude", "codex", "gemini")


def planta(directorio):
    """Deja un ejecutable de mentira por cada CLI y devuelve sus rutas."""
    rutas = {}
    for nombre in CLIS:
        f = pathlib.Path(directorio) / nombre
        f.write_text("#!/bin/sh\nexit 0\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        rutas[nombre] = str(f)
    return rutas


def carga(path):
    os.environ["PATH"] = path
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    return ns


def fila_claude():
    return {"name": "2222bbbb-0000-0000-0000-000000000000", "title": "del historial",
            "title_full": "del historial",
            "meta": {"cwd": "/", "id": "2222bbbb-0000-0000-0000-000000000000"}}


def fila_codex():
    return {"name": "3333cccc-0000-0000-0000-000000000000", "title": "de codex",
            "title_full": "de codex", "abrir": ["codex", "resume", "3333cccc"],
            "meta": {"cwd": "/"}}


def main():
    fallos = []
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    path_original = os.environ.get("PATH", "")

    try:
        # ── con los CLI en el PATH: todo sale con la ruta ────────────────────
        with tempfile.TemporaryDirectory() as bin_falso, \
                tempfile.TemporaryDirectory() as tmp_launch:
            rutas = planta(bin_falso)
            ns = carga(bin_falso + os.pathsep + "/usr/bin:/bin")
            ns["LAUNCH"] = pathlib.Path(tmp_launch)

            # Control positivo del montaje: si el `claude` de mentira no se encuentra,
            # todo lo de abajo compararia contra el nombre pelado y pasaria solo.
            for nombre, ruta in rutas.items():
                dado = ns["bin_cli"](nombre)
                if dado != ruta:
                    fallos.append("el montaje no funciona: bin_cli(%r) da %r y el "
                                  "ejecutable plantado esta en %r"
                                  % (nombre, dado, ruta))
            if fallos:
                for f in fallos:
                    print("FALLA:", f)
                return 1

            ordenes = {
                "_comando_de (historial de Claude)": ns["_comando_de"](fila_claude())[0],
                "_comando_de (historial de Codex)": ns["_comando_de"](fila_codex())[0],
                "ARNESES['claude'] (relevo)": ns["ARNESES"]["claude"]("hola"),
                "ARNESES['codex'] (relevo)": ns["ARNESES"]["codex"]("hola"),
                "ARNESES['gemini'] (relevo)": ns["ARNESES"]["gemini"]("hola"),
            }
            ruta_cfg, _pest = ns["write_launch_config"](
                [{"id": "aaaa1111", "cwd": "/tmp", "resume_flags__list": [],
                  "title": "una huerfana"}])
            for i, cmd in enumerate(re.findall(r"^ {12}- exec: (.+)$",
                                               ruta_cfg.read_text(), re.M)):
                ordenes["write_launch_config (huerfana %d)" % i] = cmd

            if len(ordenes) != 6:
                fallos.append("se esperaban 6 ordenes que comprobar y hay %d: %r"
                              % (len(ordenes), sorted(ordenes)))

            for donde, cmd in ordenes.items():
                primero = shlex.split(cmd)[0] if cmd.strip() else ""
                if not os.path.isabs(primero):
                    fallos.append("%s: la orden arranca con %r, que no es una ruta "
                                  "absoluta — un alias se la queda" % (donde, primero))
                elif primero not in rutas.values():
                    fallos.append("%s: arranca con %r, que no es ninguno de los CLI "
                                  "plantados" % (donde, primero))
                # Y no basta con que EMPIECE bien: el nombre pelado no puede seguir
                # apareciendo como primera palabra en ningun sitio de la orden.
                if re.match(r"^(claude|codex|gemini)\b", cmd):
                    fallos.append("%s: la orden sigue empezando por el nombre pelado: "
                                  "%r" % (donde, cmd[:60]))

            # El relevo entrega el destino en Bypass Permissions por defecto, y el flag
            # va EXPLICITO en ARNESES (no por un alias). Va DESPUES de la ruta: el
            # bloque de arriba ya comprueba que el primer token sigue siendo la ruta.
            bypass = {"claude": "--permission-mode bypassPermissions",
                      "codex": "--dangerously-bypass-approvals-and-sandbox"}
            for cli, flag in bypass.items():
                orden = ns["ARNESES"][cli]("hola")
                if flag not in orden:
                    fallos.append("ARNESES[%r] ya no releva en bypass: falta %r en %r"
                                  % (cli, flag, orden))

            # La sesion viva no cambia: se abre por tmux, y `TMUX_BIN` ya era una ruta.
            viva = ns["_comando_de"]({"name": "cc-proyecto-1111aaaa",
                                      "meta": {"cwd": "/"}})[0]
            if "attach" not in viva:
                fallos.append("la sesion viva ha dejado de abrirse con tmux: %r" % viva)

        # ── control negativo: sin el CLI en el PATH se sigue abriendo ────────
        # Devolver "" o reventar aqui seria peor que el alias: no abriria nada. El
        # nombre pelado es el ultimo recurso a proposito.
        with tempfile.TemporaryDirectory() as vacio:
            ns2 = carga(vacio)
            if ns2["bin_cli"]("claude") != "claude":
                fallos.append("sin claude en el PATH, bin_cli devuelve %r en vez del "
                              "nombre pelado: no se podria abrir nada"
                              % ns2["bin_cli"]("claude"))
            cmd = ns2["_comando_de"](fila_claude())[0]
            if not cmd.startswith("claude --resume "):
                fallos.append("sin claude en el PATH la orden es %r, y tiene que caer "
                              "al nombre pelado" % cmd[:60])
    finally:
        os.environ["PATH"] = path_original

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: las 6 ordenes salen con la ruta del CLI, y sin el en el PATH caen al "
          "nombre pelado en vez de no abrir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
