#!/usr/bin/env bash
# Publica una release. `./release.sh 1.13.1` desde la raiz del repo.
#
# Existe por un fallo concreto, no por gusto de automatizar. El procedimiento se hacia
# a mano y una de sus lineas era:
#
#     git show $SHA:sereno > /tmp/rel/sereno
#
# En zsh eso NO extrae el fichero. `$SHA:sereno` empieza por `:s`, que es el modificador
# de sustitucion, asi que zsh se come el sufijo y deja el sha pelado: el comando pasa a
# ser `git show <sha>`, que imprime el LOG del commit. Sin error y con exit 0. El asset
# publicado de la v1.13.0 fue eso, un log, y las releases de GitHub son inmutables: no se
# pudo reemplazar. La v1.13.0 se queda con un binario que no arranca.
#
# La trampa solo salta cuando la ruta empieza por `s` —`$V:foo` se expande bien— y el
# fichero de este repo se llama `sereno`. O sea: no se puede recordar, hay que blindarlo.
#
# De ahi las dos cosas que hace este guion y que un procedimiento escrito no hace:
# llaves alrededor de la variable, y GUARDAS sobre lo extraido antes de subir nada.
set -euo pipefail

VER="${1:-}"
[ -n "$VER" ] || { echo "uso: ./release.sh <version>   (p.ej. 1.13.1)" >&2; exit 2; }

cd "$(dirname "$0")"
SHA="$(git rev-parse HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Las llaves NO son cosmetica: sin ellas esto extrae el log en vez del fichero.
git show "${SHA}:sereno" > "$TMP/sereno"
chmod +x "$TMP/sereno"

# ── guardas: hechos, y el veredicto compuesto encima ────────────────────────────
# El `|| true` NO es de adorno. Con `set -euo pipefail`, si lo extraido no es un
# programa de python la tuberia devuelve el fallo de python3, la asignacion falla y el
# script muere AHI: aborta —que es lo correcto— pero sin imprimir una sola linea, asi
# que quien lo lanza no sabe por que. Es justo el caso que estas guardas existen para
# explicar. Se vio escribiendo `tests/test_release_guardas.py`, no antes: la primera
# comprobacion uso un fichero valido, y con uno valido python3 no falla.
primera="$(head -1 "$TMP/sereno")"
bytes="$(wc -c < "$TMP/sereno" | tr -d ' ')"
declarada="$(python3 "$TMP/sereno" --version 2>/dev/null | awk '{print $2}' || true)"
echo "extraido: ${bytes}B · primera linea: ${primera} · dice ser: ${declarada:-<nada>}"

[ "$primera" = "#!/usr/bin/env python3" ] || {
  echo "ABORTA: lo extraido no empieza por el shebang; no es el programa." >&2; exit 1; }
[ "$declarada" = "$VER" ] || {
  echo "ABORTA: el fichero dice ser '${declarada:-<nada>}' y la release es '$VER'." >&2
  echo "        bumpea VERSION en \`sereno\` y commitea antes de publicar." >&2; exit 1; }

( cd "$TMP" && shasum -a 256 sereno > SHA256SUMS )
esperado="$(awk '{print $1}' "$TMP/SHA256SUMS")"

# ── notas: la seccion del CHANGELOG mas el bloque Install de la release anterior ─
python3 - "$VER" "$TMP" <<'PY'
import pathlib, subprocess, sys
ver, tmp = sys.argv[1], pathlib.Path(sys.argv[2])
ch = pathlib.Path("CHANGELOG.md").read_text()
if f"## {ver}" not in ch:
    sys.exit(f"ABORTA: el CHANGELOG no tiene seccion para {ver}")
cuerpo = ch.split(f"## {ver}", 1)[1].split("\n## ", 1)[0].strip()
prev = subprocess.run(["gh", "release", "view", "--repo", "ElRaxy/sereno",
                       "--json", "body", "-q", ".body"],
                      capture_output=True, text=True).stdout
inst = prev.split("### Install", 1)[1] if "### Install" in prev else ""
(tmp / "notas.md").write_text(cuerpo + ("\n\n### Install" + inst if inst else "") + "\n")
PY

git tag -a "v$VER" "$SHA" -m "sereno $VER"
git push origin "v$VER"
gh release create "v$VER" --repo ElRaxy/sereno --title "sereno $VER" \
   --notes-file "$TMP/notas.md" "$TMP/sereno" "$TMP/SHA256SUMS"

# ── verificacion: se DESCARGA lo publicado, no se cree lo que se subio ──────────
BAJA="$TMP/baja"; mkdir -p "$BAJA"
gh release download "v$VER" --repo ElRaxy/sereno -D "$BAJA"
real="$(shasum -a 256 "$BAJA/sereno" | awk '{print $1}')"
dice="$(python3 "$BAJA/sereno" --version 2>/dev/null | awk '{print $2}')"
echo "publicado: sha=$real · dice ser: ${dice:-<nada>}"
[ "$real" = "$esperado" ] && [ "$dice" = "$VER" ] \
  && echo "OK  v$VER publicada y verificada por descarga" \
  || { echo "FALLO: lo publicado no cuadra con lo que se subio." >&2; exit 1; }

# ── el tap de Homebrew, que se bumpea solo ──────────────────────────────────────
# El README decia que no habria formula porque "es una segunda copia del numero de
# version que se queda vieja la semana que se te olvide". El argumento era bueno: lo
# que lo tumba no es cambiar de opinion, es que ese numero ya no lo escriba nadie.
#
# Va DESPUES de la verificacion por descarga a proposito: el tap solo puede apuntar a un
# asset que ya se ha bajado y comprobado. Y si esto falla, la release ya esta publicada y
# sigue siendo buena — de ahi que el mensaje lo diga, en vez de un "FALLO" a secas que
# haga pensar que hay que republicar algo que no se puede republicar.
if [ "${SERENO_SIN_TAP:-}" = "1" ]; then
  echo "tap: saltado (SERENO_SIN_TAP=1)"
elif ./bump-tap.sh "$VER" "$esperado"; then
  :
else
  echo "AVISO: el tap se quedo atras, pero la release v$VER SI esta publicada y es buena." >&2
  echo "       Reintenta solo esa parte:  ./bump-tap.sh $VER $esperado" >&2
  exit 1
fi
