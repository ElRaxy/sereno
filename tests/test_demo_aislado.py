#!/usr/bin/env python3
"""El modo demo no puede devolver ni una fila que venga del disco de verdad.

Esto no es celo: la primera grabacion del GIF salio con nombres de clientes dentro.
`main()` arrancaba con filas falsas, pero pulsar TAB llamaba a `sesiones_externas()`,
que leia el disco. Una guarda en la entrada no protege lo que se carga despues, asi
que el test recorre TODAS las funciones que leen datos reales.
"""
import os, pathlib, sys, tempfile, json, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CANARIO = "CANARIO-CLIENTE-CONFIDENCIAL"


def carga(home):
    os.environ["HOME"] = str(home)
    os.environ["SERENO_DEMO"] = "1"
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    return ns


def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    # Un transcript que parece de verdad, con un canario dentro. Si alguna funcion
    # lee disco en modo demo, el canario aparece.
    proj = tmp / ".claude/projects/-home-someone-secret"
    proj.mkdir(parents=True)
    t = proj / "11111111-2222-3333-4444-555555555555.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in (
        {"type": "user", "cwd": "/home/someone/secret",
         "message": {"content": f"{CANARIO} deploy the thing"}},
        {"type": "assistant", "aiTitle": CANARIO,
         "message": {"content": [{"type": "text", "text": CANARIO}]}},
    )) + "\n")
    os.utime(t, (time.time(), time.time()))

    ns = carga(tmp)
    fallos = []
    for nombre in ("live_sessions", "orphans", "sesiones_externas",
                   "sesiones_de_disco", "sesiones_demo"):
        filas = ns[nombre]() or []
        for f in filas:
            if not isinstance(f, dict):
                continue
            if not f.get("_demo"):
                fallos.append(f"{nombre}: fila sin marca _demo -> {f.get('title_full')!r}")
            if CANARIO in json.dumps(f, default=str):
                fallos.append(f"{nombre}: el canario se ha colado")

    # `buscar()` lee transcripts a proposito, asi que en demo tiene que devolver vacio:
    # es la funcion que mas facil se olvida al anadir una guarda, porque no pinta filas.
    if ns["buscar"](CANARIO, todo=True):
        fallos.append("buscar: en modo demo ha leido transcripts de verdad")

    # y la salida que se graba en el GIF tampoco puede traerlo
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["print_live"](ns["sesiones_demo"]())
    if CANARIO in buf.getvalue():
        fallos.append("print_live: el canario se ha colado")
    if not buf.getvalue().strip():
        fallos.append("print_live: no ha pintado nada en modo demo")

    for f in fallos:
        print("FALLO:", f)
    print("ok: ninguna funcion devuelve datos reales en modo demo" if not fallos
          else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
