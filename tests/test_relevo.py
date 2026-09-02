#!/usr/bin/env python3
"""Entregar una sesion a otro CLI: es un relevo, no una migracion.

Un relevo es un TRASPASO, asi que por defecto lleva el ultimo intercambio —lo que se le
pidio y lo ultimo que dijo— para que quien lo reciba pueda seguir. El briefing acaba
DENTRO del YAML de launch de Warp, que se queda en el disco, asi que hay una salida para
el caso de trabajo de cliente: `SERENO_RELEVO=seco` lo deja en solo hechos.

Lo que vigila este test:

  1. por defecto SI sale el ultimo intercambio; con `SERENO_RELEVO=seco`, no;
  2. `con_conversacion` (tecla k) alarga esos trozos;
  3. una fila cuyo directorio ya no existe NO se releva, porque arrancaria en `~` con
     pinta de haber funcionado.
"""
import os, pathlib, shlex, sys, tempfile

# La orden arranca con la RUTA del CLI, no con su nombre: un nombre pelado lo
# secuestra un alias de la shell interactiva en la que Warp escribe el comando.
# Por eso no se compara contra el literal "codex " — en una maquina sin codex
# instalado `bin_cli` devuelve el nombre pelado y el literal pasaria en verde
# sin haber comprobado nada. Se compara contra lo que `bin_cli` diga AHI.

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SECRETO_P = "el precio que le pasamos a ese cliente"
SECRETO_R = "lo dejo hablado con su gestoria"


def main():
    fallos = []
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    os.environ.pop("SERENO_RELEVO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    briefing, relevo_pest = ns["briefing"], ns["pestanas_de_relevo"]

    with tempfile.TemporaryDirectory() as tmp:
        vivo, muerto = pathlib.Path(tmp), pathlib.Path(tmp) / "ya-no-existe"
        # `_det` precocinado: `detalles()` lo respeta y no abre ningun transcript.
        def fila(cwd, nombre="cc-x-1111aaaa"):
            return {"name": nombre, "title": "una sesion", "title_full": "una sesion",
                    "meta": {"cwd": str(cwd), "id": "1111aaaa"},
                    "idle": 3, "pulso": {"escribe": True, "herramienta": False},
                    "_det": {"cwd": str(cwd), "gitBranch": "main", "peso": 10,
                             "lastPrompt": SECRETO_P, "resp": SECRETO_R,
                             "fase": None, "tool": None, "ruta": []}}

        # 1. Por defecto, el ultimo intercambio SALE: es lo que deja seguir a quien releva.
        base = briefing(fila(vivo))
        for aguja, que in ((SECRETO_P, "el ultimo prompt"), (SECRETO_R, "la respuesta")):
            if aguja not in base:
                fallos.append(f"el briefing por defecto ya no lleva {que}")
        if "main" not in base or str(vivo) not in base:
            fallos.append("el briefing no lleva ni la rama ni el directorio")

        # 1b. `SERENO_RELEVO=seco` lo quita — la salida para cuando en esa sesion hay
        #     trabajo de cliente, porque el briefing se queda en el YAML de Warp en disco.
        os.environ["SERENO_RELEVO"] = "seco"
        seco = briefing(fila(vivo))
        os.environ.pop("SERENO_RELEVO", None)
        for aguja, que in ((SECRETO_P, "el ultimo prompt"), (SECRETO_R, "la respuesta")):
            if aguja in seco:
                fallos.append(f"con SERENO_RELEVO=seco el briefing sigue llevando {que}")
        if "main" not in seco or str(vivo) not in seco:
            fallos.append("SERENO_RELEVO=seco se lleva por delante tambien los hechos")

        # 2. `con_conversacion` (tecla k) alarga los trozos: una respuesta larga se recorta
        #    por defecto y sale mas entera cuando se pide. Sin esto, un briefing vacio
        #    pasaria el caso 1.
        largo = fila(vivo)
        largo["_det"]["resp"] = "R" * 2000
        if len(briefing(largo, con_conversacion=True)) <= len(briefing(largo)):
            fallos.append("con_conversacion no alarga el briefing")

        # 2b. El briefing da la RUTA del transcript: es lo que deja al agente que releva
        #     leer TODA la historia (Sereno no la resume, pero el agente la lee). Sin esto
        #     el receptor solo tenia la cola y "no sabia que estaba haciendo". Va bajo el
        #     mismo `seco`: es un puntero al trabajo.
        con_ruta = fila(vivo)
        con_ruta["meta"]["_transcript"] = "/tmp/una-sesion/transcript.jsonl"
        if "/tmp/una-sesion/transcript.jsonl" not in briefing(con_ruta):
            fallos.append("el briefing no da la ruta del transcript para leer el contexto")
        os.environ["SERENO_RELEVO"] = "seco"
        seco_ruta = briefing(con_ruta)
        os.environ.pop("SERENO_RELEVO", None)
        if "/tmp/una-sesion/transcript.jsonl" in seco_ruta:
            fallos.append("con SERENO_RELEVO=seco el briefing sigue soltando la ruta del "
                          "transcript (que apunta al trabajo)")

        # 3. Sin directorio no hay relevo.
        pest, sin, _mismo = relevo_pest(
            [fila(vivo), fila(muerto, "cc-x-2222bbbb")], "codex")
        if len(pest) != 1 or len(sin) != 1:
            fallos.append(f"{len(pest)} pestanas y {len(sin)} descartadas, "
                          "se esperaba 1 y 1")
        arranca_codex = shlex.quote(ns["bin_cli"]("codex")) + " "
        if pest and not pest[0][1].startswith(arranca_codex):
            fallos.append(f"la orden no arranca por {arranca_codex!r}: "
                          f"{pest[0][1][:60]!r}")
        if pest and pest[0][2] != str(vivo):
            fallos.append("la pestana no arranca en el directorio de la sesion")

        # 4. El briefing viaja DENTRO de la orden, entero y citado: si se partiera por
        #    un espacio, codex recibiria media frase como prompt y el resto como flags.
        if pest:
            trozos = shlex.split(pest[0][1])
            if len(trozos) != 2:
                fallos.append(f"la orden se parte en {len(trozos)} trozos, se esperaban 2")
            elif trozos[1] != briefing(fila(vivo)):
                fallos.append("el prompt que recibe codex no es el briefing")

        # 5. El YAML sobrevive a una orden de varias lineas. Es el fallo que casi se
        #    publica: el briefing lleva saltos, `- exec: <orden>` los escupia sueltos y
        #    el fichero salia invalido — la ventana no abre y no hay error en ninguna
        #    parte del programa. Se comprueba deshaciendo el bloque literal a mano, sin
        #    PyYAML: `sereno` es solo stdlib y sus tests tambien.
        ns["LAUNCH"] = pathlib.Path(tmp)
        orden = "codex 'primera\n  sangrada\n\ntras un hueco'"
        ruta = ns["_escribe_config"]("prueba", [("t", orden, str(vivo))])
        lineas = ruta.read_text().split("\n")
        try:
            i = lineas.index("            - exec: |-")
        except ValueError:
            fallos.append("una orden de varias lineas no sale como bloque literal: "
                          "el YAML queda invalido y la ventana no abre")
        else:
            cuerpo, j = [], i + 1
            while j < len(lineas) and (lineas[j].startswith("                ")
                                       or not lineas[j].strip()):
                cuerpo.append(lineas[j][16:])
                j += 1
            if "\n".join(cuerpo).rstrip("\n") != orden:
                fallos.append("el bloque literal no devuelve la orden tal cual")

        # 6. Solo se ofrece lo que existe en el PATH.
        for nombre in ns["arneses_disponibles"]():
            if nombre not in ns["ARNESES"]:
                fallos.append(f"se ofrece {nombre!r}, que no esta en ARNESES")

        # 7. Un `cwd` vacio NO es un directorio. `Path("").is_dir()` devuelve True
        #    —Python lee la ruta vacia como `.`— asi que la guarda anterior dejaba pasar
        #    todas las filas de Codex, que traen "": el relevo arrancaba donde estuviera
        #    el proceso y lo contaba como entregado. Se prueba con el cwd en los DOS
        #    sitios de los que se lee, porque `detalles()` y `meta` se consultan en
        #    cascada y vaciar solo uno no prueba nada.
        hueca = fila(vivo, "cc-x-3333cccc")
        hueca["meta"]["cwd"] = ""
        hueca["_det"]["cwd"] = ""
        pest_h, sin_h, _m = relevo_pest([hueca], "codex")
        if pest_h or len(sin_h) != 1:
            fallos.append("una fila sin cwd se releva igual: arrancaria en el "
                          "directorio del proceso diciendo que ha funcionado")

        # 8. Una ruta relativa tampoco vale, y por lo mismo: existe respecto al proceso,
        #    no respecto a la sesion. Sin este caso, el 7 pasaria con un `if cwd:` suelto.
        rel = fila(vivo, "cc-x-4444dddd")
        rel["meta"]["cwd"] = rel["_det"]["cwd"] = "tests"
        pest_r, sin_r, _m = relevo_pest([rel], "codex")
        if pest_r or len(sin_r) != 1:
            fallos.append("una ruta relativa pasa la guarda del directorio")

        # 9. Nadie se releva a si mismo. Una fila de Codex entregada a Codex abria una
        #    sesion en blanco y se contaba como exito.
        propia = fila(vivo, "cx-1")
        propia["fuente"] = "codex"
        pest_p, sin_p, mismo_p = relevo_pest([propia], "codex")
        if pest_p or len(mismo_p) != 1 or sin_p:
            fallos.append("una sesion de codex se releva a codex")

        # 10. Y en el otro sentido si va: Codex -> Claude, con el briefing diciendo de
        #     donde viene. El briefing hablaba SIEMPRE de "una sesion de Claude Code",
        #     que para una fila de Codex es falso.
        pest_c, sin_c, mismo_c = relevo_pest([propia], "claude")
        if len(pest_c) != 1 or mismo_c or sin_c:
            fallos.append("una sesion de codex no se puede relevar a claude")
        elif not pest_c[0][1].startswith(shlex.quote(ns["bin_cli"]("claude")) + " "):
            fallos.append(f"la orden no arranca por la ruta de claude: "
                          f"{pest_c[0][1][:60]!r}")
        brief_cx = briefing(propia)
        if "Codex" not in brief_cx or "Claude Code" in brief_cx:
            fallos.append("el briefing de una fila de Codex sigue diciendo que "
                          "viene de Claude Code")
        if "Claude Code" not in briefing(fila(vivo)):
            fallos.append("el briefing de una fila de Claude ya no dice de donde viene")

        # 11. `cli_de`: "historial" es Claude Code parado, no otro programa. Si se
        #     tratara como CLI ajeno, una sesion cerrada de Claude se ofreceria para
        #     relevar a Claude.
        cli_de = ns["cli_de"]
        for fu, esperado in (("claude", "claude"), ("historial", "claude"),
                             ("codex", "codex"), ("gemini", "gemini")):
            if cli_de({"fuente": fu}) != esperado:
                fallos.append(f"cli_de({fu!r}) no es {esperado!r}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_relevo" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
