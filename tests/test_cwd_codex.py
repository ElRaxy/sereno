#!/usr/bin/env python3
"""El directorio de una sesion de Codex sale de su rollout, no del indice.

Existe por el relevo. El indice de Codex trae `{id, thread_name, updated_at}` y nada
mas, asi que sus filas llegaban con `cwd` vacio — y una fila sin directorio no se puede
relevar sin abrir el otro CLI en un sitio que no es el suyo. La cabecera del rollout si
lo trae, en `payload.cwd`.

Lo que se vigila aqui:

  1. que se lea, y del rollout correcto de entre varios;
  2. que una sesion sin rollout se quede con el `cwd` vacio en vez de heredar el de otra
     — que es la forma que tomaria el fallo: un relevo aterrizando en el proyecto
     equivocado, con pinta de haber funcionado.
"""
import json, os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ID_A = "01a04937-b7f4-75a3-bb98-d23e8175d32b"
ID_B = "01a0481d-321a-7811-ba25-adee51865dda"
ID_HUERFANO = "01a00000-0000-7000-0000-000000000000"


def main():
    fallos = []
    os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
    os.environ.pop("SERENO_DEMO", None)
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

    with tempfile.TemporaryDirectory() as tmp:
        raiz = pathlib.Path(tmp) / "sessions"
        dia = raiz / "2026" / "08" / "28"
        dia.mkdir(parents=True)

        def rollout(sid, cwd, fecha="2026-08-28T10-00-00", rama=""):
            f = dia / f"rollout-{fecha}-{sid}.jsonl"
            pay = {"cwd": cwd, "id": sid}
            if rama:
                pay["git"] = {"branch": rama}
            f.write_text(json.dumps({"type": "session_meta", "ordinal": 0,
                                     "payload": pay}) + "\n"
                         + json.dumps({"type": "event", "payload": {}}) + "\n")
            return f

        rollout(ID_A, "/tmp/proyecto-a", rama="feature/a")
        rollout(ID_B, "/tmp/proyecto-b", "2026-08-28T11-00-00")
        ns["CODEX_SESIONES"] = raiz

        # 1. Cada id con el suyo —cwd, rama y la ruta del rollout—. Dos ficheros a la vez,
        #    porque con uno solo un bug que devuelva "el primero que encuentre" pasaria.
        salida = ns["_cwd_codex"]([ID_A, ID_B])
        a, b = salida.get(ID_A) or {}, salida.get(ID_B) or {}
        if a.get("cwd") != "/tmp/proyecto-a" or b.get("cwd") != "/tmp/proyecto-b":
            fallos.append(f"los cwd salen cruzados o vacios: {salida}")
        if a.get("rama") != "feature/a":
            fallos.append(f"la rama no sale de la cabecera: {a.get('rama')!r}")
        if not str(a.get("rollout") or "").endswith(ID_A + ".jsonl"):
            fallos.append("no devuelve la ruta del rollout de cada sesion")

        # 2. Un id sin rollout no aparece: la fila se queda sin sitio, que es lo que
        #    hace que el relevo la descarte en vez de abrirla en el directorio de otra.
        salida = ns["_cwd_codex"]([ID_HUERFANO])
        if salida:
            fallos.append(f"una sesion sin rollout devuelve un cwd: {salida}")

        # 3. El uuid se lee del FINAL del nombre. La fecha del rollout tambien lleva
        #    guiones, asi que partir por guiones da un id que no existe y todo sale
        #    vacio — pero el caso 2 tambien espera vacio y no lo distinguiria.
        raro = raiz / "2026" / "08" / "28"
        (raro / f"rollout-2026-08-28T12-00-00-{ID_HUERFANO}.jsonl").write_text(
            json.dumps({"payload": {"cwd": "/tmp/con-fecha-larga"}}) + "\n")
        if (ns["_cwd_codex"]([ID_HUERFANO]).get(ID_HUERFANO) or {}).get("cwd") \
                != "/tmp/con-fecha-larga":
            fallos.append("el uuid no se lee del final del nombre del rollout")

        # 4. Sin carpeta de sesiones no revienta: devuelve vacio.
        ns["CODEX_SESIONES"] = pathlib.Path(tmp) / "no-existe"
        if ns["_cwd_codex"]([ID_A]) != {}:
            fallos.append("sin carpeta de sesiones no devuelve vacio")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_cwd_codex" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
