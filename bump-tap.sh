#!/usr/bin/env bash
# Apunta la formula de Homebrew a una version de sereno.
# `./bump-tap.sh 1.13.1 <sha256 de sereno> <sha256 de sereno-cuota>`.
#
# Son DOS sha porque la release son dos assets: el programa y `sereno-cuota`, el sidecar
# que consulta la cuota del plan. La formula lo trae como `resource`, asi que dentro
# lleva una segunda url y un segundo sha256 que tambien se quedan viejos.
#
# Lo llama `release.sh` cuando ya ha verificado la release DESCARGANDOLA, y por eso
# recibe el sha256 en vez de calcularlo: recalcularlo aqui seria darle otra oportunidad
# de salir distinto. Tambien se puede lanzar a mano, que es lo que hace falta el dia que
# la release salga bien y el push al tap no.
#
# Es un guion aparte y no un bloque dentro de `release.sh` por una razon concreta: alli
# viviria detras de `gh release create`, o sea que probarlo exigiria publicar una release
# de verdad. Aqui se prueba entero contra un remoto de mentira —`tests/test_bump_tap.py`
# lo hace en cuatro casos— y las guardas de abajo dejan de ser una promesa.
set -euo pipefail

VER="${1:-}"; SHA="${2:-}"; SHA_CUOTA="${3:-}"
[ -n "$VER" ] && [ -n "$SHA" ] && [ -n "$SHA_CUOTA" ] || {
  echo "uso: ./bump-tap.sh <version> <sha256 sereno> <sha256 sereno-cuota>" >&2
  echo "     (p.ej. 1.13.1 61d80f7... 9ab3c1e...)" >&2; exit 2; }

# 64 hexadecimales o nada, los dos. Un sha256 a medias no se detecta luego: Homebrew se
# limita a decir que el fichero no cuadra, y desde ahi parece que el roto es el asset.
for s in "$SHA" "$SHA_CUOTA"; do
  case "$s" in
    *[!0-9a-f]* | "") echo "ABORTA: '$s' no es un sha256 (64 hex en minusculas)." >&2; exit 2 ;;
  esac
  [ "${#s}" -eq 64 ] || {
    echo "ABORTA: el sha256 tiene ${#s} caracteres y tiene que tener 64." >&2; exit 2; }
done

REMOTO="${SERENO_TAP_REMOTO:-https://github.com/ElRaxy/homebrew-tap.git}"
BASE="${SERENO_ASSET_BASE:-https://github.com/ElRaxy/sereno/releases/download}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ── que el asset EXISTA y sea ese sha, no solo que el sha tenga forma de sha ─────
# Hasta aqui este guion validaba la FORMA (64 hex, una url y un sha256 unicos) y nunca
# el HECHO. Lo unico que impedia apuntar el tap a una version inexistente era el orden
# dentro de `release.sh`, que lo llama detras de la verificacion por descarga — y este
# guion invita por escrito a lanzarlo a mano, que es donde esa red no existe. Se probo:
# con una version inventada salia con 0 y dejaba la formula apuntando a un 404, y el
# unico que se enteraba era el cron semanal del tap, hasta siete dias despues.
command -v curl > /dev/null || {
  echo "ABORTA: hace falta curl para comprobar que el asset existe." >&2; exit 1; }
# Los dos assets, con la misma vara: existir y ser ESE sha. Comprobar solo el programa
# dejaria la mitad de la formula apuntando a un 404 exactamente igual que antes.
comprueba_asset() {  # <nombre del asset> <sha esperado>
  nombre="$1"; quiero="$2"
  url="$BASE/v$VER/$nombre"
  curl -fsSL "$url" -o "$TMP/$nombre" || {
    echo "ABORTA: no se pudo descargar $url — esa version no esta publicada." >&2; return 1; }
  hay="$(shasum -a 256 "$TMP/$nombre" | awk '{print $1}')"
  echo "asset $nombre: $(wc -c < "$TMP/$nombre" | tr -d ' ')B · sha publicado: ${hay:0:12}… · pedido: ${quiero:0:12}…"
  [ "$hay" = "$quiero" ] || {
    echo "ABORTA: el asset $nombre publicado tiene sha $hay y se pidio escribir $quiero." >&2
    return 1; }
}
comprueba_asset sereno "$SHA"
comprueba_asset sereno-cuota "$SHA_CUOTA"

git clone --quiet --depth 1 "$REMOTO" "$TMP/tap" || {
  echo "ABORTA: no se pudo clonar el tap ($REMOTO)." >&2; exit 1; }

F="$TMP/tap/Formula/sereno.rb"
[ -f "$F" ] || { echo "ABORTA: el tap clonado no tiene Formula/sereno.rb." >&2; exit 1; }

# Una stanza `version` explicita es una TERCERA copia del numero que este guion no
# toca: Homebrew usaria la vieja mientras descarga el asset de la nueva, la guarda del
# `install` haria `odie` y `brew install` quedaria roto para todo el mundo. Se reprodujo
# empujando una formula asi. Hoy la formula no la tiene, pero eso no es una garantia.
grep -qE '^\s*version\s+"' "$F" && {
  echo "ABORTA: la formula trae una stanza \`version\` explicita, que este guion no bumpea." >&2
  echo "        Quitala de la formula o bumpeala a mano; asi quedaria descuadrada." >&2; exit 1; }

python3 - "$F" "$VER" "$SHA" "$SHA_CUOTA" <<'RB'
import pathlib, re, sys
f, ver, sha, sha_cuota = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
t = f.read_text()

# El bloque `resource "sereno-cuota"` se saca APARTE antes de tocar nada. Dentro y fuera
# hay una url y un sha256 cada uno, y el patron del sha256 no sabe distinguirlos: sobre
# el fichero entero saldrian dos sustituciones, la guarda de abajo lo daria por ambiguo
# y este guion no bumpearia nunca. Separarlos deja las dos mitades con una de cada.
m = re.search(r'\n  resource "sereno-cuota" do\n.*?\n  end\n', t, re.S)
if not m:
    sys.exit('ABORTA: la formula no trae el bloque `resource "sereno-cuota"`. El sidecar '
             "no se instalaria y este guion no se lo inventa: anadelo a mano una vez.")
pre, bloque, post = t[:m.start()], m.group(0), t[m.end():]


def bump(txt, nombre, numero, hash_):
    txt, n_url = re.subn(r'(releases/download/v)[^/]+(/%s")' % nombre,
                         rf'\g<1>{numero}\g<2>', txt)
    txt, n_sha = re.subn(r'(sha256 ")[0-9a-f]{64}(")', rf'\g<1>{hash_}\g<2>', txt)
    return txt, n_url, n_sha


# `/sereno"` no casa con `/sereno-cuota"`: la comilla va pegada al nombre.
pre, u1, s1 = bump(pre, "sereno", ver, sha)
post, u2, s2 = bump(post, "sereno", ver, sha)
bloque, u3, s3 = bump(bloque, "sereno-cuota", ver, sha_cuota)
n_url, n_sha = u1 + u2, s1 + s2

# Ni cero ni dos, en las dos mitades: si la formula no tiene exactamente una de cada,
# la que se editaria no es la que se cree. Se para antes de escribir, no despues.
if n_url != 1 or n_sha != 1:
    sys.exit(f"ABORTA: la formula no tiene una url y un sha256 unicos "
             f"(url={n_url}, sha256={n_sha}); no se toca a ciegas.")
if u3 != 1 or s3 != 1:
    sys.exit(f"ABORTA: el bloque `resource \"sereno-cuota\"` no tiene una url y un "
             f"sha256 unicos (url={u3}, sha256={s3}); no se toca a ciegas.")
f.write_text(pre + bloque + post)
RB

# Guardas sobre lo escrito, no sobre lo que se creia escribir. Los dos hechos por
# separado y el veredicto compuesto encima, como en `release.sh`.
url_ok=0; sha_ok=0; url_c_ok=0; sha_c_ok=0
grep -q "releases/download/v${VER}/sereno\"" "$F" && url_ok=1
grep -q "sha256 \"${SHA}\"" "$F" && sha_ok=1
grep -q "releases/download/v${VER}/sereno-cuota\"" "$F" && url_c_ok=1
grep -q "sha256 \"${SHA_CUOTA}\"" "$F" && sha_c_ok=1
echo "tap: url v$VER: $url_ok · sha256 al dia: $sha_ok · sidecar: $url_c_ok/$sha_c_ok"
[ "$url_ok" = 1 ] && [ "$sha_ok" = 1 ] && [ "$url_c_ok" = 1 ] && [ "$sha_c_ok" = 1 ] || {
  echo "ABORTA: la formula editada no apunta a v$VER. No se empuja nada." >&2; exit 1; }

if git -C "$TMP/tap" diff --quiet; then
  echo "OK  el tap ya estaba en v$VER, nada que empujar"
  exit 0
fi

git -C "$TMP/tap" commit --quiet -am "chore(sereno): v$VER"
git -C "$TMP/tap" push --quiet origin HEAD:main

# Se relee del remoto, no del clon: lo que importa es lo que otro se va a bajar.
publicado="$(git -C "$TMP/tap" ls-remote origin main | awk '{print $1}')"
mio="$(git -C "$TMP/tap" rev-parse HEAD)"
[ "$publicado" = "$mio" ] \
  && echo "OK  tap en v$VER ($mio)" \
  || { echo "FALLO: el push no llego; el remoto sigue en $publicado." >&2; exit 1; }
