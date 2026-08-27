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
avanza_uso = ns["avanza_uso"]
sesiones_demo, tope_contexto = ns["sesiones_demo"], ns["tope_contexto"]


def fila(name, titulo="t", proy="", rama="", idle=0.0, ctx=None, modelo="claude-opus-5",
         mem=None, uso=None):
    return {"name": name, "title_full": titulo, "proyecto": proy, "rama": rama,
            "idle": idle, "mem_mb": mem, "_uso": uso,
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
    gasto = {"in": 10, "cw": 90, "out": 50, "turnos": 7, "compacta": 0,
             "completo": True}
    huecos = [fila("a", ctx=180_000, mem=500, proy="api", uso=gasto),
              fila("b", ctx=None, mem=None, proy=""),
              fila("c", ctx=20_000, mem=100, proy="web", uso=gasto),
              fila("d", ctx=None, mem=None, proy="")]
    for modo, sin in (("context", {"b", "d"}), ("memory", {"b", "d"}),
                      ("project", {"b", "d"}), ("spend", {"b", "d"})):
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

    # 6bis. `spend` no es `context` con otro nombre, y este es el caso que lo separa:
    #       una sesion COMPACTADA tiene el contexto bajo y el gasto intacto, porque
    #       compactar tira la ventana y no devuelve lo ya consumido. Medido sobre las 40
    #       sesiones de esta maquina, gasto y contexto correlacionan rho=0,85 y gasto y
    #       actividad rho=0,13; las tres sesiones compactadas eran 2a, 3a y 4a por gasto
    #       y 5a, 7a y 8a por contexto. La demo reproduce ese caso a proposito.
    #       Los dos nombres y los dos `idle` van del REVES a proposito: si el escenario
    #       empata en nombre y en actividad, el test pasa igual con `spend` cayendo al
    #       orden por defecto — comprobado, lo daba por bueno. Aqui el alfabetico y la
    #       actividad piden ["a-llena", "z-gastona"], y solo el gasto pide lo contrario.
    gs = [fila("z-gastona", idle=800, ctx=24_000,
               uso={"in": 400, "cw": 1_070_000, "out": 196_000,
                    "turnos": 229, "compacta": 1, "completo": True}),
          fila("a-llena", idle=5, ctx=176_000,
               uso={"in": 1_200, "cw": 300_000, "out": 40_000,
                    "turnos": 60, "compacta": 0, "completo": True})]
    if [r["name"] for r in ordena(gs, "spend")] != ["z-gastona", "a-llena"]:
        fallos.append("spend: no pone delante la que mas ha consumido")
    for otro in ("context", "activity", "project", "memory"):
        if [r["name"] for r in ordena(gs, otro)] == ["z-gastona", "a-llena"]:
            fallos.append(f"spend: el escenario no lo distingue de {otro}")

    # 6ter. `ordena` no toca disco. `spend` ordena por un dato que hay que ir a buscar,
    #       asi que si nadie paso por `avanza_uso` las filas son huecos y se quedan donde
    #       estaban: la lista se repinta cuatro veces por segundo y no puede ser el sitio
    #       donde se abren cuarenta transcripts.
    crudas = [fila("a", idle=5), fila("b", idle=900)]
    if [r["name"] for r in ordena(crudas, "spend")] != ["a", "b"]:
        fallos.append("spend sin avanza_uso: no deja la lista como estaba")

    # 6quater. Un acumulado a medias tampoco ordena. Mientras se lee por trozos, la cifra
    #          que hay dice cuanto se ha LEIDO, no cuanto se ha gastado: ordenar por ella
    #          pondria delante al transcript mas avanzado. Va al fondo y sube una sola
    #          vez, al terminar, que es lo que evita que la lista tiemble cargando.
    medias = [fila("z-mucho", idle=800,
                   uso={"in": 10, "cw": 900_000, "out": 90_000, "turnos": 200,
                        "compacta": 0, "completo": False}),
              fila("a-poco", idle=5,
                   uso={"in": 10, "cw": 90, "out": 50, "turnos": 7,
                        "compacta": 0, "completo": True})]
    if [r["name"] for r in ordena(medias, "spend")] != ["a-poco", "z-mucho"]:
        fallos.append("spend: un acumulado a medias no puede encabezar el orden")

    # 6quinquies. `avanza_uso` no relee lo que ya esta completo — sin eso, cada vuelta
    #             del selector volveria a abrir los cuarenta transcritos— y respeta su
    #             presupuesto: con 0 ms atiende a una fila y para.
    leidos = []
    guardado = ns["uso_de"]
    ns["uso_de"] = lambda r, tope=None: leidos.append(r.get("name"))
    try:
        hechas = [fila("a", uso={"turnos": 1, "completo": True}),
                  fila("b", uso={"turnos": 1, "completo": True})]
        avanza_uso(hechas)
        if leidos:
            fallos.append(f"avanza_uso relee filas ya completas: {leidos}")
        del leidos[:]
        avanza_uso([fila("sin", uso=None), fila("otra", uso=None)])
        if leidos:
            fallos.append(f"avanza_uso reintenta filas sin transcript: {leidos}")
        del leidos[:]
        pend = [fila(f"p{i}") for i in range(5)]
        for r in pend:
            del r["_uso"]                       # ni leida ni descartada
        avanza_uso(pend, ms=0)
        if len(leidos) != 1:
            fallos.append(f"avanza_uso con 0 ms atiende {len(leidos)} filas, no 1")
    finally:
        ns["uso_de"] = guardado

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

    # 10. Y el caso completo: filtrar por proyecto sobre la demo devuelve TODAS las de
    #     `infra`, que es lo que hoy devuelve vacio. El numero se cuenta de la propia
    #     demo y no se clava a mano: clavarlo obligaba a tocar este test cada vez que la
    #     demo gana una fila, y un test que hay que "arreglar" por un cambio legitimo
    #     acaba arreglandose sin mirar.
    esperadas = len([r for r in demo if r.get("proyecto") == "infra"])
    if esperadas < 3:
        fallos.append("la demo tiene que traer varias sesiones de 'infra' para este caso")
    if len([r for r in demo if casa(r, "infra")]) != esperadas:
        fallos.append("filtrar la demo por 'infra' no devuelve sus %d sesiones" % esperadas)

    for x in fallos:
        print("FALLO:", x)
    print(f"ok: {len(MODOS)} modos deterministas, los huecos al fondo y el filtro"
          " mira titulo, proyecto, rama e id" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
