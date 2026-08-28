#!/usr/bin/env python3
"""En una maquina sin Warp, abrir varias no revienta y no miente.

Sereno se publica para cualquiera, y `open` es un comando de macOS. En Linux
`subprocess.run(["open", ...])` lanza `FileNotFoundError`, asi que `r` y `c` **tumbaban
el programa** desde dentro de curses. Y en un macOS sin Warp no reventaban: el `open`
fallaba en silencio y la pantalla anunciaba igual *"Reattaching 3 tabs"*.

Los dos son el mismo fallo visto desde dos sitios — nadie miraba si la llamada habia
hecho algo — y por eso se prueban juntos:

  1. sin `open`, ninguna de las dos revienta;
  2. sin Warp, ninguna de las dos dice que ha abierto nada.

El control positivo del final es lo que hace que esto pruebe algo: con Warp y con `open`,
las mismas filas SI se dan por abiertas. Sin el, un `return 1` puesto a lo bruto pasaria
los dos casos de arriba.
"""
import contextlib, io, os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def carga(hay_warp, open_revienta, llamadas):
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    ns["hay_warp"] = lambda: hay_warp
    ns["LAUNCH"] = pathlib.Path(tempfile.mkdtemp())

    class Falso:
        @staticmethod
        def run(cmd, *a, **k):
            llamadas.append(cmd)
            if open_revienta:
                raise FileNotFoundError(2, "No such file or directory: 'open'")
            return type("R", (), {"returncode": 0})()
    ns["subprocess"] = Falso
    return ns


def filas(cwd, n=3):
    return [{"name": f"cc-x-{i}", "title": f"s{i}", "title_full": f"sesion {i}",
             "attached": False, "idle": 3, "meta": {"cwd": cwd, "id": str(i)},
             "_det": {"cwd": cwd, "gitBranch": "main", "peso": 1, "lastPrompt": "p",
                      "resp": "r", "fase": None, "tool": None, "ruta": []}}
            for i in range(n)]


def main():
    fallos = []
    tmp = tempfile.mkdtemp()

    # 1. Sin `open` (Linux) no revienta ninguna de las dos.
    for warp in (True, False):
        llam = []
        ns = carga(warp, True, llam)
        for nombre, fn in (("reopen", lambda: ns["reopen"](filas(tmp))),
                           ("relevo", lambda: ns["relevo"](filas(tmp), "codex"))):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    fn()
            except Exception as e:
                fallos.append(f"[warp={warp}] {nombre} revienta sin `open`: "
                              f"{type(e).__name__}: {e}")

    # 2. Sin Warp, ninguna dice que ha abierto nada.
    llam = []
    ns = carga(False, False, llam)
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = ns["reopen"](filas(tmp))
    texto = salida.getvalue()
    if codigo == 0:
        fallos.append("sin Warp `reopen` devuelve exito")
    if "Reattaching" in texto or "pesta" in texto.lower():
        fallos.append(f"sin Warp `reopen` anuncia pestanas: {texto.strip()!r}")
    arnes, aviso = ns["relevo"](filas(tmp), "codex")
    if arnes is not None or "handed over" in aviso or "entregada" in aviso:
        fallos.append(f"sin Warp `relevo` se da por hecho: {arnes!r} {aviso!r}")
    if llam:
        fallos.append(f"sin Warp se llamo igual a `open`: {llam}")

    # 3. Control positivo: con Warp y con `open`, las MISMAS filas si se abren. Sin
    #    esto, un `return 1` a lo bruto pasaria los dos casos de arriba.
    llam = []
    ns = carga(True, False, llam)
    with contextlib.redirect_stdout(io.StringIO()):
        codigo = ns["reopen"](filas(tmp))
    arnes, aviso = ns["relevo"](filas(tmp), "codex")
    if codigo != 0:
        fallos.append("con Warp `reopen` tampoco abre: el caso 2 no prueba nada")
    if arnes != "codex":
        fallos.append(f"con Warp `relevo` tampoco entrega: {arnes!r} {aviso!r}")
    if len(llam) != 2:
        fallos.append(f"con Warp se llamo {len(llam)} veces a `open`, se esperaban 2")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_sin_warp" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
