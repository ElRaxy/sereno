#!/usr/bin/env python3
"""Abrir varias por tmux, llamando a tmux DE VERDAD. Es la unica via fuera de macOS.

`test_lanzadores.py` prueba la tabla y el guion, pero nunca llega a tmux: le pasa un
`lambda: True` o le cambia `subprocess` por un doble. Asi que lo que estaba cubierto era
la decision de a quien llamar, no que la llamada abriera nada. En Linux eso deja el
camino entero sin comprobar, porque alli warp y Terminal.app no existen y tmux es lo
unico que queda: medio README prometia una portabilidad que nadie habia visto correr.

Aqui se levanta un servidor tmux propio, se abren tres pestanas y se mira que pasó:

  · que en esta maquina la tabla elige lo que toca, y en Linux eso es tmux y solo tmux;
  · que aparecen tres ventanas y no una, con los nombres pedidos;
  · que la orden de cada una LLEGA A CORRER —deja su huella en disco— y corre en el
    directorio que se pidio, que es lo que el `-c` y el `cd` del guion tienen que
    conseguir. Una ventana abierta en `~` con la orden dentro se ve igual de bien en una
    captura y es el bug que el guion existe para no tener;
  · que el guion se borra a si mismo antes del `exec`, y aun asi lo de detras se ejecuta.

**El servidor va en un socket aparte** (`-L sereno-tests`). Sin eso, correr la bateria en
la maquina de alguien que trabaja dentro de tmux —que es justo para quien se escribio
este programa— le abriria tres ventanas en mitad de sus sesiones de verdad.

Si no hay tmux, esto FALLA en vez de saltarse: un test que se calla cuando falta su
dependencia no protege nada, solo lo parece. El CI lo instala antes de la bateria.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SOCK = "sereno-tests"


def tmux(*args, **kw):
    return subprocess.run(["tmux", "-L", SOCK, *args],
                          capture_output=True, text=True, **kw)


def hechos(tmp):
    """Lo observado, en tipos cerrados. El veredicto lo compone `main`."""
    guion = pathlib.Path(tmp)/"run"
    marcas = pathlib.Path(tmp)/"marcas"; marcas.mkdir()
    dirs = []
    for i in range(3):
        d = pathlib.Path(tmp)/f"proy{i}"; d.mkdir(); dirs.append(str(d))

    dentro = RAIZ/"tests"/"_dentro_de_tmux.py"
    dentro.write_text(PROGRAMA % (json.dumps(str(RAIZ)), json.dumps(str(guion)),
                                  json.dumps(str(marcas)), json.dumps(dirs),
                                  json.dumps(str(pathlib.Path(tmp)/"hechos.json"))),
                      encoding="utf-8")
    try:
        tmux("new-session", "-d", "-s", "p",
             f"{sys.executable} {dentro} > {tmp}/salida.txt 2>&1; sleep 30")
        fin = time.time() + 60
        salida = pathlib.Path(tmp)/"hechos.json"
        while time.time() < fin and not salida.exists():
            time.sleep(0.5)
        if not salida.exists():
            return {"error": (pathlib.Path(tmp)/"salida.txt").read_text()
                    if (pathlib.Path(tmp)/"salida.txt").exists() else "sin salida"}
        return json.loads(salida.read_text())
    finally:
        dentro.unlink(missing_ok=True)
        tmux("kill-server")


# Corre DENTRO de tmux: `$TMUX` lo pone el servidor, y `hay_tmux_alrededor()` lo exige.
PROGRAMA = '''import json, os, pathlib, subprocess, sys, time
RAIZ, GUION, MARCAS, DIRS, SALIDA = pathlib.Path(%s), %s, %s, %s, %s
os.environ["SERENO_LANG"] = "en"
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ/"sereno").read_text(encoding="utf-8"), "sereno", "exec"), ns)
ns["RUN"] = pathlib.Path(GUION)
h = {"plataforma": sys.platform,
     "dentro_de_tmux": bool(os.environ.get("TMUX")),
     "hay_tmux_alrededor": bool(ns["hay_tmux_alrededor"]()),
     "lanzadores": ns["lanzadores_disponibles"](),
     "lanzador_elegido": ns["lanzador_disponible"]()}
pestanas = [("sesion-%%d" %% i,
             "sh -c 'pwd > %%s/m%%d.txt; sleep 30'" %% (MARCAS, i), DIRS[i])
            for i in range(3)]
antes = len([x for x in subprocess.run(["tmux","list-windows","-F","#{window_name}"],
            capture_output=True, text=True).stdout.split() if x])
h["devuelve"] = ns["_abre_en_tmux"](pestanas)
time.sleep(3)
nombres = [x for x in subprocess.run(["tmux","list-windows","-F","#{window_name}"],
           capture_output=True, text=True).stdout.split() if x]
h["ventanas_nuevas"] = len(nombres) - antes
h["nombres_pedidos_presentes"] = sorted(n for n in nombres if n.startswith("sesion-"))
h["cwd_observado"] = {}
for i in range(3):
    p = pathlib.Path(MARCAS)/("m%%d.txt" %% i)
    h["cwd_observado"]["m%%d" %% i] = p.read_text().strip() if p.exists() else None
h["cwd_pedido"] = {"m%%d" %% i: DIRS[i] for i in range(3)}
# El directorio de la VENTANA, que es lo unico que prueba el `-c`: la orden acabaria en
# el sitio correcto igual, porque el guion hace su propio `cd`. Sin esto las dos vias se
# tapan entre si y quitar cualquiera de las dos pasa en verde.
h["cwd_de_la_ventana"] = {}
# Sin escapes en esta plantilla a proposito: un `\\t` aqui se convierte en tabulador
# real al componer el programa, y el `\\n` en un salto que parte la linea en dos.
sep = chr(9)
fmt = "#{window_name}" + sep + "#{pane_current_path}"
for linea in subprocess.run(["tmux","list-windows","-F",fmt],
                            capture_output=True, text=True).stdout.splitlines():
    if sep in linea and linea.split(sep)[0].startswith("sesion-"):
        nom, ruta = linea.split(sep, 1)
        h["cwd_de_la_ventana"][nom] = ruta
h["guiones_que_quedan"] = len(list(pathlib.Path(GUION).glob("lanza-*.sh"))) \\
    if pathlib.Path(GUION).is_dir() else None
pathlib.Path(SALIDA).write_text(json.dumps(h))
'''


def sin_servidor(tmp):
    """Cuantas dice haber abierto cuando no hay ningun tmux al que pedirselo.

    Tiene que ser CERO: la funcion devuelve hechos —cuantas salieron— y no la cuenta de
    veces que lo intento, que es lo que quien llama usa para componer el mensaje. Se
    aisla con `TMUX_TMPDIR` a un directorio vacio y sin `$TMUX`: apuntar al servidor de
    verdad le abriria tres ventanas en las sesiones de quien corre la bateria.
    """
    vacio = pathlib.Path(tmp)/"sin-servidor"; vacio.mkdir()
    prog = ("import os,pathlib,sys\n"
            "ns={'__name__':'sereno_test'}\n"
            "exec(compile(pathlib.Path(%r).read_text(encoding='utf-8'),'sereno','exec'),ns)\n"
            "ns['RUN']=pathlib.Path(%r)\n"
            "print(ns['_abre_en_tmux']([('a','sh -c true',%r)]*3))\n"
            % (str(RAIZ/"sereno"), str(pathlib.Path(tmp)/"run2"), tmp))
    entorno = dict(os.environ, TMUX_TMPDIR=str(vacio))
    entorno.pop("TMUX", None)
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                       env=entorno, timeout=60)
    try:
        return int(r.stdout.strip().split()[-1])
    except (ValueError, IndexError):
        return None


def main():
    if not shutil.which("tmux"):
        print("FALLO: no hay tmux. Este test lo NECESITA — si se saltara, el unico")
        print("       camino que Linux tiene para abrir varias se quedaria sin red.")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        h = hechos(tmp)
        h["devuelve_sin_servidor"] = sin_servidor(tmp)
    fallos = []
    if "error" in h:
        print("FALLO: el programa de dentro no llego a escribir sus hechos:")
        print(h["error"][:2000])
        return 1

    if not h["dentro_de_tmux"] or not h["hay_tmux_alrededor"]:
        fallos.append("no se estaba dentro de tmux, asi que no se probo nada")
    # En Linux warp y Terminal.app no existen: si aparece alguno, la tabla miente.
    if h["plataforma"].startswith("linux") and h["lanzadores"] != ["tmux"]:
        fallos.append(f"en Linux los lanzadores son {h['lanzadores']}, esperaba solo tmux")
    if "tmux" not in h["lanzadores"]:
        fallos.append("tmux no aparece como disponible estando dentro de tmux")
    if h["devuelve"] != 3:
        fallos.append(f"dice haber abierto {h['devuelve']} de 3")
    if h["ventanas_nuevas"] != 3:
        fallos.append(f"{h['ventanas_nuevas']} ventanas nuevas de 3")
    if h["nombres_pedidos_presentes"] != ["sesion-0", "sesion-1", "sesion-2"]:
        fallos.append(f"los nombres son {h['nombres_pedidos_presentes']}")
    for k, pedido in h["cwd_pedido"].items():
        visto = h["cwd_observado"].get(k)
        if visto is None:
            fallos.append(f"{k}: la orden no llego a ejecutarse")
        elif visto != pedido:
            fallos.append(f"{k}: se ejecuto en {visto} y se pidio {pedido}")
    for nom, pedido in zip(("sesion-0","sesion-1","sesion-2"),
                           (h["cwd_pedido"]["m0"], h["cwd_pedido"]["m1"],
                            h["cwd_pedido"]["m2"])):
        visto = h.get("cwd_de_la_ventana", {}).get(nom)
        # Por `realpath`: en macOS el temporal vive bajo `/var`, que es un enlace a
        # `/private/var`, y tmux devuelve la resuelta. Comparar las cadenas a pelo
        # marcaria en rojo un directorio que es exactamente el que se pidio.
        #
        # Alcance medido, para que nadie lo lea como mas de lo que es: esto comprueba
        # que la ventana ACABA en el sitio pedido, no CUAL de las dos vias lo consigue.
        # El `-c cwd` de `new-window` y el `cd` del guion hacen lo mismo, y quitar
        # cualquiera de los dos deja la otra corrigiendo: el mutante que borra el `-c`
        # sobrevive a este test, y no por un hueco sino porque desde fuera no hay
        # diferencia observable. El `cd` si tiene red propia en `test_lanzadores.py`,
        # que ejecuta el guion suelto.
        if visto is None or os.path.realpath(visto) != os.path.realpath(pedido):
            fallos.append(f"la ventana {nom} quedo en {visto} y se pidio {pedido}")
    if h["devuelve_sin_servidor"] != 0:
        fallos.append(f"sin ningun tmux dice haber abierto {h['devuelve_sin_servidor']}")
    if h["guiones_que_quedan"]:
        fallos.append(f"{h['guiones_que_quedan']} guion(es) sin borrar")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: tmux abre las 3 ventanas de verdad en {h['plataforma']}, cada una en su "
          f"sitio y sin dejar guiones" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
