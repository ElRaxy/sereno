#!/usr/bin/env python3
"""Codex vivos: ascendencia, runs opcionales, privacidad y aviso en el flanco."""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

os.environ["SERENO_LANG"] = "en"
os.environ["SERENO_DEBUG"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text()

# Catalogo local: cada cambio corre el caso que demuestra la guarda, sobre una
# copia en memoria. No toca el fichero que otra prueba puede estar ejecutando.
MUTANTES_CODEX = [
    ("solo mira al padre inmediato", "actual = padres.get(actual)", "actual = None",
     "test_abuelo_y_suelto"),
    ("pierde los sueltos", "sueltos.append(hijo)", "pass", "test_abuelo_y_suelto"),
    ("acepta runs terminados", 'and j.get("phase") != "done"', "and True",
     "test_run_y_json_roto"),
    ("lee status sin limite", "f.read(65537)", "f.read(65536)", "test_run_grande"),
    ("saca datos internos por JSON", '{k: h.get(k) for k in _CAMPOS_CODEX}', 'dict(h)',
     "test_json_privado_y_cableado_live"),
    ("no recorta la fila", 'return recorta("    " + GLIFO_CLI["codex"] + " " + _clean(" · ".join(partes)), cols)',
     'return "    " + GLIFO_CLI["codex"] + " " + _clean(" · ".join(partes))',
     "test_linea_list_now_y_ancho"),
    ("repite el aviso", "hijos_antes = hijos", "hijos_antes.update(hijos)",
     "test_watch_una_vez_con_veredicto"),
    ("pierde el cableado del selector", 'enumerate(r.get("codex_children", ()), 1)',
     'enumerate((), 1)', "test_demo_y_selector"),
]


class CodexVivos(unittest.TestCase):
    fuente = FUENTE

    def setUp(self):
        self.ns = {"__name__": "sereno_test"}
        exec(compile(self.fuente, "sereno", "exec"), self.ns)
        self.ns["DEMO"] = False
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = pathlib.Path(self.tmp.name)
        self.row = dict(name="parent", title="Parent", title_full="Parent", pid="100",
                        created=0, attached=False, mem_mb=None, idle=0, working=True,
                        meta={"cwd": str(self.cwd)}, pulso={"escribe": True})
        self.ns["registro_cc"] = lambda: {}
        self.ns["lee_registro_cc"] = lambda: {}
        self.ns["cwd_procesos"] = lambda pids: {p: str(self.cwd) for p in pids}
        self.ps = "100 1 10:00 claude\n200 100 05:00 sh worker\n300 200 02:03 /bin/codex exec -m gpt-test\n400 1 00:12 codex exec --model=other\n"

    def detecta(self, ps=None, rows=None):
        calls = []
        def run(cmd, **kw):
            calls.append(cmd)
            return types.SimpleNamespace(stdout=self.ps if ps is None else ps, returncode=0)
        self.ns["subprocess"] = types.SimpleNamespace(run=run)
        orphans = self.ns["codex_vivos"]([self.row] if rows is None else rows)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "ps")
        return orphans

    def status(self, **kw):
        p = self.cwd / ".agents/runs/run-test/status.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(id="run-test", pid=200, phase="executing",
                                    ronda="1/3", worker_model="worker", **kw)))
        return p

    def test_abuelo_y_suelto(self):
        orphan, = self.detecta()
        child, = self.row["codex_children"]
        self.assertEqual((child["pid"], child["model"], child["alive_seconds"]),
                         (300, "gpt-test", 123))
        self.assertEqual((orphan["pid"], orphan["model"]), (400, "other"))
        self.assertIsNone(child["phase"])

    def test_modelo_flags_y_ausencias(self):
        for flags, esperado in (("-m gpt-test", "gpt-test"), ("--model gpt-test", "gpt-test"),
                                ("--model=gpt-test", "gpt-test"), ("-mgpt-test", "gpt-test"),
                                ('--json "prompt --model inventado"', None)):
            orphan, = self.detecta("300 1 01:02:03 codex exec " + flags)
            self.assertEqual(orphan["model"], esperado)
            self.assertEqual(orphan["alive_seconds"], 3723)
            for k in ("run_id", "phase", "ronda"):
                self.assertIsNone(orphan[k])

    def test_registro_y_ancestro_mas_cercano(self):
        self.row["pid"] = ""
        self.row["meta"]["id"] = "sid"
        self.ns["lee_registro_cc"] = lambda: {"sid": {"pid": 100}}
        self.detecta()
        self.assertEqual(self.row["codex_children"][0]["pid"], 300)
        self.detecta(self.ps.replace("10:00 claude", "10:00 python"))
        self.assertEqual(self.row["codex_children"], [])
        near = dict(self.row, name="near", pid="200", meta={})
        self.detecta(rows=[self.row, near])
        self.assertEqual(self.row["codex_children"], [])
        self.assertEqual(near["codex_children"][0]["pid"], 300)

    def test_run_y_json_roto(self):
        p = self.status()
        self.detecta()
        c = self.row["codex_children"][0]
        self.assertEqual((c["run_id"], c["phase"], c["ronda"], c["model"]),
                         ("run-test", "executing", "1/3", "worker"))
        for content in ("{roto", "[]", '{"pid": []}', "x" * 65537):
            p.write_text(content)
            self.detecta()
            self.assertIsNone(self.row["codex_children"][0]["run_id"])
        p.write_text(json.dumps(dict(id="old", pid=200, phase="done")))
        self.detecta()
        self.assertIsNone(self.row["codex_children"][0]["run_id"])

    def test_pid_propio_manda_sobre_registro(self):
        # Una fila ajena con el mismo id de sesion (un --resume sin id) no se queda los Codex
        # del proceso al que apunta el registro, vaya antes o despues en la lista.
        self.ns["lee_registro_cc"] = lambda: {"sid": {"pid": 100}}
        ps = "100 1 10:00 claude\n900 1 10:00 claude --resume\n300 100 02:03 codex exec -m gpt-test\n"
        for orden in (0, 1):
            dueno = dict(self.row, meta={"cwd": str(self.cwd), "id": "sid"})
            ajena = dict(self.row, name="ajena", pid="900", meta={"cwd": str(self.cwd), "id": "sid"})
            self.detecta(ps, [dueno, ajena] if orden == 0 else [ajena, dueno])
            self.assertEqual([c["pid"] for c in dueno["codex_children"]], [300])
            self.assertEqual(ajena["codex_children"], [])

    def test_cwd_linux_y_macos(self):
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        with patch.object(ns["sys"], "platform", "linux"), patch("os.readlink", return_value="/work"):
            self.assertEqual(ns["cwd_procesos"]([300]), {300: "/work"})
        # En macOS no se lanza nada (lsof se puede colgar en el kernel): el cwd sale de la sesion padre.
        with patch.object(ns["sys"], "platform", "darwin"), patch("subprocess.run") as run:
            self.assertEqual(ns["cwd_procesos"]([300]), {})
            self.assertEqual(run.call_count, 0)
        with patch.object(ns["sys"], "platform", "linux"), patch("os.readlink", side_effect=OSError):
            self.assertEqual(ns["cwd_procesos"]([300]), {})

    def test_run_grande(self):
        p = self.status()
        data = p.read_bytes()
        p.write_bytes(data + b" " * (65537 - len(data)))
        self.detecta()
        self.assertIsNone(self.row["codex_children"][0]["phase"])

    def test_mutantes_nuevos(self):
        for nombre, ancla, reemplazo, test in MUTANTES_CODEX:
            with self.subTest(mutante=nombre):
                self.assertEqual(FUENTE.count(ancla), 1, "ancla obsoleta")
                case = CodexVivos(test)
                case.fuente = FUENTE.replace(ancla, reemplazo, 1)
                result = unittest.TestResult()
                case.run(result)
                self.assertFalse(result.wasSuccessful(), "mutante vivo: " + nombre)

    def test_no_confunde_prompt_y_deduplica_wrapper(self):
        ps = ('100 1 10:00 claude\n200 100 05:00 sh\n'
              '299 200 02:03 node /usr/bin/codex exec -m gpt-test\n'
              '300 299 02:03 /vendor/codex exec -m gpt-test\n'
              '401 1 01:00 sh -c codex exec\n402 1 01:00 echo codex\n'
              '403 1 1-02:03:04 codex exec "a prompt --model fake"\n')
        orphan, = self.detecta(ps)
        self.assertEqual(orphan["pid"], 403)
        self.assertIsNone(orphan["model"])
        self.assertEqual(orphan["alive_seconds"], 93784)
        self.assertEqual([c["pid"] for c in self.row["codex_children"]], [300])

    def test_sin_codex_no_lee_runs_y_ciclo_termina(self):
        self.ns["cwd_procesos"] = lambda pids: self.fail("cwd sin Codex")
        self.assertEqual(self.detecta("100 1 00:01 claude\n"), [])
        self.ns["cwd_procesos"] = lambda pids: {}
        self.assertEqual(len(self.detecta("300 200 00:01 codex\n200 300 00:02 sh\n")), 1)

    def test_json_privado_y_cableado_live(self):
        self.status(task="SECRET", cmd=["SECRET"], reasons=["SECRET"])
        orphans = self.detecta()
        self.ns["CODEX_ORPHANS"] = orphans
        self.row["codex_children"][0]["prompt"] = "SECRET"
        self.ns["lee_cuota"] = lambda: {}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.ns["print_json"]([self.row])
        d = json.loads(buf.getvalue())
        expected = {"pid", "model", "alive_seconds", "run_id", "phase", "ronda"}
        self.assertEqual(set(d["sessions"][0]["codex_children"][0]), expected)
        self.assertEqual(set(d["codex_orphans"][0]), expected)
        self.assertNotIn("SECRET", buf.getvalue())
        self.assertNotIn(str(self.cwd), buf.getvalue())
        self.ns["meta_by_tmux"] = lambda *a, **k: {}
        self.ns["tmux_list"] = lambda: []
        self.ns["sesiones_de_disco"] = lambda **kw: [self.row]
        self.ns["colisiones"] = lambda rows: rows
        self.ns["cerradas_recientes"] = lambda: set()
        live = self.ns["live_sessions"]()
        self.assertEqual(live[0]["codex_children"][0]["pid"], 300)
        self.assertEqual(self.ns["CODEX_ORPHANS"][0]["pid"], 400)

    def test_linea_list_now_y_ancho(self):
        self.status()
        self.detecta()
        c = self.row["codex_children"][0]
        line = self.ns["linea_codex"](c, 90)
        self.assertIn("codex · worker · 2:03 · executing 1/3 · run-test", line)
        self.assertTrue(line.startswith("    " + self.ns["GLIFO_CLI"]["codex"]))
        for width in (58, 90):
            largo = dict(c, model="日本語" * 50)
            self.assertLessEqual(self.ns["ancho"](self.ns["linea_codex"](largo, width)), width)
            buf = io.StringIO()
            with patch("shutil.get_terminal_size", return_value=os.terminal_size((width, 24))):
                with contextlib.redirect_stdout(buf):
                    self.ns["print_live"]([self.row])
            child_lines = [s for s in buf.getvalue().splitlines() if "codex ·" in s]
            self.assertEqual(len(child_lines), 1)
            self.assertLessEqual(self.ns["ancho"](child_lines[0]), width)
        self.ns["live_sessions"] = lambda **kw: [self.row]
        self.ns["detalles"] = lambda r: {}
        rows = self.ns["que_hacen"]()
        lines = self.ns["lineas_now"](rows, 58)
        self.assertIn((self.ns["linea_codex"](c, 58), self.ns["COLOR_CLI"]["codex"]), lines)

    def test_watch_una_vez_con_veredicto(self):
        p = self.status()
        self.detecta()
        first = dict(self.row)
        empty = dict(self.row, codex_children=[])
        snapshots = iter([[first], [empty], [empty]])
        def live(**kw):
            try:
                return next(snapshots)
            except StopIteration:
                raise KeyboardInterrupt
        self.ns["live_sessions"] = live
        self.ns["lee_cuota"] = lambda: {}
        notices = []
        self.ns["notifica"] = lambda *args: notices.append(args)
        self.ns["time"] = types.SimpleNamespace(strftime=lambda x: "12:00", sleep=lambda x: None)
        p.write_text(json.dumps(dict(id="run-test", pid=200, phase="done", verdict="ready")))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(self.ns["watch"](), 0)
        self.assertEqual(len(notices), 1)
        self.assertIn("ready", buf.getvalue())
        self.assertEqual(buf.getvalue().count("\a"), 1)

    def test_watch_fallo_ps_no_es_fin_y_traspaso_a_suelto(self):
        self.detecta()
        first = dict(self.row)
        empty = dict(self.row, codex_children=[])
        snapshots = iter([([first], []), ([empty], None),
                          ([empty], first["codex_children"]), ([empty], [])])
        def live(**kw):
            try:
                rows, orphans = next(snapshots)
            except StopIteration:
                raise KeyboardInterrupt
            self.ns["CODEX_ORPHANS"] = orphans
            return rows
        self.ns["live_sessions"] = live
        self.ns["lee_cuota"] = lambda: {}
        self.ns["notifica"] = lambda *args: self.fail("un ps fallido o un huérfano no ha terminado")
        self.ns["time"] = types.SimpleNamespace(strftime=lambda x: "12:00", sleep=lambda x: None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.ns["watch"](), 0)

    def test_json_cli_sin_sesion_con_historial_y_pipe(self):
        self.ns["CODEX_ORPHANS"] = self.detecta(rows=[])
        self.ns["_quiza_en_tmux"] = lambda argv: None
        self.ns["live_sessions"] = lambda **kw: []
        self.ns["sesiones_de_disco"] = lambda **kw: [self.row]
        self.ns["lee_cuota"] = lambda: {}
        with patch("sys.argv", ["sereno", "--json"]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(self.ns["main"](), 0)
        d = json.loads(out.getvalue())
        self.assertEqual(len(d["codex_orphans"]), 2)
        self.assertEqual(len(d["sessions"]), 1)

    def test_demo_y_selector(self):
        from doble_curses import espia
        import curses as real
        self.ns["DEMO"] = True
        rows = self.ns["sesiones_demo"]()
        self.assertTrue(any(r.get("codex_children") for r in rows))
        for width in (58, 90, 150):
            cajon = []
            fake = espia(real, 30, width, [real.KEY_DOWN, ord("q")], cajon, self.ns["ancho"])
            with patch.dict("sys.modules", curses=fake), contextlib.redirect_stdout(io.StringIO()):
                self.ns["pick_ui"](rows)
            p = cajon[0]
            self.assertFalse(p.fuera)
            self.assertFalse(p.solapes)
            frames = p.fotogramas + [p.celdas]
            self.assertTrue(any("codex ·" in "".join(cells.get((y, x), " ") for x in range(width))
                                for cells in frames for y in range(30)))

    def test_selector_scroll_con_hijos(self):
        from doble_curses import espia
        import curses as real
        self.ns["DEMO"] = True
        base = self.ns["sesiones_demo"]()[0]
        rows = [dict(base, name="parent-%02d" % i, title="Parent %02d" % i,
                     title_full="Parent %02d" % i, idle=i) for i in range(20)]
        for height, width in ((12, 58), (24, 90), (30, 150)):
            cajon = []
            fake = espia(real, height, width, [real.KEY_DOWN] * 19 + [ord("q")],
                         cajon, self.ns["ancho"])
            with patch.dict("sys.modules", curses=fake), contextlib.redirect_stdout(io.StringIO()):
                self.ns["pick_ui"](rows)
            p = cajon[0]
            self.assertFalse(p.fuera)
            self.assertFalse(p.solapes)
            lines = ["".join(p.celdas.get((y, x), " ") for x in range(width))
                     for y in range(height)]
            self.assertTrue(any("Parent 19" in s for s in lines))


if __name__ == "__main__":
    unittest.main()
