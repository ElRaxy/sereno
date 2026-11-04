#!/usr/bin/env python3
"""Restaurar snapshots: plan puro, cmux simulado y guardas rotas a proposito."""
import contextlib
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / "sereno").read_text("utf-8")
CODIGO = compile(FUENTE, "sereno", "exec")
TS = 1700000000
CAB_SES = "tmux_session\tsession_id\tcwd\tpid\tstarted_epoch\tcreada_tmux\tenganchada\n"
CAB_CODEX = "run_id\tphase\tpid\tpid_vivo\toutput_file\n"


def sesion(n, cwd="/"):
    return {"tmux_session": "cc-%d" % n,
            "session_id": "%08d-0000-0000-0000-000000000000" % n,
            "cwd": str(cwd), "pid": "123", "started_epoch": str(TS - 100),
            "creada_tmux": str(TS - 100), "enganchada": "1"}


def pane(*ids):
    return {"type": "pane", "pane": {"panelIds": list(ids), "selectedPanelId": ids[0]}}


def split(orientacion, primero, segundo):
    return {"type": "split", "split": {"orientation": orientacion,
            "first": primero, "second": segundo, "dividerPosition": 0.37}}


class Restaurar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = pathlib.Path(self.tmp.name)
        entorno = {k: v for k, v in os.environ.items()
                   if not k.startswith(("SERENO_", "CLAUDE_"))}
        entorno.update(HOME=str(self.raiz), SERENO_LANG="en",
                       SERENO_RESTORE_DIR=str(self.raiz / "restore"),
                       SERENO_RESTORE_STAGGER="0")
        self.env = mock.patch.dict(os.environ, entorno, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ns = {"__name__": "sereno_test"}
        exec(CODIGO, self.ns)
        self.ns.update(HOME=self.raiz, PROJECTS=self.raiz / "projects",
                       RUN=self.raiz / "scripts", LAUNCH=self.raiz / "launch",
                       tmux_list=lambda: [], registro_cc=lambda **kw: {},
                       bin_cli=lambda nombre: "/never-run/" + nombre)
        self.abiertas = []
        self.ns["abre_varias"] = self.abrir
        self.cmux = self.raiz / "cmux stub"
        self.log = self.raiz / "cmux.jsonl"
        self.ns["subprocess"] = type("ProcesosAislados", (), {
            "TimeoutExpired": subprocess.TimeoutExpired,
            "run": self.proceso,
        })()

    def proceso(self, argv, **kw):
        self.assertIsInstance(argv, list)
        self.assertFalse(kw.get("shell"))
        self.assertEqual(argv[0], str(self.cmux), "llamada externa fuera del stub")
        return subprocess.run(argv, **kw)

    def abrir(self, pestanas, config, cual=None):
        self.abiertas.extend(pestanas)
        return "stub", len(pestanas)

    def snapshot(self, nombre="20231114-221320", ts=TS, filas=None):
        ruta = self.raiz / "restore" / nombre
        ruta.mkdir(parents=True)
        filas = [sesion(1, self.raiz)] if filas is None else filas
        (ruta / "meta.txt").write_text(
            "ts_epoch=%s\nboottime_epoch=1\nhost=test\nsesiones=%d\n"
            "codex_huerfanas=0\ncmux=ausente\n" % (ts, len(filas)))
        claves = CAB_SES.strip().split("\t")
        (ruta / "sesiones.tsv").write_text(CAB_SES + "".join(
            "\t".join(f[c] for c in claves) + "\n" for f in filas))
        (ruta / "codex.tsv").write_text(CAB_CODEX)
        return ruta

    def transcript(self, fila, mtime):
        carpeta = self.ns["PROJECTS"] / "proyecto"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / (fila["session_id"] + ".jsonl")
        ruta.write_text(json.dumps({"type": "user", "sessionId": fila["session_id"],
                                   "cwd": str(self.raiz), "message": {"content": "test"}}) + "\n")
        os.utime(str(ruta), (mtime, mtime))

    def ejecutar(self, argv=(), **kw):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            rc = self.ns["cmd_restore"](list(argv), arranque=lambda: TS + 100,
                                        reloj=lambda: TS + 200, **kw)
        return rc, salida.getvalue()

    def stub_cmux(self, ping=0, falla="", latencia=0):
        self.cmux.write_text("#!" + sys.executable + "\n" +
            "import json, os, pathlib, sys, time\n"
            "p = pathlib.Path(%r)\n" % str(self.log) +
            "a = sys.argv[1:]\n"
            "with p.open('a') as f: f.write(json.dumps([a, os.environ.get('CMUX_QUIET')]) + '\\n')\n"
            "if a in (['ping'], ['list-windows']): sys.exit(%d)\n" % ping +
            "if %r:\n" % latencia +
            "    time.sleep(%r)\n" % latencia +
            "    assert not list(pathlib.Path(%r).glob('puerta-*'))\n" % str(self.ns["RUN"]) +
            "    with pathlib.Path(%r).open('a') as f: f.write(str(time.time()) + '\\n')\n" % str(self.raiz / "fin-cmux") +
            "if %r and %r in a: sys.exit(1)\n" % (falla, falla) +
            "n = len([l for l in p.read_text().splitlines() if json.loads(l)[0][0] != 'ping'])\n"
            "print('OK surface:%d workspace:%d' % (n, n))\n")
        self.cmux.chmod(0o700)
        os.environ["SERENO_CMUX_BIN"] = str(self.cmux)

    def test_elige_anterior_y_no_posterior_ni_igual(self):
        candidatos = [{"ruta": pathlib.Path(str(t)), "ts_epoch": t}
                      for t in (TS - 10, TS + 100, TS + 200, TS)]
        self.assertEqual(self.ns["elige_snapshot"](candidatos, TS + 100)["ts_epoch"], TS)
        self.assertIsNone(self.ns["elige_snapshot"](candidatos[1:3], TS + 100))
        viejo = self.snapshot()
        self.snapshot("20231114-221640", TS + 200)
        rc, texto = self.ejecutar(cmux="")
        self.assertEqual(rc, 0)
        self.assertIn(str(viejo), texto)
        self.assertNotIn("20231114-221640", texto)

    def test_sin_snapshot(self):
        rc, texto = self.ejecutar(cmux="")
        self.assertEqual(rc, 1)
        self.assertIn("snapshot", texto.lower())
        self.assertFalse(self.abiertas)

    def test_clasifica_orden_retardos_y_all(self):
        filas = [sesion(n) for n in range(1, 6)]
        mtimes = {filas[0]["session_id"]: TS - 10,
                  filas[1]["session_id"]: TS - 20,
                  filas[2]["session_id"]: TS - 10801,
                  filas[3]["session_id"]: TS - 5,
                  filas[4]["session_id"]: TS - 10800}
        foto = {"sesiones": list(reversed(filas)), "ts_epoch": TS, "ignoradas": 2}
        opciones = dict(mtimes=mtimes, hibernadas={filas[3]["tmux_session"]}, stagger=7)
        plan = self.ns["plan_restore"](foto, **opciones)
        entradas = plan["entradas"]
        self.assertEqual([e["session_id"] for e in entradas],
                         [filas[n]["session_id"] for n in (0, 1, 4, 2, 3)])
        self.assertEqual([e["estado"] for e in entradas],
                         ["activa", "activa", "activa", "quieta", "hibernada"])
        self.assertEqual([e["retardo"] for e in entradas[:3]], [0, 7, 14])
        self.assertEqual([e["esperar"] for e in entradas], [False, False, False, True, True])
        self.assertEqual(plan["ignoradas"], 2)
        todas = self.ns["plan_restore"](foto, todas=True, **opciones)["entradas"]
        self.assertEqual([e["esperar"] for e in todas], [False, False, False, False, True])
        self.assertEqual(todas[3]["retardo"], 21)

    def test_excluye_tmux_e_id_vivos(self):
        filas = [sesion(n) for n in range(1, 4)]
        foto = {"sesiones": filas, "ts_epoch": TS, "ignoradas": 0}
        plan = self.ns["plan_restore"](foto, vivas={"cc-1"},
                                       ids_vivos={filas[1]["session_id"]})
        self.assertEqual(plan["vivas"], 2)
        self.assertEqual([e["session_id"] for e in plan["entradas"]], [filas[2]["session_id"]])
        self.snapshot(filas=filas)
        self.ns["tmux_list"] = lambda: [("cc-1", 0, False, "", "0")]
        self.ns["registro_cc"] = lambda **kw: {filas[1]["session_id"]: {"pid": 123}}
        self.assertEqual(self.ejecutar(["--yes"], cmux="")[0], 0)
        self.assertEqual([p[0] for p in self.abiertas], ["cc-3"])

    def test_tolerancia_y_tokens_hibernadas(self):
        filas = [sesion(n, self.raiz) for n in range(1, 4)]
        ruta = self.snapshot(filas=filas)
        with (ruta / "sesiones.tsv").open("a") as f:
            f.write("fila rota\n" + "\t".join(["cc-vacia", "", "/", "0", "0", "0", "0"]) + "\n")
        (ruta / "codex.tsv").unlink()
        h = ruta / "hibernadas"
        h.mkdir()
        (h / "lista").write_text(filas[0]["session_id"] + "\ncc-2\ncc-30\n")
        for fila in filas:
            self.transcript(fila, TS - 1)
        foto = self.ns["lee_snapshot"](ruta)
        self.assertGreaterEqual(foto["ignoradas"], 2)
        rc, texto = self.ejecutar(["--yes"], cmux="")
        self.assertEqual(rc, 0, texto)
        self.assertEqual(len(self.abiertas), 3)
        guiones = {p[0]: pathlib.Path(shlex.split(p[1])[-1]).read_text() for p in self.abiertas}
        self.assertIn("hibern", guiones["cc-1"])
        self.assertIn("hibern", guiones["cc-2"])
        self.assertNotIn("hibern", guiones["cc-3"])

    def test_prompt_runs_y_tokens_sin_shell(self):
        fila = sesion(1)
        runs = self.raiz / "runs"
        codex = []
        for nombre, sid, vivo in (("mia", fila["session_id"], "0"),
                                  ("ajena", sesion(2)["session_id"], "0"),
                                  ("viva", fila["session_id"], "1"),
                                  ("rota", None, "0")):
            d = runs / nombre
            d.mkdir(parents=True)
            (d / "status.json").write_text(json.dumps({"session_id": sid}) if sid else "{")
            codex.append({"run_id": nombre, "phase": "executing", "pid": "123",
                          "pid_vivo": vivo, "output_file": nombre + ".out"})
        foto = {"ts_epoch": TS, "codex": codex}
        prompt = self.ns["prompt_restore"](fila, foto, str(runs))
        for palabra in ("mia", "Codex", "subagent", "background", "human"):
            self.assertIn(palabra.lower(), prompt.lower())
        for nombre in ("ajena", "viva.out", "rota.out"):
            self.assertNotIn(nombre, prompt)
        orden = self.ns["orden_restore"](fila, prompt,
                   plantilla="'/Applications/Claude CLI/claude' --resume {id}")
        self.assertEqual(orden, ["/Applications/Claude CLI/claude", "--resume", fila["session_id"], prompt])
        orden = self.ns["orden_restore"](fila, prompt)
        self.assertEqual(orden[:3], ["/never-run/claude", "--resume", fila["session_id"]])
        self.assertEqual(orden[-1], prompt)

    def test_entorno_llega_a_guiones_y_all_no_despierta_hibernadas(self):
        filas = [sesion(n, self.raiz) for n in range(1, 5)]
        ruta = self.snapshot(filas=filas)
        for fila, mt in zip(filas, (TS - 1, TS - 2, TS - 3601, TS - 1)):
            self.transcript(fila, mt)
        (ruta / "hibernadas").write_text(filas[3]["session_id"])
        os.environ.update(SERENO_RESTORE_STAGGER="7", SERENO_RESTORE_IDLE_HOURS="1",
                          SERENO_RESUME_CMD="'/fake Claude/cli' --resume {id}")
        rc, texto = self.ejecutar(["--yes", "--all"], cmux="")
        self.assertEqual(rc, 0, texto)
        guiones = {p[0]: pathlib.Path(shlex.split(p[1])[-1]).read_text() for p in self.abiertas}
        self.assertIn('-v espera=7.0 ', guiones["cc-2"])
        self.assertIn('-v espera=14.0 ', guiones["cc-3"])
        self.assertIn("Enter", guiones["cc-4"])
        self.assertIn('-v espera=0 ', guiones["cc-4"])
        self.assertLess(guiones["cc-4"].index("IFS= read"),
                        guiones["cc-4"].index("awk "))
        for guion in guiones.values():
            orden = shlex.split(next(l[5:] for l in guion.splitlines() if l.startswith("exec ")))
            self.assertEqual(orden[0], "/fake Claude/cli")
            self.assertEqual(orden[1], "--resume")
            self.assertIn("human", orden[-1].lower())
        self.assertIn(str(ruta), texto)

    def test_notify_una_vez_sin_lanzar(self):
        self.snapshot()
        avisos = []
        avisar = lambda titulo, cuerpo: avisos.append((titulo, cuerpo))
        for _ in range(2):
            self.assertEqual(self.ejecutar(["--notify", "--yes"], cmux="", notificar=avisar)[0], 0)
        self.assertEqual(len(avisos), 1)
        self.assertIn("sereno --restore", " ".join(avisos[0]))
        self.assertTrue((self.raiz / "restore" / ("avisado-%d" % (TS + 100))).exists())
        self.assertFalse(self.abiertas)
        self.assertFalse(self.ns["RUN"].exists())

    def test_notify_nada_o_todo_vivo(self):
        avisos = []
        avisar = lambda *args: avisos.append(args)
        self.assertEqual(self.ejecutar(["--notify"], cmux="", notificar=avisar)[0], 0)
        self.snapshot()
        self.ns["tmux_list"] = lambda: [("cc-1", 0, False, "", "0")]
        self.assertEqual(self.ejecutar(["--notify"], cmux="", notificar=avisar)[0], 0)
        self.assertFalse(avisos)
        self.assertFalse(list((self.raiz / "restore").glob("avisado-*")))

    def test_sin_tty_y_confirmacion_negativa_no_ejecutan(self):
        self.snapshot()
        with mock.patch.object(sys, "stdin", io.StringIO("")):
            rc, texto = self.ejecutar(cmux="")
        self.assertEqual(rc, 0)
        self.assertIn("cc-1", texto)
        self.assertFalse(self.abiertas)
        self.assertFalse(self.ns["RUN"].exists())
        entrada = io.StringIO("n\n")
        entrada.isatty = lambda: True
        with mock.patch.object(sys, "stdin", entrada):
            rc, texto = self.ejecutar(cmux="")
        self.assertEqual(rc, 0)
        self.assertFalse(self.abiertas)
        self.assertIn("[y/N]", texto)
        entrada = io.StringIO("y\n")
        entrada.isatty = lambda: True
        with mock.patch.object(sys, "stdin", entrada):
            self.assertEqual(self.ejecutar(cmux="")[0], 0)
        self.assertEqual(len(self.abiertas), 1)

    def test_guion_espera_enter_y_eof(self):
        testigo = self.raiz / "ejecutado"
        orden = " ".join(shlex.quote(p) for p in [sys.executable, "-c",
                    "import pathlib; pathlib.Path(%r).write_text('ok')" % str(testigo)])
        for entrada in ("", "\n"):
            ruta = self.ns["_guion"](orden, str(self.raiz), espera=0,
                                     esperar_enter=True, mensaje="hibernated · Enter to resume")
            resultado = subprocess.run(["/bin/sh", str(ruta)], input=entrada,
                                       capture_output=True, text=True, timeout=5)
            self.assertIn("Enter to resume", resultado.stdout)
            self.assertEqual(testigo.exists(), bool(entrada))
        ruta = self.ns["_guion"](orden, str(self.raiz), espera=2)
        self.assertIn("sleep 2", ruta.read_text())
        # Un sleep local deja constancia sin consumir dos segundos ni lanzar Claude.
        sleep = self.raiz / "sleep"
        marca = self.raiz / "retardo"
        sleep.write_text("#!/bin/sh\nprintf '%s' \"$1\" > " + shlex.quote(str(marca)) + "\n")
        sleep.chmod(0o700)
        r = subprocess.run(["/bin/sh", str(ruta)], capture_output=True, text=True,
                           env=dict(os.environ, PATH=str(self.raiz) + os.pathsep + os.environ["PATH"]),
                           timeout=5)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(marca.read_text(), "2")

    def test_layout_cmux_orden_refs_shell_y_sesion_sin_panel(self):
        filas = [sesion(n, self.raiz) for n in range(1, 7)]
        ruta = self.snapshot(filas=filas)
        for fila in filas:
            self.transcript(fila, TS - 1)
        paneles = [{"id": "p%d" % n, "directory": str(self.raiz),
                    "terminal": {"agent": {"sessionId": filas[n - 1]["session_id"]}}}
                   for n in range(1, 6)]
        paneles[1]["terminal"] = {"resumeBinding": {"checkpointId": "cc-2"}}
        paneles.append({"id": "shell", "directory": str(self.raiz / "shell")})
        (self.raiz / "shell").mkdir()
        workspaces = [
            {"customTitle": "Primero", "processTitle": "ignorado", "currentDirectory": str(self.raiz),
             "panels": paneles[:2], "layout": split("horizontal", pane("p1"), pane("p2"))},
            {"processTitle": "Segundo", "currentDirectory": str(self.raiz), "panels": paneles[2:],
             "layout": split("vertical", pane("p3", "p5"),
                             split("vertical", pane("p4"), pane("shell")))}]
        (ruta / "cmux.json").write_text(json.dumps({"windows": [{"tabManager": {"workspaces": workspaces}}]}))
        self.stub_cmux()
        rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 0, texto)
        llamadas = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertTrue(all(quiet == "1" for _, quiet in llamadas))
        ordenes = [a for a, _ in llamadas if a[0] not in ("ping", "list-windows")]
        # p5 estaba en una pestana NO seleccionada: se enumera, no reaparece al final.
        self.assertEqual([a[:2] for a in ordenes], [
            ["workspace", "create"], ["new-split", "right"],
            ["workspace", "create"], ["new-split", "down"], ["new-split", "down"],
            ["workspace", "create"]])
        for indice, nombre in ((0, "Primero"), (2, "Segundo"), (5, "cc-6")):
            a = ordenes[indice]
            self.assertEqual(a[a.index("--name") + 1], nombre)
        for indice, ref in ((1, "surface:1"), (3, "surface:3"), (4, "surface:4")):
            a = ordenes[indice]
            self.assertEqual(a[a.index("--surface") + 1], ref)
        for a in ordenes:
            self.assertEqual(a[a.index("--focus") + 1], "false")
        shell = ordenes[4]
        comando_shell = shell[shell.index("--command") + 1]
        guion_shell = pathlib.Path(shlex.split(comando_shell)[-1]).read_text()
        self.assertIn("cd " + shlex.quote(str(self.raiz / "shell")), guion_shell)
        self.assertNotIn("--resume", guion_shell)
        self.assertIn("p5", texto)
        self.assertIn("Divider positions", texto)
        self.assertFalse(self.abiertas)

    def test_arranque_sysctl_y_fallo(self):
        llamadas = []
        def sysctl(argv, **kw):
            llamadas.append(argv)
            return subprocess.CompletedProcess(argv, 0, "{ sec = 1700000100, usec = 1234 } Thu Nov")
        self.ns["subprocess"] = type("SysctlFalso", (), {
            "run": staticmethod(sysctl), "TimeoutExpired": subprocess.TimeoutExpired})
        self.assertEqual(self.ns["arranque_restore"](), TS + 100)
        self.assertEqual(llamadas, [["sysctl", "-n", "kern.boottime"]])
        self.ns["subprocess"].run = staticmethod(lambda *a, **k: subprocess.CompletedProcess([], 1, ""))
        self.assertIsNone(self.ns["arranque_restore"]())

    def test_arbol_puro_y_fallo_parcial_cmux(self):
        filas = [sesion(n, self.raiz) for n in (1, 2)]
        ruta = self.snapshot(filas=filas)
        ws = [{"customTitle": "ws-%d" % i, "currentDirectory": str(self.raiz),
               "layout": pane("p%d" % i), "panels": [{"id": "p%d" % i,
               "terminal": {"agent": {"sessionId": f["session_id"]}}}]}
              for i, f in enumerate(filas, 1)]
        datos = {"windows": [{"tabManager": {"workspaces": ws}}]}
        original = json.dumps(datos, sort_keys=True)
        entradas = self.ns["plan_restore"]({"sesiones": filas, "ts_epoch": TS})["entradas"]
        antes = json.dumps(entradas, sort_keys=True)
        resultado = self.ns["arbol_restore"](datos, entradas)
        self.assertEqual(len(resultado[0]), 2)
        self.assertEqual(json.dumps(datos, sort_keys=True), original)
        self.assertEqual(json.dumps(entradas, sort_keys=True), antes)
        (ruta / "cmux.json").write_text(json.dumps(datos))
        self.stub_cmux(falla="ws-2")
        rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 1)
        self.assertFalse(self.abiertas, "fallo parcial no debe duplicar en otro lanzador")
        self.assertIn("p2", texto)
        self.assertIn("1 waiting for Enter", texto)

    def test_configuracion_invalida(self):
        self.snapshot()
        for clave, valor in (("SERENO_RESTORE_STAGGER", "-1"),
                             ("SERENO_RESTORE_STAGGER", "nan"),
                             ("SERENO_RESTORE_IDLE_HOURS", "infinity"),
                             ("SERENO_RESUME_CMD", "claude --resume sin-id"),
                             ("SERENO_RESUME_CMD", "'comilla")):
            with mock.patch.dict(os.environ, {clave: valor}):
                self.assertEqual(self.ejecutar(["--yes"], cmux="")[0], 2, (clave, valor))
        self.assertFalse(self.abiertas)

    def test_cmux_no_disponible_reutiliza_lanzador(self):
        ruta = self.snapshot()
        (ruta / "cmux.json").write_text('{"windows": []}')
        self.stub_cmux(ping=1)
        rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 0, texto)
        self.assertEqual(len(self.abiertas), 1)
        llamadas = [json.loads(l)[0] for l in self.log.read_text().splitlines()]
        self.assertEqual(llamadas, [["ping"], ["list-windows"]])

    def test_panel_vivo_se_recrea_vacio(self):
        filas = [sesion(n, self.raiz) for n in (1, 2)]
        ruta = self.snapshot(filas=filas)
        self.ns["tmux_list"] = lambda: [("cc-1", 0, False, "", "0")]
        workspace = {"currentDirectory": str(self.raiz), "layout": pane("p1"),
                     "panels": [{"id": "p1", "directory": str(self.raiz),
                                 "terminal": {"agent": {"sessionId": filas[0]["session_id"]}}}]}
        (ruta / "cmux.json").write_text(json.dumps(
            {"windows": [{"tabManager": {"workspaces": [workspace]}}]}))
        self.stub_cmux()
        rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 0, texto)
        ordenes = [json.loads(l)[0] for l in self.log.read_text().splitlines()][1:]
        self.assertEqual(len(ordenes), 2)
        self.assertEqual(ordenes[0][ordenes[0].index("--name") + 1], "sereno")
        if "--command" in ordenes[0]:
            comando = ordenes[0][ordenes[0].index("--command") + 1]
            guion = pathlib.Path(shlex.split(comando)[-1]).read_text()
            self.assertNotIn("--resume", guion)
        self.assertEqual(ordenes[1][ordenes[1].index("--name") + 1], "cc-2")

    def test_cmux_estructura_rota_se_ignora(self):
        ruta = self.snapshot()
        self.stub_cmux()
        rotos = [{"windows": None},
                 {"windows": [{"tabManager": {"workspaces": [{"panels": [None]}]}}]},
                 {"windows": [{"tabManager": {"workspaces": [{"layout":
                     split("horizontal", "no-es-un-nodo", pane("shell"))}]}}]}]
        for campo, valor in (("customTitle", 123), ("currentDirectory", 123)):
            rotos.append({"windows": [{"tabManager": {"workspaces": [
                {campo: valor, "layout": pane("shell"), "panels": [{"id": "shell"}]}]}}]})
        rotos.append({"windows": [{"tabManager": {"workspaces": [
            {"layout": pane("shell"), "panels": [{"id": "shell", "directory": 123}]}]}}]})
        for layout in (split("diagonal", pane("shell"), pane("otro")),
                       {"type": "pane", "pane": {"panelIds": "shell", "selectedPanelId": "shell"}}):
            rotos.append({"windows": [{"tabManager": {"workspaces": [{"layout": layout}]}}]})
        for datos in rotos:
            with self.subTest(datos=datos):
                self.abiertas.clear()
                (ruta / "cmux.json").write_text(json.dumps(datos))
                foto = self.ns["lee_snapshot"](ruta)
                self.assertIsNone(foto["cmux"])
                self.assertEqual(foto["ignoradas"], 1)
                rc, texto = self.ejecutar(["--yes"])
                self.assertEqual(rc, 0, texto)
                self.assertEqual(len(self.abiertas), 1)
                self.assertIn("1 ignored rows", texto)
        self.assertFalse(self.log.exists(), "un export roto no debe llegar al CLI")

    def test_todas_vivas_recrea_layout_como_shells(self):
        fila = sesion(1, self.raiz)
        ruta = self.snapshot(filas=[fila])
        self.ns["tmux_list"] = lambda: [("cc-1", 0, False, "", "0")]
        workspace = {"customTitle": "Vivas", "currentDirectory": str(self.raiz),
                     "layout": pane("p1"), "panels": [{"id": "p1",
                         "directory": str(self.raiz),
                         "terminal": {"agent": {"sessionId": fila["session_id"]}}}]}
        (ruta / "cmux.json").write_text(json.dumps(
            {"windows": [{"tabManager": {"workspaces": [workspace]}}]}))
        self.stub_cmux()
        avisos = []
        self.assertEqual(self.ejecutar(["--notify"], notificar=lambda *a: avisos.append(a))[0], 0)
        self.assertFalse(avisos)
        self.assertFalse(self.log.exists())
        rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 0, texto)
        self.assertTrue(self.log.exists(), "el layout sigue teniendo terminales que recrear")
        llamadas = [json.loads(l)[0] for l in self.log.read_text().splitlines()]
        self.assertEqual([a[:2] for a in llamadas], [["ping"], ["workspace", "create"]])
        orden = llamadas[-1]
        comando = orden[orden.index("--command") + 1]
        guion = pathlib.Path(shlex.split(comando)[-1]).read_text()
        self.assertNotIn("--resume", guion)
        self.assertIn("0 launched", texto)
        self.assertIn("1 already live", texto)
        self.assertFalse(self.abiertas)

    def test_fallo_raiz_enumera_todos_los_paneles_perdidos(self):
        filas = [sesion(n, self.raiz) for n in (1, 2, 3)]
        ruta = self.snapshot(filas=filas)
        workspace = {"customTitle": "Falla", "currentDirectory": str(self.raiz),
                     "layout": split("horizontal", pane("p1"),
                                     split("vertical", pane("p2"), pane("p3"))),
                     "panels": [{"id": "p%d" % i,
                                 "terminal": {"agent": {"sessionId": f["session_id"]}}}
                                for i, f in enumerate(filas, 1)]}
        (ruta / "cmux.json").write_text(json.dumps(
            {"windows": [{"tabManager": {"workspaces": [workspace]}}]}))
        for falla, perdidos in (("Falla", ("p1", "p2", "p3")),
                                ("new-split", ("p2", "p3"))):
            with self.subTest(falla=falla):
                if self.log.exists():
                    self.log.unlink()
                self.stub_cmux(falla=falla)
                rc, texto = self.ejecutar(["--yes"])
                self.assertEqual(rc, 1)
                resumen = [l for l in texto.splitlines() if "Panels not recreated:" in l][-1]
                for panel in perdidos:
                    self.assertIn(panel, resumen)
                if falla == "new-split":
                    self.assertNotIn("p1", resumen)
                self.assertFalse(self.abiertas)

    def test_puerta_cmux_despues_del_layout_y_retardos_del_plan(self):
        filas = [sesion(n, self.raiz) for n in (1, 2)]
        ruta = self.snapshot(filas=filas)
        for fila, mt in zip(filas, (TS - 1, TS - 2)):
            self.transcript(fila, mt)
        os.environ["SERENO_RESTORE_STAGGER"] = "10"
        paneles = [{"id": nombre, "directory": str(self.raiz)}
                   for nombre in ("B", "shell1", "shell2", "A")]
        for panel, fila in ((paneles[0], filas[1]), (paneles[3], filas[0])):
            panel["terminal"] = {"agent": {"sessionId": fila["session_id"]}}
        ws = {"currentDirectory": str(self.raiz), "panels": paneles,
              "layout": split("horizontal", pane("B"),
                  split("vertical", pane("shell1"),
                        split("horizontal", pane("shell2"), pane("A"))))}
        (ruta / "cmux.json").write_text(json.dumps(
            {"windows": [{"tabManager": {"workspaces": [ws]}}]}))
        self.stub_cmux(latencia=0.03)
        reemplazar = os.replace
        publicadas = []

        def publica(temporal, puerta):
            temporal, puerta = pathlib.Path(temporal), pathlib.Path(puerta)
            self.assertEqual(temporal.parent, puerta.parent)
            self.assertFalse(puerta.exists())
            finales = (self.raiz / "fin-cmux").read_text().splitlines()
            self.assertEqual(len(finales), 4)
            self.assertGreaterEqual(int(temporal.read_text()), int(float(finales[-1])))
            self.assertEqual(len(self.log.read_text().splitlines()), 5)
            reemplazar(temporal, puerta)
            publicadas.append(puerta)

        with mock.patch.object(os, "replace", side_effect=publica):
            rc, texto = self.ejecutar(["--yes"])
        self.assertEqual(rc, 0, texto)
        self.assertEqual(len(publicadas), 1)
        puerta = publicadas[0]
        self.assertRegex(puerta.name, r"^puerta-[0-9a-f]{12}$")
        self.assertEqual(puerta.parent.stat().st_mode & 0o777, 0o700)
        ordenes = [json.loads(l)[0] for l in self.log.read_text().splitlines()][1:]
        guiones = [pathlib.Path(shlex.split(a[a.index("--command") + 1])[-1]).read_text()
                   for a in ordenes]
        for guion in guiones:
            self.assertIn(shlex.quote(str(puerta)), guion)
        self.assertIn(filas[1]["session_id"], guiones[0])
        self.assertIn('-v espera=10.0 ', guiones[0])
        self.assertIn(filas[0]["session_id"], guiones[3])
        self.assertIn('-v espera=0.0 ', guiones[3])

    def test_puerta_sin_cmux_despues_de_ambos_grupos_incluso_fallo(self):
        filas = [sesion(n, self.raiz) for n in (1, 2)]
        self.snapshot(filas=filas)
        self.transcript(filas[0], TS - 1)
        llamadas = []

        def abre(pestanas, config, cual=None):
            self.assertFalse(list(self.ns["RUN"].glob("puerta-*")))
            llamadas.append(pestanas)
            return "stub", 0

        self.ns["abre_varias"] = abre
        self.assertEqual(self.ejecutar(["--yes"], cmux="")[0], 1)
        self.assertEqual(len(llamadas), 2)
        puertas = list(self.ns["RUN"].glob("puerta-*"))
        self.assertEqual(len(puertas), 1)
        self.assertTrue(puertas[0].read_text().isdigit())
        for grupo in llamadas:
            guion = pathlib.Path(shlex.split(grupo[0][1])[-1]).read_text()
            self.assertIn(shlex.quote(str(puertas[0])), guion)
        self.ns["abre_varias"] = mock.Mock(side_effect=OSError("panel rechazado"))
        with self.assertRaises(OSError):
            self.ejecutar(["--yes"], cmux="")
        nuevas = set(self.ns["RUN"].glob("puerta-*")) - set(puertas)
        self.assertEqual(len(nuevas), 1)
        self.assertTrue(nuevas.pop().read_text().isdigit())

    def test_puerta_cmux_se_publica_aunque_falle_un_panel(self):
        fila = sesion(1, self.raiz)
        foto = self.ns["lee_snapshot"](self.snapshot(filas=[fila]))
        entradas = self.ns["plan_restore"](foto)["entradas"]
        workspaces, _, _ = self.ns["arbol_restore"]({"windows": []}, entradas)
        self.stub_cmux(falla="workspace")
        hechas, fallos = self.ns["ejecuta_cmux_restore"](str(self.cmux), workspaces, foto, "")
        self.assertFalse(hechas)
        self.assertEqual(fallos, ["cc-1"])
        puertas = list(self.ns["RUN"].glob("puerta-*"))
        self.assertEqual(len(puertas), 1)
        self.assertTrue(puertas[0].read_text().isdigit())

    def test_guiones_reales_puerta_escalona_cero_y_un_segundo(self):
        puerta = self.raiz / "puerta con ' comilla"
        salidas = [self.raiz / ("salida-%d" % n) for n in (0, 1)]
        guiones = [self.ns["_guion"]("date +%s > " + shlex.quote(str(salida)),
                    str(self.raiz), espera=2 * n, puerta=puerta)
                   for n, salida in enumerate(salidas)]
        # Los guiones arrancan ANTES de la puerta: tienen que esperarla, no encontrarla.
        procesos = [subprocess.Popen(["/bin/sh", str(guion)], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE) for guion in guiones]
        time.sleep(1.5)
        self.assertFalse(any(s.exists() for s in salidas))
        t0 = int(time.time())
        puerta.write_text(str(t0))
        try:
            for proceso in procesos:
                _, err = proceso.communicate(timeout=5)
                self.assertEqual(proceso.returncode, 0, err)
        finally:
            for proceso in procesos:
                if proceso.poll() is None:
                    proceso.kill()
                    proceso.wait()
        cero, uno = [int(s.read_text()) for s in salidas]
        self.assertGreaterEqual(cero, t0)
        self.assertGreater(uno, cero)

    def test_guion_puerta_sondeo_acotado_y_epoch_pasado(self):
        puerta = self.raiz / "puerta ausente"
        marca = self.raiz / "sondeos"
        sleep = self.raiz / "sleep"
        sleep.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" >> " + shlex.quote(str(marca)) + "\n")
        sleep.chmod(0o700)
        for contenido, sondeos in ((None, 300), ("1", 0), ("no-es-epoch", 0)):
            if contenido is not None:
                puerta.write_text(contenido)
            marca.write_text("")
            guion = self.ns["_guion"]("printf terminado", str(self.raiz), espera=1, puerta=puerta)
            resultado = subprocess.run(["/bin/sh", str(guion)], capture_output=True, text=True,
                env=dict(os.environ, PATH=str(self.raiz) + os.pathsep + os.environ["PATH"]), timeout=5)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertEqual(resultado.stdout, "terminado")
            self.assertEqual(marca.read_text().splitlines(), ["1"] * sondeos)

    def test_guion_sin_puerta_conserva_bytes(self):
        for espera, enter in ((0, False), (2, False), (2, True)):
            ruta = self.ns["_guion"]("printf listo", str(self.raiz), espera=espera,
                                      esperar_enter=enter, mensaje="mensaje")
            antes = "printf '%s\\n' mensaje\nIFS= read -r respuesta || exit 1\n" if enter else ""
            if espera:
                antes += "sleep 2\n"
            esperado = ("#!/bin/sh\ncd %s || exit 1\nunset TMUX\nrm -f -- %s\n%sexec printf listo\n"
                        % (shlex.quote(str(self.raiz)), shlex.quote(str(ruta)), antes))
            self.assertEqual(ruta.read_bytes(), esperado.encode())

    def test_cmd_limpia_solo_puertas_de_mas_de_un_dia(self):
        self.ns["RUN"].mkdir()
        ahora = time.time()
        for nombre, edad in (("puerta-vieja", 86401), ("puerta-reciente", 86399),
                             ("lanza-viejo.sh", 90000)):
            p = self.ns["RUN"] / nombre
            p.touch()
            os.utime(str(p), (ahora - edad, ahora - edad))
        self.assertEqual(self.ejecutar(cmux="")[0], 1)
        self.assertFalse((self.ns["RUN"] / "puerta-vieja").exists())
        self.assertTrue((self.ns["RUN"] / "puerta-reciente").exists())
        self.assertTrue((self.ns["RUN"] / "lanza-viejo.sh").exists())
        with mock.patch.object(pathlib.Path, "unlink", side_effect=OSError("sin acceso")):
            os.utime(str(self.ns["RUN"] / "puerta-reciente"), (1, 1))
            self.assertEqual(self.ejecutar(cmux="")[0], 1)

    def test_prompt_respaldo_runs_sin_acceso_o_tabla_vacia(self):
        fila = sesion(1)
        ruta = self.snapshot(filas=[fila])
        with (ruta / "meta.txt").open("a") as f:
            f.write("codex_runs=sin_acceso\nextra=con=igual\n")
        foto = self.ns["lee_snapshot"](ruta)
        self.assertEqual(foto["meta"]["codex_runs"], "sin_acceso")
        self.assertEqual(foto["meta"]["extra"], "con=igual")
        runs = self.raiz / "runs"
        for nombre, cambios in (
                ("z-mia", {}), ("ajena", {"session_id": sesion(2)["session_id"]}),
                ("terminada", {"phase": "done"}), ("viva", {"pid": 12}),
                ("sin-permiso", {"pid": 13}), ("bool", {"pid": True}),
                ("cadena", {"pid": "11"}), ("sin-pid", {"pid": None})):
            d = runs / nombre
            d.mkdir(parents=True)
            estado = dict(session_id=fila["session_id"], phase="executing", pid=11,
                          output_file=nombre + ".out")
            estado.update(cambios)
            (d / "status.json").write_text(json.dumps(estado))

        def kill(pid, signal):
            self.assertEqual(signal, 0)
            if pid == 11:
                raise ProcessLookupError()
            if pid == 13:
                raise PermissionError()
            self.assertEqual(pid, 12)

        for meta in (foto["meta"], {}):
            foto["meta"] = meta
            with mock.patch.object(os, "kill", side_effect=kill):
                prompt = self.ns["prompt_restore"](fila, foto, str(runs))
            lineas = [l for l in prompt.splitlines() if l.startswith("Orphaned Codex run:")]
            self.assertEqual(lineas, ["Orphaned Codex run: z-mia · phase: executing · output: z-mia.out"])
        d = runs / "a-mia"
        d.mkdir()
        (d / "status.json").write_text(json.dumps(dict(
            session_id=fila["session_id"], phase="executing", pid=11)))
        with mock.patch.object(os, "kill", side_effect=kill):
            prompt = self.ns["prompt_restore"](fila, foto, str(runs))
        self.assertIn("a-mia · phase: executing · output: ?", prompt)
        self.assertLess(prompt.index("a-mia"), prompt.index("z-mia"))

    def test_flags_alias_from_y_despacho(self):
        ruta = self.snapshot()
        for alias in ("--restore", "--restaurar"):
            args = [alias, "--from", str(ruta), "--yes", "--all", "--notify"]
            self.assertEqual(self.ns["flags_desconocidos"](args), [])
            self.assertIn(alias, self.ns["_SIN_SELECTOR"])
            self.assertIn(alias, self.ns["__doc__"])
            llamadas = []
            with mock.patch.dict(self.ns, cmd_restore=lambda argv: llamadas.append(argv) or 17):
                with mock.patch.object(sys, "argv", ["sereno"] + args):
                    self.assertEqual(self.ns["main"](), 17)
            self.assertEqual(len(llamadas), 1)
        self.assertEqual(self.ejecutar(["--from"], cmux="")[0], 2)
        self.assertEqual(self.ejecutar(["--from", "--yes"], cmux="")[0], 2)


# Se completa con anclas de las guardas del modo nuevo. Solo se muta una copia
# en memoria: una interrupcion nunca deja roto el ejecutable del usuario.
MUTANTES = [
    ("la puerta se publica antes de crear el layout",
     '    try:\n        for ws in workspaces:',
     '    _abre_puerta_restore(puerta)\n    try:\n        for ws in workspaces:',
     "test_puerta_cmux_despues_del_layout_y_retardos_del_plan"),
    ("el guion pierde el retardo asignado por el plan",
     'espera=e["retardo"], esperar_enter=e["esperar"]',
     'espera=0, esperar_enter=e["esperar"]',
     "test_puerta_cmux_despues_del_layout_y_retardos_del_plan"),
    ("el sondeo termina antes de las 300 vueltas",
     '-lt 300', '-lt 299', "test_guion_puerta_sondeo_acotado_y_epoch_pasado"),
    ("una tabla vacia no busca runs en disco",
     'respaldo = not runs', 'respaldo = False',
     "test_prompt_respaldo_runs_sin_acceso_o_tabla_vacia"),
    ("un booleano se acepta como pid de una run",
     'type(pid) is not int', 'not isinstance(pid, int)',
     "test_prompt_respaldo_runs_sin_acceso_o_tabla_vacia"),
    ("cmux acepta un directorio que no es texto",
     '        if not isinstance(directory, str):', '        if False:',
     "test_cmux_estructura_rota_se_ignora"),
    ("fallar un workspace oculta sus paneles descendientes",
     'for ws in workspaces for p in hojas(ws["layout"]) if id(p) not in creadas',
     'for ws in workspaces for p in [next(hojas(ws["layout"]))] if id(p) not in creadas',
     "test_fallo_raiz_enumera_todos_los_paneles_perdidos"),
    ("un export cmux estructuralmente roto se acepta",
     '            arbol_restore(datos, [])', '            pass',
     "test_cmux_estructura_rota_se_ignora"),
    ("todas vivas impide reconstruir los terminales vacios",
     '    runs_dir = _env("RUNS_DIR")',
     '    if not entradas:\n        return 0\n    runs_dir = _env("RUNS_DIR")',
     "test_todas_vivas_recrea_layout_como_shells"),
    ("un snapshot del arranque mismo se acepta",
     'and 0 < s["ts_epoch"] < arranque', 'and 0 < s["ts_epoch"] <= arranque',
     "test_elige_anterior_y_no_posterior_ni_igual"),
    ("sin snapshot se anuncia exito",
     'return 0 if avisar else 1', 'return 0', "test_sin_snapshot"),
    ("la antiguedad ignora las horas configuradas",
     'elif mt < snapshot["ts_epoch"] - idle_hours * 3600:',
     'elif mt < snapshot["ts_epoch"] - idle_hours:', "test_clasifica_orden_retardos_y_all"),
    ("el orden reciente se invierte",
     '(prioridad[e["estado"]], -e["mtime"])', '(prioridad[e["estado"]], e["mtime"])',
     "test_clasifica_orden_retardos_y_all"),
    ("all despierta tambien las hibernadas",
     'esperar=estado == "hibernada" or (estado == "quieta" and not todas)',
     'esperar=estado in ("hibernada", "quieta") and not todas',
     "test_entorno_llega_a_guiones_y_all_no_despierta_hibernadas"),
    ("se duplica una sesion viva por id",
     'if nombre in nombres or sid in ids_vivos:', 'if nombre in nombres:',
     "test_excluye_tmux_e_id_vivos"),
    ("se duplica un panel de sesion viva en tmux",
     'if nombre in nombres or sid in ids_vivos:', 'if sid in ids_vivos:',
     "test_panel_vivo_se_recrea_vacio"),
    ("la marca hibernada deja de clasificar",
     'if sid in dormidas or nombre in dormidas:', 'if False:',
     "test_tolerancia_y_tokens_hibernadas"),
    ("el prompt recibe runs de otra sesion",
     'or estado.get("session_id") != entrada["session_id"]', 'or False',
     "test_prompt_runs_y_tokens_sin_shell"),
    ("la plantilla pierde las comillas de la ruta",
     'partes = shlex.split(plantilla)', 'partes = plantilla.split()',
     "test_prompt_runs_y_tokens_sin_shell"),
    ("cada aviso usa una marca nueva",
     'marca = base / ("avisado-%d" % inicio)',
     'marca = base / ("avisado-" + uuid.uuid4().hex)',
     "test_notify_una_vez_sin_lanzar"),
    ("se avisa aunque todas esten vivas",
     '    if avisar:\n        if entradas:', '    if avisar:\n        if True:',
     "test_notify_nada_o_todo_vivo"),
    ("no se pide confirmacion antes de ejecutar",
     '    if "--yes" not in flags:', '    if False:',
     "test_sin_tty_y_confirmacion_negativa_no_ejecutan"),
    ("EOF reanuda sin pulsar Enter",
     'IFS= read -r respuesta || exit 1', 'IFS= read -r respuesta',
     "test_guion_espera_enter_y_eof"),
    ("el guion ignora el retardo",
     '    if espera > 0:', '    if False:', "test_guion_espera_enter_y_eof"),
    ("cmux pierde el surface del segundo subarbol",
     '        divide(n["second"], otra)', '        divide(n["second"], superficie)',
     "test_layout_cmux_orden_refs_shell_y_sesion_sin_panel"),
    ("cmux intercambia los ejes",
     'direccion="right" if s.get("orientation") == "horizontal" else "down"',
     'direccion="down" if s.get("orientation") == "horizontal" else "right"',
     "test_layout_cmux_orden_refs_shell_y_sesion_sin_panel"),
    ("una pestana no seleccionada reaparece al final",
     'if e["session_id"] not in representadas:', 'if e["session_id"] not in usadas:',
     "test_layout_cmux_orden_refs_shell_y_sesion_sin_panel"),
    ("la deteccion de cmux omite list-windows",
     'for prueba in (["ping"], ["list-windows"]):', 'for prueba in (["ping"],):',
     "test_cmux_no_disponible_reutiliza_lanzador"),
    ("el timestamp del kernel no se interpreta",
     'return int(m.group(1)) if r.returncode == 0 and m else None',
     'return None', "test_arranque_sysctl_y_fallo"),
    ("la configuracion acepta retardos negativos",
     'if not (0 <= stagger < float("inf") and 0 <= idle < float("inf")):',
     'if not (stagger < float("inf") and 0 <= idle < float("inf")):',
     "test_configuracion_invalida"),
    ("cmux cuenta como abierta la superficie rechazada",
     'if not r or r.returncode != 0 or "surface" not in refs or "workspace" not in refs:',
     'if not r:', "test_arbol_puro_y_fallo_parcial_cmux"),
    ("el modo restaurar no llega al despacho",
     '    if "--restore" in argv or "--restaurar" in argv:',
     '    if False:', "test_flags_alias_from_y_despacho"),
]


def main():
    global CODIGO
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Restaurar)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if not resultado.wasSuccessful():
        return 1
    for nombre, ancla, cambio, test in MUTANTES:
        if FUENTE.count(ancla) != 1:
            print("FALLA: ancla obsoleta:", nombre)
            return 1
        CODIGO = compile(FUENTE.replace(ancla, cambio, 1), "sereno-mutado", "exec")
        salida = io.StringIO()
        resultado = unittest.TextTestRunner(stream=salida).run(Restaurar(test))
        if resultado.wasSuccessful():
            print("FALLA: mutante vivo:", nombre)
            return 1
        print("muere:", nombre)
    print("ok: %d casos y %d mutantes de restore" %
          (unittest.defaultTestLoader.loadTestsFromTestCase(Restaurar).countTestCases(), len(MUTANTES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
