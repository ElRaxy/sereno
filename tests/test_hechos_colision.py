#!/usr/bin/env python3
"""Los ocho hechos que se le ensenan a una sesion sobre la de al lado, uno por uno.

`hechos_colision` es la mitad de abajo de la frontera que pide
`.claude/rules/llm-decision-boundary.md`: constata, y `nivel_colision` compone el
veredicto encima. Esa mitad de abajo estaba cubierta solo por los dos campos mas
gruesos —el fichero comun y la carpeta comun—, medido por mutacion: de diez cambios
minimos aplicados a la funcion, siete pasaban los cincuenta y un tests en verde.

Los siete importan porque cada uno rompe el detector por el lado caro:

  · dos sesiones que no estan en ningun repo pasarian a compartirlo, y con el un
    `git commit` de una saltaria como aviso en la otra;
  · un `rm -r` sobre una carpeta que no toca nadie mas gritaria igual;
  · la carpeta compartida dejaria de contar escrituras, que es lo que distingue una
    carrera de AHORA de un rastro de hace un rato;
  · un tiempo que no se pudo medir se leeria como "hace cero segundos", que es
    justo lo contrario de lo que significa;
  · el aviso diria que la orden ancha la lanzo el otro cuando la lanzaste tu;
  · y la lista de ficheros del aviso enseniaria los de la sesion de al lado en vez
    de los compartidos, que ademas de ser falso saca a pantalla rutas de un cliente
    que no tienen nada que ver contigo.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

CAMPOS = {"mismo_fichero", "mismo_directorio", "mismo_repo", "ficheros",
          "escrituras_recientes", "segundos_desde_la_ultima", "orden_ancha",
          "orden_es_mia"}

# Lo que veria de mas quien listara los ficheros de la otra sesion en vez de los
# compartidos: la ruta esta escrita para que se reconozca de un vistazo en el diff.
CANARIO = "/r/clientes/CANARIO-CONFIDENCIAL/factura.py"

AHORA = 1_700_000_000


def s(repo, *toques):
    """Una sesion como la ve `hechos_colision`: {(clase, ruta, verbo): epoch}."""
    return {"repo": repo, "toques": {t: AHORA - 30 for t in toques}}


def w(ruta):
    return ("w", ruta, "Edit")


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    hechos = ns["hechos_colision"]
    fallos = []

    # ── control positivo: antes de opinar sobre ningun campo, que los campos sean
    # estos. Sin esto un renombrado convierte cada comprobacion de abajo en
    # `None == None`, y el test aprobaria una funcion que ya no existe.
    h = hechos(s("/r", w("/r/a.py")), s("/r", w("/r/a.py")), AHORA)
    if set(h) != CAMPOS:
        fallos.append("los campos ya no son los que este test comprueba: "
                      "sobran %s, faltan %s" % (sorted(set(h) - CAMPOS),
                                                sorted(CAMPOS - set(h))))
        for f in fallos:
            print("FALLO:", f)
        return 1
    if not (h["mismo_fichero"] and h["ficheros"] == ("/r/a.py",)):
        fallos.append("el caso mas simple —las dos escriben el mismo fichero— ya no "
                      "se detecta; lo de abajo no significa nada")

    def comprueba(que, h, **esperado):
        for k, v in esperado.items():
            if h[k] != v:
                fallos.append("%s: %s = %r, se esperaba %r" % (que, k, h[k], v))

    # ── 1. sin repo conocido no hay repo compartido ──────────────────────────
    # `raiz_repo` devuelve "" para un cwd que no cuelga de ningun repo. Si "" == ""
    # contase como el mismo repo, todas las sesiones de fuera de un repo pasarian a
    # compartirlo — y con el, las ordenes anchas de cualquiera de ellas.
    comprueba("dos sesiones sin repo",
              hechos(s("", w("/tmp/x/a.py")),
                     s("", w("/tmp/y/b.py"), ("repo", "", "git commit")), AHORA),
              mismo_repo=False, orden_ancha="")

    # ── 2. una orden ancha solo choca si cae sobre terreno de la otra ────────
    comprueba("rm -r sobre una carpeta que no toca nadie mas",
              hechos(s("/r", w("/r/src/a.py")),
                     s("/r", ("dir", "/r/otros", "rm -r")), AHORA),
              orden_ancha="")
    comprueba("rm -r sobre la carpeta donde escribe la otra",
              hechos(s("/r", w("/r/src/a.py")),
                     s("/r", ("dir", "/r/src", "rm -r")), AHORA),
              orden_ancha="rm -r", orden_es_mia=False)

    # ── 3. de quien es la orden ancha ────────────────────────────────────────
    # No es cosmetico: "estas a punto de llevarte lo suyo" y "te estan a punto de
    # llevar lo tuyo" piden cosas distintas de quien lo lee.
    comprueba("el rm -r lo lanzo la sesion que mira",
              hechos(s("/r", ("dir", "/r/src", "rm -r")),
                     s("/r", w("/r/src/b.py")), AHORA),
              orden_ancha="rm -r", orden_es_mia=True)

    # ── 4. la carpeta compartida cuenta escrituras aunque no haya fichero comun ─
    # Es la medida de si esto esta caliente AHORA. Sin ella, dos sesiones en la
    # misma carpeta salen con el contador a cero y el aviso parece un rastro viejo.
    comprueba("misma carpeta, ficheros distintos",
              hechos(s("/r", w("/r/src/a.py")), s("/r", w("/r/src/b.py")), AHORA),
              mismo_fichero=False, mismo_directorio=True,
              escrituras_recientes=1, segundos_desde_la_ultima=30)

    # ── 5. las ordenes anchas del mismo repo tambien son actividad ───────────
    comprueba("la otra acaba de hacer un commit sin pathspec",
              hechos(s("/r", w("/r/src/a.py")),
                     s("/r", ("repo", "/r", "git commit")), AHORA),
              orden_ancha="git commit", escrituras_recientes=1,
              segundos_desde_la_ultima=30)

    # ── 6. lo que no se pudo medir no es cero ───────────────────────────────
    # Un `0` se lee como "hace nada", que es lo contrario de "no lo se". Es la regla
    # de `llm-decision-boundary.md` aplicada a un campo concreto.
    comprueba("nada en comun: no hay ultima escritura que fechar",
              hechos(s("/r1", w("/r1/a.py")), s("/r2", w("/r2/b.py")), AHORA),
              escrituras_recientes=0, segundos_desde_la_ultima=None,
              mismo_repo=False, mismo_directorio=False)

    # ── 7. los ficheros del aviso son los COMPARTIDOS ───────────────────────
    h = hechos(s("/r", w("/r/a.py"), w("/r/mio.py")),
               s("/r", w("/r/a.py"), w(CANARIO)), AHORA)
    comprueba("solo los ficheros comunes", h, ficheros=("/r/a.py",))
    if CANARIO in h["ficheros"]:
        fallos.append("el aviso saca a pantalla un fichero que solo toco la otra "
                      "sesion: " + CANARIO)

    for f in fallos:
        print("FALLO:", f)
    print("ok" if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
