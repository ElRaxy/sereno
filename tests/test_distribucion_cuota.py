#!/usr/bin/env python3
"""`sereno-cuota` llega a la maquina de quien instala, por cualquiera de las dos vias.

Existe por un agujero que no rompia ningun test y sin embargo se veia desde fuera: el
sidecar estaba escrito, probado (`tests/test_cuota.py`), documentado en los dos README y
anunciado en el CHANGELOG desde la 1.41.0 — y **no lo distribuia nadie**. La release
subia un solo asset, la formula del tap hacia `bin.install "sereno"` y el instalador se
bajaba un fichero. Quien instalaba por brew, leia el README y tecleaba `sereno-cuota`
recibia un `command not found` por un comando que la propia documentacion le ofrecia.

Es la clase de fallo que no se caza mirando el codigo del programa, porque el programa
esta bien: falta en el reparto. De ahi que lo que se prueba aqui sea el REPARTO, y sobre
lo que queda en el disco, no sobre lo que los guiones dicen que hacen.

Sin una sola llamada a la red: el instalador se apunta a un directorio local con
`SERENO_RAW_BASE` (curl habla `file://` igual de bien), y `bump-tap.sh` a un tap de
mentira. Lo que ejerce el camino entero es que los ficheros aparecen de verdad.

Los dos casos que fallan valen poco sin el primero, que es el CONTROL POSITIVO, y sin el
tercero tampoco: un instalador que no bajara nada pasaria "el sidecar no aborta la
instalacion" sin bajar tampoco el programa.
"""
import hashlib, os, pathlib, shutil, stat, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INSTALL = RAIZ / "install.sh"
BUMP = RAIZ / "bump-tap.sh"

PROGRAMA = b"#!/usr/bin/env python3\nprint('sereno')\n"
SIDECAR = b"#!/usr/bin/env python3\nprint('cuota')\n"

ENT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")

FORMULA = '''class Sereno < Formula
  url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno"
  sha256 "{sha}"

  resource "sereno-cuota" do
    url "https://github.com/ElRaxy/sereno/releases/download/v1.0.0/sereno-cuota"
    sha256 "{sha_cuota}"
  end
end
'''


def ejecutable(p):
    """Un hecho, no una impresion: existe Y tiene el bit de ejecucion puesto."""
    return p.is_file() and bool(p.stat().st_mode & stat.S_IXUSR)


def instala(con_sidecar=True, con_programa=True):
    """Corre `install.sh` contra un 'servidor' que es un directorio. Devuelve
    (codigo, salida, carpeta de instalacion)."""
    origen = pathlib.Path(tempfile.mkdtemp())
    if con_programa:
        (origen / "sereno").write_bytes(PROGRAMA)
    if con_sidecar:
        (origen / "sereno-cuota").write_bytes(SIDECAR)
    destino = pathlib.Path(tempfile.mkdtemp()) / "bin"
    ent = dict(os.environ, SERENO_BIN=str(destino),
               SERENO_RAW_BASE="file://" + str(origen))
    r = subprocess.run(["sh", str(INSTALL)], capture_output=True, text=True,
                       timeout=120, env=ent)
    shutil.rmtree(str(origen), ignore_errors=True)
    return r.returncode, r.stdout + r.stderr, destino


def tap(contenido):
    """Un tap de mentira: un repo bare al que se puede empujar, con la formula dentro."""
    d = pathlib.Path(tempfile.mkdtemp())
    trabajo, bare = d / "trabajo", d / "tap.git"
    (trabajo / "Formula").mkdir(parents=True)
    (trabajo / "Formula" / "sereno.rb").write_text(contenido)
    g = lambda *a: subprocess.run(["git", *a], cwd=trabajo, check=True, env=ENT,
                                  capture_output=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)],
                   check=True, env=ENT)
    g("init", "-q", "-b", "main", ".")
    g("add", "-A"); g("commit", "-qm", "x")
    g("push", "-q", str(bare), "HEAD:main")
    return d, bare


def bump(bare, base, *args):
    ent = dict(ENT, SERENO_TAP_REMOTO=str(bare), SERENO_ASSET_BASE="file://" + str(base))
    r = subprocess.run(["bash", str(BUMP), *args], cwd=RAIZ, capture_output=True,
                       text=True, timeout=120, env=ent)
    return r.returncode, r.stdout + r.stderr


def main():
    fallos = []

    # ── CONTROL POSITIVO: el instalador deja los DOS ficheros ejecutables ─────────
    cod, salida, bin_ = instala()
    if cod != 0:
        fallos.append(f"instalacion normal: salio con {cod}. Dijo: {salida.strip()[:200]!r}")
    if not ejecutable(bin_ / "sereno"):
        fallos.append("instalacion normal: `sereno` no quedo ejecutable en $SERENO_BIN")
    if not ejecutable(bin_ / "sereno-cuota"):
        fallos.append("instalacion normal: `sereno-cuota` no quedo ejecutable — es el "
                      "agujero que este fichero existe para tapar")
    if (bin_ / "sereno-cuota").is_file() and \
            (bin_ / "sereno-cuota").read_bytes() != SIDECAR:
        fallos.append("instalacion normal: lo instalado como sidecar no es el sidecar")
    shutil.rmtree(str(bin_.parent), ignore_errors=True)

    # ── el sidecar que no baja AVISA, y no se lleva por delante la instalacion ────
    # Es un accesorio: sin el, `sereno` no ensena la celda de cuota y ya esta. Abortar
    # aqui cambiaria un fallo pequeno por uno grande.
    cod, salida, bin_ = instala(con_sidecar=False)
    if cod != 0:
        fallos.append(f"sidecar ausente: salio con {cod}; tenia que seguir. "
                      f"Dijo: {salida.strip()[:200]!r}")
    if not ejecutable(bin_ / "sereno"):
        fallos.append("sidecar ausente: se llevo por delante la instalacion de `sereno`")
    if "sereno-cuota" not in salida:
        fallos.append(f"sidecar ausente: no lo aviso. Dijo: {salida.strip()[:200]!r}")
    if (bin_ / "sereno-cuota").exists():
        fallos.append("sidecar ausente: dejo un `sereno-cuota` a medias en el PATH, que "
                      "es peor que no dejar ninguno")
    shutil.rmtree(str(bin_.parent), ignore_errors=True)

    # ── CONTROL NEGATIVO: si lo que falta es el programa, si aborta ───────────────
    cod, salida, bin_ = instala(con_programa=False)
    if cod == 0:
        fallos.append("programa ausente: salio con 0; el instalador no baja nada y no "
                      "se entera, asi que los dos casos de arriba no prueban nada")
    if (bin_ / "sereno").exists() and (bin_ / "sereno").stat().st_size == 0:
        fallos.append("programa ausente: dejo un `sereno` vacio en el PATH")
    shutil.rmtree(str(bin_.parent), ignore_errors=True)

    # ── el tap: sin el segundo asset publicado, no se bumpea nada ─────────────────
    releases = pathlib.Path(tempfile.mkdtemp())
    (releases / "v2.0.0").mkdir()
    (releases / "v2.0.0" / "sereno").write_bytes(PROGRAMA)
    sha_p = hashlib.sha256(PROGRAMA).hexdigest()
    sha_c = hashlib.sha256(SIDECAR).hexdigest()

    d, bare = tap(FORMULA.format(sha="a" * 64, sha_cuota="e" * 64))
    try:
        cod, salida = bump(bare, releases, "2.0.0", sha_p, sha_c)
        if cod == 0:
            fallos.append("tap sin el sidecar publicado: salio con 0; dejaria la formula "
                          "apuntando a un 404 dentro del resource")
        if "sereno-cuota" not in salida:
            fallos.append(f"tap sin el sidecar publicado: no dijo cual falta. "
                          f"Dijo: {salida.strip()[:200]!r}")
        fin = subprocess.run(["git", "show", "main:Formula/sereno.rb"], cwd=bare,
                             capture_output=True, text=True, env=ENT).stdout
        if "v2.0.0" in fin:
            fallos.append("tap sin el sidecar publicado: toco el remoto pese a abortar")
    finally:
        shutil.rmtree(str(d), ignore_errors=True)
        shutil.rmtree(str(releases), ignore_errors=True)

    # ── y `release.sh` reparte los dos: sha, subida y traspaso al tap ─────────────
    # Tres hechos leidos del guion, no un "parece que lo hace". Las guardas de ejecucion
    # viven en `tests/test_release_guardas.py`; esto vigila que el sidecar no se caiga
    # de ninguno de los tres sitios donde tiene que aparecer.
    rel = (RAIZ / "release.sh").read_text()
    for trozo, por_que in [
        ("shasum -a 256 sereno sereno-cuota", "el sidecar entra en SHA256SUMS"),
        ('"$TMP/sereno-cuota" "$TMP/SHA256SUMS"', "el sidecar se sube como asset"),
        ('./bump-tap.sh "$VER" "$esperado" "$esperado_cuota"',
         "su sha llega al tap"),
    ]:
        if trozo not in rel:
            fallos.append(f"release.sh ya no cumple que {por_que} (no aparece {trozo!r})")

    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("ok: install.sh deja los dos ficheros ejecutables, un sidecar que no baja se "
          "avisa sin tumbar la instalacion, sin programa si aborta, el tap no se bumpea "
          "con el sidecar sin publicar, y release.sh lo firma, lo sube y pasa su sha")
    return 0


if __name__ == "__main__":
    sys.exit(main())
