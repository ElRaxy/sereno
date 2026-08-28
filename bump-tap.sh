#!/usr/bin/env bash
# Apunta la formula de Homebrew a una version de sereno. `./bump-tap.sh 1.13.1 <sha256>`.
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

VER="${1:-}"; SHA="${2:-}"
[ -n "$VER" ] && [ -n "$SHA" ] || {
  echo "uso: ./bump-tap.sh <version> <sha256>   (p.ej. 1.13.1 61d80f7...)" >&2; exit 2; }

# 64 hexadecimales o nada. Un sha256 a medias no se detecta luego: Homebrew se limita a
# decir que el fichero no cuadra, y desde ahi parece que el roto es el asset.
case "$SHA" in
  *[!0-9a-f]* | "") echo "ABORTA: '$SHA' no es un sha256 (64 hex en minusculas)." >&2; exit 2 ;;
esac
[ "${#SHA}" -eq 64 ] || {
  echo "ABORTA: el sha256 tiene ${#SHA} caracteres y tiene que tener 64." >&2; exit 2; }

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
URL="$BASE/v$VER/sereno"
curl -fsSL "$URL" -o "$TMP/asset" || {
  echo "ABORTA: no se pudo descargar $URL — esa version no esta publicada." >&2; exit 1; }
real="$(shasum -a 256 "$TMP/asset" | awk '{print $1}')"
echo "asset: $(wc -c < "$TMP/asset" | tr -d ' ')B · sha publicado: ${real:0:12}… · pedido: ${SHA:0:12}…"
[ "$real" = "$SHA" ] || {
  echo "ABORTA: el asset publicado tiene sha $real y se pidio escribir $SHA." >&2; exit 1; }

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

python3 - "$F" "$VER" "$SHA" <<'RB'
import pathlib, re, sys
f, ver, sha = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t = f.read_text()
t, n_url = re.subn(r'(releases/download/v)[^/]+(/sereno")', rf'\g<1>{ver}\g<2>', t)
t, n_sha = re.subn(r'(sha256 ")[0-9a-f]{64}(")', rf'\g<1>{sha}\g<2>', t)
# Ni cero ni dos: si la formula no tiene exactamente una de cada, la que se editaria
# no es la que se cree. Se para antes de escribir, no despues.
if n_url != 1 or n_sha != 1:
    sys.exit(f"ABORTA: la formula no tiene una url y un sha256 unicos "
             f"(url={n_url}, sha256={n_sha}); no se toca a ciegas.")
f.write_text(t)
RB

# Guardas sobre lo escrito, no sobre lo que se creia escribir. Los dos hechos por
# separado y el veredicto compuesto encima, como en `release.sh`.
url_ok=0; sha_ok=0
grep -q "releases/download/v${VER}/sereno\"" "$F" && url_ok=1
grep -q "sha256 \"${SHA}\"" "$F" && sha_ok=1
echo "tap: url v$VER: $url_ok · sha256 al dia: $sha_ok"
[ "$url_ok" = 1 ] && [ "$sha_ok" = 1 ] || {
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
