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

# ── el sidecar, que estaba documentado y no lo distribuia nadie ─────────────────
# `sereno-cuota` sale en los dos README y en el CHANGELOG desde que existe, pero la
# release subia UN solo asset: quien instalaba por brew y tecleaba lo que acababa de leer
# se llevaba un "command not found". Va detras de las guardas de `sereno` a proposito,
# para que a un commit sin sidecar le conteste una linea propia y no el error de `git
# show`, que no explica nada a quien publica.
git show "${SHA}:sereno-cuota" > "$TMP/sereno-cuota" 2> /dev/null || {
  echo "ABORTA: el commit no trae \`sereno-cuota\`; el sidecar viaja en la release." >&2
  exit 1; }
chmod +x "$TMP/sereno-cuota"

# No tiene `--version`: no lleva numero propio, viaja con el del programa. Asi que la
# guarda equivalente a "dime quien eres" es que python lo acepte — lo mismo que hace la
# formula del tap en el otro extremo del cable, y por el mismo motivo: un asset roto
# cuyo sha256 cuadra se instala sin una queja y no se ve hasta ejecutarlo.
primera_c="$(head -1 "$TMP/sereno-cuota")"
bytes_c="$(wc -c < "$TMP/sereno-cuota" | tr -d ' ')"
compila_c=0
if python3 -m py_compile "$TMP/sereno-cuota" 2> /dev/null; then compila_c=1; fi
echo "sidecar: ${bytes_c}B · primera linea: ${primera_c} · lo compila python: ${compila_c}"

[ "$primera_c" = "#!/usr/bin/env python3" ] || {
  echo "ABORTA: el sidecar no empieza por el shebang; no es el programa." >&2; exit 1; }
[ "$bytes_c" -gt 1000 ] || {
  echo "ABORTA: el sidecar son ${bytes_c}B, que no es \`sereno-cuota\`." >&2; exit 1; }
[ "$compila_c" = 1 ] || {
  echo "ABORTA: python3 no acepta el sidecar extraido; no es un programa." >&2; exit 1; }

( cd "$TMP" && shasum -a 256 sereno sereno-cuota > SHA256SUMS )
# Con dos lineas en el fichero, `awk '{print $1}'` devolveria las dos pegadas y el sha
# que se le pasaria al tap no seria un sha. Se pide por nombre, no por posicion.
esperado="$(awk '$2 == "sereno" {print $1}' "$TMP/SHA256SUMS")"
esperado_cuota="$(awk '$2 == "sereno-cuota" {print $1}' "$TMP/SHA256SUMS")"

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
   --notes-file "$TMP/notas.md" "$TMP/sereno" "$TMP/sereno-cuota" "$TMP/SHA256SUMS"

# ── verificacion: se DESCARGA lo publicado, no se cree lo que se subio ──────────
BAJA="$TMP/baja"; mkdir -p "$BAJA"
gh release download "v$VER" --repo ElRaxy/sereno -D "$BAJA"
real="$(shasum -a 256 "$BAJA/sereno" | awk '{print $1}')"
dice="$(python3 "$BAJA/sereno" --version 2>/dev/null | awk '{print $2}')"
real_c="$(shasum -a 256 "$BAJA/sereno-cuota" 2>/dev/null | awk '{print $1}')"
compila_baja=0
if python3 -m py_compile "$BAJA/sereno-cuota" 2> /dev/null; then compila_baja=1; fi
echo "publicado: sha=$real · dice ser: ${dice:-<nada>}"
echo "publicado: sidecar sha=${real_c:-<nada>} · lo compila python: $compila_baja"
[ "$real" = "$esperado" ] && [ "$dice" = "$VER" ] \
  && [ "$real_c" = "$esperado_cuota" ] && [ "$compila_baja" = 1 ] \
  && echo "OK  v$VER publicada y verificada por descarga (programa y sidecar)" \
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
elif ./bump-tap.sh "$VER" "$esperado" "$esperado_cuota"; then
  :
else
  echo "AVISO: el tap se quedo atras, pero la release v$VER SI esta publicada y es buena." >&2
  echo "       Reintenta solo esa parte:  ./bump-tap.sh $VER $esperado $esperado_cuota" >&2
  exit 1
fi
