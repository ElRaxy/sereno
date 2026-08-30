#!/usr/bin/env python3
"""Las sesiones de Codex, leidas de su indice y no de sus 441 rollouts.

El indice de Codex es un fichero que solo crece: cada vez que una sesion cambia se
anade una linea mas con el MISMO id. Leerlo sin deduplicar no da un error, da una lista
con la misma sesion nueve veces y las demas empujadas fuera del limite — el fallo se ve
como "me faltan sesiones", que es lo ultimo que se mira aqui.

Lo que este test sostiene, y lo que cuesta cada cosa si se rompe:

  · **deduplicar por id, quedandose con lo ULTIMO.** Un titulo que ya se cambio saldria
    con el viejo, y la fila se ordenaria por una fecha que ya no es.
  · **una linea corrupta se salta.** El indice lo escribe otro programa; que una linea
    a medias —Codex escribiendo mientras leemos— deje la lista entera vacia convierte
    un parpadeo en "Codex no tiene sesiones".
  · **el orden y el limite.** Se pintan las 40 mas recientes; sin orden, las 40 son
    cualesquiera.
  · **leer la cola y no el fichero entero**, que es la razon de existir de leer el
    indice en vez de los rollouts.
"""
import io
import os
import pathlib
import sys
import tempfile

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent


def linea(sid, titulo, cuando):
    import json
    return json.dumps({"id": sid, "thread_name": titulo, "updated_at": cuando})


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    fallos = []

    # El cwd sale de la cabecera de cada rollout, que aqui no existe: se anula para que
    # el test hable solo del indice.
    ns["_cwd_codex"] = lambda ids: {}

    tmp = pathlib.Path(tempfile.mkdtemp())
    indice = tmp / "session_index.jsonl"
    ns["CODEX_INDEX"] = indice

    def sesiones(**kw):
        return ns["sesiones_codex"](**kw)

    def comprueba(que, cond, extra=""):
        if not cond:
            fallos.append(que + (": " + extra if extra else ""))

    # ── control positivo: sin esto, "no sale lo que no debe" pasaria con [] ──
    indice.write_text("\n".join([
        linea("aaa", "la primera", "2026-08-30T10:00:00Z"),
        linea("bbb", "la segunda", "2026-08-30T11:00:00Z"),
    ]) + "\n")
    r = sesiones()
    if len(r) != 2 or {x["title_full"] for x in r} != {"la primera", "la segunda"}:
        print("FALLO: el caso mas simple ya no funciona: %r"
              % ([x.get("title_full") for x in r],))
        return 1

    # ── el indice solo crece: la misma sesion, muchas lineas ────────────────
    indice.write_text("\n".join([
        linea("aaa", "titulo viejo", "2026-08-30T10:00:00Z"),
        linea("bbb", "otra", "2026-08-30T10:30:00Z"),
        linea("aaa", "titulo nuevo", "2026-08-30T12:00:00Z"),
    ]) + "\n")
    r = sesiones()
    comprueba("una sesion repetida en el indice sale mas de una vez",
              len(r) == 2, "salen %d" % len(r))
    aaa = [x for x in r if x["name"] == "aaa"]
    comprueba("la sesion repetida no aparece", aaa)
    if aaa:
        comprueba("gana la linea vieja en vez de la ultima",
                  aaa[0]["title_full"] == "titulo nuevo", aaa[0]["title_full"])

    # ── el orden es por fecha, de lo mas reciente a lo mas viejo ────────────
    indice.write_text("\n".join([
        linea("v", "la vieja", "2026-08-01T10:00:00Z"),
        linea("n", "la nueva", "2026-08-30T10:00:00Z"),
        linea("m", "la de en medio", "2026-08-15T10:00:00Z"),
    ]) + "\n")
    comprueba("el orden no es por fecha descendente",
              [x["name"] for x in sesiones()] == ["n", "m", "v"],
              repr([x["name"] for x in sesiones()]))

    # ── el limite recorta, y recorta por el final ───────────────────────────
    indice.write_text("\n".join(
        linea("s%02d" % i, "t%d" % i, "2026-08-%02dT10:00:00Z" % (i + 1))
        for i in range(20)) + "\n")
    r3 = sesiones(limite=3)
    comprueba("el limite no recorta", len(r3) == 3, "salen %d" % len(r3))
    comprueba("el limite se queda con las viejas en vez de las recientes",
              [x["name"] for x in r3] == ["s19", "s18", "s17"],
              repr([x["name"] for x in r3]))

    # ── una linea a medias no se lleva por delante a las demas ──────────────
    indice.write_text("\n".join([
        linea("ok1", "buena", "2026-08-30T10:00:00Z"),
        '{"id": "rota", "thread_nam',
        "",
        "no soy json en absoluto",
        linea("ok2", "otra buena", "2026-08-30T11:00:00Z"),
    ]) + "\n")
    r = sesiones()
    comprueba("una linea corrupta deja la lista sin las buenas",
              {x["name"] for x in r} == {"ok1", "ok2"},
              repr([x["name"] for x in r]))

    # ── una entrada sin titulo se pinta igual, con nombre de relleno ────────
    import json as _json
    indice.write_text(_json.dumps({"id": "sin", "updated_at":
                                   "2026-08-30T10:00:00Z"}) + "\n")
    r = sesiones()
    comprueba("una sesion sin titulo desaparece de la lista", len(r) == 1)
    if r:
        comprueba("una sesion sin titulo se pinta con el titulo vacio",
                  r[0]["title_full"].strip(), repr(r[0]["title_full"]))

    # ── sin fichero, nada; y no una excepcion ───────────────────────────────
    ns["CODEX_INDEX"] = tmp / "no-existe.jsonl"
    try:
        vacio = sesiones()
    except Exception as e:
        vacio = "revento: %s" % e
    comprueba("sin indice de Codex no se devuelve la lista vacia", vacio == [],
              repr(vacio))
    ns["CODEX_INDEX"] = indice

    # ── el coste: se lee la COLA, no el indice entero ───────────────────────
    # Es la razon de leer el indice en vez de los rollouts. Un indice de anos con
    # cientos de miles de lineas no puede costar mas que abrir el selector.
    relleno = "\n".join(linea("viejo%06d" % i, "t", "2026-01-01T10:00:00Z")
                        for i in range(60000))
    indice.write_text(relleno + "\n" + linea("z", "la ultima",
                                             "2026-08-30T10:00:00Z") + "\n")
    tam = indice.stat().st_size
    leidos = [0]
    abre = pathlib.Path.open

    def espia(self, *a, **kw):
        f = abre(self, *a, **kw)
        if self != indice:
            return f
        real = f.read

        def read(n=-1):
            b = real(n)
            leidos[0] += len(b)
            return b
        f.read = read
        return f

    pathlib.Path.open = espia
    try:
        r = sesiones()
    finally:
        pathlib.Path.open = abre
    comprueba("con un indice enorme se pierde la ultima sesion",
              any(x["name"] == "z" for x in r))
    comprueba("se lee el indice entero en vez de su cola",
              leidos[0] <= 1024 * 1024,
              "%.1f MB leidos de un indice de %.1f MB"
              % (leidos[0] / 1048576.0, tam / 1048576.0))

    for f in fallos:
        print("FALLO:", f)
    print("ok" if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
