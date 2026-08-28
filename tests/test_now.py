#!/usr/bin/env python3
"""`--now` ensena las nueve a la vez, y el resumen de arriba no puede contradecir a las filas.

El panel ya pintaba este recorrido, pero solo el de la fila bajo el cursor: saber en que
anda cada sesion costaba bajar el cursor una vez por sesion. Lo que puede romperse aqui
es que la linea de cabecera ("7 trabajando, 2 te esperan") se cuente por su cuenta y
deje de cuadrar con lo que hay debajo — un numero que nadie recalcula al leerlo.

Corre sobre `SERENO_DEMO=1`, que son sesiones inventadas: ni se abre un transcript real
ni sale trabajo de nadie por pantalla.
"""
import contextlib, io, os, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ESTADOS = {"writing", "in_command", "waiting", "stopped", "unknown"}


def main():
    fallos = []
    os.environ["SERENO_DEMO"] = "1"
    os.environ["SERENO_LANG"] = "en"
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    que_hacen, cmd_now = ns["que_hacen"], ns["cmd_now"]

    filas = que_hacen()
    if not filas:
        print("FALLA: el modo demo no da ni una fila")
        return 1

    # 1. Hechos tipados, enum cerrado. El veredicto lo compone quien imprime.
    for f in filas:
        if f["estado"] not in ESTADOS:
            fallos.append(f"estado fuera del enum: {f['estado']!r}")
        if not isinstance(f["eventos"], list):
            fallos.append(f"{f['id']}: los eventos no son una lista")

    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        cod = cmd_now(cols=100)
    texto = salida.getvalue()
    if cod != 0:
        fallos.append(f"cmd_now devuelve {cod}, se esperaba 0")

    # 2. La cabecera no puede desmentir a las filas.
    m = re.search(r"(\d+) live \D+(\d+) working, (\d+) waiting", texto)
    if not m:
        fallos.append(f"no se encuentra la cabecera en:\n{texto[:200]}")
    else:
        n, trab, esp = (int(x) for x in m.groups())
        trab_real = sum(1 for f in filas if f["estado"] in ("writing", "in_command"))
        if (n, trab, esp) != (len(filas), trab_real, len(filas) - trab_real):
            fallos.append(f"la cabecera dice {n}/{trab}/{esp} y las filas son "
                          f"{len(filas)}/{trab_real}/{len(filas) - trab_real}")

    # 3. Cada sesion sale una vez, con su titulo.
    for f in filas:
        if f["titulo"] and texto.count(f["titulo"]) != 1:
            fallos.append(f"{f['titulo']!r} sale {texto.count(f['titulo'])} veces")

    # 4. El atasco se avisa donde los sintomas dicen que lo hay, y no en otro sitio.
    con_atasco = [f for f in filas if f["atasco"]]
    if not con_atasco:
        fallos.append("el demo ya no trae ninguna sesion atascada: este test se queda "
                      "sin el caso que existe para vigilar")
    if texto.count("\n  ! ") != sum(len(f["atasco"]) for f in filas):
        fallos.append(f"{texto.count(chr(10) + '  ! ')} avisos impresos frente a "
                      f"{sum(len(f['atasco']) for f in filas)} en los hechos")

    # 5. Se ensena la COLA del recorrido, no la cabeza: lo ultimo es lo que dice en que
    #    anda. Con tope=1 tiene que quedar el ultimo evento de cada una.
    #    Se compara por la llamada (`nom` + `res`) y no por el objeto entero: en demo el
    #    recorrido nace con tiempos relativos al reloj, asi que dos lecturas seguidas
    #    nunca dan dicts iguales y la comparacion estricta fallaba por eso, no por el
    #    orden — que es lo unico que este caso vigila.
    uno = que_hacen(tope_eventos=1)
    llamada = lambda e: (e["nom"], e["res"])
    for a, b in zip(filas, uno):
        if a["eventos"] and b["eventos"] and llamada(a["eventos"][-1]) != llamada(b["eventos"][0]):
            fallos.append(f"{a['id']}: con tope=1 no queda el ultimo evento")
    if all(len(f["eventos"]) <= 1 for f in filas):
        fallos.append("ninguna fila del demo trae mas de un evento: el caso del tope "
                      "no se esta probando contra nada")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_now" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
