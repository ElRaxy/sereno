#!/usr/bin/env python3
"""La cuota del plan la trae un programa APARTE, y `sereno` solo lee su fichero.

`sereno` no abre conexiones —lo promete el README y lo impide `test_sin_red.py`— asi que
la unica cifra que no esta en el disco, el porcentaje gastado de la ventana de 5 horas del
plan, la pide `sereno-cuota`. Este test sostiene las dos mitades de ese trato:

  · el sidecar habla con un servidor de mentira y con un `security` de mentira. No toca la
    red de verdad ni el llavero de verdad, y el token NO sale por ninguna parte;
  · cuando la lectura falla —te frenan con un 429, el token caduco— NO se ponen los
    porcentajes a cero: se conserva la ultima buena CON su fecha, que es lo que deja ver
    que esta vieja. Un cero se leeria como "no has gastado nada", que es la mentira mas
    facil de contar aqui.

Y la tercera: sin fichero, `sereno --json` saca `null` en los tres campos y no cero.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TMP = tempfile.TemporaryDirectory()
CASA = pathlib.Path(TMP.name)

PAYLOAD_LLAVERO = {"claudeAiOauth": {
    "accessToken": "sk-ant-oat01-EL-TOKEN-QUE-NO-DEBE-SALIR",
    "expiresAt": 4_000_000_000_000, "subscriptionType": "max"}}
SECRETO = PAYLOAD_LLAVERO["claudeAiOauth"]["accessToken"]

# Recortada de la respuesta real que documenta el fixture de Codenotch. `utilization` y
# `percent` son % GASTADO, no restante.
RESPUESTA = {
    "five_hour": {"utilization": 52.0, "resets_at": "2026-09-07T09:50:00+00:00"},
    "seven_day": {"utilization": 17.0, "resets_at": "2026-09-12T17:00:00+00:00"},
    "limits": [
        {"kind": "session", "percent": 34, "resets_at": "2026-09-07T12:00:00+00:00"},
        {"kind": "weekly_all", "percent": 12, "resets_at": "2026-09-12T17:00:00+00:00"},
    ],
}


def security_falso(payload=PAYLOAD_LLAVERO, mdat="20260906185117Z"):
    """Un `security` de pega: los atributos sin `-w`, el secreto con `-w`. El de verdad
    pediria permiso por pantalla, y un test que abre un dialogo no corre en CI."""
    ruta = CASA / ("security-%d" % abs(hash((str(payload), mdat))))
    ruta.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if '-w' in sys.argv[1:]:\n"
        "    sys.stdout.write(json.dumps(%s))\n"
        "else:\n"
        "    sys.stdout.write('    \"mdat\"<timedate>=0x3230  \"%s\\\\000\"\\n')\n"
        % (json.dumps(payload), mdat))
    ruta.chmod(0o755)
    return str(ruta)


class Servidor:
    """Un endpoint local de un solo uso. Cuenta las peticiones: que NO se llame es un
    hecho tan comprobable como que se llame, y hace falta para el token caducado."""

    def __init__(self, estado=200, cuerpo=None):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        self.peticiones = []
        cuerpo = json.dumps(cuerpo if cuerpo is not None else RESPUESTA).encode()
        dueno = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                dueno.peticiones.append(self.headers.get("Authorization") or "")
                self.send_response(estado)
                self.send_header("Content-Type", "application/json")
                if estado == 429:
                    self.send_header("Retry-After", "0")
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d/usage" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def para(self):
        self.srv.shutdown()
        self.srv.server_close()


def carga(nombre):
    ns = {"__name__": "sereno_test_%s" % nombre}
    exec(compile((RAIZ / nombre).read_text(), nombre, "exec"), ns)
    return ns


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    os.environ["SERENO_SECURITY_BIN"] = security_falso()
    cu = carga("sereno-cuota")
    destino = CASA / "cuota.json"

    # ── el reparto de porcentajes: `limits[]` manda y `five_hour` es el respaldo ──
    p = cu["porcentajes"](RESPUESTA)
    f(p["session_pct"] == 34 and p["weekly_pct"] == 12,
      "`limits[]` es la forma nueva y tiene que ganar: %r" % p)
    p2 = cu["porcentajes"]({"five_hour": {"utilization": 52.0},
                            "seven_day": {"utilization": 17.0}})
    f(p2["session_pct"] == 52 and p2["weekly_pct"] == 17,
      "sin `limits[]` hay que caer a five_hour/seven_day: %r" % p2)
    vacio = cu["porcentajes"]({})
    f(vacio["session_pct"] is None,
      "una respuesta sin datos da %r y tiene que dar None, no 0"
      % vacio["session_pct"])

    # ── una pasada buena: hechos en el fichero, y ni rastro del token ────────────
    srv = Servidor()
    cu["SECURITY"] = os.environ["SERENO_SECURITY_BIN"]
    h, _e = cu["una_pasada"](destino=destino, url=srv.url)
    srv.para()
    f(len(srv.peticiones) == 1, "no se llamo al endpoint una sola vez: %d"
      % len(srv.peticiones))
    f(srv.peticiones and srv.peticiones[0] == "Bearer " + SECRETO,
      "la cabecera Authorization no lleva el token del llavero")
    escrito = json.loads(destino.read_text())
    f(escrito["session_pct"] == 34 and escrito["weekly_pct"] == 12,
      "el fichero no trae los porcentajes: %r" % escrito)
    f(escrito["plan"] == "max", "el plan sale del llavero y no llego: %r"
      % escrito.get("plan"))
    f(escrito["http_status"] == 200 and escrito["error"] is None,
      "una lectura buena no puede traer error: %r" % escrito)
    f(escrito["resets_at"] == "2026-09-07T12:00:00+00:00",
      "el `resets_at` que vale es el de la ventana de 5h: %r"
      % escrito.get("resets_at"))
    f(SECRETO not in destino.read_text(), "EL TOKEN ESTA ESCRITO EN EL FICHERO")
    f(SECRETO not in cu["linea"](h), "el token sale por la salida estandar")
    buena = escrito["fetched_at"]

    # ── y una mala: te frenan, y la ultima buena se conserva CON su edad ─────────
    srv2 = Servidor(estado=429, cuerpo={})
    h2, espera = cu["una_pasada"](destino=destino, url=srv2.url)
    srv2.para()
    tras = json.loads(destino.read_text())
    f(tras["http_status"] == 429, "el 429 no queda anotado: %r" % tras.get("http_status"))
    f(tras["error"], "un 429 tiene que dejar dicho que fallo")
    f(tras["session_pct"] == 34 and tras["weekly_pct"] == 12,
      "un 429 se llevo por delante la ultima lectura buena: %r" % tras)
    f(tras["fetched_at"] == buena,
      "la fecha tiene que seguir siendo la de la lectura BUENA, para que se vea vieja")

    # ── token caducado: no se refresca, no se llama, y se dice ───────────────────
    caducado = dict(PAYLOAD_LLAVERO)
    caducado["claudeAiOauth"] = dict(PAYLOAD_LLAVERO["claudeAiOauth"], expiresAt=1000)
    cu["SECURITY"] = security_falso(caducado, "20260101000000Z")
    srv3 = Servidor()
    h3, _e3 = cu["una_pasada"](destino=destino, url=srv3.url)
    srv3.para()
    f(srv3.peticiones == [],
      "con el token caducado NO se puede llamar al endpoint, y se llamo %d vez(ces)"
      % len(srv3.peticiones))
    fin = json.loads(destino.read_text())
    f(fin["error"] == "token caducado", "no se dice que el token caduco: %r"
      % fin.get("error"))
    f(fin["session_pct"] == 34, "tambien aqui se conserva la ultima buena: %r" % fin)

    # ── los atributos del llavero se leen sin pedir el secreto ───────────────────
    cu["SECURITY"] = os.environ["SERENO_SECURITY_BIN"]
    f(cu["mdat_del_llavero"]() == "20260906185117Z",
      "no se saca el `mdat` de los atributos: %r" % cu["mdat_del_llavero"]())

    # ── y del otro lado: lo que `sereno` hace con ese fichero ────────────────────
    se = carga("sereno")
    f(se["nivel_cuota"]({"session_pct": None}) == 0,
      "sin lectura no se avisa: `None` no es 0 %")
    f(se["nivel_cuota"]({"session_pct": 79}) == 0, "el 79 % no cruza el primer escalon")
    f(se["nivel_cuota"]({"session_pct": 80}) == 80, "el 80 % si lo cruza")
    f(se["nivel_cuota"]({"session_pct": 97}) == 95, "manda el escalon mas alto pasado")
    f(se["cuota_nueva"](0, {"session_pct": 84}) == 80, "el cruce del 80 % es noticia")
    f(se["cuota_nueva"](80, {"session_pct": 84}) == 0,
      "dentro del mismo escalon NO se repite el aviso")
    f(se["cuota_nueva"](80, {"session_pct": 96}) == 95, "subir de escalon si es noticia")
    f(se["cuota_nueva"](95, {"session_pct": 12}) == 0,
      "al resetearse la ventana el nivel cae solo, sin avisar de la bajada")
    f(se["texto_cuota"]({}) == "", "sin fichero, la cabecera no gasta ni una columna")
    fresco = se["texto_cuota"]({"session_pct": 34, "weekly_pct": 12,
                                "fetched_at": 1000}, ahora=1000)
    f("34" in fresco and "12" in fresco, "la celda no dice los dos porcentajes: %r"
      % fresco)
    viejo = se["texto_cuota"]({"session_pct": 34, "fetched_at": 0}, ahora=3 * 3600)
    f(viejo != fresco and "3h" in viejo,
      "un dato de hace tres horas se pinta igual de fresco que uno de ahora: %r" % viejo)

    # ── y el contrato de --json, corriendo el programa de verdad ─────────────────
    entorno = dict(os.environ, SERENO_DEMO="1", SERENO_DIR=str(CASA / "vacio"))
    sin = json.loads(subprocess.run([sys.executable, str(RAIZ / "sereno"), "--json"],
                                    capture_output=True, text=True, env=entorno).stdout)
    f(sin["quota_session_pct"] is None and sin["quota_weekly_pct"] is None
      and sin["quota_fetched_at"] is None,
      "sin fichero los tres campos tienen que ser null y son %r"
      % {k: v for k, v in sin.items() if k.startswith("quota")})

    con_dir = CASA / "con"
    con_dir.mkdir(exist_ok=True)
    (con_dir / "cuota.json").write_text(json.dumps(
        {"session_pct": 34, "weekly_pct": 12, "fetched_at": 1788700000,
         "resets_at": None, "plan": "max", "http_status": 200, "error": None}))
    entorno["SERENO_DIR"] = str(con_dir)
    con = json.loads(subprocess.run([sys.executable, str(RAIZ / "sereno"), "--json"],
                                    capture_output=True, text=True, env=entorno).stdout)
    f(con["quota_session_pct"] == 34 and con["quota_weekly_pct"] == 12
      and con["quota_fetched_at"] == 1788700000,
      "con fichero, --json tiene que publicar los tres campos: %r"
      % {k: v for k, v in con.items() if k.startswith("quota")})
    f(con["schema"] == 1,
      "anadir campos al sobre NO sube el esquema, y aqui dice %r" % con.get("schema"))

    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos else
          "ok: el sidecar escribe hechos y no el token, un fallo conserva la ultima "
          "lectura buena con su edad, y sin fichero --json dice null")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
