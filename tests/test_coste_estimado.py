#!/usr/bin/env python3
"""Una estimacion no sustituye al coste del CLI ni convierte un dato ausente en cero.

Las cuatro clases de tokens se cobran por separado. Se prueban la fila JSON y las
dos vistas, no solo la cuenta, porque perder el modelo al pintar oculta la cifra.
El refresco se prueba con respuestas locales: la suite no depende de models.dev.
"""
import contextlib, io, json, pathlib, threading, urllib.request
from unittest.mock import patch

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
with patch.object(urllib.request, "urlopen", side_effect=AssertionError("red al cargar")) as red:
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    assert not red.called


def main():
    coste = ns["coste_estimado"]
    u = {"in": 1_000_000, "out": 200_000, "cw": 400_000, "cr": 3_000_000,
         "usd": None, "turnos": 1, "compacta": 0, "pico": 0, "activo": 0,
         "completo": True}
    modelo = "claude-opus-5"
    # 5 + 5 + 2.5 + 1.5: mezclar cualquier pareja cambia el resultado.
    assert coste(u, modelo) == 14.0
    assert isinstance(coste(u, modelo), float)
    assert coste(dict(u, **{"in": 11, "out": 13, "cw": 17, "cr": 19}), modelo) == 0.0005
    assert coste(u, "desconocido") is None
    assert coste(None, modelo) is None
    assert coste(u, None) is None
    assert coste(u, "") is None
    assert coste(dict(u, **{"in": 0, "out": 0, "cw": 0, "cr": 0}), modelo) == 0.0
    for m in ("CLAUDE-OPUS-5", "claude-opus-5-20260401", "anthropic.claude-opus-5",
              "us.anthropic.claude-opus-5", "eu-west-1.anthropic.claude-opus-5",
              "US.ANTHROPIC.CLAUDE-OPUS-5-20260401[1M]", "claude-opus-5[1m]"):
        assert coste(u, m) == 14.0, m

    tabla = ns["TARIFAS_USD_MTOK"]
    assert tabla == {
        "claude-fable-5-1": (10, 50, 12.5, 0.25),
        "claude-fable-5": (10, 50, 12.5, 0.25),
        "claude-opus-5-5": (4, 20, 5, 0.20),
        "claude-opus-5": (5, 25, 6.25, 0.50),
        "claude-opus-4-8": (5, 25, 6.25, 0.50),
        "claude-opus-4-7": (5, 25, 6.25, 0.50),
        "claude-opus-4-6": (5, 25, 6.25, 0.50),
        "claude-sonnet-5-5": (2, 10, 2.5, 0.20),
        "claude-sonnet-5": (2, 10, 2.5, 0.20),
        "claude-sonnet-4-6": (3, 15, 3.75, 0.30),
        "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01),
        "claude-haiku-4-5": (1, 5, 1.25, 0.10),
    }
    fila = {"name": "prueba", "title": "prueba", "attached": False,
            "created": 0, "mem_mb": None, "pulso": {"modelo": modelo}}
    with patch.object(urllib.request, "urlopen", side_effect=AssertionError("red por defecto")) as red:
        for uso in (False, True):
            ns["USO"] = uso
            salida = ns["filas_json"]([dict(fila)])[0]
            assert "estimated_cost_usd" in salida
            assert salida["estimated_cost_usd"] is None
        fila["_uso"] = u
        salida = ns["filas_json"]([fila])[0]
        assert salida["estimated_cost_usd"] == 14.0
        assert salida["api_cost_usd"] is None
        assert list(salida).index("estimated_cost_usd") == list(salida).index("api_cost_usd") + 1
        ns["USO"] = False
        assert ns["filas_json"]([fila])[0]["estimated_cost_usd"] is None
        ns["USO"] = True
        for idioma in ("en", "es"):
            ns["LANG_UI"] = idioma
            for usd in (None, 0.0, 9.87):
                u["usd"] = usd
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ns["print_live"]([fila])
                campos = ns["campos_panel"](fila, {}, "", ahora=0)
                panel = next(c[1] for c in campos if c[0] == ns["_"]("spent"))
                for texto in (buf.getvalue(), panel):
                    assert "~$14.00 est." in texto
                    if usd is not None:
                        assert "$%.2f · ~$14.00 est." % usd in texto
                assert ns["filas_json"]([fila])[0]["api_cost_usd"] == usd
            assert "est." not in ns["_uso_texto"](u, "desconocido")
            assert "$9.87" in ns["_uso_texto"](u)
            u["usd"] = None
            assert "$" not in ns["_uso_texto"](u, "desconocido")
        assert not red.called

    original = dict(tabla)
    completo = {"cost": {"input": 6, "output": 30, "cache_write": 7.5, "cache_read": 0.6}}

    def refresca(datos):
        with patch.object(urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(datos).encode())) as red:
            hilo = ns["refresca_tarifas_models_dev"](timeout=0.1)
            hilo.join(2)
            assert not hilo.is_alive()
            red.assert_called_once_with("https://models.dev/api.json", timeout=0.1)

    try:
        refresca({"anthropic": {"models": {modelo: completo,
                 "claude-fable-5": {"cost": {"input": 999}}, "desconocido": completo}}})
        assert tabla == dict(original, **{modelo: (6, 30, 7.5, 0.6)})
        tabla.update(original)
        for datos in ({}, [], {"anthropic": {"models": []}},
                      {"anthropic": {"models": {modelo: completo, "claude-fable-5": None}}},
                      {"anthropic": {"models": {modelo: completo, "claude-fable-5": {"cost": []}}}}):
            refresca(datos)
            assert tabla == original
        for valor in (None, "6", True, -1, float("inf"), float("nan")):
            malo = {"cost": dict(completo["cost"], input=valor)}
            refresca({"anthropic": {"models": {modelo: completo, "claude-fable-5": malo}}})
            assert tabla == original
        with patch.object(urllib.request, "urlopen", side_effect=TimeoutError):
            hilo = ns["refresca_tarifas_models_dev"]()
            hilo.join(2)
            assert not hilo.is_alive()
            assert tabla == original
        with patch.object(urllib.request, "urlopen", return_value=io.BytesIO(b"no es json")):
            hilo = ns["refresca_tarifas_models_dev"]()
            hilo.join(2)
            assert tabla == original
        # La red queda esperando, pero quien llama ya ha recuperado el control.
        entra, sale = threading.Event(), threading.Event()

        def espera(*args, **kwargs):
            entra.set()
            assert sale.wait(2)
            raise TimeoutError

        with patch.object(urllib.request, "urlopen", side_effect=espera):
            hilo = ns["refresca_tarifas_models_dev"]()
            try:
                assert entra.wait(1)
                assert hilo.is_alive()
                assert tabla == original
            finally:
                sale.set()
                hilo.join(2)
    finally:
        tabla.clear()
        tabla.update(original)
    print("ok: costes, ausencias, normalizacion, JSON, vistas bilingues y refresco opt-in")


if __name__ == "__main__":
    main()
