#!/usr/bin/env python3
"""De que CLI es cada fila, y cuando merece la pena decirlo.

Antes el CLI de una sesion solo se sabia por la pestana en la que estabas — o sea, nunca
en la vista mezclada, que es justo donde hace falta. Y la barra mezclaba dos ejes:
`historial` no es un CLI, son sesiones de Claude paradas, un ESTADO.

Lo que se vigila:

  1. el glifo sale SOLO cuando la lista mezcla CLIs. En la pestana de uno, repetiria
     ocho veces lo que la pestana activa ya dice, y esas dos columnas las quiere el
     titulo;
  2. cada CLI tiene el suyo, y todos miden UNA columna — un glifo de dos descuadra la
     tabla entera, y es un fallo que no da ningun error;
  3. `historial` cae dentro de `claude` y no es una pestana;
  4. la barra y el ciclo del Tab salen del MISMO calculo. Tenian una copia cada uno, y
     una miraba `fuente` mientras la otra miraba el CLI: el Tab paraba en una pestana
     que la barra no dibujaba y la lista salia vacia.
"""
import os, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
os.environ["SERENO_DEMO"] = "1"
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)


def main():
    fallos = []
    ancho = ns["ancho"]

    # 2. Uno por CLI, y de UNA columna.
    for cli, gl in ns["GLIFO_CLI"].items():
        if ancho(gl) != 1:
            fallos.append(f"el glifo de {cli} mide {ancho(gl)} columnas, no 1")
    if len(set(ns["GLIFO_CLI"].values())) != len(ns["GLIFO_CLI"]):
        fallos.append("dos CLI comparten glifo")
    # Y ninguno choca con los que ya usa la lista para otra cosa: `▪` es "tiene
    # pestana abierta" y `●`/`◐` son el estado.
    for ocupado in ("▪", "●", "◐", "○", "⧉", "↻", "▎"):
        if ocupado in ns["GLIFO_CLI"].values():
            fallos.append(f"el glifo {ocupado!r} ya significa otra cosa en la lista")

    # 3. `historial` no es pestana, y cae en `claude`.
    if "historial" in ns["ORDEN_FUENTES"]:
        fallos.append("`historial` sigue siendo una pestana: no es un CLI, es un estado")
    if ns["cli_de"]({"fuente": "historial"}) != "claude":
        fallos.append("una sesion parada de Claude no cuenta como Claude")

    # 4. Un solo calculo para la barra y para el Tab.
    filas = [{"fuente": "claude"}, {"fuente": "historial"}, {"fuente": "codex"}]
    if ns["clis_presentes"](filas) != ["claude", "codex"]:
        fallos.append(f"clis_presentes: {ns['clis_presentes'](filas)}")
    # Un CLI que nadie previo no se pierde: va al final, ordenado.
    if ns["clis_presentes"](filas + [{"fuente": "zzz"}])[-1] != "zzz":
        fallos.append("un CLI desconocido desaparece de las pestanas")
    fuente = (RAIZ / "sereno").read_text()
    if fuente.count("+ sorted(f for f in hay if f not in ORDEN_FUENTES)") != 1:
        fallos.append("vuelve a haber dos copias del calculo de pestanas: es lo que "
                      "hizo que el Tab y la barra dejaran de estar de acuerdo")

    # 1. El coste en columnas solo se paga con mezcla. `reparto` es pura y tiene su
    #    propio test; aqui solo se mira que el parametro haga algo y en el sentido bueno.
    solo, mezclada = (ns["reparto"](100, 40, 12, True, True, m) for m in (False, True))
    if solo[4] + ns["COL_CLI"] != mezclada[4]:
        fallos.append(f"la mezcla no cuesta {ns['COL_CLI']} columnas: "
                      f"{solo[4]} contra {mezclada[4]}")
    if mezclada[0] > solo[0]:
        fallos.append("con mezcla el titulo GANA ancho: el glifo sale gratis y eso "
                      "significa que no se esta pintando")

    # 5. Y en pantalla, que es donde se ve: el glifo esta en la vista mezclada y NO en
    #    la de un solo CLI. Lo demas de este test mira tablas; esto mira celdas.
    import contextlib, io
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from doble_curses import espia
    os.environ["SERENO_DEBUG"] = "1"

    def pinta(teclas, h=26, w=128):
        import curses as real
        cajon = []
        sys.modules["curses"] = espia(real, h, w, list(teclas) + [ord("q")], cajon,
                                      ns["ancho"])
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ns["pick_ui"](ns["live_sessions"](), recargar=ns["live_sessions"])
        finally:
            sys.modules["curses"] = real
        p = cajon[0]
        celdas = p.celdas or (p.fotogramas[-1] if p.fotogramas else {})
        return "\n".join("".join(celdas.get((y, x), " ") for x in range(w))
                          for y in range(h))

    solo_claude = pinta([])
    mezclada_p = pinta([9, 9])              # Tab, Tab -> "todas"
    gl_claude, gl_codex = ns["GLIFO_CLI"]["claude"], ns["GLIFO_CLI"]["codex"]
    # En la vista de un CLI el glifo sale UNA vez: en su pestana, que hace de leyenda.
    if solo_claude.count(gl_claude) != 1:
        fallos.append(f"en la vista de un solo CLI el glifo sale "
                      f"{solo_claude.count(gl_claude)} veces, se esperaba 1 (la pestana)")
    # En la mezclada, en su pestana y ademas en cada fila de ese CLI.
    if mezclada_p.count(gl_claude) < 3 or mezclada_p.count(gl_codex) < 2:
        fallos.append(f"en la vista mezclada faltan glifos: claude x"
                      f"{mezclada_p.count(gl_claude)}, codex x{mezclada_p.count(gl_codex)}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_glifo_cli" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
