#!/usr/bin/env python3
"""El texto de los dos cuadros que preguntan antes de abrir ventanas.

`test_cuadro_relevo.py` comprueba que el cuadro CABE y que la eleccion llega entera a
`relevo()`. Lo que dice cada linea no lo miraba nadie: de los cuatro cambios minimos
probados sobre este compositor, los cuatro pasaban los 53 tests en verde.

Y aqui el texto es la funcion. El cuadro es lo ultimo que se ve antes de abrir ventanas
de otro CLI, asi que cada linea responde a una pregunta que no se puede dejar a medias:
cuantas sesiones se entregan —el plural mal escrito hace dudar de si son estas o todas—,
cuales son —si se recortan a cinco hay que DECIR que hay mas, o la lista miente por
omision—, y por que no aparece el CLI que uno esperaba: uno de los motivos se arregla
instalandolo y el otro no, asi que agruparlos bajo un mismo renglon deja al lector sin
saber cual es el suyo.

Los dos cuadros —`lineas_relevo` y `lineas_abrir`— comparten la mitad de arriba palabra
por palabra: el titulo con su plural, las cinco primeras filas y el "y N mas". Es codigo
duplicado a proposito, y por eso se comprueban juntos: un arreglo en uno que no llegue al
otro es exactamente el fallo que esta forma invita a cometer.
"""
import os
import pathlib
import shlex
import sys

os.environ["SERENO_DEMO"] = "1"
os.environ["SERENO_LANG"] = "en"
RAIZ = pathlib.Path(__file__).resolve().parent.parent


def filas(n, titulo="una sesion cualquiera"):
    return [{"title_full": "%s %d" % (titulo, i), "name": "id%d" % i}
            for i in range(n)]


def textos(lineas):
    return [t for t, _par in lineas]


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    lr = ns["lineas_relevo"]
    fallos = []

    # Los ausentes los decide el PATH de la maquina, que en el CI esta vacio y aqui no.
    # Se fija a mano para que el test diga lo mismo en los dos sitios.
    ausentes = [("codex", "not installed"), ("gemini", "not checked how to seed it")]
    ns["ausentes_de_relevo"] = lambda destinos: list(ausentes)

    # ── control positivo: sin esto, lo de abajo comprobaria listas vacias ────
    base = textos(lr(filas(1), ["claude"], False, 60))
    if not any("claude" in t for t in base):
        print("FALLO: el destino ofrecido no aparece en el cuadro: %r" % (base,))
        return 1
    if not any("una sesion cualquiera 0" in t for t in base):
        print("FALLO: la sesion que se entrega no aparece en el cuadro")
        return 1

    def comprueba(que, cond, extra=""):
        if not cond:
            fallos.append(que + (": " + extra if extra else ""))

    # ── cuantas se entregan: el singular no es cosmetico ─────────────────────
    una = " ".join(textos(lr(filas(1), ["claude"], False, 60)))
    tres = " ".join(textos(lr(filas(3), ["claude"], False, 60)))
    comprueba("con una sesion el titulo va en plural", "1 session to" in una, una[:60])
    comprueba("con tres sesiones el titulo va en singular",
              "3 sessions to" in tres, tres[:60])

    # ── recortar la lista sin decirlo es mentir por omision ──────────────────
    t8 = textos(lr(filas(8), ["claude"], False, 60, tope=5))
    nombradas = [t for t in t8 if "una sesion cualquiera" in t]
    comprueba("se pintan mas filas que el tope", len(nombradas) == 5,
              "son %d" % len(nombradas))
    comprueba("no se dice cuantas quedan fuera", any("3 more" in t for t in t8),
              repr(t8))
    t5 = textos(lr(filas(5), ["claude"], False, 60, tope=5))
    comprueba("sale un 'y N mas' con la lista completa",
              not any("more" in t for t in t5))

    # ── los ausentes, cada uno con SU motivo ─────────────────────────────────
    t = textos(lr(filas(1), ["claude"], False, 60))
    linea_codex = [x for x in t if "codex" in x]
    linea_gemini = [x for x in t if "gemini" in x]
    comprueba("no se dice que codex no se puede ofrecer", linea_codex)
    comprueba("no se dice que gemini no se puede ofrecer", linea_gemini)
    if linea_codex and linea_gemini:
        comprueba("los dos ausentes caen en el mismo renglon",
                  linea_codex[0] != linea_gemini[0])
        comprueba("codex no lleva su motivo", "not installed" in linea_codex[0])
        comprueba("gemini no lleva su motivo",
                  "not checked how to seed it" in linea_gemini[0])
    # Dos CLI con el MISMO motivo si comparten renglon: es lo que hace legible la lista
    # cuando faltan cuatro.
    ausentes[:] = [("codex", "not installed"), ("gemini", "not installed")]
    juntos = [x for x in textos(lr(filas(1), ["claude"], False, 60))
              if "not installed" in x]
    comprueba("dos ausentes por lo mismo se parten en dos renglones",
              len(juntos) == 1 and "codex" in juntos[0] and "gemini" in juntos[0],
              repr(juntos))
    ausentes[:] = [("codex", "not installed"),
                   ("gemini", "not checked how to seed it")]

    # ── el toggle de la conversacion dice su estado, y lo dice en color ──────
    off = lr(filas(1), ["claude"], False, 60)
    on = lr(filas(1), ["claude"], True, 60)
    k_off = [(t, p) for t, p in off if t.startswith("[k]")]
    k_on = [(t, p) for t, p in on if t.startswith("[k]")]
    comprueba("no hay linea de toggle de conversacion", k_off and k_on)
    if k_off and k_on:
        comprueba("el toggle no dice si esta activo", k_off[0][0] != k_on[0][0])
        comprueba("el toggle se pinta igual activo que apagado",
                  k_off[0][1] != k_on[0][1])
    comprueba("con la conversacion activada no se avisa de que se escribe a disco",
              any("on disk" in t for t in textos(on)))
    comprueba("el aviso de disco sale con la conversacion apagada",
              not any("on disk" in t for t in textos(off)))

    # ── donde abrirlas: preguntar con un solo sitio es ruido ─────────────────
    uno = textos(lr(filas(1), ["claude"], False, 60, donde="Warp",
                    hay_donde=("Warp",)))
    dos = textos(lr(filas(1), ["claude"], False, 60, donde="Warp",
                    hay_donde=("Warp", "Terminal")))
    comprueba("se pregunta donde abrir habiendo un solo sitio",
              not any(t.startswith("[w]") for t in uno))
    comprueba("no se pregunta donde abrir habiendo dos",
              any(t.startswith("[w]") for t in dos))

    # ── el titulo se recorta al ancho del cuadro ─────────────────────────────
    # Solo el titulo: las lineas fijas —las teclas, los ausentes— no dependen del
    # ancho y son las que lo FIJAN, que es lo que mide `test_cuadro_relevo.py`. Un
    # titulo sin recortar, en cambio, estira el cuadro hasta sacarlo de la pantalla.
    ancho = 40
    puestas = [t for t in textos(lr([{"title_full": "t" * 300, "name": "x"}],
                                    ["claude"], False, ancho))
               if t.startswith("\u00b7 ")]
    comprueba("el titulo no se pinta", puestas)
    if puestas:
        comprueba("el titulo se sale del cuadro",
                  max(len(t) for t in puestas) <= ancho,
                  "mide %d con ancho %d" % (max(len(t) for t in puestas), ancho))

    # ── el cuadro gemelo: `lineas_abrir` copia la mitad de arriba ────────────
    la = ns["lineas_abrir"]
    una_a = " ".join(textos(la(filas(1), ["Warp"], 60)))
    tres_a = " ".join(textos(la(filas(3), ["Warp"], 60)))
    comprueba("abrir: con una sesion el titulo va en plural",
              "1 session in" in una_a, una_a[:60])
    comprueba("abrir: con tres sesiones el titulo va en singular",
              "3 sessions in" in tres_a, tres_a[:60])
    a8 = textos(la(filas(8), ["Warp"], 60, tope=5))
    comprueba("abrir: se pintan mas filas que el tope",
              len([x for x in a8 if "una sesion cualquiera" in x]) == 5)
    comprueba("abrir: no se dice cuantas quedan fuera",
              any("3 more" in x for x in a8), repr(a8))
    puestas_a = [x for x in textos(la([{"title_full": "t" * 300, "name": "x"}],
                                      ["Warp"], ancho))
                 if x.startswith("\u00b7 ")]
    comprueba("abrir: el titulo no se pinta", puestas_a)
    if puestas_a:
        comprueba("abrir: el titulo se sale del cuadro",
                  max(len(x) for x in puestas_a) <= ancho)
    comprueba("abrir: el sitio ofrecido no aparece",
              any("Warp" in x for x in textos(la(filas(1), ["Warp"], 60))))

    # ── el toggle de modelo: dice su estado, en color, y solo cuando hay que elegir ──
    hay_m = (None, "opus", "sonnet")
    off_m = lr(filas(1), ["claude"], False, 60)                       # sin hay_modelo
    def_m = lr(filas(1), ["claude"], False, 60, modelo=None, hay_modelo=hay_m)
    on_m = lr(filas(1), ["claude"], False, 60, modelo="opus", hay_modelo=hay_m)
    comprueba("relevo: el toggle de modelo sale sin haber entre que elegir",
              not any(t.startswith("[m]") for t in textos(off_m)))
    m_def = [(t, p) for t, p in def_m if t.startswith("[m]")]
    m_on = [(t, p) for t, p in on_m if t.startswith("[m]")]
    comprueba("relevo: no hay linea de toggle de modelo", m_def and m_on)
    if m_def and m_on:
        comprueba("relevo: 'por defecto' no se pinta como el valor por defecto",
                  "default" in m_def[0][0])
        comprueba("relevo: el modelo elegido no aparece en el toggle",
                  "opus" in m_on[0][0])
        comprueba("relevo: el toggle de modelo se pinta igual puesto que por defecto",
                  m_def[0][1] != m_on[0][1])
    # y el gemelo `lineas_abrir` lleva el mismo toggle, con la misma regla
    off_a = la(filas(1), ["Warp"], 60)
    on_a = la(filas(1), ["Warp"], 60, modelo="opus", hay_modelo=hay_m)
    comprueba("abrir: el toggle de modelo sale sin haber entre que elegir",
              not any(t.startswith("[m]") for t in textos(off_a)))
    comprueba("abrir: no hay linea de toggle de modelo",
              any(t.startswith("[m]") and "opus" in t for t in textos(on_a)))

    # ── el modelo elegido llega a la orden compuesta, y SOLO donde toca ──────
    cd = ns["_comando_de"]
    ar = ns["ARNESES"]
    r_claude = {"name": "sid", "title_full": "parada", "meta": {"cwd": "/", "id": "sid-1"}}
    r_codex = {"name": "x", "title_full": "codex", "abrir": ["codex", "resume", "3333"],
               "meta": {"cwd": "/"}}
    r_gem = {"name": "g", "title_full": "gem", "abrir": ["gemini", "-i", "hola"],
             "meta": {"cwd": "/"}}
    r_live = {"name": "cc-proyecto-1", "title_full": "viva", "meta": {"cwd": "/"}}

    cmd_c = cd(r_claude, modelo="opus")[0]
    comprueba("la reapertura de Claude no lleva el modelo elegido",
              "--model opus" in cmd_c, cmd_c)
    comprueba("el binario deja de ser el primer token al colar el modelo",
              cmd_c.strip() and not shlex.split(cmd_c)[0].startswith("--"), cmd_c)
    comprueba("sin modelo, la reapertura de Claude mete un flag igualmente",
              "--model" not in cd(r_claude)[0], cd(r_claude)[0])

    cmd_x = cd(r_codex, modelo="gpt-5")[0]
    comprueba("la reapertura de Codex no lleva -m con el modelo",
              "-m gpt-5" in cmd_x, cmd_x)

    cmd_l = cd(r_live, modelo="opus")[0]
    comprueba("a una sesion viva (tmux attach) se le cuela un modelo",
              "opus" not in cmd_l and "--model" not in cmd_l, cmd_l)

    cmd_g = cd(r_gem, modelo="pro")[0]
    comprueba("a gemini reabierto se le cuela un modelo que no sabemos pedirle",
              "pro" not in cmd_g and "-m" not in shlex.split(cmd_g), cmd_g)

    comprueba("el relevo a Claude no lleva --model",
              "--model sonnet" in ar["claude"]("brief", "sonnet"))
    comprueba("el relevo a Codex no lleva -m",
              "-m sonnet" in ar["codex"]("brief", "sonnet"))
    comprueba("al relevo a Gemini se le cuela un modelo",
              "sonnet" not in ar["gemini"]("brief", "sonnet"))
    comprueba("sin modelo el relevo a Claude mete un flag",
              "--model" not in ar["claude"]("brief"))

    # ── el contrato de la tecla que CIERRA: la unica accion irreversible ─────
    # No es un cuadro de texto, pero es la misma clase de decision que estos cuadros
    # y hasta ahora vivia inline, sin test ni mutante: una tecla de mas o de menos en
    # el set cambia en silencio que se cierra o que no.
    ac = ns["acepta_cierre"]
    for t in ("s", "S", "y", "Y"):
        comprueba("'%s' deberia confirmar el cierre" % t, ac(ord(t)))
    for t in ("n", "N", "q", "x", " "):
        comprueba("'%s' NO deberia cerrar sesiones" % t, not ac(ord(t)))
    comprueba("el -1 de 'sin tecla' (timeout) no debe cerrar", not ac(-1))

    # ── la geometria del cuadro de cerrar: dos filas ancladas al fondo ───────
    # El cuadro no es un composer puro —el "OJO" y el "[y]" se pintan en `alto - 3` y
    # `alto - 2`—, asi que lo que se prueba es la aritmetica, como con `caja_now`. En
    # una terminal de menos de tres filas esos indices eran negativos, `addnstr`
    # lanzaba `curses.error` y el wrapper lo tragaba: el selector desaparecia sin
    # decir nada al pulsar `x`.
    cc = ns["caja_cierre"]
    for h in (1, 2, 3, 4, 5, 6, 8, 11, 24):
        for w in (10, 20, 30, 80, 200):
            for n in (0, 1, 3, 5, 9):
                alto, ancho, y, x, caben, f_ojo, f_pie = cc(h, w, n)
                donde = "h=%d w=%d n=%d" % (h, w, n)
                comprueba(donde + ": el cuadro se sale por abajo", alto <= h and y + alto <= h)
                comprueba(donde + ": el cuadro se sale por la derecha",
                          ancho <= w and x + ancho <= w)
                # Las sesiones se listan desde la fila 2; la ultima no pisa el borde.
                comprueba(donde + ": caben mas filas de las marcadas o de las que caben",
                          caben <= min(n, 5) and (not caben or 1 + caben <= alto - 2))
                if alto < 2:
                    continue        # quien llama no pinta: no hay filas que sujetar
                comprueba(donde + ": el 'OJO' cae fuera del cuadro (%d)" % f_ojo,
                          1 <= f_ojo <= alto - 1)
                comprueba(donde + ": el '[y]' cae fuera del cuadro (%d)" % f_pie,
                          1 <= f_pie <= alto - 1)
                comprueba(donde + ": el '[y]' queda por encima del 'OJO'", f_ojo <= f_pie)
    # Control: a la altura de siempre la geometria es la de antes del arreglo, o el
    # clamp estaria cambiando lo que se ve en vez de solo evitar el reventon.
    comprueba("a 24 filas el cuadro de 5 sesiones ya no mide 11 y ancla igual",
              cc(24, 80, 5) == (11, 74, 6, 3, 5, 8, 9))
    comprueba("con una sola fila no hay cuadro y el alto lo dice",
              cc(1, 80, 3)[0] < 2)

    for f in fallos:
        print("FALLO:", f)
    print("ok" if not fallos else "%d fallos" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
