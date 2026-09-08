#!/usr/bin/env python3
"""`release.sh` se niega a publicar algo que no es el programa.

Existe porque ya paso: la v1.13.0 publico la salida de `git show` del commit —el log—
en vez del fichero, porque en zsh `$SHA:sereno` empieza por `:s`, el modificador de
sustitucion, y el shell se come el sufijo. Sin error y con exit 0. Y las releases de
GitHub son inmutables: no se pudo reemplazar.

Se prueba EJECUTANDO el guion en repos de mentira, no leyendo sus condiciones: escrito
del otro modo no habria cazado que con un fichero basura el guion moria en la linea que
lee la version —por `set -euo pipefail`— y abortaba **sin imprimir nada**.

Los tres casos paran antes de `git tag` y antes de tocar la red, asi que el test no
publica nada ni necesita `gh`. Y se comprueba ademas que ninguno deja un tag detras.

El CONTROL POSITIVO es imprescindible, y sin el los demas no valen: un guion que
abortara SIEMPRE los pasaria todos. Ese caso lleva ficheros buenos con la version
correcta, asi que las guardas tienen que DEJARLO PASAR — y lo para el siguiente
escalon, el CHANGELOG sin su seccion, que es un mensaje distinto y por eso distingue
"la guarda salto" de "esto no arranca nunca".

Desde la 1.42.0 la release son DOS assets: el programa y `sereno-cuota`, el sidecar que
consulta la cuota del plan. Estuvo tres versiones documentado en los dos README sin que
lo distribuyera nadie, asi que sus guardas son las mismas que las del programa —existir
en el commit, empezar por el shebang, pesar algo y que python lo acepte— y se prueban
igual, ejecutando el guion.
"""
import os, pathlib, shutil, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GUION = RAIZ / "release.sh"

PROGRAMA = '#!/usr/bin/env python3\nimport sys\nprint("sereno %s" % "{v}")\n'
LOG = "commit 0123456789abcdef0123456789abcdef01234567\nAuthor: Alguien <a@b.c>\nDate: hoy\n"
# Un sidecar que pasa las tres guardas: shebang, mas de mil bytes y python lo compila.
SIDECAR = ('#!/usr/bin/env python3\n"""sereno-cuota de mentira, pero python de verdad."""\n'
           + "# relleno, que la guarda de tamano existe para cazar un fichero vacio\n" * 20
           + 'print("cuota")\n')
SIDECAR_ENANO = '#!/usr/bin/env python3\nprint("x")\n'
SIDECAR_ROTO = SIDECAR.replace('print("cuota")', 'print("cuota"')


def repo(contenido, changelog, sidecar=SIDECAR):
    """Un repo de un solo commit con ese `sereno` dentro, y el guion al lado.

    `sidecar=None` deja el commit SIN `sereno-cuota`, que es el estado en el que estuvo
    el repo hasta la 1.42.0: el fichero existia pero la release no lo subia.
    """
    d = pathlib.Path(tempfile.mkdtemp())
    ent = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "init", "-q", "."], cwd=d, check=True)
    (d / "sereno").write_text(contenido)
    (d / "CHANGELOG.md").write_text(changelog)
    aniade = ["sereno", "CHANGELOG.md"]
    if sidecar is not None:
        (d / "sereno-cuota").write_text(sidecar)
        aniade.append("sereno-cuota")
    subprocess.run(["git", "add", *aniade], cwd=d, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=d, check=True, env=ent)
    shutil.copy(str(GUION), str(d / "release.sh"))
    os.chmod(str(d / "release.sh"), 0o755)
    return d


def corre(d, version):
    r = subprocess.run(["bash", "./release.sh", version], cwd=d,
                       capture_output=True, text=True, timeout=120)
    tags = subprocess.run(["git", "tag", "--list"], cwd=d,
                          capture_output=True, text=True).stdout.split()
    return r.returncode, (r.stdout + r.stderr), tags


def main():
    fallos = []
    casos = [
        # (nombre, contenido, changelog, version pedida, que dice, sidecar)
        ("lo extraido no es el programa (el caso de la v1.13.0)",
         LOG, "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0", "shebang", SIDECAR),
        ("el fichero dice una version y se publica otra",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 2.0.0\n\nx\n", "2.0.0", "dice ser",
         SIDECAR),
        # ── el sidecar, con la misma vara que el programa ──────────────────────────
        ("el commit no trae el sidecar",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0", "no trae",
         None),
        ("el sidecar no es un programa",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0",
         "sidecar no empieza", LOG),
        ("el sidecar es un cascaron de dos lineas",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0",
         "sidecar son", SIDECAR_ENANO),
        ("el sidecar no compila",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0",
         "no acepta el sidecar", SIDECAR_ROTO),
        # CONTROL POSITIVO: las guardas de los dos ficheros tienen que dejarlo pasar
        ("control: fichero bueno, sidecar bueno y version correcta pasan las guardas",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 9.9.9\n\nx\n", "1.0.0", "CHANGELOG",
         SIDECAR),
    ]
    for nombre, contenido, ch, version, esperado, sidecar in casos:
        d = repo(contenido, ch, sidecar)
        try:
            cod, salida, tags = corre(d, version)
            if cod == 0:
                fallos.append(f"{nombre}: salio con 0; tenia que abortar")
            if esperado not in salida:
                fallos.append(f"{nombre}: no dijo {esperado!r}. Dijo: {salida.strip()[:160]!r}")
            if not salida.strip():
                fallos.append(f"{nombre}: aborto MUDO, sin una linea que lo explique")
            if tags:
                fallos.append(f"{nombre}: dejo tags detras: {tags}")
        finally:
            shutil.rmtree(str(d), ignore_errors=True)

    # sin argumento no hace nada y lo dice
    d = repo(PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 1.0.0\n\nx\n")
    try:
        cod, salida, tags = corre(d, "")
        if cod == 0 or "uso:" not in salida:
            fallos.append(f"sin version: cod={cod}, salida={salida.strip()[:120]!r}")
        if tags:
            fallos.append(f"sin version: dejo tags detras: {tags}")
    finally:
        shutil.rmtree(str(d), ignore_errors=True)

    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("ok: no publica un log, ni una version que no cuadra, ni una release sin el "
          "sidecar o con un sidecar que no es un programa; lo dice en voz alta, un "
          "commit bueno pasa las guardas, y ningun caso deja tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
