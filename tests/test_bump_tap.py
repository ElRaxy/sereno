#!/usr/bin/env python3
"""`bump-tap.sh` deja el tap apuntando a la version publicada, o no lo toca.

La formula de Homebrew es la segunda copia del numero de version, y una segunda copia
que escribe una persona se queda vieja. Por eso la escribe `release.sh` — y por eso hay
que probar que la escribe BIEN, que es justo lo que no se puede comprobar leyendo el
guion: la reescritura son dos regex sobre un fichero ajeno.

Se prueba contra un remoto de mentira (`SERENO_TAP_REMOTO` apuntando a un repo bare en
un directorio temporal), asi que el test empuja de verdad y luego RELEE del remoto. Ni
una llamada a la red, y aun asi se ejerce el camino entero: clonar, editar, empujar y
verificar.

Los tres casos que abortan valen poco sin el primero, que es el CONTROL POSITIVO: un
guion que no hiciera nada nunca pasaria los tres. Y el ultimo mira la otra mitad de lo
mismo — que un bump repetido no invente un commit vacio.
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GUION = RAIZ / "bump-tap.sh"
SHA_A = "a" * 64
SHA_B = "b" * 64

FORMULA = '''class Sereno < Formula
  url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno"
  sha256 "{sha}"
end
'''

ENT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")


def tap(contenido):
    """Un tap de mentira: un repo bare al que se puede empujar, con la formula dentro."""
    d = pathlib.Path(tempfile.mkdtemp())
    trabajo, bare = d / "trabajo", d / "tap.git"
    (trabajo / "Formula").mkdir(parents=True)
    (trabajo / "Formula" / "sereno.rb").write_text(contenido)
    g = lambda *a, **k: subprocess.run(["git", *a], cwd=trabajo, check=True, env=ENT,
                                       capture_output=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=ENT)
    g("init", "-q", "-b", "main", ".")
    g("add", "-A"); g("commit", "-qm", "x")
    g("push", "-q", str(bare), "HEAD:main")
    return d, bare


def publicado(bare):
    """Lo que se bajaria hoy de ese tap. Se lee del remoto, no del clon que empujo."""
    return subprocess.run(["git", "show", "main:Formula/sereno.rb"], cwd=bare,
                          capture_output=True, text=True, env=ENT).stdout


def corre(bare, *args):
    r = subprocess.run(["bash", str(GUION), *args], cwd=RAIZ, capture_output=True,
                       text=True, timeout=120,
                       env=dict(ENT, SERENO_TAP_REMOTO=str(bare)))
    return r.returncode, r.stdout + r.stderr


def main():
    fallos = []

    # ── CONTROL POSITIVO: una formula normal se bumpea y el remoto lo refleja ──────
    d, bare = tap(FORMULA.format(sha=SHA_A))
    try:
        cod, salida = corre(bare, "2.0.0", SHA_B)
        fin = publicado(bare)
        if cod != 0:
            fallos.append(f"formula buena: salio con {cod}. Dijo: {salida.strip()[:200]!r}")
        if "download/v2.0.0/sereno" not in fin:
            fallos.append(f"formula buena: el remoto no apunta a v2.0.0. Quedo: {fin!r}")
        if SHA_B not in fin or SHA_A in fin:
            fallos.append(f"formula buena: el sha256 no se cambio. Quedo: {fin!r}")

        # ── y un segundo bump igual no inventa un commit ──────────────────────────
        antes = subprocess.run(["git", "rev-parse", "main"], cwd=bare, capture_output=True,
                               text=True, env=ENT).stdout
        cod2, salida2 = corre(bare, "2.0.0", SHA_B)
        despues = subprocess.run(["git", "rev-parse", "main"], cwd=bare, capture_output=True,
                                 text=True, env=ENT).stdout
        if cod2 != 0 or "ya estaba" not in salida2:
            fallos.append(f"segundo bump: cod={cod2}, dijo {salida2.strip()[:160]!r}")
        if antes != despues:
            fallos.append("segundo bump: movio el remoto sin tener nada que cambiar")
    finally:
        shutil.rmtree(str(d), ignore_errors=True)

    # ── los que tienen que abortar, y dejar el remoto intacto ─────────────────────
    casos = [
        ("una formula sin url de release",
         'class Sereno < Formula\n  sha256 "%s"\nend\n' % SHA_A, "2.0.0", SHA_B, "url=0"),
        ("una formula con dos sha256",
         FORMULA.format(sha=SHA_A).replace("end\n", '  sha256 "%s"\nend\n' % SHA_A),
         "2.0.0", SHA_B, "sha256=2"),
        ("un sha256 que no es un sha256",
         FORMULA.format(sha=SHA_A), "2.0.0", "nosoyunsha", "no es un sha256"),
        ("un sha256 de 63 caracteres",
         FORMULA.format(sha=SHA_A), "2.0.0", "a" * 63, "63 caracteres"),
    ]
    for nombre, contenido, ver, sha, esperado in casos:
        d, bare = tap(contenido)
        try:
            antes = publicado(bare)
            cod, salida = corre(bare, ver, sha)
            if cod == 0:
                fallos.append(f"{nombre}: salio con 0; tenia que abortar")
            if esperado not in salida:
                fallos.append(f"{nombre}: no dijo {esperado!r}. Dijo: {salida.strip()[:200]!r}")
            if not salida.strip():
                fallos.append(f"{nombre}: aborto MUDO, sin una linea que lo explique")
            if publicado(bare) != antes:
                fallos.append(f"{nombre}: toco el remoto pese a abortar")
        finally:
            shutil.rmtree(str(d), ignore_errors=True)

    # ── sin argumentos no hace nada y lo dice ─────────────────────────────────────
    d, bare = tap(FORMULA.format(sha=SHA_A))
    try:
        cod, salida = corre(bare)
        if cod == 0 or "uso:" not in salida:
            fallos.append(f"sin argumentos: cod={cod}, salida={salida.strip()[:120]!r}")
    finally:
        shutil.rmtree(str(d), ignore_errors=True)

    # ── y `release.sh` sigue llamandolo, DESPUES de verificar lo publicado ───────────
    # La garantia entera de este guion es de POSICION: `bump-tap.sh` no comprueba que la
    # version exista —valida la forma del sha y de la formula, no el hecho— asi que lo
    # unico que impide apuntar el tap a un asset no verificado es que la llamada vaya
    # detras de la descarga de comprobacion. Comprobar solo que la llamada EXISTE dejaba
    # pasar adelantarla: probado moviendola antes de `gh release create`, y el test seguia
    # verde. Un invariante que nadie vigila deja de ser un invariante.
    rel = (RAIZ / "release.sh").read_text()
    i_bump = rel.find('./bump-tap.sh "$VER" "$esperado"')
    i_baja = rel.find("gh release download")
    i_crea = rel.find("gh release create")
    if i_bump < 0:
        fallos.append("release.sh ya no llama a ./bump-tap.sh con la version y el sha verificados")
    elif not (0 < i_crea < i_baja < i_bump):
        fallos.append("release.sh llama al bump fuera de sitio: create=%d, download=%d, bump=%d. "
                      "Tiene que ir DESPUES de descargar y verificar lo publicado."
                      % (i_crea, i_baja, i_bump))

    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("ok: bumpea y el remoto lo refleja, repetirlo no mueve nada, y una formula "
          "ambigua o un sha256 falso lo paran sin tocar el tap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
