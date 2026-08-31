#!/usr/bin/env python3
"""El panel lateral reparte su altura sin salirse, y compone lo que compone.

Las tres funciones que se prueban aqui vivian dentro de `pick_ui`, que son 1.200 lineas
de curses, asi que el panel solo se podia mirar por lo que acababa pintando.
`test_panel_geometria.py` ya vigila eso —que nada se salga del marco y que ninguna celda
se escriba dos veces— pero desde el otro lado: ve el SINTOMA, no el reparto que lo causa,
y solo con los datos del demo. De nueve cambios minimos a estas tres funciones, cinco
pasaban la bateria entera en verde: un bloque con cero lineas bajo su cabecera, un
recorrido sin sitio pintando su cabecera sola, los campos vacios llegando como etiquetas
en blanco, y "ahora mismo" repitiendo lo que el recorrido ya cuenta.

`reparto_panel` es la mas cara de las tres: decide QUE SE VE cuando no cabe todo. Se
comprueba por barrido —77.824 combinaciones de altura, campos, bloques y recorrido— y
no con un puñado de casos, porque basta que falle una para que algo se pinte fuera del
area, y curses no avisa cuando eso pasa.

Alcance: esto fija el REPARTO y la COMPOSICION, no el pintado. Que lo repartido acabe
en la pantalla lo cubre `test_tui_arranca.py`, que arranca la interfaz de verdad.
"""
import itertools
import os
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def carga():
    # Los textos se comparan en ingles: en la maquina de Alex el locale es el castellano
    # y el test compararia contra la traduccion, que es lo que hace que un test pase o
    # falle segun quien lo corra.
    os.environ["SERENO_LANG"] = "en"
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(encoding="utf-8"), "sereno", "exec"), ns)
    return ns


def bloque(texto, tope):
    return ("cabecera", texto, 6, tope, True)


def prueba_reparto(S):
    """Ninguna zona se sale del area, y las tres no se pisan entre si."""
    fallos = []
    # 400 y no 4.000: lo que se prueba es que el tope satura, y con un panel de
    # 26 columnas 400 caracteres ya piden 16 lineas contra topes de 2 a 5. Medir
    # el ancho de cadenas de 4.000 en 77.824 vueltas costaba 50 s de los 55 que
    # dura la bateria entera.
    textos = ("", "corto", "x" * 120, "y" * 400)
    bloques_posibles = [
        [],
        [bloque(textos[1], 4)],
        [bloque(textos[2], 4), bloque(textos[3], 5)],
        [bloque(textos[1], 3), bloque(textos[2], 2), bloque(textos[3], 5)],
    ]
    combinaciones = itertools.product(
        (2, 3),                        # fila0
        range(3, 41),                  # fondo
        (0, 1, 5, 11),                 # cuantos campos
        range(len(bloques_posibles)),
        (0, 1, 6, 20),                 # pasos del recorrido que existen
        (0, 3),                        # alertas del recorrido
        (0, 26, 70, 200),              # ancho del panel
    )
    n = 0
    for fila0, fondo, n_campos, ib, n_ruta_total, n_alertas, ancho_det in combinaciones:
        bloques = bloques_posibles[ib]
        for pedido in (False, True):
            n += 1
            hay = pedido and n_ruta_total > 0
            base_c, base_r, n_ruta, hay_ruta, cuotas = S["reparto_panel"](
                fila0, fondo, n_campos, bloques, n_ruta_total, n_alertas,
                ancho_det, hay)
            caso = (f"fila0={fila0} fondo={fondo} campos={n_campos} bloques={len(bloques)} "
                    f"ruta={n_ruta_total} alertas={n_alertas} ancho={ancho_det} hay={hay}")

            # 1. Las tres zonas van en orden y ninguna empieza por encima del techo.
            if not (fila0 <= base_r <= base_c):
                fallos.append(f"zonas cruzadas ({base_r} / {base_c}) · {caso}")

            # 2. El recorrido cabe entero entre donde empieza y donde empiezan los
            #    campos: cabecera + alertas + pasos, mas la linea en blanco.
            if hay_ruta and base_r + 1 + n_alertas + n_ruta > base_c:
                fallos.append(f"el recorrido se mete en los campos · {caso}")

            # 3. Un recorrido que se anuncia tiene al menos un paso; uno que no cabe se
            #    apaga entero en vez de pintar la cabecera sola.
            if hay_ruta and n_ruta < 1:
                fallos.append(f"recorrido encendido y vacio · {caso}")
            if not hay_ruta and n_ruta:
                fallos.append(f"recorrido apagado con {n_ruta} pasos · {caso}")

            # 4. Nunca se ensenan mas pasos de los que hay, ni mas del tope.
            if n_ruta > min(S["RUTA_VISIBLE"], n_ruta_total):
                fallos.append(f"{n_ruta} pasos de {n_ruta_total} · {caso}")

            # 5. Una cuota por bloque, ninguna a cero —una cabecera sin nada debajo no
            #    informa— y ninguna por encima de su propio tope.
            if len(cuotas) != len(bloques):
                fallos.append(f"{len(cuotas)} cuotas para {len(bloques)} bloques · {caso}")
            for (_e, _t, _p, tope, _c), q in zip(bloques, cuotas):
                if not (1 <= q <= tope):
                    fallos.append(f"cuota {q} fuera de [1,{tope}] · {caso}")

            # 6. Los campos empiezan donde caben todos, salvo que el techo lo impida:
            #    ceder por arriba es lo correcto, pintar por debajo del borde no.
            if base_c > fila0 + 2 and base_c + n_campos - 1 > fondo:
                fallos.append(f"los campos pasan del fondo ({base_c}+{n_campos}) · {caso}")
    return fallos, n


def prueba_campos(S):
    """Un campo vacio no llega, y lo que se copia no siempre es lo que se pinta."""
    fallos = []
    r = {"name": "sesion-1", "created": 1000.0, "mem_mb": 120,
         "proyecto": "VanguardIA", "rama": "main",
         "pulso": {"ctx": 40000, "modelo": "claude-opus-5"}, "_uso": None}
    d = {"fase": "te espera", "peso": 5 * 1024 * 1024}
    campos = S["campos_panel"](r, d, "/Users/alex/Desktop/VanguardIA", ahora=1060.0)
    por_etiqueta = {c[0]: c for c in campos}

    if any(not c[1] for c in campos):
        fallos.append("un campo vacio llego a la lista")

    # El clic copia la ruta ENTERA, no el nombre corto que se lee en el panel.
    proy = por_etiqueta.get("project")
    if not proy:
        fallos.append("falta el campo del proyecto")
    elif len(proy) < 4 or proy[3] != "/Users/alex/Desktop/VanguardIA":
        fallos.append("el proyecto no copia la ruta completa")
    elif proy[1] == proy[3]:
        fallos.append("copia lo mismo que pinta: el clic no rescata nada")

    # Una sesion sin nada que contar no deja una lista de etiquetas en blanco.
    vacia = S["campos_panel"]({"name": "n", "created": None, "mem_mb": None},
                              {}, "", ahora=1060.0)
    if any(not c[1] for c in vacia):
        fallos.append("una sesion sin datos deja etiquetas vacias")

    # Mientras el acumulado se lee, un guion y no media cifra.
    a_medias = dict(r, _uso={"completo": False})
    etiquetas = {c[0]: c[1] for c in S["campos_panel"](a_medias, d, "", ahora=1060.0)}
    if "spent" in etiquetas and etiquetas["spent"] not in ("reading…",):
        fallos.append("el gasto a medias se pinta como si fuera el total")
    return fallos


def prueba_bloques(S):
    """El choque va primero, y 'ahora mismo' solo cuando el recorrido no cabe."""
    fallos = []
    d = {"tool": "Bash", "resp": "lo que contesto"}
    r = {"colision": None, "pulso": {"herramienta": "Bash"}}

    sin_ruta = S["bloques_panel"](r, d, "lo que dijo", hay_ruta=False)
    con_ruta = S["bloques_panel"](r, d, "lo que dijo", hay_ruta=True)
    if len(sin_ruta) != len(con_ruta) + 1:
        fallos.append("'ahora mismo' no desaparece cuando el recorrido lo cuenta")

    con_choque = S["bloques_panel"](dict(r, colision={"ficheros": ["/x/src/webhooks.py"],
                                          "mismo_directorio": True,
                                          "titulo": "la otra sesion"}),
                                    d, "lo que dijo", hay_ruta=True)
    if not con_choque or "writing here too" not in con_choque[0][0]:
        fallos.append("el choque no va el primero de todos")

    # Sin nada que decir, ni una cabecera: el panel no pinta titulos huecos.
    if S["bloques_panel"]({}, {}, "", hay_ruta=True):
        fallos.append("bloques sin texto llegaron a pintarse")

    # Solo el prompt y la respuesta se copian al pincharlos.
    copiables = [b[0] for b in sin_ruta if b[4]]
    if len(copiables) != 2:
        fallos.append(f"{len(copiables)} bloques copiables, esperaba 2")
    return fallos


def main():
    S = carga()
    fallos, n = prueba_reparto(S)
    fallos += prueba_campos(S)
    fallos += prueba_bloques(S)
    for f in fallos[:20]:
        print("FALLO:", f)
    if len(fallos) > 20:
        print(f"... y {len(fallos) - 20} mas")
    print(f"ok: el panel reparte sin salirse en {n} combinaciones, y compone lo que debe"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
