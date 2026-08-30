#!/usr/bin/env python3
"""Una sesion cerrada no vuelve a la lista a los pocos segundos, y encima como viva.

El bug, tal cual lo conto Alex: marcas varias, las cierras, se cierran — y a los segundos
reaparecen como activas.

La lista se compone de dos fuentes: lo que tmux ensena y un barrido de
`~/.claude/projects` con lo que tmux NO ensena. Lo segundo excluye lo primero. Asi que
matar una sesion la sacaba de tmux, con lo que dejaba de estar excluida, y **volvia a
entrar desde el disco**: su transcript se habia tocado hace segundos, o sea `idle` casi
cero, o sea pintada como viva. Ademas con el uuid por nombre en vez del suyo, con lo que
ni parecia la misma fila.

Lo que se vigila:

  1. tras cerrar, no vuelve — ni por el mismo proceso ni por uno nuevo (se apunta en
     disco, porque el susto se repite al reabrir el selector);
  2. **control positivo**: una sesion que NO se cerro y que tmux no ve sigue saliendo del
     disco. Sin esto, romper el barrido entero pasaria el caso 1;
  3. el apunte caduca: pasados `VIVA` segundos ya no filtra a nadie — el propio mtime la
     tira, y un apunte eterno esconderia una sesion que de verdad revivio.
"""
import json, os, pathlib, sys, tempfile, time, uuid

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def monta():
    """Un mundo de mentira: su carpeta de transcripts, su registro y su tmux."""
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "proyectos" / "-demo").mkdir(parents=True)
    ns["PROJECTS"] = tmp / "proyectos"
    ns["ROOT"] = tmp / "reg"
    ns["LIVE"] = ns["ROOT"] / "live"
    ns["LIVE"].mkdir(parents=True)
    ns["CERRADAS"] = ns["ROOT"] / "closed-recientes.txt"
    ns["rss_por_arbol"] = lambda *a, **k: {}
    return ns, tmp


def transcript(ns, tmp, sid):
    p = ns["PROJECTS"] / "-demo" / f"{sid}.jsonl"
    p.write_text(json.dumps({"type": "user", "cwd": "/tmp",
                             "message": {"role": "user", "content": "hola"},
                             "timestamp": "2026-08-28T20:00:00Z"}) + "\n")
    return p


def main():
    fallos = []
    ns, tmp = monta()
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    transcript(ns, tmp, a)
    transcript(ns, tmp, b)          # esta nadie la cierra: es el control positivo
    (ns["LIVE"] / "999-1.env").write_text(
        f"id={a}\ncwd=/home/u/proyecto\npid=999\ntmux_session=cc-demo-1\n")
    viva = [("cc-demo-1", int(time.time()) - 60, False, "una sesion", "999")]
    ns["tmux_list"] = lambda *x, **k: viva
    ns["tmux_kill"] = lambda *x, **k: viva.clear()

    antes = ns["live_sessions"]()
    if len(antes) != 2:
        fallos.append(f"de partida deberia haber 2 sesiones, hay {len(antes)}")

    cerrada = [r for r in antes if r["name"] == "cc-demo-1"]
    if not cerrada:
        fallos.append("la sesion de tmux no sale en la lista de partida")
    else:
        ns["stop_rows"](cerrada, forget=True)
        quedan = ns["live_sessions"]()
        nombres = [r["name"] for r in quedan]
        if any(a in n or n == "cc-demo-1" for n in nombres):
            fallos.append(f"la cerrada vuelve a la lista: {nombres}")
        # 2. Control positivo: la otra, que nadie cerro, SIGUE saliendo del disco. Sin
        #    esto, un barrido roto del todo pasaria el caso de arriba.
        if not any(b in n for n in nombres):
            fallos.append("la que no se cerro tampoco sale: el filtro se lleva todo "
                          "por delante y el caso de arriba no prueba nada")

    # 3. Se apunta en DISCO: al reabrir el selector es otro proceso, y el susto se
    #    repetiria. Se comprueba releyendo el programa entero desde cero.
    ns2 = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns2)
    for k in ("PROJECTS", "ROOT", "LIVE", "CERRADAS", "rss_por_arbol"):
        ns2[k] = ns[k]
    ns2["tmux_list"] = lambda *x, **k: []
    nombres2 = [r["name"] for r in ns2["live_sessions"]()]
    if any(a in n for n in nombres2):
        fallos.append(f"en un proceso nuevo la cerrada vuelve: {nombres2}")
    if not any(b in n for n in nombres2):
        fallos.append("en un proceso nuevo no sale la que nadie cerro")

    # 4. Una sesion REANUDADA no se llama como su id: su registro dice `id=X` y su
    #    transcript es `Y.jsonl`. Si solo se apunta el id, el barrido encuentra la Y y
    #    la resucita igual. Sin este caso, quitar el stem del apunte pasaba el test —
    #    medido: arriba id y stem coinciden y no distinguen nada.
    ns3, tmp3 = monta()
    viejo_id, stem_real = str(uuid.uuid4()), str(uuid.uuid4())
    tr = transcript(ns3, tmp3, stem_real)
    ns3["tmux_list"] = lambda *x, **k: []
    ns3["tmux_kill"] = lambda *x, **k: None
    ns3["stop_rows"]([{"name": "cc-reanudada",
                       "meta": {"id": viejo_id, "_transcript": tr}}], forget=False)
    nombres3 = [r["name"] for r in ns3["live_sessions"]()]
    if any(stem_real in n for n in nombres3):
        fallos.append("una sesion reanudada vuelve: se apunto su id pero no el stem "
                      f"de su transcript ({nombres3})")

    # 5. El apunte caduca. Uno viejo no puede seguir escondiendo una sesion: si el
    #    transcript se toca otra vez, es que alguien la revivio y tiene que verse.
    ns["CERRADAS"].write_text("%.0f %s\n" % (time.time() - ns["VIVA"] - 5, b))
    if b not in "".join(ns["cerradas_recientes"]()):
        pass                        # correcto: ya no esta
    else:
        fallos.append("un apunte mas viejo que VIVA sigue filtrando")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_cerrada_no_resucita" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
