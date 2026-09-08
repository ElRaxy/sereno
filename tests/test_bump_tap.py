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

Los casos que abortan valen poco sin el primero, que es el CONTROL POSITIVO: un guion
que no hiciera nada nunca los pasaria todos. Y el segundo mira la otra mitad de lo
mismo — que un bump repetido no invente un commit vacio.

Desde la 1.42.0 la formula trae ademas un `resource "sereno-cuota"` con su propia url y
su propio sha256, asi que la reescritura son CUATRO sustituciones en dos mitades. El
patron del sha256 no sabe de cual de las dos es, y por eso el guion parte la formula por
el bloque antes de tocar nada: aqui se prueba que las dos mitades quedan al dia y que una
formula sin el bloque no se edita a ciegas.
"""
import hashlib, os, pathlib, re, shutil, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GUION = RAIZ / "bump-tap.sh"
SHA_A = "a" * 64
SHA_B = "b" * 64

FORMULA = '''class Sereno < Formula
  url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno"
  sha256 "{sha}"

  resource "sereno-cuota" do
    url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno-cuota"
    sha256 "{sha_cuota}"
  end
end
'''
SIN_RESOURCE = '''class Sereno < Formula
  url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno"
  sha256 "{sha}"
end
'''
SHA_C_VIEJO = "e" * 64

ENT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")


def assets(version="2.0.0", cuerpo=b"#!/usr/bin/env python3\n",
           cuerpo_cuota=b"#!/usr/bin/env python3\n# sereno-cuota\n", con_cuota=True):
    """Un 'servidor' de releases que es un directorio, servido por `file://`.

    El guion comprueba contra la red que los assets existen y que su sha es el que se le
    pide. Probar eso contra GitHub ataria el test a que haya conexion y a que una release
    concreta siga publicada; `curl` habla `file://` igual de bien, asi que la
    comprobacion se ejerce ENTERA sin salir de la maquina.

    `con_cuota=False` publica solo el programa: la release de antes de la 1.42.0.
    """
    d = pathlib.Path(tempfile.mkdtemp())
    (d / ("v" + version)).mkdir()
    (d / ("v" + version) / "sereno").write_bytes(cuerpo)
    if con_cuota:
        (d / ("v" + version) / "sereno-cuota").write_bytes(cuerpo_cuota)
    return d, hashlib.sha256(cuerpo).hexdigest(), hashlib.sha256(cuerpo_cuota).hexdigest()


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


def corre(bare, *args, base=None):
    ent = dict(ENT, SERENO_TAP_REMOTO=str(bare))
    # Sin base, se apunta a un directorio vacio: cualquier version sale como no publicada.
    ent["SERENO_ASSET_BASE"] = "file://" + str(base if base else tempfile.mkdtemp())
    r = subprocess.run(["bash", str(GUION), *args], cwd=RAIZ, capture_output=True,
                       text=True, timeout=120, env=ent)
    return r.returncode, r.stdout + r.stderr


def main():
    fallos = []

    # ── CONTROL POSITIVO: una formula normal se bumpea y el remoto lo refleja ──────
    releases, SHA_B, SHA_C = assets("2.0.0")
    d, bare = tap(FORMULA.format(sha=SHA_A, sha_cuota=SHA_C_VIEJO))
    try:
        cod, salida = corre(bare, "2.0.0", SHA_B, SHA_C, base=releases)
        fin = publicado(bare)
        if cod != 0:
            fallos.append(f"formula buena: salio con {cod}. Dijo: {salida.strip()[:200]!r}")
        if "download/v2.0.0/sereno\n" not in fin and 'download/v2.0.0/sereno"' not in fin:
            fallos.append(f"formula buena: el remoto no apunta a v2.0.0. Quedo: {fin!r}")
        if SHA_B not in fin or SHA_A in fin:
            fallos.append(f"formula buena: el sha256 no se cambio. Quedo: {fin!r}")
        # ── y la otra mitad: el resource del sidecar, que es la que no existia ─────
        if 'download/v2.0.0/sereno-cuota"' not in fin:
            fallos.append(f"formula buena: el resource sigue sin apuntar a v2.0.0. Quedo: {fin!r}")
        if SHA_C not in fin or SHA_C_VIEJO in fin:
            fallos.append(f"formula buena: el sha256 del sidecar no se cambio. Quedo: {fin!r}")

        # ── y un segundo bump igual no inventa un commit ──────────────────────────
        antes = subprocess.run(["git", "rev-parse", "main"], cwd=bare, capture_output=True,
                               text=True, env=ENT).stdout
        cod2, salida2 = corre(bare, "2.0.0", SHA_B, SHA_C, base=releases)
        despues = subprocess.run(["git", "rev-parse", "main"], cwd=bare, capture_output=True,
                                 text=True, env=ENT).stdout
        if cod2 != 0 or "ya estaba" not in salida2:
            fallos.append(f"segundo bump: cod={cod2}, dijo {salida2.strip()[:160]!r}")
        if antes != despues:
            fallos.append("segundo bump: movio el remoto sin tener nada que cambiar")
    finally:
        shutil.rmtree(str(d), ignore_errors=True)

    # ── los que tienen que abortar, y dejar el remoto intacto ─────────────────────
    buena = FORMULA.format(sha=SHA_A, sha_cuota=SHA_C_VIEJO)
    casos = [
        ("una formula sin url de release",
         buena.replace('  url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno"\n',
                       ""), "2.0.0", SHA_B, SHA_C, "url=0"),
        # El segundo sha256 va FUERA del resource a proposito: dentro seria el otro
        # mensaje, y lo que este caso vigila es la mitad de siempre.
        ("una formula con dos sha256",
         buena.replace('  sha256 "%s"\n' % SHA_A, '  sha256 "%s"\n  sha256 "%s"\n'
                       % (SHA_A, SHA_A), 1),
         "2.0.0", SHA_B, SHA_C, "sha256=2"),
        # El bloque del sidecar no se inventa: sin el, `brew install` dejaria fuera
        # `sereno-cuota` y el README seguiria prometiendo un comando que no existe.
        ("una formula sin el bloque resource del sidecar",
         SIN_RESOURCE.format(sha=SHA_A), "2.0.0", SHA_B, SHA_C, "resource"),
        ("un sha256 que no es un sha256",
         buena, "2.0.0", "nosoyunsha", SHA_C, "no es un sha256"),
        ("un sha256 de 63 caracteres",
         buena, "2.0.0", "a" * 63, SHA_C, "63 caracteres"),
        ("un sha256 del sidecar que no es un sha256",
         buena, "2.0.0", SHA_B, "tampocosoyunsha", "no es un sha256"),
        # Estos tres son los que la auditoria echo en falta: el guion validaba la FORMA
        # y nunca el HECHO, asi que un dedazo en el numero dejaba el tap apuntando a un
        # 404 y salia con 0. Lo unico que lo tapaba era el orden dentro de `release.sh`.
        ("una version que no esta publicada",
         buena, "99.99.99", SHA_B, SHA_C, "no esta publicada"),
        ("un sha que no es el del asset publicado",
         buena, "2.0.0", "c" * 64, SHA_C, "se pidio escribir"),
        ("un sha del sidecar que no es el del asset publicado",
         buena, "2.0.0", SHA_B, "d" * 64, "sereno-cuota publicado"),
        ("una formula con una stanza `version` explicita",
         buena.replace("class Sereno < Formula\n",
                       'class Sereno < Formula\n  version "1.0.0"\n'),
         "2.0.0", SHA_B, SHA_C, "stanza"),
    ]
    for nombre, contenido, ver, sha, sha_c, esperado in casos:
        d, bare = tap(contenido)
        try:
            antes = publicado(bare)
            cod, salida = corre(bare, ver, sha, sha_c, base=releases)
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
    d, bare = tap(FORMULA.format(sha=SHA_A, sha_cuota=SHA_C_VIEJO))
    try:
        cod, salida = corre(bare, base=releases)
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
    print("ok: bumpea las dos mitades —programa y resource del sidecar—, el remoto lo "
          "refleja, repetirlo no mueve nada, y lo paran sin tocar el tap una formula "
          "ambigua, una sin el bloque resource, un sha falso de cualquiera de los dos, "
          "una version sin publicar y una stanza `version` que no bumpea")
    return 0


if __name__ == "__main__":
    sys.exit(main())
