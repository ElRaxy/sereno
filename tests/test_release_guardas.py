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

El tercero es el CONTROL POSITIVO, y sin el los otros dos no valen: un guion que
abortara SIEMPRE los pasaria los dos. Ese caso lleva un fichero bueno con la version
correcta, asi que las dos guardas tienen que DEJARLO PASAR — y lo para el siguiente
escalon, el CHANGELOG sin su seccion, que es un mensaje distinto y por eso distingue
"la guarda salto" de "esto no arranca nunca".
"""
import os, pathlib, shutil, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GUION = RAIZ / "release.sh"

PROGRAMA = '#!/usr/bin/env python3\nimport sys\nprint("sereno %s" % "{v}")\n'
LOG = "commit 0123456789abcdef0123456789abcdef01234567\nAuthor: Alguien <a@b.c>\nDate: hoy\n"


def repo(contenido, changelog):
    """Un repo de un solo commit con ese `sereno` dentro, y el guion al lado."""
    d = pathlib.Path(tempfile.mkdtemp())
    ent = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "init", "-q", "."], cwd=d, check=True)
    (d / "sereno").write_text(contenido)
    (d / "CHANGELOG.md").write_text(changelog)
    subprocess.run(["git", "add", "sereno", "CHANGELOG.md"], cwd=d, check=True)
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
        # (nombre, contenido del fichero, changelog, version pedida, que tiene que decir)
        ("lo extraido no es el programa (el caso de la v1.13.0)",
         LOG, "# Changelog\n\n## 1.0.0\n\nx\n", "1.0.0", "shebang"),
        ("el fichero dice una version y se publica otra",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 2.0.0\n\nx\n", "2.0.0", "dice ser"),
        # CONTROL POSITIVO: las dos guardas tienen que dejarlo pasar
        ("control: fichero bueno y version correcta pasan las guardas",
         PROGRAMA.format(v="1.0.0"), "# Changelog\n\n## 9.9.9\n\nx\n", "1.0.0", "CHANGELOG"),
    ]
    for nombre, contenido, ch, version, esperado in casos:
        d = repo(contenido, ch)
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
    print("ok: no publica un log ni una version que no cuadra, lo dice en voz alta, "
          "un fichero bueno pasa las guardas, y ningun caso deja tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
