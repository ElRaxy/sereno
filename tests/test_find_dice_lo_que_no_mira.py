#!/usr/bin/env python3
"""`--find` dice cuantos transcripts se ha dejado fuera.

Por defecto mira los 200 mas recientes. En esta maquina hay 601, asi que una busqueda
normal recorre un tercio y la cabecera decia solo "buscando en 200 transcripts": quien la
lee entiende que eso es todo lo que hay. Un "no lo dijiste nunca" que en realidad es "no
estaba en el tercio que mire" es la peor respuesta que puede dar un buscador.

El aviso va por stderr, como el de peso, para no ensuciar la salida de quien la canalice.
"""
import contextlib, io, json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID = "0123abcd-4567-89ef-0123-4567890000%02d"


def main():
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-home-u-proyecto"
        proy.mkdir(parents=True)
        for i in range(5):
            linea = {"type": "user", "cwd": "/home/u/proyecto",
                     "message": {"role": "user",
                                 "content": f"una aguja concreta numero {i} " + "x" * 40}}
            f = proy / (UUID % i + ".jsonl")
            f.write_text(json.dumps(linea) + "\n")
            os.utime(f, (time.time() - i * 60, time.time() - i * 60))

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        buscar = ns["buscar"]

        def corre(**kw):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                res = buscar("una aguja concreta", **kw)
            return res, err.getvalue()

        # 1. Con tope, dice cuantas quedan fuera y cuantas mira.
        res, err = corre(limite=2)
        if len(res) != 2:
            fallos.append(f"con limite=2 devuelve {len(res)} sesiones, se esperaban 2")
        if "3" not in err or "--all" not in err:
            fallos.append(f"no avisa de las 3 que deja fuera ni de --all: {err.strip()!r}")

        # 2. Con `--all` no hay nada que avisar, y ese es el control: si el aviso saliera
        #    siempre, el caso de arriba pasaria sin que el mensaje dijera la verdad.
        res, err = corre(todo=True)
        if len(res) != 5:
            fallos.append(f"con todo=True devuelve {len(res)} sesiones, se esperaban 5")
        if "--all" in err:
            fallos.append(f"avisa de que deja fuera algo cuando no deja nada: {err.strip()!r}")

        # 3. Y si el tope no recorta, tampoco avisa.
        _res, err = corre(limite=99)
        if "--all" in err:
            fallos.append("avisa con un tope que no llega a recortar")

        # 4. El aviso NO va por stdout: `--find` se canaliza.
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            buscar("una aguja concreta", limite=2)
        if out.getvalue().strip():
            fallos.append(f"escribe en stdout: {out.getvalue()[:80]!r}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_find_dice_lo_que_no_mira" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
