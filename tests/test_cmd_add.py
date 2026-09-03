#!/usr/bin/env python3
"""`cmd_add` no vuelca un traceback ni registra basura con argv incompleto o torcido.

`sereno --add` es un comando interno: el wrapper le pasa el argv ya formado. Pero es
alcanzable a mano, y leia `argv` sin comprobar limites y sin mirar QUE leia:

    sereno --add                      -> IndexError (sid = argv[0])
    sereno --add x --cwd              -> IndexError (cwd = argv[i + 1])
    sereno --add x --title            -> IndexError (title = argv[i + 1])
    sereno --add --cwd /tmp           -> registraba "--cwd" como id, en silencio
    sereno --add ""                   -> registraba un id vacio, en silencio
    sereno --add x --cwd --title t    -> registraba cwd="--title", en silencio

El id no puede faltar, ni ser vacio/espacios, ni un token de opcion; y ni --cwd ni --title
se tragan la siguiente opcion como si fuera su valor. Las tres ramas devuelven un error
limpio traducido con codigo 2, y NO escriben nada.

Se conduce por el enlace real —`main()` leyendo `sys.argv`— y no llamando a `cmd_add` a
pelo: asi el test protege tambien el dispatch `argv[0] == "--add"`, no solo la funcion.

El control positivo es la mitad que hace que esto pruebe algo: el caso valido SI registra
y devuelve 0. Sin el, borrar la escritura del `.env` pasaria los casos de arriba. Y cada
negativo comprueba ademas que LIVE sigue sin `.env`: devolver 2 no basta si de paso escribio.

El registro se aisla con SERENO_REGISTRY a un temporal; el entorno y `sys.argv` que se tocan
se restauran al salir, para no ensuciar a quien importe este modulo.
"""
import contextlib, io, os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent

MSG = {
    "add":   ("--add needs a session id.", "--add necesita un id de sesión."),
    "cwd":   ("--cwd needs a path.",       "--cwd necesita una ruta."),
    "title": ("--title needs a value.",    "--title necesita un valor."),
}

NEGATIVOS = [
    (["--add"],                                  "add"),
    (["--add", ""],                              "add"),
    (["--add", "   "],                           "add"),
    (["--add", "--cwd", "/tmp"],                 "add"),
    (["--add", "x", "--cwd"],                    "cwd"),
    (["--add", "x", "--cwd", "--title", "t"],    "cwd"),
    (["--add", "x", "--title"],                  "title"),
    (["--add", "x", "--title", "--cwd", "/tmp"], "title"),
]


def carga(registro):
    """Fija el entorno ANTES del import: ROOT/LIVE se calculan al cargar el modulo."""
    os.environ["SERENO_REGISTRY"] = str(registro)
    os.environ.pop("SERENO_TMUX_AUTO", None)
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text("utf-8"), "sereno", "exec"), ns)
    return ns


def corre(ns, args, lang):
    """Conduce main() con un argv y un idioma. `_()` lee LANG_UI en cada llamada, asi que
    reasignar el global entre casos basta para probar EN y ES sin recargar el modulo."""
    ns["LANG_UI"] = lang
    sys.argv = ["sereno"] + args
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ns["main"]()
    return code, buf.getvalue()


def envs(ns):
    return list(pathlib.Path(ns["LIVE"]).glob("manual-*.env"))


def cuerpo(fallos):
    with tempfile.TemporaryDirectory() as tmp:
        ns = carga(pathlib.Path(tmp) / "reg")

        for args, clave in NEGATIVOS:
            en, es = MSG[clave]
            for lang, esperado in (("en", en), ("es", es)):
                try:
                    code, out = corre(ns, args, lang)
                except Exception as e:                      # noqa: BLE001
                    fallos.append(f"{args} {lang}: reventó con {type(e).__name__}: {e}")
                    continue
                if code != 2:
                    fallos.append(f"{args} {lang}: return {code!r}, esperaba 2")
                if esperado not in out:
                    fallos.append(f"{args} {lang}: no salió {esperado!r}; salió {out!r}")
                if envs(ns):
                    fallos.append(f"{args} {lang}: registró un .env pese a rechazar el argv")

        # Control positivo: el caso valido registra y devuelve 0.
        destino = pathlib.Path(tmp) / "proyecto"
        try:
            code, out = corre(ns, ["--add", "sesion-1", "--cwd", str(destino),
                                   "--title", "t"], "en")
        except Exception as e:                              # noqa: BLE001
            fallos.append(f"caso válido: reventó con {type(e).__name__}: {e}")
            code, out = None, ""
        if code != 0:
            fallos.append(f"caso válido: return {code!r}, esperaba 0")
        if "registered" not in out:
            fallos.append(f"caso válido: no dijo 'registered'; salió {out!r}")
        marcas = envs(ns)
        if not marcas:
            fallos.append("caso válido: no escribió ningún .env en LIVE")
        else:
            texto = marcas[-1].read_text("utf-8")
            if "title=t\n" not in texto:
                fallos.append(f"caso válido: no serializó title=t; cuerpo:\n{texto}")
            if "title_explicit=1\n" not in texto:
                fallos.append(f"caso válido: title_explicit != 1; cuerpo:\n{texto}")


def main():
    fallos = []
    argv0 = list(sys.argv)
    guardado = {k: os.environ.get(k) for k in
                ("SERENO_REGISTRY", "SERENO_TMUX_AUTO", "SERENO_DEMO")}
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
        print("FALLA cmd_add:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: cmd_add rechaza argv incompleto o torcido con return 2, mensaje traducido "
          "y sin registrar nada; y registra el caso válido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
