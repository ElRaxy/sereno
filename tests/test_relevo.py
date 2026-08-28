#!/usr/bin/env python3
"""Entregar una sesion a otro CLI: es un relevo, no una migracion, y no lleva
conversacion salvo que se pida.

El briefing acaba DENTRO del YAML de launch de Warp, que se queda en el disco. Por eso
lo que vigila este test no es que el texto quede bonito, sino los dos cortes que hacen
que sea seguro dejarlo puesto:

  1. por defecto no sale ni el prompt ni la respuesta de la sesion;
  2. una fila cuyo directorio ya no existe NO se releva, porque arrancaria en `~` con
     pinta de haber funcionado.
"""
import os, pathlib, sys, tempfile

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

        # 1. Por defecto, cero conversacion.
        seco = briefing(fila(vivo))
        for aguja, que in ((SECRETO_P, "el ultimo prompt"), (SECRETO_R, "la respuesta")):
            if aguja in seco:
                fallos.append(f"el briefing por defecto lleva {que}")
        if "main" not in seco or str(vivo) not in seco:
            fallos.append("el briefing no lleva ni la rama ni el directorio")

        # 2. Pedida, sale. Sin esto el caso 1 pasaria aunque el briefing fuera vacio.
        con = briefing(fila(vivo), con_conversacion=True)
        if SECRETO_P not in con or SECRETO_R not in con:
            fallos.append("con conversacion pedida sigue sin salir: el caso de arriba "
                          "no estaria probando nada")

        # 3. Sin directorio no hay relevo.
        pest, sin = relevo_pest([fila(vivo), fila(muerto, "cc-x-2222bbbb")], "codex")
        if len(pest) != 1 or len(sin) != 1:
            fallos.append(f"{len(pest)} pestanas y {len(sin)} descartadas, "
                          "se esperaba 1 y 1")
        if pest and not pest[0][1].startswith("codex "):
            fallos.append(f"la orden no arranca codex: {pest[0][1][:40]!r}")
        if pest and pest[0][2] != str(vivo):
            fallos.append("la pestana no arranca en el directorio de la sesion")

        # 4. El briefing viaja DENTRO de la orden, entero y citado: si se partiera por
        #    un espacio, codex recibiria media frase como prompt y el resto como flags.
        if pest:
            import shlex
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

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_relevo" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
