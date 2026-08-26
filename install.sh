#!/bin/sh
# Instala sereno en ~/.local/bin (o en $SERENO_BIN). Un fichero y nada mas.
set -eu

REPO="${SERENO_REPO:-ElRaxy/sereno}"
BIN="${SERENO_BIN:-$HOME/.local/bin}"
URL="https://raw.githubusercontent.com/$REPO/main/sereno"

command -v python3 >/dev/null 2>&1 || {
  echo "sereno needs python3 (3.8 or newer). Install it and run this again." >&2
  exit 1
}
# 3.8 es el suelo de verdad: por debajo no hay f-strings con `=` ni walrus, y el
# script los usa. Comprobarlo aqui evita un traceback en la primera ejecucion.
python3 - <<'PY' || { echo "sereno needs python3 >= 3.8" >&2; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)
PY

mkdir -p "$BIN"
if command -v curl >/dev/null 2>&1; then
  curl -fsSLo "$BIN/sereno" "$URL"
else
  wget -qO "$BIN/sereno" "$URL"
fi
chmod +x "$BIN/sereno"

echo "sereno -> $BIN/sereno"
case ":$PATH:" in
  *":$BIN:"*) echo "Run: sereno" ;;
  *) echo "$BIN is not on your PATH. Add this to your shell rc:"
     echo "    export PATH=\"$BIN:\$PATH\"" ;;
esac
