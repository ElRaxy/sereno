#!/usr/bin/env python3
"""La cola del transcript: lineas COMPLETAS, las ultimas, y sin releer el fichero.

Es el bucle vivo del selector. `pulso()` la llama con 80 lineas por cada sesion en
cada refresco, asi que aqui un fallo no se ve como un error: se ve como una sesion en
mitad de un comando figurando como parada, que fue el bug que obligo a escribir la
funcion. Leer "los ultimos N bytes" no vale porque una sola linea de `tool_result`
pasa de 96 KB: la ventana cae entera dentro de esa linea, se descarta como parcial y
el lector se queda sin nada que mirar.

Ademas del resultado se mide el COSTE, y aqui no es un adorno: la version anterior
volvia a leer desde el nuevo tope hasta el final en cada vuelta, asi que un transcript
de 8 MB en una sola linea se leia dieciseis veces —135 MB de disco por 8 MB de
fichero— dentro del bucle que repinta la lista. El invariante que lo cierra es simple:
ningun byte se lee dos veces.
"""
import io
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


class _Fichero(io.BytesIO):
    """Un fichero de mentira que apunta cuantos bytes se le han pedido."""

    def __init__(self, espia):
        io.BytesIO.__init__(self, espia.datos)
        self.espia = espia

    def read(self, n=-1):
        b = io.BytesIO.read(self, n)
        self.espia.leidos += len(b)
        return b


class Espia:
    """Lo minimo que `ultimas_lineas` le pide a un `Path`: `stat()` y `open()`."""

    def __init__(self, datos):
        self.datos = datos
        self.leidos = 0

    def stat(self):
        class S:
            st_size = len(self.datos)
        return S()

    def open(self, modo):
        return _Fichero(self)


class NoExiste:
    def stat(self):
        raise OSError("no existe")

    def open(self, modo):
        raise OSError("no existe")


class SeBorra:
    """Existe al mirarlo y ya no al abrirlo: la carrera con una sesion viva."""

    def __init__(self, datos):
        self.datos = datos

    def stat(self):
        class S:
            st_size = len(self.datos)
        return S()

    def open(self, modo):
        raise OSError("desaparecio entre el stat y el open")


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ul = ns["ultimas_lineas"]
    fallos = []

    # ── control positivo: el caso trivial, antes de medir nada mas ───────────
    # Sin esto, un cambio que devolviese siempre `[]` pasaria varias de las
    # comprobaciones de abajo —"no hay lineas partidas", "no hay blancos"— en verde.
    e = Espia(b"una\ndos\ntres\n")
    if ul(e, 60) != ["una", "dos", "tres"]:
        print("FALLO: el caso mas simple ya no funciona: %r" % (ul(e, 60),))
        return 1

    # ── las ULTIMAS, en orden, y la cuenta es la pedida ──────────────────────
    e = Espia(b"".join(b"l%d\n" % i for i in range(500)))
    r = ul(e, 60)
    if r != ["l%d" % i for i in range(440, 500)]:
        fallos.append("no son las ultimas 60 en orden: %r ... %r (%d)"
                      % (r[:2], r[-2:], len(r)))

    # ── un fichero que cabe entero no pierde su primera linea ────────────────
    # El descarte de la linea partida por el `seek` solo tiene sentido si se
    # retrocedio: cuando se llego al principio del fichero, la primera es buena.
    e = Espia(b"primera\nsegunda\n")
    if ul(e, 60)[:1] != ["primera"]:
        fallos.append("se pierde la primera linea de un fichero que cabe entero: %r"
                      % (ul(e, 60),))

    # ── la linea que no cabe en la ventana: el bug que dio origen a esto ─────
    gorda = b"z" * (300 * 1024)
    e = Espia(b"a\nb\nc\n" + gorda + b"\n")
    r = ul(e, 3)
    if not r:
        fallos.append("una ultima linea de 300 KB deja al lector sin nada que mirar")
    elif r[-1].encode() != gorda:
        fallos.append("la linea de 300 KB vuelve partida: %d bytes de %d"
                      % (len(r[-1]), len(gorda)))

    # ── ninguna linea vuelve partida por el retroceso ────────────────────────
    datos = b"".join(b"%d-%s\n" % (i, b"x" * 50000) for i in range(40))
    r = ul(Espia(datos), 10)
    partidas = [l for l in r if not l.endswith("x" * 50) or "-" not in l]
    if partidas:
        fallos.append("%d lineas vuelven partidas por el retroceso" % len(partidas))

    # ── lo que no se puede abrir no revienta: devuelve nada ──────────────────
    if ul(NoExiste(), 60) != []:
        fallos.append("un fichero ilegible no devuelve la lista vacia")
    # Y el que desaparece DESPUES del `stat`, que es la carrera de verdad: el
    # selector mira transcripts que otra sesion esta escribiendo, y uno que se va a
    # mitad no puede tumbar el repintado de la lista.
    try:
        r = ul(SeBorra(b"a\nb\n"), 60)
    except OSError:
        r = "revento"
    if r != []:
        fallos.append("un fichero que desaparece tras el stat no devuelve la lista "
                      "vacia: %r" % (r,))

    # ── el tope corta antes de juntar las lineas pedidas: la de arriba viene
    #    partida por el retroceso y no puede colarse en el resultado ───────────
    mega = b"".join(b"m" * (1024 * 1024) + b"\n" for _ in range(20))
    r = ul(Espia(mega), 60, 8 * 1024 * 1024)
    malas = [len(l) for l in r if len(l) != 1024 * 1024]
    if malas:
        fallos.append("con el tope alcanzado se cuela la linea partida: %r" % malas)

    # ── los blancos no son lineas ────────────────────────────────────────────
    if ul(Espia(b"a\n\n\n   \nb\n"), 60) != ["a", "b"]:
        fallos.append("las lineas en blanco cuentan como lineas: %r"
                      % (ul(Espia(b"a\n\n\n   \nb\n"), 60),))

    # ── el coste: ningun byte se lee dos veces ───────────────────────────────
    # Hechos medidos, y el veredicto compuesto encima
    # (`.claude/rules/llm-decision-boundary.md`).
    tope = 8 * 1024 * 1024
    casos = [
        ("transcript normal", b"".join(b"%d %s\n" % (i, b"x" * 200)
                                       for i in range(20000))),
        ("un transcript de 8 MB en una sola linea", b"y" * tope),
        # Por encima del tope se para: leer una linea de 12 MB entera para mirar la
        # cola es traer 12 MB a la memoria de un equipo de 8 GB por cada refresco.
        ("una linea mas grande que el tope", b"y" * (tope + 4 * 1024 * 1024)),
        ("sesenta lineas de 150 KB", b"".join(b"%s\n" % (b"w" * 150000)
                                              for _ in range(60))),
    ]
    for que, datos in casos:
        e = Espia(datos)
        ul(e, 80, tope)
        techo = min(len(datos), tope + 256 * 1024)
        if e.leidos > techo:
            fallos.append("%s: leidos %.1f MB de un fichero de %.1f MB (x%.1f), "
                          "techo %.1f MB — se esta releyendo"
                          % (que, e.leidos / 1048576.0, len(datos) / 1048576.0,
                             e.leidos / float(len(datos)), techo / 1048576.0))

    for f in fallos:
        print("FALLO:", f)
    print("ok" if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
