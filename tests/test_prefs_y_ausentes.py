#!/usr/bin/env python3
"""El cuadro recuerda lo que elegiste, y dice lo que NO puede ofrecerte.

Dos cosas pequenas que se notan cada vez que se usa la tecla:

  · **Recordar.** Quien releva a Codex una vez suele relevar a Codex siempre. Empezar
    cada vez por el primero de la lista es hacerle teclear lo mismo una y otra vez. Lo
    ultimo elegido pasa al frente, y el sitio donde se abren se queda puesto.
  · **Decir lo que falta.** Con solo Codex instalado, el cuadro ensenaba una opcion y
    nada mas: no habia forma de enterarse de que esto va con mas CLIs. Ahora los otros
    salen en gris, y con SU motivo — que no es el mismo: uno se arregla instalandolo y
    el otro exige comprobar en su `--help` como se le pasa un prompt inicial, que es la
    regla por la que `gemini` no esta en `ARNESES` y no un olvido.

Las preferencias se guardan en un fichero, no en una variable de entorno: la gracia es
no tener que decirlo cada vez, y una variable hay que ponerla igual.
"""
import os, pathlib, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
os.environ["SERENO_DEMO"] = "1"
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
ns["PREFS"] = pathlib.Path(tempfile.mkdtemp()) / "prefs.json"


def main():
    fallos = []

    # 1. Guardar y leer, sin pisar lo que ya habia.
    ns["guarda_pref"](relevo_arnes="codex")
    ns["guarda_pref"](relevo_donde="tmux")
    if ns["pref"]("relevo_arnes") != "codex":
        fallos.append("guardar una preferencia pisa la anterior")
    if ns["pref"]("relevo_donde") != "tmux":
        fallos.append("la segunda preferencia no se guarda")
    if ns["pref"]("no_existe", "x") != "x":
        fallos.append("una preferencia que no esta no devuelve el defecto")

    # 2. Un `None` no borra lo guardado: los cuadros pasan el valor tal cual y con un
    #    lanzador ausente seria `None`, que no es una eleccion.
    ns["guarda_pref"](relevo_arnes=None)
    if ns["pref"]("relevo_arnes") != "codex":
        fallos.append("guardar None borra la preferencia buena")

    # 3. Un fichero ilegible no revienta nada: es una comodidad, no un dato.
    ns["PREFS"].write_text("{ esto no es json")
    if ns["pref"]("relevo_arnes", "d") != "d":
        fallos.append("un fichero de preferencias roto no cae al defecto")
    try:
        ns["guarda_pref"](relevo_arnes="claude")
    except Exception as e:
        fallos.append(f"guardar sobre un fichero roto revienta: {type(e).__name__}")
    if ns["pref"]("relevo_arnes") != "claude":
        fallos.append("no se puede recuperar de un fichero roto")

    # 4. Los ausentes, con su motivo. `gemini` esta en los CLI conocidos pero NO en
    #    `ARNESES`: su motivo tiene que ser el de "no se ha comprobado", no el de "no
    #    instalado" — son dos arreglos distintos.
    fuera = dict(ns["ausentes_de_relevo"](["codex"]))
    if "claude" not in fuera and "claude" in ns["ARNESES"]:
        pass                        # si `claude` esta en el PATH, no es un ausente
    if "gemini" not in fuera:
        fallos.append(f"gemini no sale como ausente: {fuera}")
    elif fuera["gemini"] != ns["_"]("not checked how to seed it"):
        fallos.append(f"el motivo de gemini es el equivocado: {fuera['gemini']!r}")
    # Y lo que SI se ofrece no aparece como ausente.
    if "codex" in fuera:
        fallos.append("un destino ofrecido sale ademas como ausente")

    # 5. Un CLI de `ARNESES` que no esta en el PATH sale como "no instalado", que es el
    #    otro motivo. Sin este caso, los dos textos podrian ser el mismo y nadie lo veria.
    real_which = ns["shutil"].which
    ns["ARNESES"] = dict(ns["ARNESES"], gemini=lambda p: "gemini " + p)
    ns["shutil"].which = lambda n: None
    try:
        fuera2 = dict(ns["ausentes_de_relevo"]([]))
    finally:
        ns["shutil"].which = real_which
    if fuera2.get("gemini") != ns["_"]("not installed"):
        fallos.append(f"un CLI conocido y sin instalar no lo dice: {fuera2}")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_prefs_y_ausentes" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
