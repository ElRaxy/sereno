#!/usr/bin/env python3
"""Una estimacion no sustituye al coste del CLI ni convierte un dato ausente en cero.

Las cuatro clases de tokens se cobran por separado. Se prueban la fila JSON y las
dos vistas, no solo la cuenta, porque perder el modelo al pintar oculta la cifra.
Los transcripts son fixtures temporales: nunca se leen conversaciones reales.
"""
import contextlib, io, json, os, pathlib, tempfile, urllib.request
from unittest.mock import Mock, patch

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
        "claude-fable-5": (10, 50, 12.5, 1.0),
        "claude-opus-5-5": (4, 20, 5, 0.20),
        "claude-opus-5": (5, 25, 6.25, 0.50),
        "claude-opus-4-8": (5, 25, 6.25, 0.50),
        "claude-opus-4-7": (5, 25, 6.25, 0.50),
        "claude-opus-4-6": (5, 25, 6.25, 0.50),
        "claude-sonnet-5-5": (2, 10, 2.5, 0.10),
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

    with patch.dict(ns, DEMO=True, USO=True):
        filas = ns["sesiones_demo"]()
        precargados = [r["_uso"] for r in filas]
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("demo lee disco")), \
                patch.object(pathlib.Path, "stat", side_effect=AssertionError("demo mira disco")), \
                patch.object(pathlib.Path, "rglob", side_effect=AssertionError("demo busca hijos")):
            ns["filas_json"]([r for r in filas if r["_uso"] is not None])
        salida = ns["filas_json"](filas)
        for r, u, s in zip(filas, precargados, salida):
            if u is not None:
                assert r["_uso"] is u
                assert s["input_tokens"] == u["in"]
                if s["model"] is not None:
                    assert s["estimated_cost_usd"] is not None
                else:
                    assert s["estimated_cost_usd"] is None
        assert salida[0]["input_tokens"] == 1200
        assert salida[0]["estimated_cost_usd"] == 53.7667

    prueba_transcripts()
    with tempfile.TemporaryDirectory() as tmp:
        test_agregado_memorizado(pathlib.Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_hijos_no_se_enumeran_dentro_del_plazo(pathlib.Path(tmp))
    print("ok: costes, ausencias, normalizacion, JSON, vistas bilingues, subagentes, "
          "cache 1h, modelos mixtos y deduplicacion incremental")


def respuesta(mid, modelo="claude-opus-5", ent=0, out=0, cw=0, cr=0, cache=None):
    uso = {"input_tokens": ent, "output_tokens": out,
           "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}
    if cache is not None:
        uso["cache_creation"] = cache
    return json.dumps({"type": "assistant", "message": {
        "id": mid, "model": modelo, "usage": uso}}) + "\n"


def prueba_transcripts():
    coste, uso_de, cache_uso = ns["coste_estimado"], ns["uso_de"], ns["_CACHE_USO"]
    with tempfile.TemporaryDirectory() as tmp, \
            patch.object(ns["time"], "monotonic", return_value=100.0) as reloj:
        p = pathlib.Path(tmp) / "sesion.jsonl"
        sub = p.with_suffix("") / "subagents" / "agent-x.jsonl"
        flujo = p.with_suffix("") / "workflows" / "anidado" / "paso.jsonl"
        sub.parent.mkdir(parents=True)
        flujo.parent.mkdir(parents=True)
        p.write_text(respuesta("a", ent=1_000_000, out=10_000)
                     + respuesta("b", "claude-sonnet-5-5", ent=1_000_000)
                     + respuesta("a", ent=1_000_000, out=100_000))
        sub.write_text(respuesta("x", out=1_000)
                       + respuesta("y", "claude-sonnet-5-5", ent=500_000, out=50_000)
                       + respuesta("x", out=200_000))
        flujo.write_text(respuesta("z", "claude-haiku-5-5", ent=1_000_000))
        fila = {"name": "prueba", "title": "prueba", "attached": False,
                "created": 0, "mem_mb": None, "meta": {"_transcript": p},
                "pulso": {"modelo": "desconocido"}}
        u = uso_de(fila)
        # Principal: (5 + 2.5) + 2 = 9.5. Subagente: 5 + (1 + .5) = 6.5.
        # Workflow: .1. La salida parcial y el modelo del panel no mandan.
        assert coste(u, "desconocido") == 16.1
        assert u["in"] == 2_000_000 and u["out"] == 100_000
        assert u["turnos"] == 2 and u["cw"] == 0 and u["cr"] == 0
        assert u["activo"] == 0 and u["pico"] == 1_000_000
        assert ns["filas_json"]([fila])[0]["estimated_cost_usd"] == 16.1
        assert "~$16.10 est." in ns["_uso_texto"](u, "desconocido")
        # Una fila nueva y una existente reutilizan los tres ficheros sin abrirlos.
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("relectura")):
            assert coste(uso_de(fila)) == 16.1
            assert coste(uso_de({"meta": fila["meta"]})) == 16.1
        with sub.open("a") as f:
            f.write(respuesta("x", out=400_000))
        # Solo cambio el hijo: 5 dolares mas, con principal y workflow intactos.
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert coste(uso_de(fila)) == 21.1
        with p.open("a") as f:
            f.write(respuesta("a", ent=1_000_000, out=200_000))
        assert coste(uso_de(fila)) == 23.6
        incremental = uso_de(fila)
        cache_uso.clear()
        ns["_CACHE_AGREGADO"].clear()
        assert coste(uso_de(fila)) == 23.6
        assert uso_de(fila)["out"] == incremental["out"] == 200_000
        # Copia de workflow: id global, vale la ultima observacion una sola vez.
        with flujo.open("a") as f:
            f.write(respuesta("x", out=500_000))
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert coste(uso_de(fila)) == 26.1
        # El presupuesto es compartido: no se lee un trozo por cada subagente.
        cache_uso.clear()
        ns["_CACHE_AGREGADO"].clear()
        abiertos, abrir = [], pathlib.Path.open

        def abre(path, *args, **kwargs):
            abiertos.append(path.name)
            return abrir(path, *args, **kwargs)

        with patch.object(pathlib.Path, "open", abre):
            parcial = uso_de(fila, 1)
        assert abiertos == ["sesion.jsonl"]
        assert not parcial["completo"]
        assert sum(d[2]["_pos"] for d in cache_uso.values()) == len(
            respuesta("a", ent=1_000_000, out=10_000).encode())
        for vuelta in range(20):
            parcial = uso_de(fila, 1)
            if parcial["completo"]:
                break
        assert parcial["completo"] and coste(parcial) == 26.1
        # Reescritura con el mismo tamano: mtime distinto invalida el offset.
        viejo = sub.stat().st_mtime
        sub.write_text(sub.read_text().replace('400000', '600000'))
        os.utime(sub, (viejo + 1, viejo + 1))
        assert ns["_uso"](sub)["out"] == 650_000
        # Borrar un hijo tambien debe quitar su coste, aunque no cambie el principal.
        flujo.unlink()
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert coste(uso_de(fila)) == 28.5

        p = pathlib.Path(tmp) / "cache.jsonl"
        fila = {"meta": {"_transcript": p}}
        p.write_text(respuesta("hora", ent=100_000, out=20_000, cw=300_000,
                               cr=1_000_000, cache={"ephemeral_5m_input_tokens": 100_000,
                                                   "ephemeral_1h_input_tokens": 200_000}))
        # .5 entrada + .5 salida + .625 cache 5m + 2 cache 1h + .5 lectura.
        assert coste(uso_de(fila)) == 4.125
        assert uso_de(fila)["cw"] == 300_000
        p.write_text(respuesta("cinco", ent=100_000, out=20_000,
                               cw=300_000, cr=1_000_000))
        assert coste(uso_de(fila)) == 3.375
        # Con solo media pareja no hay desglose completo: se conserva el fallback 5m.
        p.write_text(respuesta("incompleto", cw=300_000,
                               cache={"ephemeral_1h_input_tokens": 200_000}))
        cache_uso.clear()
        ns["_CACHE_AGREGADO"].clear()
        assert coste(uso_de(fila)) == 1.875
        # Ausencia de tarifa no es cero; tampoco se hereda el ultimo modelo del panel.
        p.write_text(respuesta("sin", "desconocido", ent=1_000_000)
                     + respuesta("sintetico", "<synthetic>", ent=1_000_000))
        cache_uso.clear()
        ns["_CACHE_AGREGADO"].clear()
        assert coste(uso_de(fila), "claude-opus-5") is None
        p.write_text(respuesta("cero"))
        assert coste(uso_de(fila)) == 0.0
        # Una ultima linea sin tarifa retira el precio anterior del mismo id.
        with p.open("a") as f:
            f.write(respuesta("cero", "<synthetic>"))
        assert coste(uso_de(fila)) is None
        # Las respuestas pequenas se redondean despues de sumar: 20 * .000005.
        p.write_text("".join(respuesta(str(i), ent=1) for i in range(20)))
        cache_uso.clear()
        ns["_CACHE_AGREGADO"].clear()
        assert coste(uso_de(fila)) == 0.0001
        # Mas de 200 hijos no deben vaciar la cache y releerse en cada refresco.
        p = pathlib.Path(tmp) / "muchos.jsonl"
        p.write_text(respuesta("principal", ent=1_000_000))
        hijos = p.with_suffix("") / "subagents"
        hijos.mkdir(parents=True)
        for i in range(201):
            (hijos / ("agent-%d.jsonl" % i)).write_text(respuesta(str(i), ent=1_000_000))
        fila = {"meta": {"_transcript": p}}
        assert coste(uso_de(fila)) == 1010.0
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("relectura")):
            assert coste(uso_de(fila)) == 1010.0


def test_agregado_memorizado(tmp_path):
    coste, uso_de = ns["coste_estimado"], ns["uso_de"]
    cache_uso, cache_agregado = ns["_CACHE_USO"], ns["_CACHE_AGREGADO"]
    cache_uso.clear()
    cache_agregado.clear()
    recorridos = 0

    class MensajesContados(dict):
        def items(self):
            nonlocal recorridos
            recorridos += 1
            return super().items()

    parche = patch.object(ns["time"], "monotonic", return_value=100.0)
    reloj = parche.start()
    try:
        p = tmp_path / "sesion.jsonl"
        p.write_text(respuesta("principal", ent=1_000_000))
        hijos = []
        for i in range(201):
            carpeta = "subagents" if i % 2 else "workflows"
            hijo = p.with_suffix("") / carpeta / "anidado" / ("hijo-%d.jsonl" % i)
            hijo.parent.mkdir(parents=True, exist_ok=True)
            hijo.write_text(respuesta("hijo-%d" % i, ent=1_000_000))
            hijos.append(hijo)
        fila = {"meta": {"_transcript": p}}
        primero = uso_de(fila)
        assert primero["completo"] and coste(primero) == 1010.0
        assert len(cache_uso) == 202
        for entrada in cache_uso.values():
            entrada[2]["_mensajes"] = MensajesContados(entrada[2]["_mensajes"])
        # Recargar crea filas nuevas: la reutilizacion debe depender del transcript.
        segundo = uso_de({"meta": fila["meta"]})
        assert recorridos == 0
        assert coste(segundo) == coste(primero)
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert uso_de({"meta": fila["meta"]}) is primero
        assert recorridos == 0

        hijo = hijos[0]
        viejo = hijo.stat().st_mtime
        with hijo.open("a") as f:
            f.write(respuesta("nuevo", out=1_000_000))
        os.utime(hijo, (viejo + 1, viejo + 1))
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        cambiado = uso_de({"meta": fila["meta"]})
        assert recorridos > 0
        assert cambiado["completo"] and coste(cambiado) == 1035.0

        nuevo = hijo.with_name("nuevo.jsonl")
        nuevo.write_text(respuesta("otro", ent=1_000_000))
        recorridos = 0
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert coste(uso_de({"meta": fila["meta"]})) == 1040.0
        assert recorridos > 0
        nuevo.unlink()
        recorridos = 0
        reloj.return_value += ns["REVISA_HIJOS_S"] + 1
        assert coste(uso_de({"meta": fila["meta"]})) == 1035.0
        assert recorridos > 0
    finally:
        parche.stop()
        cache_uso.clear()
        cache_agregado.clear()


def test_hijos_no_se_enumeran_dentro_del_plazo(tmp_path):
    coste, uso_de = ns["coste_estimado"], ns["uso_de"]
    cache_uso, cache_agregado = ns["_CACHE_USO"], ns["_CACHE_AGREGADO"]
    cache_uso.clear()
    cache_agregado.clear()
    enumeraciones, rglob = 0, pathlib.Path.rglob

    def enumera(path, patron):
        nonlocal enumeraciones
        enumeraciones += 1
        return rglob(path, patron)

    try:
        p = tmp_path / "sesion.jsonl"
        p.write_text(respuesta("principal", ent=1_000_000))
        hijos = p.with_suffix("") / "subagents"
        hijos.mkdir(parents=True)
        (hijos / "primero.jsonl").write_text(respuesta("primero", ent=1_000_000))
        fila = {"meta": {"_transcript": p}}
        with patch.object(ns["time"], "monotonic", return_value=100.0) as reloj, \
                patch.object(pathlib.Path, "rglob", enumera):
            primero = uso_de(fila)
            assert enumeraciones > 0 and coste(primero) == 10.0
            enumeraciones = 0
            reloj.return_value += 1
            with patch.dict(ns, {"_uso": Mock(side_effect=AssertionError(
                    "_uso dentro del plazo"))}), \
                    patch.object(pathlib.Path, "stat", autospec=True,
                                 side_effect=pathlib.Path.stat) as stat:
                assert uso_de({"meta": fila["meta"]}) is primero
                assert stat.call_count == 1 and stat.call_args.args == (p,)
            assert enumeraciones == 0 and coste(fila["_uso"]) == 10.0

            viejo = p.stat().st_mtime
            with p.open("a") as f:
                f.write(respuesta("principal-nuevo", out=1_000_000))
            os.utime(p, (viejo + 1, viejo + 1))
            assert coste(uso_de(fila)) == 35.0
            assert enumeraciones > 0

            enumeraciones = 0
            (hijos / "nuevo.jsonl").write_text(respuesta("nuevo", ent=1_000_000))
            reloj.return_value += 1
            assert coste(uso_de(fila)) == 35.0
            assert enumeraciones == 0
            reloj.return_value += ns["REVISA_HIJOS_S"] + 1
            assert coste(uso_de(fila)) == 40.0
            assert enumeraciones > 0
            enumeraciones = 0
            reloj.return_value += ns["REVISA_HIJOS_S"] + 1
            assert coste(uso_de(fila)) == 40.0
            assert enumeraciones > 0
            enumeraciones = 0
            reloj.return_value += 1
            assert coste(uso_de(fila)) == 40.0
            assert enumeraciones == 0
    finally:
        cache_uso.clear()
        cache_agregado.clear()


if __name__ == "__main__":
    main()
