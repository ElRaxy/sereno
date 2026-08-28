#!/usr/bin/env python3
"""Una huerfana que no se abre NO se archiva. Si se archiva, se pierde.

Las huerfanas son las sesiones que sobrevivieron a cerrar Warp: viven como entradas en el
registro y la lista las ofrece para reanudarlas. Archivar una es decir "esta ya esta
resuelta", y a partir de ahi **no se vuelve a ofrecer**.

El orden estaba al reves:

    path = write_launch_config(elegidas)
    archive(elegidas, "restored")          # <- primero
    subprocess.run(["open", ...])          # <- y luego, sin mirar

Asi que un `open` que fallara —una maquina sin Warp, un Linux donde ese binario ni
existe— dejaba las huerfanas marcadas como restauradas sin haberlas abierto: no se
reanudaban y ademas desaparecian de la lista. No es un mensaje equivocado, es perderlas.

El control positivo es la mitad que hace que esto pruebe algo: cuando SI se abren, se
archivan. Sin el, un `archive` borrado del codigo pasaria el caso de arriba.
"""
import contextlib, io, os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def carga(abre):
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ns["LAUNCH"] = pathlib.Path(tempfile.mkdtemp())
    ns["abre_varias"] = lambda pestanas, config, cual=None: (
        ("warp", len(pestanas)) if abre else (None, 0))
    return ns


def huerfana(tmp, sid):
    f = tmp / f"{sid}.env"
    f.write_text(f"id={sid}\ncwd=/tmp\n")
    return {"id": sid, "cwd": "/tmp", "title": "una", "_file": f,
            "resume_flags__list": []}


def main():
    fallos = []
    for abre, deberia_archivar in ((False, False), (True, True)):
        tmp = pathlib.Path(tempfile.mkdtemp())
        ns = carga(abre)
        ns["ROOT"] = tmp / "registro"
        elegidas = [huerfana(tmp, "aaaa1111"), huerfana(tmp, "bbbb2222")]
        archivadas = []
        real_archive = ns["archive"]
        ns["archive"] = lambda items, folder: (archivadas.extend(items)
                                               or real_archive(items, folder))
        _path, pestanas = ns["write_launch_config"](elegidas)
        cual, hechas = ns["abre_varias"](pestanas, ns["CONFIG_NAME"])
        # Se replica la decision tal cual la toma el programa: archivar SOLO si hechas.
        if hechas:
            ns["archive"](elegidas, "restored")
        if bool(archivadas) != deberia_archivar:
            fallos.append(f"con abre={abre} se archivaron {len(archivadas)}: "
                          f"se esperaba {'archivar' if deberia_archivar else 'NO archivar'}")
        # Y el fichero de la huerfana sigue donde estaba cuando no se abrio: es lo que
        # hace que la lista se la vuelva a ofrecer manana.
        sigue = all(h["_file"].exists() for h in elegidas)
        if abre and sigue:
            fallos.append("abiertas y sin archivar: volverian a ofrecerse ya reanudadas")
        if not abre and not sigue:
            fallos.append("sin abrir, el fichero de la huerfana ya no esta: perdida")

    # Y la fuente no puede volver al orden de antes. Esto mira el CODIGO porque el caso
    # de arriba replica la decision: si alguien la invierte en el programa, el test
    # seguiria verde sin esto.
    fuente = (RAIZ / "sereno").read_text()
    for trozo, que in (
        ('archive(elegidas, "restored")\n                    aviso = _("{n} resumed with',
         "el selector de huerfanas archiva dentro del `if hechas`"),
        ('    archive(resumable + skipped, "restored")\n    print("\\n" + _("Opening {n} tabs with',
         "la ruta de linea de comandos archiva despues de abrir"),
    ):
        if trozo not in fuente:
            fallos.append(f"cambio el orden: ya no se cumple que {que}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_huerfanas_no_se_archivan_sin_abrir" if not fallos
          else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
