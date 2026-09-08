#!/bin/sh
# Instala sereno en ~/.local/bin (o en $SERENO_BIN). El programa y su sidecar.
set -eu

REPO="${SERENO_REPO:-ElRaxy/sereno}"
BIN="${SERENO_BIN:-$HOME/.local/bin}"
# De donde se bajan los dos ficheros. Se puede apuntar a otro sitio (SERENO_RAW_BASE)
# para probar el instalador entero sin salir de la maquina: `tests/test_distribucion_cuota.py`
# le pone un `file://` delante y comprueba lo que deja en el disco.
BASE="${SERENO_RAW_BASE:-https://raw.githubusercontent.com/$REPO/main}"

command -v python3 >/dev/null 2>&1 || {
  echo "sereno needs python3 (3.8 or newer). Install it and run this again." >&2
  exit 1
}
# 3.8 es el suelo de verdad: por debajo no hay f-strings con `=` ni walrus, y el
# script los usa. Comprobarlo aqui evita un traceback en la primera ejecucion.
python3 - <<'PY' || { echo "sereno needs python3 >= 3.8" >&2; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)
PY

baja() {   # <url> <destino>
  if command -v curl >/dev/null 2>&1; then
    curl -fsSLo "$2" "$1"
  else
    wget -qO "$2" "$1"
  fi
}

mkdir -p "$BIN"
baja "$BASE/sereno" "$BIN/sereno"
chmod +x "$BIN/sereno"
echo "sereno -> $BIN/sereno"

# El sidecar de la cuota. Estuvo documentado en los dos README antes que instalado por
# nadie: quien leia "ejecuta sereno-cuota" recibia un `command not found`.
#
# Si no baja se AVISA y se sigue, no se aborta. `sereno` funciona sin el —sin fichero de
# cuota no hay celda en la cabecera y ya esta— y tumbar la instalacion del programa por
# un accesorio seria cambiar un fallo pequeno por uno grande. Con `-f`, curl no escribe
# el cuerpo de un error pero si deja el fichero creado y vacio: de ahi el `rm`.
if baja "$BASE/sereno-cuota" "$BIN/sereno-cuota"; then
  chmod +x "$BIN/sereno-cuota"
  echo "sereno-cuota -> $BIN/sereno-cuota"
else
  rm -f "$BIN/sereno-cuota"
  echo "sereno-cuota: no se pudo bajar; sereno queda instalado y funciona sin el." >&2
fi
case ":$PATH:" in
  *":$BIN:"*) echo "Run: sereno" ;;
  *) echo "$BIN is not on your PATH. Add this to your shell rc:"
     echo "    export PATH=\"$BIN:\$PATH\"" ;;
esac
