#!/usr/bin/env python3
"""`--dismiss` descarta las entradas muertas AUNQUE haya sesiones vivas.

El flag existe, esta en `--help` y hasta la 1.30.2 no hacia nada en la maquina de nadie:
vivia despues de la bifurcacion de `main()`, asi que con una sola sesion abierta —o sea,
siempre— el programa imprimia la lista de las vivas y salia con **0 sin descartar nada**.
Un flag que no existe se dice (`test_flags.py`); este existia y se tragaba en silencio,
que es peor.

Se prueba llamando a `main()` de verdad, no a `orphans()`: lo que fallaba no era la
funcion, era el sitio donde estaba escrita. Un caso sobre la funcion habria pasado en
verde todo el tiempo que el fallo estuvo vivo.
"""
import os, pathlib, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def entrada(live, pid, sid):
    f = live / f"{pid}-1700000000.env"
    f.write_text(f"id={sid}\ncwd=/home/u/proyecto\npid={pid}\nstarted=hoy\ntitle=una\n")
    return f


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        registro = casa / ".claude/warp-sessions"
        live = registro / "live"
        live.mkdir(parents=True)
        # Una con el proceso muerto (un pid imposible) y otra con uno VIVO de verdad.
        # No vale el pid de este test: `alive()` exige ademas que la linea de comando
        # mencione "claude" —para no dar por viva una entrada cuyo pid se reciclo— y un
        # `python3 tests/...` no la menciona. Asi que se lanza un proceso cuyo comando si
        # la lleva, que es la unica forma de ejercitar la guarda de verdad en vez de
        # esquivarla parcheando `alive`.
        muerta = entrada(live, "999999", "aaaa1111-0000-0000-0000-000000000000")
        guion = casa / "claude-de-mentira.sh"
        guion.write_text("#!/bin/sh\nsleep 30\n")
        guion.chmod(0o700)
        proceso = subprocess.Popen(["/bin/sh", str(guion)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        viva = entrada(live, str(proceso.pid), "bbbb2222-0000-0000-0000-000000000000")

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_REGISTRY"] = str(registro)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

        # Hay sesiones vivas: es la rama que se comia el flag. Sin esto el test pasaria
        # por la ruta de las huerfanas, que es justo la que nunca fallo.
        fila = {"name": "cc-x", "title": "una", "title_full": "una", "working": False,
                "attached": True, "idle": 10, "pulso": {}, "proyecto": "p",
                "created": 0, "mem_mb": None, "fuente": "claude"}
        ns["live_sessions"] = lambda **kw: [fila]

        class _Sys:
            argv = ["sereno", "--dismiss"]
            stdin = type("S", (), {"isatty": staticmethod(lambda: True)})()

            def __getattr__(self, n):
                return getattr(sys, n)

        ns["sys"] = _Sys()
        codigo = ns["main"]()

        if codigo != 0:
            fallos.append(f"--dismiss sale con {codigo}, se esperaba 0")
        if muerta.exists():
            fallos.append("con sesiones vivas, --dismiss NO descarto la entrada muerta: "
                          "la rama de las vivas se comio el flag")
        if not viva.exists():
            fallos.append("--dismiss se llevo por delante una entrada con proceso VIVO")
        movidas = list((registro / "dismissed").glob("*/*.env"))
        if len(movidas) != 1:
            fallos.append(f"en dismissed/ hay {len(movidas)} ficheros, se esperaba 1")
        elif movidas[0].name != muerta.name:
            fallos.append(f"se archivo la que no era: {movidas[0].name}")

        # Y sin nada muerto lo dice, en vez de anunciar que descarto cero.
        salida = []
        ns["print"] = lambda *a, **k: salida.append(" ".join(str(x) for x in a))
        if ns["main"]() != 0:
            fallos.append("sin nada que descartar, --dismiss no sale con 0")
        if not any("discard" in t.lower() or "descartar" in t.lower() for t in salida):
            fallos.append(f"sin nada que descartar no lo dice: {salida!r}")

        proceso.terminate()
        proceso.wait(timeout=10)

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_dismiss_no_se_lo_come_la_lista" if not fallos
          else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
