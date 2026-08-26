#!/usr/bin/env python3
"""El orden no pierde filas, no las baraja al refrescar, y el filtro mira lo que se ve.

Dos sintomas reales detras de este test.

El primero: teclear el nombre de un proyecto que esta EN PANTALLA, y en dos filas,
devolvia "(nada coincide)" — el filtro solo miraba el titulo.

El segundo es el que no se ve venir. La lista se repinta sola cada 2,5 s, asi que un
orden con empates sin desempatar cambia de sitio dos filas entre un refresco y el
siguiente: no es un fallo que reviente nada, es una lista que tiembla debajo del
cursor mientras intentas marcarla. Por eso `ordena` desempata por nombre y por eso
aqui se ordena la MISMA lista barajada y se exige el mismo resultado.

Y el tercero, que es de lectura: un dato que no consta no es un cero. Una sesion sin
contexto no puede encabezar el orden por contexto ni aunque lo invierta.
"""
import os, pathlib, random, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
ordena, casa, MODOS = ns["ordena"], ns["casa"], ns["MODOS_ORDEN"]
sesiones_demo, tope_contexto = ns["sesiones_demo"], ns["tope_contexto"]


def fila(name, titulo="t", proy="", rama="", idle=0.0, ctx=None, modelo="claude-opus-5",
         mem=None):
    return {"name": name, "title_full": titulo, "proyecto": proy, "rama": rama,
            "idle": idle, "mem_mb": mem,
            "pulso": {"escribe": False, "herramienta": False,
                      "ctx": ctx, "modelo": modelo}}


def main():
    fallos = []
    demo = sesiones_demo()

    # 1. Ordenar no pierde ni inventa filas. Es lo unico que un orden NO puede hacer,
    #    y es barato de romper: un `sorted` con clave que revienta y un `except` que
    #    devuelve la lista a medias tiene exactamente esta pinta desde fuera.
    for modo in MODOS:
        for inv in (False, True):
            salida = ordena(demo, modo, inv)
            if sorted(r["name"] for r in salida) != sorted(r["name"] for r in demo):
                fallos.append(f"{modo}/inv={inv}: la lista cambia de contenido")

    # 2. Determinismo: la misma lista en otro orden de entrada da la MISMA salida.
    #    Sin esto, la lista tiembla sola cada 2,5 s en cuanto hay dos filas empatadas.
    for modo in MODOS:
        for inv in (False, True):
            esperado = [r["name"] for r in ordena(demo, modo, inv)]
            for semilla in range(6):
                barajada = list(demo)
                random.Random(semilla).shuffle(barajada)
                if [r["name"] for r in ordena(barajada, modo, inv)] != esperado:
                    fallos.append(f"{modo}/inv={inv}: el orden depende de la entrada")
                    break

    # 3. Un hueco no es un cero: las filas sin el dato van al final en LAS DOS
    #    direcciones. Tratarlas como 0 las pondria las primeras al invertir.
    huecos = [fila("a", ctx=180_000, mem=500, proy="api"),
              fila("b", ctx=None, mem=None, proy=""),
              fila("c", ctx=20_000, mem=100, proy="web"),
              fila("d", ctx=None, mem=None, proy="")]
    for modo, sin in (("context", {"b", "d"}), ("memory", {"b", "d"}),
                      ("project", {"b", "d"})):
        for inv in (False, True):
            cola = {r["name"] for r in ordena(huecos, modo, inv)[-len(sin):]}
            if cola != sin:
                fallos.append(f"{modo}/inv={inv}: los huecos no van al final ({cola})")

    # 4. El contexto ordena por FRACCION del tope, no por tokens. 402k en una ventana
    #    de un millon esta mas vacia que 93k en una de 200k; por tokens crudos saldria
    #    al reves y la lista pondria delante la sesion que menos falta hace tocar.
    par = [fila("millon", ctx=402_000, modelo="claude-opus-5[1m]"),
           fila("normal", ctx=93_000, modelo="claude-opus-5")]
    if [r["name"] for r in ordena(par, "context")] != ["normal", "millon"]:
        fallos.append("context: ordena por tokens crudos y no por fraccion del tope")

    # 5. `activity` por defecto pone delante lo que acaba de moverse, e invertido lo
    #    que lleva mas parado. Son el mismo orden del reves: por eso "tiempo parada"
    #    no es un quinto modo.
    esc = [fila("vieja", idle=90_000), fila("nueva", idle=3), fila("media", idle=400)]
    if [r["name"] for r in ordena(esc, "activity")] != ["nueva", "media", "vieja"]:
        fallos.append("activity: no pone delante la que acaba de moverse")
    if [r["name"] for r in ordena(esc, "activity", True)] != ["vieja", "media", "nueva"]:
        fallos.append("activity invertido: no pone delante la que lleva mas parada")

    # 6. `project` agrupa, y dentro de cada proyecto manda la actividad.
    pr = [fila("b1", proy="beta", idle=10), fila("a2", proy="alfa", idle=900),
          fila("a1", proy="alfa", idle=5), fila("b2", proy="beta", idle=800)]
    if [r["name"] for r in ordena(pr, "project")] != ["a1", "a2", "b1", "b2"]:
        fallos.append("project: no agrupa por proyecto y actividad dentro")

    # 7. Un modo que no existe cae al de por defecto en vez de reventar. `SERENO_SORT`
    #    lo escribe una persona en su .zshrc y una errata no puede tirar el programa.
    if [r["name"] for r in ordena(esc, "loquesea")] != \
            [r["name"] for r in ordena(esc, "activity")]:
        fallos.append("un modo desconocido no cae al de por defecto")

    # 8. El filtro mira los cuatro campos que identifican una sesion y que ademas se
    #    ven en pantalla. El sintoma que lo motivo es el caso "infra".
    f = fila("demo-infra-7", titulo="Shrink the docker image", proy="infra",
             rama="chore/ci")
    for aguja in ("shrink", "SHRINK", "infra", "chore/ci", "demo-infra-7", ""):
        if not casa(f, aguja):
            fallos.append(f"el filtro no encuentra {aguja!r}")
    if casa(f, "nada-de-esto"):
        fallos.append("el filtro casa con algo que no esta en la fila")

    # 9. Sin tildes encuentra con tildes: quien filtra teclea `sesion`, y el titulo que
    #    escribio Claude dice `sesión`.
    if not casa(fila("x", titulo="Revisar la sesión de pagos"), "sesion"):
        fallos.append("el filtro no ignora las tildes")

    # 10. Y el caso completo: filtrar por proyecto sobre la demo devuelve las tres de
    #     `infra`, que es lo que hoy devuelve vacio.
    if len([r for r in demo if casa(r, "infra")]) != 3:
        fallos.append("filtrar la demo por 'infra' no devuelve sus tres sesiones")

    for x in fallos:
        print("FALLO:", x)
    print(f"ok: {len(MODOS)} modos deterministas, los huecos al fondo y el filtro"
          " mira titulo, proyecto, rama e id" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
