#!/usr/bin/env python3
"""Un crash dentro de curses deja su traza en `ROOT/sereno-crash.log`, no en la nada.

`curses.wrapper` restaura la terminal (endwin) antes de propagar la excepcion, asi que
el `except Exception` de `pick_ui` la tragaba y el usuario se quedaba con la pantalla
limpia y cero pistas de que el TUI habia reventado. Ahora, antes de devolver None, se
vuelca el traceback a un fichero bajo ROOT.

No se prueba el render (el TUI no se verifica headless): se fuerza el fallo sustituyendo
`curses.wrapper` por uno que revienta, que es justo la rama que este cambio protege. El
control es doble: el log NO existe antes del crash (asi sabemos que lo creo el crash) y
el volcado trae el traceback de verdad —marcador, `Traceback`, `RuntimeError`—, no un
fichero vacio. Y una segunda llamada APENDE (dos cabeceras), no pisa la anterior.

El registro se aisla con SERENO_REGISTRY a un temporal, que es tambien donde cae el log
(ROOT = registro): un test no escribe en el `~/.claude/warp-sessions` real. Entorno y
`sys.argv` tocados se restauran al salir.
"""
import contextlib, io, os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MARCA = "boom-de-prueba-en-curses-8137"


def carga(registro):
    """Fija el entorno ANTES del import: ROOT/LIVE se calculan al cargar el modulo."""
    os.environ["SERENO_REGISTRY"] = str(registro)
    for k in ("SERENO_TMUX_AUTO", "SERENO_DEMO", "SERENO_DEBUG", "CLAUDE_DEBUG"):
        os.environ.pop(k, None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text("utf-8"), "sereno", "exec"), ns)
    return ns


def revienta(*a, **k):
    raise RuntimeError(MARCA)


def cuerpo(fallos):
    import curses
    with tempfile.TemporaryDirectory() as tmp:
        reg = pathlib.Path(tmp) / "reg"
        ns = carga(reg)
        log = pathlib.Path(ns["ROOT"]) / "sereno-crash.log"

        # El log real vive bajo ROOT, que es el temporal: nunca en el registro de verdad.
        if pathlib.Path(ns["ROOT"]) != reg:
            fallos.append(f"ROOT no es el temporal: {ns['ROOT']!r}")
        if log.exists():
            fallos.append("el log ya existia antes del crash")

        original = curses.wrapper
        curses.wrapper = revienta
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                out = ns["pick_ui"]([])
        except Exception as e:                              # noqa: BLE001
            fallos.append(f"pick_ui propago en vez de tragar: {type(e).__name__}: {e}")
            out = "propago"
        finally:
            curses.wrapper = original

        if out is not None:
            fallos.append(f"pick_ui devolvio {out!r}, esperaba None tras el crash")
        if not log.exists():
            fallos.append("no se escribio el log de crash")
            return
        texto = log.read_text("utf-8")
        for aguja in (MARCA, "Traceback", "RuntimeError"):
            if aguja not in texto:
                fallos.append(f"el log no trae {aguja!r}; cuerpo:\n{texto}")

        # Segunda llamada: apende, no pisa. Deben quedar dos cabeceras "=====".
        curses.wrapper = revienta
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ns["pick_ui"]([])
        finally:
            curses.wrapper = original
        if log.read_text("utf-8").count("=====") < 4:
            fallos.append("la segunda llamada pisó el log en vez de apendear")


def main():
    fallos = []
    argv0 = list(sys.argv)
    claves = ("SERENO_REGISTRY", "SERENO_TMUX_AUTO", "SERENO_DEMO",
              "SERENO_DEBUG", "CLAUDE_DEBUG")
    guardado = {k: os.environ.get(k) for k in claves}
    try:
        cuerpo(fallos)
    finally:
        sys.argv = argv0
        for k, v in guardado.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    if fallos:
        print("FALLA crash_log:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: un crash dentro de curses vuelca su traceback a ROOT/sereno-crash.log, "
          "apende en llamadas sucesivas y pick_ui devuelve None")
    return 0


if __name__ == "__main__":
    sys.exit(main())
