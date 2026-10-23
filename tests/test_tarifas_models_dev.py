#!/usr/bin/env python3
"""Tarifas locales, prioridad y origen; solo la actualizacion explicita abre la red."""
import ast, contextlib, datetime, io, json, os, pathlib, sys, tempfile, urllib.request
from unittest.mock import patch

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text(encoding="utf-8")
CUOTA = (RAIZ / "sereno-cuota").read_text(encoding="utf-8")
FECHA = "2026-10-23T12:34:56+00:00"
USO = {"in": 1_000_000, "out": 200_000, "cw": 400_000, "cr": 3_000_000,
       "usd": None, "turnos": 1, "compacta": 0, "pico": 0, "activo": 0,
       "completo": True}


@contextlib.contextmanager
def entorno():
    with tempfile.TemporaryDirectory() as tmp, \
            patch.dict(os.environ, {"HOME": tmp, "XDG_CACHE_HOME": tmp + "/cache",
                                    "SERENO_DEMO": "", "CLAUDE_DEMO": "",
                                    "SERENO_DIR": tmp + "/cuota", "SERENO_LANG": "es",
                                    "SERENO_TARIFAS_URL": ""}), \
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("red inesperada")) as red:
        ns = {"__name__": "sereno_test"}
        exec(compile(FUENTE, "sereno", "exec"), ns)
        assert not red.called
        ns["LANG_UI"] = "es"
        yield ns
        assert not red.called


def guarda(ns, modelos=None, **cambios):
    datos = {"fuente": "models.dev", "fecha": FECHA,
             "modelos": modelos if modelos is not None else {"claude-opus-5": [2, 3, 4, 5]}}
    datos.update(cambios)
    ruta = ns["_ruta_tarifas"]()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def captura(funcion, *args, **kwargs):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = funcion(*args, **kwargs)
    return codigo, salida.getvalue()


def invoca(ns, *args):
    with patch.object(sys, "argv", ["sereno"] + list(args)), \
            patch.dict(os.environ, {"SERENO_TMUX_AUTO": "", "CLAUDE_TMUX_AUTO": ""}):
        return captura(ns["main"])


def carga_cuota():
    ns = {"__name__": "cuota_test"}
    exec(compile(CUOTA, "sereno-cuota", "exec"), ns)
    return ns


def invoca_tarifas():
    cu = carga_cuota()
    with patch.dict(cu, {"credencial": lambda: sys.exit("llavero inesperado"),
                         "una_pasada": lambda: sys.exit("cuota inesperada"),
                         "bucle": lambda: sys.exit("bucle inesperado")}):
        return captura(cu["main"], ["--tarifas"])


def descarga(ns, datos):
    contenido = datos if isinstance(datos, bytes) else json.dumps(datos).encode()
    respuesta = io.BytesIO(contenido)
    with patch.object(respuesta, "read", wraps=respuesta.read) as lectura, \
            patch.object(urllib.request, "urlopen", return_value=respuesta) as red:
        codigo, salida = invoca_tarifas()
        red.assert_called_once_with(os.environ.get("SERENO_TARIFAS_URL")
                                    or "https://models.dev/api.json", timeout=15)
        lectura.assert_called_once_with(20 * 1024 * 1024)
    return codigo, salida


def catalogo():
    return {"anthropic": {"models": {
        "US.ANTHROPIC.CLAUDE-NUEVO-20261023[1M]": {
            "cost": {"input": 2, "output": 3, "cache_write": 4, "cache_read": 5}},
        "incompleto": {"cost": {"input": 1, "output": 2}},
        "booleano": {"cost": {"input": True, "output": 2, "cache_write": 3, "cache_read": 4}},
        "infinito": {"cost": {"input": float("inf"), "output": 2, "cache_write": 3, "cache_read": 4}},
        "sin-coste": None}}, "otro": {"models": {"ajeno": {"cost": {
            "input": 1, "output": 2, "cache_write": 3, "cache_read": 4}}}}}


def test_cache_prioridad():
    with entorno() as ns:
        guarda(ns, {"claude-nuevo": [2, 3, 4, 5], "claude-opus-5": [2, 3, 4, 5]})
        for modelo in ("claude-nuevo", "claude-opus-5", "anthropic.claude-nuevo-20261023[1m]"):
            assert ns["coste_estimado"](USO, modelo) == 19.2
        assert ns["coste_estimado"](USO, "claude-haiku-4-5") == 2.8
        assert ns["coste_estimado"](USO, "desconocido") is None
        assert ns["coste_estimado"](None, "claude-nuevo") is None


def test_formas_invalidas():
    malos = [None, [], {}, {"fuente": "otra", "fecha": FECHA, "modelos": {}},
             {"fuente": "models.dev", "fecha": FECHA, "modelos": []}]
    for fecha in (None, True, "no-fecha", "2026-10-23\n12:34:56"):
        malos.append({"fuente": "models.dev", "fecha": fecha,
                      "modelos": {"claude-opus-5": [2, 3, 4, 5]}})
    for precios in ([True, 2, 3, 4], [1, "2", 3, 4], [1, None, 3, 4], [1, 2, 3],
                    [1, 2, 3, 4, 5], [float("nan"), 2, 3, 4], [float("inf"), 2, 3, 4],
                    {"in": 1}, None):
        malos.append({"fuente": "models.dev", "fecha": FECHA,
                      "modelos": {"claude-opus-5": precios}})
    for datos in malos + ["{", b"\xff"]:
        with entorno() as ns:
            ruta = guarda(ns)
            ruta.write_bytes(datos if isinstance(datos, bytes) else
                             (datos if isinstance(datos, str) else json.dumps(datos)).encode())
            assert ns["_tarifas_cache"]() is None, datos
            assert ns["coste_estimado"](USO, "claude-opus-5") == 14.0


def test_una_lectura_y_rutas():
    for existe in (False, True):
        with entorno() as ns:
            ruta = guarda(ns) if existe else ns["_ruta_tarifas"]()
            assert ruta == pathlib.Path(os.environ["XDG_CACHE_HOME"]) / "sereno/tarifas.json"
            abrir = pathlib.Path.open
            with patch.object(pathlib.Path, "open", autospec=True, side_effect=abrir) as lecturas:
                primero = ns["_tarifas_cache"]()
                assert ns["_tarifas_cache"]() is primero
                ns["coste_estimado"](USO, "claude-opus-5")
                assert lecturas.call_count == 1
            guarda(ns, {"claude-opus-5": [100, 200, 300, 400]})
            assert ns["_tarifas_cache"]() is primero
    with entorno() as ns, patch.dict(os.environ, {"XDG_CACHE_HOME": ""}):
        assert ns["_ruta_tarifas"]() == pathlib.Path(os.environ["HOME"]) / ".cache/sereno/tarifas.json"
        with patch.object(pathlib.Path, "open", side_effect=PermissionError("ilegible")) as lecturas:
            assert ns["coste_estimado"](USO, "claude-opus-5") == 14.0
            assert ns["_tarifas_cache"]() is None
            assert lecturas.call_count == 1


def test_actualizacion():
    with entorno() as ns:
        assert ns["_tarifas_cache"]() is None
        codigo, salida = descarga(ns, catalogo())
        ruta = ns["_ruta_tarifas"]()
        assert codigo == 0 and len(salida.splitlines()) == 1
        assert "1 modelos" in salida and str(ruta) in salida
        datos = json.loads(ruta.read_text())
        assert set(datos) == {"fuente", "fecha", "modelos"}
        assert datos["fuente"] == "models.dev"
        assert datetime.datetime.fromisoformat(datos["fecha"]).tzinfo is not None
        assert datos["modelos"] == {"claude-nuevo": [2, 3, 4, 5]}
        assert ns["_tarifas_cache"]() is None
        lector = {"__name__": "sereno_lector"}
        exec(compile(FUENTE, "sereno", "exec"), lector)
        assert lector["coste_estimado"](USO, "claude-nuevo") == 19.2
        assert list(ruta.parent.iterdir()) == [ruta]


def test_descargas_fallidas():
    for previa in (False, True):
        with entorno() as ns:
            ruta = guarda(ns) if previa else ns["_ruta_tarifas"]()
            anterior = ruta.read_bytes() if previa else None
            with patch.object(urllib.request, "urlopen", side_effect=OSError("sin red\nsegunda linea")):
                codigo, salida = invoca_tarifas()
            assert codigo == 1 and len(salida.splitlines()) == 1 and "sin red" in salida
            assert (ruta.read_bytes() if ruta.exists() else None) == anterior
            assert not ruta.parent.exists() or list(ruta.parent.iterdir()) == [ruta]
    for datos in (b"{", b"\xff", [], {}, {"anthropic": {"models": []}},
                  {"anthropic": {"models": {"sin-coste": {}}}},
                  b" " * (20 * 1024 * 1024 + 8)):
        with entorno() as ns:
            codigo, salida = descarga(ns, datos)
            assert codigo == 1 and len(salida.splitlines()) == 1
            assert not ns["_ruta_tarifas"]().parent.exists()


def test_escritura_atomica():
    for falla in ("replace", "dump"):
        with entorno() as ns:
            ruta = guarda(ns)
            anterior = ruta.read_bytes()

            def rompe_dump(datos, fichero, **kwargs):
                fichero.write("{parcial")
                raise OSError("disco lleno")

            def rompe_replace(origen, destino):
                assert pathlib.Path(origen).parent == ruta.parent
                assert pathlib.Path(destino) == ruta
                assert json.loads(pathlib.Path(origen).read_text())["fuente"] == "models.dev"
                raise OSError("reemplazo fallido")

            modulo, nombre, funcion = ((ns["os"], "replace", rompe_replace) if falla == "replace"
                                       else (ns["json"], "dump", rompe_dump))
            with patch.object(modulo, nombre, side_effect=funcion):
                codigo, salida = descarga(ns, catalogo())
            assert codigo == 1 and len(salida.splitlines()) == 1
            assert ruta.read_bytes() == anterior
            assert list(ruta.parent.iterdir()) == [ruta]


def test_origen_texto_json():
    for cache in (False, True):
        with entorno() as ns:
            if cache:
                guarda(ns)
            for idioma, esperado in (("es", "tarifas: models.dev, " + FECHA if cache
                                      else "tarifas: tabla interna"),
                                     ("en", "rates: models.dev, " + FECHA if cache
                                      else "rates: internal table")):
                ns["LANG_UI"] = idioma
                ns["USO"] = True
                for filas in ([], ns["sesiones_demo"]()):
                    assert captura(ns["print_live"], filas)[1].splitlines()[-1] == esperado
                    with patch.dict(ns, {"lee_cuota": lambda: {}}):
                        datos = json.loads(captura(ns["print_json"], filas)[1])
                    assert datos["schema"] == 1
                    assert datos["tarifas_fuente"] == ("models.dev" if cache else "tabla_interna")
                    assert all("tarifas_fuente" not in f for f in datos["sessions"])
                codigo, texto = invoca(ns, "--demo", "--usage", "--list")
                assert codigo == 0 and texto.splitlines()[-1] == esperado
                codigo, texto = invoca(ns, "--demo", "--usage", "--json")
                assert codigo == 0 and json.loads(texto)["tarifas_fuente"] == datos["tarifas_fuente"]
            ns["USO"] = False
            assert captura(ns["print_live"], [])[1] == ""
            with patch.dict(ns, {"lee_cuota": lambda: {}}):
                assert "tarifas_fuente" not in json.loads(captura(ns["print_json"], [])[1])


def test_origen_main_vacio_y_pie():
    with entorno() as ns:
        with patch.dict(ns, {"live_sessions": lambda **kw: [], "sesiones_de_disco": lambda **kw: [],
                             "orphans": lambda: [], "nada_que_ensenar": lambda: "vacio"}):
            for flags in (("--usage",), ("--usage", "--list")):
                codigo, texto = invoca(ns, *flags)
                assert codigo == 0 and texto.splitlines()[-1] == "tarifas: tabla interna"
        filas = ns["sesiones_demo"]()[:1]
        with patch.dict(ns, {"live_sessions": lambda **kw: filas}), \
                patch.object(sys.stdin, "isatty", return_value=False):
            codigo, texto = invoca(ns, "--usage")
            assert codigo == 0 and texto.splitlines()[-1] == "tarifas: tabla interna"
            assert texto.count("tarifas:") == 1


def test_origen_historial_y_huerfanas():
    casos = ("historial_sin_tty", "historial_selector_cancelado", "huerfana_reanudable",
             "huerfana_sin_transcript", "huerfana_selector_cancelado")
    for cache in (False, True):
        for caso in casos:
            with entorno() as ns:
                if cache:
                    guarda(ns)
                esperado = "tarifas: models.dev, " + FECHA if cache else "tarifas: tabla interna"
                item = {"id": "fixture"}
                if caso != "huerfana_sin_transcript":
                    item["_transcript"] = ns["HOME"] / "fixture.jsonl"
                historial = caso.startswith("historial")
                parches = {"live_sessions": lambda **kw: [],
                           "sesiones_de_disco": lambda **kw: [{"name": "fixture"}] if historial else [],
                           "orphans": lambda: [] if historial else [item],
                           "describe": lambda e: "fixture huerfana",
                           "archive": lambda *args: None,
                           "fila_de_huerfana": lambda e: {"name": "fixture"},
                           "pick_ui": lambda *args, **kwargs: None}
                with patch.dict(ns, parches), patch.object(sys.stdin, "isatty",
                        return_value=caso.endswith("selector_cancelado")):
                    sin_codigo, sin_uso = invoca(ns)
                    codigo, con_uso = invoca(ns, "--usage")
                assert codigo == sin_codigo == 0, caso
                assert con_uso == sin_uso + esperado + "\n", caso


def test_solo_opcion_explicita():
    ast.parse(FUENTE, feature_version=(3, 8))
    ast.parse(CUOTA, feature_version=(3, 8))
    assert "actualizar_tarifas" not in FUENTE
    with entorno() as ns:
        for flags in (("--help",), ("--version",), ("--demo", "--list"),
                      ("--demo", "--json"), ("--demo", "--usage", "--json")):
            assert invoca(ns, *flags)[0] == 0
        cu = carga_cuota()
        assert "--tarifas" in cu["__doc__"] and "SERENO_TARIFAS_URL" in cu["__doc__"]
        for flags in (["--help"], ["-h"], ["--help", "--tarifas"]):
            assert captura(cu["main"], flags)[0] == 0
        with patch.dict(cu, {"una_pasada": lambda: ({"error": None}, 0),
                             "bucle": lambda: None}):
            for flags in ([], ["--once"], ["--watch"]):
                assert captura(cu["main"], flags)[0] == 0


def test_idiomas_y_helpers():
    casos = [({"SERENO_LANG": "ES", "LC_ALL": "en_US"}, "es"),
             ({"SERENO_LANG": "en", "LC_ALL": "es_ES"}, "en"),
             ({"LC_ALL": "es_ES", "LC_MESSAGES": "en_US"}, "es"),
             ({"LC_ALL": "C", "LC_MESSAGES": "en_US", "LANG": "es_ES"}, "en"),
             ({"LANG": "es_ES.UTF-8"}, "es"), ({"LANG": "C"}, "en"),
             ({"CLAUDE_LANG": "es"}, "es")]
    for variables, esperado in casos:
        with entorno() as ns, patch.dict(os.environ, dict(
                {k: "" for k in ("SERENO_LANG", "CLAUDE_LANG", "LC_ALL", "LC_MESSAGES", "LANG")},
                **variables)), patch.object(sys, "platform", "linux"):
            cu = carga_cuota()
            assert cu["_detecta_idioma"]() == ns["_detecta_idioma"]() == esperado
            codigo, salida = descarga(ns, catalogo())
            assert codigo == 0
            assert salida.startswith("Tarifas de 1 modelos" if esperado == "es"
                                     else "Saved rates for 1 models")
            for datos, ingles, espanol in (
                    ({}, "invalid models.dev data", "datos de models.dev no válidos"),
                    ({"anthropic": {"models": {}}}, "no valid Anthropic models",
                     "ningún modelo de Anthropic válido"),
                    (b" " * (20 * 1024 * 1024), "response reaches the 20 MB limit",
                     "la respuesta alcanza el límite de 20 MB")):
                codigo, salida = descarga(ns, datos)
                prefijo = "No se pudieron actualizar las tarifas: " if esperado == "es" else "Could not update rates: "
                assert codigo == 1 and salida == prefijo + (espanol if esperado == "es" else ingles) + "\n"
            for modelo in (None, "", "US.ANTHROPIC.CLAUDE-OPUS-5-20261023[1M]", "claude-opus-5"):
                assert cu["_modelo_tarifa"](modelo) == ns["_modelo_tarifa"](modelo)
            for precios in ([0, 1, 2, 3], [True, 1, 2, 3], [float("nan"), 1, 2, 3], [1, 2]):
                assert cu["_precios_validos"](precios) == ns["_precios_validos"](precios)
            assert cu["_ruta_tarifas"]() == ns["_ruta_tarifas"]()
            with patch.dict(os.environ, {"XDG_CACHE_HOME": ""}):
                assert cu["_ruta_tarifas"]() == ns["_ruta_tarifas"]()


def test_cuota_sin_tarifas_no_contacta_url():
    with entorno() as ns, patch.dict(os.environ, {
            "SERENO_CUOTA_URL": "https://cuota.invalid/usage",
            "SERENO_TARIFAS_URL": "https://tarifas.invalid/api.json"}):
        cu = carga_cuota()
        assert cu["URL_TARIFAS"] == os.environ["SERENO_TARIFAS_URL"]
        peticiones = []

        def responde(pet, **kwargs):
            assert pet.full_url == os.environ["SERENO_CUOTA_URL"]
            assert pet.get_header("Authorization") == "Bearer fixture"
            peticiones.append(pet.full_url)
            respuesta = io.BytesIO(json.dumps({"five_hour": {"utilization": 12}}).encode())
            respuesta.getcode = lambda: 200
            return respuesta

        with patch.dict(cu, {"credencial": lambda: {"token": "fixture"}}), \
                patch.object(urllib.request, "urlopen", side_effect=responde):
            for flags in ([], ["--once"]):
                codigo, salida = captura(cu["main"], flags)
                assert codigo == 0 and "5h 12%" in salida
        assert peticiones == [os.environ["SERENO_CUOTA_URL"]] * 2
        assert not ns["_ruta_tarifas"]().exists()
        cuota = pathlib.Path(os.environ["SERENO_DIR"]) / "cuota.json"
        anterior = cuota.read_bytes()
        codigo, salida = descarga(ns, catalogo())
        assert codigo == 0 and "Tarifas de 1 modelos" in salida
        assert cuota.read_bytes() == anterior
        assert json.loads(ns["_ruta_tarifas"]().read_text())["modelos"] == {"claude-nuevo": [2, 3, 4, 5]}


def main():
    pruebas = [f for nombre, f in globals().items() if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
    print("ok: %d pruebas de tarifas, actualizacion atomica, origen y aislamiento de red" % len(pruebas))


if __name__ == "__main__":
    main()
