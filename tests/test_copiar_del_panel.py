#!/usr/bin/env python3
"""Los valores del panel que se pegan en otro sitio se copian pinchandolos.

Lo que se prueba aqui no es "el portapapeles funciona" —de eso ya se encarga
`copia_al_portapapeles`, que es cuatro lineas— sino las dos cosas que se rompen sin
hacer ruido:

1. **Que lo que se copia no sea lo que se lee.** El campo `project` ensena el nombre
   corto del proyecto y la rama, pero lo que uno pega en una terminal es la ruta
   entera, que en el panel no aparece NUNCA (medido: 40 de 40 sesiones del historial
   de esta maquina). Un clic que copiara lo pintado copiaria justo lo que ya se estaba
   leyendo, y desde fuera se ve identico: se copia algo, sale el rotulo, todo verde.
   Por eso el caso se elige con las dos cadenas distintas y se comprueba la de verdad,
   la que sale por OSC 52.
2. **Que se vea que es copiable ANTES de pinchar.** Eso es el subrayado. El doble de
   `stdscr` no distingue colores —los pares valen 0— pero `A_UNDERLINE` es una
   constante del curses real y llega con su valor, asi que esta mitad si se puede
   comprobar sin terminal.

Y se comprueba tambien lo contrario: un campo que no lleva nada que copiar no sale
subrayado y pincharlo no copia nada. Sin ese negativo, "todo esta subrayado y todo
copia" pasaria los tres positivos.
"""
import base64, contextlib, io, os, pathlib, re, sys

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_LANG"] = "en"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doble_curses import espia            # noqa: E402  (el path se fija arriba)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

Q = ord("q")
OSC52 = re.compile("\033]52;c;([A-Za-z0-9+/=]*)\a")


def pinta(previas=(), clicks=(), h=32, w=170):
    """Pinta el panel y devuelve (celdas, atributos, [lo copiado], alto, ancho).

    `previas` son teclas que se pulsan ANTES de pinchar: hacen falta porque el bloque
    de la respuesta solo cabe en las filas cuyo recorrido es corto, y la primera de la
    demo no lo es. Las coordenadas del click se sacan del fotograma pintado con esas
    mismas teclas, no del de arriba.

    `clicks` son pares (x, y). Cada uno entra como un KEY_MOUSE y `getmouse` los va
    devolviendo en orden: es el mismo camino que recorre un click de verdad, con la
    zona resuelta dentro de `run()`. Pinchar sin pasar por ahi probaria la funcion de
    copiar, que no es lo que aqui se duda.
    """
    import curses as real
    pendientes = list(clicks)
    teclas = list(previas) + [real.KEY_MOUSE] * len(pendientes) + [Q]
    cajon = []
    falso = espia(real, h, w, teclas, cajon, ns["ancho"])

    def raton():
        x, y = pendientes.pop(0)
        return (0, x, y, 0, real.BUTTON1_PRESSED)

    falso.getmouse = raton
    salida = io.StringIO()
    sys.modules["curses"] = falso
    try:
        with contextlib.redirect_stdout(salida):
            ns["pick_ui"](ns["sesiones_demo"]())
    finally:
        sys.modules["curses"] = real
    p = cajon[0]
    copiado = [base64.b64decode(m).decode("utf-8")
               for m in OSC52.findall(salida.getvalue())]
    return p.celdas, p.atributos, copiado, h, w


def texto(celdas, y, x0, x1, w):
    return "".join(celdas.get((y, x), " ") for x in range(x0, min(x1, w))).strip()


def busca_etiqueta(celdas, etiqueta, h, w, x0=None):
    """(y, x) donde empieza esa etiqueta del panel.

    `x0` no es un lujo: sin anclar la columna, buscar "session" encontraba primero la
    cabecera «another session is writing here too» y el test se media contra un bloque
    que no era el suyo. Todo lo del panel —etiquetas y cabeceras— empieza en la misma
    columna, asi que se exige ahi.
    """
    for y in range(h):
        fila = "".join(celdas.get((y, x), " ") for x in range(w))
        if x0 is not None:
            if fila[x0:x0 + len(etiqueta)] == etiqueta:
                return y, x0
            continue
        i = fila.find(etiqueta)
        if i >= 0:
            return y, i
    return None, None


def subrayado(atributos, y, x0, x1):
    import curses as real
    celdas = [atributos.get((y, x), 0) for x in range(x0, x1)]
    return [bool(a & real.A_UNDERLINE) for a in celdas]


def main():
    fallos = []
    # Dos filas mas abajo: el bloque de la respuesta solo cabe donde el recorrido es
    # corto, y en las dos primeras de la demo ocupa ocho lineas y lo desplaza fuera.
    SALTOS = (ord("j"), ord("j"))
    celdas, atributos, _c, h, w = pinta(previas=SALTOS)
    demo = {(r.get("proyecto"), r.get("rama")): (r.get("meta") or {}).get("cwd")
            for r in ns["sesiones_demo"]()}

    # ── 1. el campo `project`: subrayado, y lo que copia NO es lo que pinta ────
    y, x0 = busca_etiqueta(celdas, "project", h, w)
    if y is None:
        print("FALLO: el panel no pinta el campo `project`")
        return 1
    xv = x0 + 10                                   # la etiqueta ocupa 10 columnas
    pintado = texto(celdas, y, xv, w, w)
    if not pintado:
        fallos.append("el campo `project` sale vacio")

    marcas = subrayado(atributos, y, xv, xv + len(pintado))
    if not all(marcas):
        fallos.append(f"el valor de `project` no sale subrayado entero: {marcas}")
    if any(subrayado(atributos, y, x0, x0 + len("project"))):
        fallos.append("la ETIQUETA `project` sale subrayada; solo el valor se copia")

    _cel, _at, copiado, _h, _w = pinta(previas=SALTOS, clicks=[(xv + 1, y)])
    if len(copiado) != 1:
        fallos.append(f"un click en `project` copio {len(copiado)} veces, esperaba 1")
    else:
        obtenido = copiado[0]
        clave = (tuple(t.strip() for t in pintado.split("\u00b7"))
                 if "\u00b7" in pintado else (pintado.strip(), ""))
        esperado = demo.get(clave)
        if obtenido == pintado:
            fallos.append("`project` copio lo PINTADO; tiene que copiar la ruta entera")
        elif esperado is None:
            fallos.append(f"no encuentro en la demo la fila pintada {clave!r}")
        elif obtenido != esperado:
            fallos.append(f"`project` copio {obtenido!r}, esperaba {esperado!r}")

    # ── 2. el campo `session`: aqui lo copiado SI es lo pintado ────────────────
    ys, xs = busca_etiqueta(celdas, "session", h, w, x0)
    if ys is None:
        fallos.append("el panel no pinta el campo `session`")
    else:
        xvs = xs + 10
        pint_s = texto(celdas, ys, xvs, w, w)
        if not all(subrayado(atributos, ys, xvs, xvs + len(pint_s))):
            fallos.append("el valor de `session` no sale subrayado")
        _c1, _a1, cop_s, _h1, _w1 = pinta(previas=SALTOS, clicks=[(xvs + 1, ys)])
        if cop_s != [pint_s]:
            fallos.append(f"`session` copio {cop_s!r}, esperaba [{pint_s!r}]")

    # ── 3. la cabecera de la respuesta copia el CUERPO, no la cabecera ─────────
    cab = "\u25b8 what it last replied"
    yr, xr = busca_etiqueta(celdas, cab, h, w, x0)
    if yr is None:
        fallos.append("el panel no pinta el bloque de la ultima respuesta")
    else:
        if not all(subrayado(atributos, yr, xr, xr + len(cab))):
            fallos.append("la cabecera de la respuesta no sale subrayada")
        _c2, _a2, cop_r, _h2, _w2 = pinta(previas=SALTOS, clicks=[(xr + 2, yr)])
        if len(cop_r) != 1:
            fallos.append(f"un click en la cabecera copio {len(cop_r)} veces")
        elif cab in cop_r[0]:
            fallos.append("la cabecera se copio a si misma en vez del texto de debajo")
        else:
            # el cuerpo pintado es el mismo texto troceado: tiene que empezar igual
            debajo = texto(celdas, yr + 1, xr, w, w)
            if debajo and not cop_r[0].startswith(debajo[:20]):
                fallos.append(f"lo copiado no es el texto de debajo: {cop_r[0][:40]!r}")

    # ── 4. el negativo: un campo sin nada que copiar ni se subraya ni copia ────
    ym, xm = busca_etiqueta(celdas, "model", h, w, x0)
    if ym is None:
        fallos.append("el panel no pinta el campo `model` (hace falta de control)")
    else:
        xvm = xm + 10
        pint_m = texto(celdas, ym, xvm, w, w)
        if any(subrayado(atributos, ym, xvm, xvm + max(1, len(pint_m)))):
            fallos.append("`model` sale subrayado y no lleva nada que copiar")
        _c3, _a3, cop_m, _h3, _w3 = pinta(previas=SALTOS, clicks=[(xvm + 1, ym)])
        if cop_m:
            fallos.append(f"un click en `model` copio {cop_m!r} y no debia copiar nada")

    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("ok: project copia la ruta entera, session el id, la cabecera el cuerpo, "
          "y model ni se subraya ni copia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
