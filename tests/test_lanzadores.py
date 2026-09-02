#!/usr/bin/env python3
"""Abrir varias a la vez sin Warp: tmux y Terminal.app, y el guion que va por delante.

Hasta la 1.24.0 "varias a la vez" era Warp o nada, y nada queria decir macOS o nada. Lo
que se prueba aqui es la tabla que lo abre y el guion que la hace posible.

El guion no es un rodeo. `do script` de Terminal.app y `tmux new-window` reciben la orden
como UNA cadena, y el briefing de un relevo lleva saltos de linea y comillas: inline es el
mismo fallo que rompia el YAML de Warp con otro traje. Por eso el guion tiene tres cosas y
las tres se comprueban una por una:

  · `cd` al directorio, y **abortar** si no esta — no seguir en `~`;
  · `unset TMUX`, porque el reenganche es `tmux attach` y dentro de tmux falla con
    "sessions should be nested with care";
  · borrarse antes del `exec`, y que el resto se ejecute igual — `sh` ya tiene el fichero
    abierto, y un fichero borrado sigue siendo legible por su descriptor.

Los dos ultimos se prueban EJECUTANDO un guion de verdad, no leyendolo: que el texto
ponga `rm` no dice que lo que viene detras llegue a correr.
"""
import contextlib, io, os, pathlib, shlex, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def carga(run_dir):
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    os.environ.pop("SERENO_LANZADOR", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ns["RUN"] = run_dir
    return ns


def main():
    fallos = []
    tmp = pathlib.Path(tempfile.mkdtemp())
    ns = carga(tmp / "lanzar")

    # 1. El guion lleva las tres cosas, y con el directorio citado: un `cd` sin comillas
    #    se rompe con el primer proyecto que tenga un espacio en la ruta.
    con_espacio = tmp / "con espacio"
    con_espacio.mkdir()
    ruta = ns["_guion"]("echo hola", str(con_espacio))
    texto = ruta.read_text()
    for aguja, que in ((f"cd '{con_espacio}'", "el cd citado al directorio"),
                       ("|| exit 1", "el abortar si el cd falla"),
                       ("unset TMUX", "el unset TMUX"),
                       ("rm -f -- " + shlex.quote(str(ruta)),
                        "el borrarse a si mismo"),
                       ("exec echo hola", "el exec de la orden")):
        if aguja not in texto:
            fallos.append(f"al guion le falta {que}")
    if oct(ruta.stat().st_mode)[-3:] != "700":
        fallos.append(f"el guion es legible por otros: {oct(ruta.stat().st_mode)}")
    if oct(ruta.parent.stat().st_mode)[-3:] != "700":
        fallos.append("la carpeta de guiones es legible por otros")

    # 2. Ejecutado de verdad: se borra Y el exec de despues corre igual.
    testigo = tmp / "testigo.txt"
    ruta = ns["_guion"](f"sh -c 'echo corrio > {testigo}'", str(tmp))
    subprocess.run(["sh", str(ruta)], capture_output=True, timeout=20)
    if ruta.exists():
        fallos.append("el guion no se borro al correr: el briefing se queda en disco")
    if testigo.read_text().strip() != "corrio" if testigo.exists() else True:
        fallos.append("lo que va DESPUES del rm no se ejecuto: borrarse rompe el guion")

    # 3. El `unset TMUX` llega al proceso hijo. Sin el, `tmux attach` —que es lo que hace
    #    `r`— responde "sessions should be nested with care" y no reengancha nada.
    salida = tmp / "env.txt"
    ruta = ns["_guion"](f"sh -c 'echo \"[${{TMUX}}]\" > {salida}'", str(tmp))
    subprocess.run(["sh", str(ruta)], capture_output=True, timeout=20,
                   env={**os.environ, "TMUX": "/tmp/algo,1,0"})
    if salida.read_text().strip() != "[]":
        fallos.append(f"TMUX sigue puesto en el hijo: {salida.read_text().strip()!r}")

    # 4. Un directorio que ya no existe aborta el guion en vez de seguir en otro sitio.
    fantasma = tmp / "no-existe"
    ruta = ns["_guion"](f"sh -c 'echo NO_DEBERIA > {tmp}/mal.txt'", str(fantasma))
    r = subprocess.run(["sh", str(ruta)], capture_output=True, timeout=20)
    if r.returncode == 0 or (tmp / "mal.txt").exists():
        fallos.append("con el directorio borrado el guion sigue y ejecuta la orden")

    # 5. La tabla: el ORDEN de verdad, el de `LANZADORES`, no el del sustituto de abajo.
    #    Sin esto, invertir tmux y Terminal.app en el programa pasaba el test entero: los
    #    casos de eleccion montan su propia tabla y no verian el cambio.
    if list(ns["LANZADORES"]) != ["warp", "iterm", "kitty", "tmux", "terminal"]:
        fallos.append(f"el orden de LANZADORES cambio: {list(ns['LANZADORES'])} "
                      "(los que abren ventanas de verdad primero —iTerm antes que kitty, "
                      "que gasta un proceso por ventana—; tmux luego, que es el unico "
                      "que va fuera de macOS; Terminal.app ultimo porque macOS restaura "
                      "sus ventanas al reiniciar)")

    # 5b. Todo lanzador de la tabla dice QUE abre. El cuadro tira de `_QUE_ABRE` con
    #      un `.get(n, lambda: n)`, asi que a uno sin texto no le pasa nada: sale con
    #      el nombre pelado y sin explicacion, en la unica pantalla donde hay que
    #      elegir entre varios. Un lanzador nuevo es exactamente cuando se olvida.
    sin_texto = [n for n in ns["LANZADORES"] if n not in ns["_QUE_ABRE"]]
    if sin_texto:
        fallos.append(f"lanzadores sin decir que abren: {sin_texto}")
    sobran = [n for n in ns["_QUE_ABRE"] if n not in ns["LANZADORES"]]
    if sobran:
        fallos.append(f"_QUE_ABRE describe lanzadores que ya no existen: {sobran}")


    # 6. Se elige el primero disponible, y `SERENO_LANZADOR` fuerza.
    ns["hay_warp"] = lambda: False
    ns["hay_tmux_alrededor"] = lambda: True
    ns["hay_terminal_app"] = lambda: True
    ns["LANZADORES"] = {"warp": (lambda: False, None),
                        "tmux": (lambda: True, ns["_abre_en_tmux"]),
                        "terminal": (lambda: True, ns["_abre_en_terminal"])}
    if ns["lanzador_disponible"]() != "tmux":
        fallos.append("con Warp fuera no se cae a tmux, que va antes que Terminal.app")
    os.environ["SERENO_LANZADOR"] = "terminal"
    if ns["lanzador_disponible"]() != "terminal":
        fallos.append("SERENO_LANZADOR no fuerza el lanzador")
    os.environ["SERENO_LANZADOR"] = "no-existe-este"
    if ns["lanzador_disponible"]() != "tmux":
        fallos.append("un SERENO_LANZADOR inventado no cae al orden normal")
    os.environ.pop("SERENO_LANZADOR")
    ns["LANZADORES"] = {k: (lambda: False, v[1]) for k, v in ns["LANZADORES"].items()}
    if ns["lanzador_disponible"]() is not None:
        fallos.append("sin ninguno disponible sigue eligiendo uno")

    # 6b. Dentro de tmux, `tmux` pasa al frente: es el unico que abre "donde ya estas"
    #     —una pestana mas en la ventana viva— mientras que Warp abre SIEMPRE una ventana
    #     nueva. Asi el relevo y el reabrir caen por defecto en el mismo Warp del que sales.
    #     Fuera de tmux, el orden de siempre; y `SERENO_LANZADOR` manda incluso dentro.
    nst = carga(tmp / "lanzar_tmux")
    nst["LANZADORES"] = {k: (lambda: True, v[1]) for k, v in nst["LANZADORES"].items()}
    nst["hay_tmux_alrededor"] = lambda: True
    en_tmux = nst["lanzadores_disponibles"]()
    if not en_tmux or en_tmux[0] != "tmux":
        fallos.append(f"dentro de tmux el relevo no abre por defecto donde ya estas: "
                      f"{en_tmux}")
    nst["hay_tmux_alrededor"] = lambda: False
    fuera = nst["lanzadores_disponibles"]()
    if fuera != ["warp", "iterm", "kitty", "tmux", "terminal"]:
        fallos.append(f"fuera de tmux el orden de siempre cambio (tmux no debe colarse "
                      f"al frente): {fuera}")
    nst["hay_tmux_alrededor"] = lambda: True
    os.environ["SERENO_LANZADOR"] = "terminal"
    forzado_en_tmux = nst["lanzadores_disponibles"]()
    os.environ.pop("SERENO_LANZADOR")
    if forzado_en_tmux != ["terminal"]:
        fallos.append(f"SERENO_LANZADOR no manda dentro de tmux: {forzado_en_tmux}")

    # 6c. Auto-tmux (opt-in): el SELECTOR se re-lanza dentro de tmux para que el relevo
    #     caiga en la misma ventana. Solo con SERENO_TMUX_AUTO, fuera de tmux, en un tty y
    #     con tmux instalado; nunca en los modos que imprimen y salen. Se prueba la
    #     DECISION (`_plan_tmux`), no el `execvp`, que se llevaria el proceso del test.
    npt = carga(tmp / "lanzar_plan")
    which0 = npt["shutil"].which
    npt["shutil"].which = lambda n: "/usr/bin/" + str(n)      # tmux "instalado"
    os.environ.pop("TMUX", None)
    os.environ.pop("SERENO_TMUX_AUTO", None)
    try:
        if npt["_plan_tmux"]([], True) is not None:
            fallos.append("sin SERENO_TMUX_AUTO el selector se mete en tmux igual")
        os.environ["SERENO_TMUX_AUTO"] = "1"
        if npt["_plan_tmux"]([], False) is not None:
            fallos.append("fuera de un tty se mete en tmux (romperia --json y los hooks)")
        plan = npt["_plan_tmux"]([], True)
        if (not plan or plan[0] != npt["TMUX_BIN"] or "new-session" not in plan
                or plan[1] != "-L" or plan[2] != npt["SOCK"]):
            fallos.append(f"con SERENO_TMUX_AUTO y tty no re-lanza en tmux (mismo socket): "
                          f"{plan}")
        if npt["_plan_tmux"](["--json"], True) is not None:
            fallos.append("un modo que imprime y sale (--json) se mete en tmux")
        os.environ["TMUX"] = "/tmp/fake,1,0"
        if npt["_plan_tmux"]([], True) is not None:
            fallos.append("ya dentro de tmux se vuelve a envolver: bucle de re-lanzado")
    finally:
        npt["shutil"].which = which0
        os.environ.pop("TMUX", None)
        os.environ.pop("SERENO_TMUX_AUTO", None)

    # 7. Y ninguno revienta si su binario no esta: es el fallo de la 1.24.0 volviendo por
    #    la puerta de al lado. Cuentan 0 abiertas, que es la verdad.
    ns2 = carga(tmp / "lanzar2")
    class SinBinario:
        @staticmethod
        def run(*a, **k):
            raise FileNotFoundError(2, "No such file or directory")
    ns2["subprocess"] = SinBinario
    pest = [("t", "echo x", str(tmp))]
    for nombre in ("_abre_en_tmux", "_abre_en_terminal", "_abre_en_iterm",
                   "_abre_en_kitty"):
        try:
            n = ns2[nombre](pest)
        except Exception as e:
            fallos.append(f"{nombre} revienta sin su binario: {type(e).__name__}: {e}")
            continue
        if n != 0:
            fallos.append(f"{nombre} dice haber abierto {n} sin binario")

    # 7b. Lo que se le pide EXACTAMENTE a iTerm2 y a kitty, que no es cosmetica: las dos
    #     formas se eligieron midiendo, y una tabla de argumentos que se toque sin volver
    #     a medir rompe el lanzador sin que nada se queje.
    #
    #     kitty lleva `-n` y **no** `-1`: con `--single-instance` la segunda llamada y la
    #     tercera se las traga la instancia ya viva, y `open` devuelve **0 en las tres**
    #     abriendo una sola ventana (medido 2026-08-31, kitty 0.48.2). Contar ese 0 como
    #     exito es justo el fallo que `abre_varias` existe para no tener.
    #
    #     Y va por `open`, no por `kitty` a secas: lanzado directo se queda en primer
    #     plano hasta que su orden termina, y `subprocess.run` colgaria el selector
    #     entero mientras hubiera una sesion abierta.
    ns3 = carga(tmp / "lanzar3")
    vistas = []
    class Apunta:
        @staticmethod
        def run(argv, *a, **k):
            vistas.append(argv)
            class R: returncode = 0
            return R()
    ns3["subprocess"] = Apunta
    ns3["_abre_en_kitty"]([("t", "echo x", str(tmp))])
    argv = vistas[-1] if vistas else []
    if argv[:4] != ["open", "-na", "kitty.app", "--args"]:
        fallos.append(f"kitty no se lanza por `open -na kitty.app --args`: {argv[:4]}")
    if "-1" in argv or "--single-instance" in argv:
        fallos.append("kitty lleva --single-instance: la 2a y la 3a ventana no se abren "
                      "y `open` devuelve 0 igual")
    if "-d" not in argv or argv[argv.index("-d") + 1] != str(tmp):
        fallos.append("kitty no recibe el directorio de la sesion en `-d`")
    if "-T" not in argv:
        fallos.append("kitty no recibe el titulo en `-T`")

    vistas.clear()
    ns3["_abre_en_iterm"]([("t", "echo x", str(tmp))])
    argv = vistas[-1] if vistas else []
    guion = " ".join(argv)
    if argv[:2] != ["osascript", "-e"]:
        fallos.append(f"iTerm2 no se pide por osascript: {argv[:2]}")
    if "create window with default profile command" not in guion:
        fallos.append("iTerm2 no recibe `create window with default profile command`; "
                      "`do script` es de Terminal.app y iTerm2 no lo entiende")
    if "do script" in guion:
        fallos.append("a iTerm2 se le manda `do script`, que es la orden de Terminal.app")

    # 7bis. iTerm2 y kitty son de macOS y aqui se declaran de macOS. El guard parece de
    #       adorno —en un Linux normal no hay `/Applications`— pero `~/Applications` es
    #       una carpeta que cualquiera puede crear, y un lanzador que se ofrece donde no
    #       puede abrir nada deja al usuario con "0 de 3 abiertas" y sin explicacion.
    #       Se falsean las DOS cosas: la plataforma y la existencia de las carpetas. Con
    #       solo la plataforma, el caso pasaba en verde en una maquina sin iTerm2 ni
    #       kitty —el CI, sin ir mas lejos— porque el `is_dir()` ya devolvia False por su
    #       cuenta: el test aprobaba el guard sin haberlo ejercitado, y solo cazaba el
    #       fallo en la maquina donde ambas apps estaban instaladas.
    home_de_verdad = ns3["HOME"]

    class SiempreEsta:
        def __truediv__(self, otro):
            return self
        def is_dir(self):
            return True
    class TodoExiste:
        Path = staticmethod(lambda *a, **k: SiempreEsta())
    class OtroSistema:
        platform = "linux"
        def __getattr__(self, k):
            return getattr(sys, k)
    ns3["sys"], ns3["pathlib"], ns3["HOME"] = OtroSistema(), TodoExiste(), SiempreEsta()
    for nombre in ("hay_iterm", "hay_kitty", "hay_terminal_app", "hay_warp"):
        if ns3[nombre]():
            fallos.append(f"{nombre} dice que si fuera de macOS, con la carpeta ahi")
    # Y con la plataforma de verdad: si las carpetas estan, los de macOS dicen que si.
    # Sin este contraste el caso de arriba lo aprobaria tambien un `return False` pelado.
    ns3["sys"] = sys
    if sys.platform == "darwin":
        for nombre in ("hay_iterm", "hay_kitty", "hay_terminal_app", "hay_warp"):
            if not ns3[nombre]():
                fallos.append(f"{nombre} dice que no con su carpeta delante")
    ns3["pathlib"], ns3["HOME"] = pathlib, home_de_verdad

    # 7c. Y ninguno de los dos cuenta como abierta una ventana que el sistema rechazo:
    #     `open` con una app que no esta y `osascript` con una app que no existe salen
    #     los dos con rc distinto de 0 (medido), asi que el contador puede fiarse de el.
    class Rechaza:
        @staticmethod
        def run(*a, **k):
            class R: returncode = 1
            return R()
    ns3["subprocess"] = Rechaza
    for nombre in ("_abre_en_iterm", "_abre_en_kitty"):
        n_ab = ns3[nombre]([("t", "echo x", str(tmp))] * 3)
        if n_ab != 0:
            fallos.append(f"{nombre} dice haber abierto {n_ab} con el sistema diciendo que no")

    # 8. El eslabon de en medio: `abre_varias` PROPAGA lo que cuenta el abridor, no el
    #    numero de pestanas que le pidieron. Es la pieza entera de la 1.24.0 —que la
    #    pantalla no mienta— y sustituirla por `len(pestanas)`, o sea el bug de antes,
    #    pasaba los 44 tests: el caso 7 mide el abridor y el 6 la eleccion, pero nadie
    #    miraba que el 0 llegara hasta arriba.
    ns3 = carga(tmp / "lanzar3")
    tres = [("a", "echo 1", str(tmp)), ("b", "echo 2", str(tmp)), ("c", "echo 3", str(tmp))]
    for cuantas, espera in ((0, 0), (2, 2), (3, 3)):
        ns3["LANZADORES"] = {"tmux": (lambda: True, lambda pest, n=cuantas: n)}
        cual, hechas = ns3["abre_varias"](tres, "cfg")
        if (cual, hechas) != ("tmux", espera):
            fallos.append(f"el abridor cuenta {cuantas} y abre_varias dice "
                          f"{(cual, hechas)}: se esperaba ('tmux', {espera})")
    # Y el 0 llega hasta la pantalla: `reopen` sale con 1 y NO anuncia haber abierto nada.
    ns3["LANZADORES"] = {"tmux": (lambda: True, lambda pest: 0)}
    ns3["_escribe_config"] = lambda nombre, pestanas: "/tmp/cfg.yaml"
    ns3["pestanas_de"] = lambda sel: (tres, [])
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = ns3["reopen"]([{"id": "x"}])
    dicho = salida.getvalue()
    if codigo != 1:
        fallos.append(f"sin abrir ninguna, reopen sale con {codigo}: se esperaba 1")
    if "3" in dicho or "tabs with" in dicho or "pestanas con" in dicho:
        fallos.append(f"sin abrir ninguna, reopen anuncia haberlas abierto: {dicho!r}")

    # 9. Y el ultimo binario que se llamaba a pelo: `tmux_kill`. Llevaba `check=False`,
    #    que ignora el codigo de salida pero NO protege de que el binario no exista —eso
    #    es un FileNotFoundError, y dentro de curses se lleva el programa sin dejar
    #    rastro. Hoy no es alcanzable (sin tmux no hay filas que matar), pero eso es una
    #    invariante de otro sitio, no una proteccion suya.
    ns4 = carga(tmp / "lanzar4")
    ns4["subprocess"] = SinBinario
    for arg in (None, "una-sesion"):
        try:
            ns4["tmux_kill"](arg) if arg else ns4["tmux_kill"]()
        except Exception as e:
            fallos.append(f"tmux_kill({arg!r}) revienta sin su binario: "
                          f"{type(e).__name__}: {e}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_lanzadores" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
