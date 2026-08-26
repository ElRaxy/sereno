#!/usr/bin/env python3
"""El titulo es lo ultimo que se recorta, y la fila nunca se sale de la ventana.

Antes de esto el reparto de columnas vivia dentro del bucle de pintado y no habia
forma de comprobarlo sin arrancar curses. El sintoma que lo motivo: a 70 columnas la
lista mostraba "Refactor pa..." al lado de un "checkout-api" con su rama entera, o
sea recortaba la identidad de la sesion para conservar un dato que se repite en cada
fila y que ademas sale entero en el panel.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
reparto, T_COMODO, COL_BASE = ns["reparto"], ns["T_COMODO"], ns["COL_BASE"]
ANCHOS = (44, 56, 70, 84, 100, 110, 120, 150, 200)
LARGO, PROY = 32, 27          # titulo y proyecto tipicos de una fila real


def main():
    fallos = []

    for hueco in ANCHOS:
        for hay_ctx in (False, True):
            for hay_ram in (False, True):
                t, ap, ac, ar, fijas = reparto(hueco, LARGO, PROY, hay_ctx, hay_ram)

                # 1. La fila cabe. Es el fallo que se lleva el programa entero:
                #    escribir pasado el borde aborta curses con ERR.
                if t + fijas > hueco and hueco >= COL_MINIMA():
                    fallos.append(f"{hueco}: la fila pide {t + fijas}")

                # 2. Ninguna columna de apoyo sobrevive a costa del titulo: el
                #    titulo cobra primero y solo el sobrante enciende columnas.
                if t < min(LARGO, T_COMODO) and (ap or ac or ar):
                    fallos.append(
                        f"{hueco}: titulo a {t} con proy={ap} ctx={ac} ram={ar}")

                # 3. Una columna que no tiene nada que decir no ocupa.
                if not hay_ctx and ac:
                    fallos.append(f"{hueco}: contexto vacio ocupando {ac}")
                if not hay_ram and ar:
                    fallos.append(f"{hueco}: RAM vacia ocupando {ar}")

    # 4. Monotonia: mas ventana nunca puede dar menos titulo. Un reparto que se
    #    ensancha a saltos raros se nota como parpadeo al redimensionar.
    previo = 0
    for hueco in ANCHOS:
        t = reparto(hueco, LARGO, PROY, True, True)[0]
        if t < previo:
            fallos.append(f"{hueco}: el titulo encoge al ensanchar ({previo} -> {t})")
        previo = t

    # 5. El orden de renuncia es el declarado: la RAM cae antes que el proyecto, y
    #    el proyecto antes que el contexto.
    visto = []
    for hueco in range(200, 40, -1):
        _, ap, ac, ar = reparto(hueco, LARGO, PROY, True, True)[:4]
        estado = (bool(ar), bool(ap), bool(ac))
        if not visto or estado != visto[-1]:
            visto.append(estado)
    esperado = [(True, True, True), (True, True, True),
                (False, True, True), (False, False, True), (False, False, False)]
    # (el segundo escalon es el proyecto estrechandose, que no cambia la tripleta)
    unicos = [e for i, e in enumerate(visto) if i == 0 or e != visto[i - 1]]
    if unicos != [e for i, e in enumerate(esperado) if i == 0 or e != esperado[i - 1]]:
        fallos.append(f"orden de renuncia inesperado: {unicos}")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: el reparto aguanta {len(ANCHOS)} anchos y el titulo cede el ultimo"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


def COL_MINIMA():
    """Por debajo de esto no cabe ni el titulo minimo: la lista se recorta y ya."""
    return COL_BASE + 12


if __name__ == "__main__":
    sys.exit(main())
