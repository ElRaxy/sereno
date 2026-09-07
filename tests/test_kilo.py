#!/usr/bin/env python3
"""Las sesiones de Kilo Code, leidas de su sqlite y sin escribir en ella.

Kilo Code (fork de opencode) es el primer CLI de la lista que NO deja un fichero por
sesion: las guarda todas en una base comun. Eso mueve dos riesgos de sitio, y son los
dos que este test sujeta:

  · **la base es de otro programa.** Se abre en SOLO LECTURA y por URI; si el modo se
    pierde, `sereno` estaria abriendo en escritura la base que Kilo tiene viva. Aqui se
    comprueba por las malas: se intenta escribir por esa misma conexion y tiene que
    fallar. Sin ese caso, `mode=ro` es una cadena que nadie verifica.
  · **el esquema es de upstream y puede moverse.** Kilo Code v2 lleva parches sobre
    opencode: si una tabla o una columna cambia de nombre, la consulta revienta. El
    contrato es que la lista se quede vacia, NUNCA que se lleve por delante a las
    sesiones de los demas CLI. Se prueba con una base corrupta y con una ausente.

Y lo demas que se afirma en el codigo y no se ve mirando: que las subsesiones
(`parent_id`) y las archivadas (`time_archived`) no se listan, que los tiempos de Kilo
van en MILISEGUNDOS, y que `_pulso_kilo` publica HECHOS —las cinco claves de `pulso()`—
sin componer ningun veredicto, que es lo que exige la frontera LLM/codigo.

El esquema de la base sintetica sale del fuente de Kilo Code en el commit `7de8f5b`:
`packages/core/src/session/sql.ts:22` (session), `:71` (message), `:85` (part),
`packages/core/src/control-plane/workspace.sql.ts:6` (workspace) y
`packages/core/src/database/schema.sql.ts:3` (`time_created`/`time_updated`, en ms).

AVISO DE ALCANCE: esta base la escribe este test, no Kilo. Nadie ha corrido `kilo` en
esta maquina, asi que lo que aqui se prueba es que el lector hace lo que dice sobre el
esquema DOCUMENTADO — no que ese sea el esquema que Kilo escribe hoy.
"""
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import time
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
os.environ["SERENO_DEMO"] = "1"

ESQUEMA = """
CREATE TABLE session (
  id TEXT PRIMARY KEY, project_id TEXT, workspace_id TEXT, parent_id TEXT,
  slug TEXT, directory TEXT, path TEXT, title TEXT, version TEXT,
  cost REAL DEFAULT 0, tokens_input INTEGER DEFAULT 0, tokens_output INTEGER DEFAULT 0,
  agent TEXT, model TEXT,
  time_created INTEGER, time_updated INTEGER, time_archived INTEGER);
CREATE TABLE workspace (
  id TEXT PRIMARY KEY, type TEXT, name TEXT DEFAULT '', branch TEXT,
  directory TEXT, extra TEXT, project_id TEXT, time_used INTEGER);
CREATE TABLE message (
  id TEXT PRIMARY KEY, session_id TEXT,
  time_created INTEGER, time_updated INTEGER, data TEXT);
CREATE TABLE part (
  id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
  time_created INTEGER, time_updated INTEGER, data TEXT);
"""

AHORA = int(time.time() * 1000)


def base(ruta):
    """Una `kilo.db` sintetica con dos sesiones listables, una hija y una archivada."""
    con = sqlite3.connect(str(ruta))
    con.executescript(ESQUEMA)
    con.execute("INSERT INTO workspace (id, type, name, branch, project_id, time_used) "
                "VALUES ('w1', 'worktree', 'wt', 'feat/pagos', 'p1', ?)", (AHORA,))
    filas = [
        # id, workspace_id, parent_id, directory, title, time_updated, time_archived
        ("s-vieja", None, None, "/tmp/proyecto-viejo", "lo de ayer", AHORA - 90000000, None),
        ("s-viva", "w1", None, "/tmp/proyecto-vivo", "webhooks de pago", AHORA, None),
        ("s-hija", None, "s-viva", "/tmp/proyecto-vivo", "subagente", AHORA, None),
        ("s-archivada", None, None, "/tmp/otro", "guardada", AHORA, AHORA),
    ]
    for sid, wid, pid, direc, titulo, upd, arch in filas:
        con.execute(
            "INSERT INTO session (id, project_id, workspace_id, parent_id, slug, "
            "directory, title, version, time_created, time_updated, time_archived) "
            "VALUES (?, 'p1', ?, ?, ?, ?, ?, '2.0.0', ?, ?, ?)",
            (sid, wid, pid, sid, direc, titulo, upd - 1000, upd, arch))
    mensajes = [
        ("m1", "s-viva", AHORA - 3000, {"role": "user", "time": {"created": AHORA - 3000},
                                        "agent": "build"}),
        ("m2", "s-viva", AHORA - 2000,
         {"role": "assistant", "time": {"created": AHORA - 2000}, "modelID": "claude-sonnet-4",
          "providerID": "anthropic", "agent": "build", "finish": "stop",
          "path": {"cwd": "/tmp/proyecto-vivo", "root": "/tmp/proyecto-vivo"},
          "tokens": {"input": 120, "output": 30, "reasoning": 0,
                     "cache": {"read": 900, "write": 40}}}),
        # El ultimo assistant NO tiene `time.completed` y deja una herramienta corriendo:
        # es el estado "esta trabajando", y el que decide `escribe` y `herramienta`.
        ("m3", "s-viva", AHORA - 1000,
         {"role": "assistant", "time": {"created": AHORA - 1000}, "modelID": "gpt-5-codex",
          "providerID": "openai", "agent": "build",
          "path": {"cwd": "/tmp/proyecto-vivo", "root": "/tmp/proyecto-vivo"},
          "tokens": {"input": 200, "output": 10, "reasoning": 0,
                     "cache": {"read": 1000, "write": 0}}}),
    ]
    for mid, sid, creado, datos in mensajes:
        con.execute("INSERT INTO message (id, session_id, time_created, time_updated, data) "
                    "VALUES (?, ?, ?, ?, ?)", (mid, sid, creado, creado, json.dumps(datos)))
    partes = [
        ("p1", "m1", {"type": "text", "text": "arregla el reintento del webhook"}),
        ("p2", "m2", {"type": "text", "text": "hecho, quedan los tests"}),
        ("p3", "m2", {"type": "tool", "callID": "c1", "tool": "read",
                      "state": {"status": "completed", "title": "src/webhooks.py",
                                "input": {}, "output": "", "metadata": {},
                                "time": {"start": AHORA - 2500, "end": AHORA - 2400}}}),
        ("p4", "m3", {"type": "text", "text": "voy a correr los tests"}),
        ("p5", "m3", {"type": "tool", "callID": "c2", "tool": "bash",
                      "state": {"status": "running", "title": "pytest -q", "input": {},
                                "time": {"start": AHORA - 900}}}),
    ]
    for pid, mid, datos in partes:
        con.execute("INSERT INTO part (id, message_id, session_id, time_created, "
                    "time_updated, data) VALUES (?, ?, 's-viva', ?, ?, ?)",
                    (pid, mid, AHORA, AHORA, json.dumps(datos)))
    con.commit()
    con.close()


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    fallos = []

    def f(cond, que, extra=""):
        if not cond:
            fallos.append(que + (": " + extra if extra else ""))

    tmp = pathlib.Path(tempfile.mkdtemp())
    db = tmp / "kilo.db"
    base(db)
    os.environ["SERENO_KILO_DB"] = str(db)

    # ── control positivo ────────────────────────────────────────────────────
    # Sin el, todo lo que sigue ("no sale lo que no debe") lo cumpliria una lista vacia.
    filas = ns["sesiones_kilo"]()
    if len(filas) != 2:
        print("FALLA: el control positivo no lee la base: %d filas, se esperaban 2"
              % len(filas))
        return 1

    # ── lo que se lista y lo que no ─────────────────────────────────────────
    ids = [r["name"] for r in filas]
    f(ids == ["s-viva", "s-vieja"], "el orden no es por `time_updated` descendente",
      str(ids))
    f("s-hija" not in ids, "una subsesion (`parent_id`) se cuela en la lista")
    f("s-archivada" not in ids, "una sesion archivada se cuela en la lista")

    viva = filas[0]
    f(viva["fuente"] == "kilo", "la fila no dice de que CLI es")
    f(viva["title_full"] == "webhooks de pago", "el titulo no sale de `session.title`")
    f(viva["meta"]["cwd"] == "/tmp/proyecto-vivo",
      "el directorio no sale de `session.directory`")
    f(viva["meta"]["_rama"] == "feat/pagos",
      "la rama no sale del `workspace` enlazado", repr(viva["meta"].get("_rama")))
    f(filas[1]["meta"]["_rama"] == "",
      "una sesion sin worktree deberia quedarse sin rama, no reventar")
    # Los tiempos de Kilo van en milisegundos. Sin el /1000 esto sale en el ano 57000.
    f(abs(viva["created"] - AHORA / 1000.0) < 2,
      "el epoch no esta en segundos: Kilo guarda milisegundos", str(viva["created"]))
    f(viva["idle"] is not None and viva["idle"] < 90,
      "una sesion tocada ahora mismo no puede salir inactiva")
    f(viva["abrir"] == ["kilo", "--session", "s-viva"],
      "el comando de reabrir no es el documentado", str(viva["abrir"]))
    # El peso NO se publica: la base es de todos los proyectos a la vez.
    f(viva["mem_mb"] is None, "una fila de Kilo no puede traer memoria de proceso")

    # ── solo lectura, comprobado escribiendo ────────────────────────────────
    con = ns["_abre_kilo"](db)
    f(con is not None, "no se puede abrir la base de prueba")
    if con is not None:
        try:
            con.execute("DELETE FROM session")
            con.commit()
            fallos.append("la base se abrio en ESCRITURA: `mode=ro` no esta llegando")
        except sqlite3.OperationalError:
            pass
        finally:
            con.close()
        # Y que sigue entera despues del intento.
        f(len(ns["sesiones_kilo"]()) == 2, "el intento de escritura se llevo las filas")
    # Si el `mode=ro` se rompiera, ese DELETE habria vaciado la base y todo lo que
    # sigue hablaria de otra cosa —o reventaria por una lista vacia, que se lee como un
    # error del test y no del programa—. Se rehace antes de seguir.
    db.unlink()
    base(db)

    # ── una base que no esta, y una rota ────────────────────────────────────
    os.environ["SERENO_KILO_DB"] = str(tmp / "no-existe.db")
    f(ns["sesiones_kilo"]() == [], "sin base, la lista deberia estar vacia y no reventar")
    rota = tmp / "rota.db"
    rota.write_bytes(b"esto no es una base de datos, ni de lejos" * 40)
    os.environ["SERENO_KILO_DB"] = str(rota)
    try:
        f(ns["sesiones_kilo"]() == [], "una base corrupta deberia dar lista vacia")
    except sqlite3.DatabaseError as e:
        fallos.append("una base corrupta revienta la lista entera: %r" % e)
    # Y una base valida SIN el esquema de Kilo: es lo que pasaria si upstream renombra
    # una tabla. Tiene que caer igual, no llevarse por delante a los otros CLI.
    ajena = tmp / "ajena.db"
    otra = sqlite3.connect(str(ajena))
    otra.execute("CREATE TABLE cualquiera (x TEXT)")
    otra.commit()
    otra.close()
    os.environ["SERENO_KILO_DB"] = str(ajena)
    try:
        f(ns["sesiones_kilo"]() == [], "un esquema desconocido deberia dar lista vacia")
    except sqlite3.Error as e:
        fallos.append("un esquema desconocido revienta la lista: %r" % e)

    # ── el detalle y el pulso ───────────────────────────────────────────────
    os.environ["SERENO_KILO_DB"] = str(db)
    viva = ns["sesiones_kilo"]()[0]
    d = ns["_det_kilo"](viva)
    f(d.get("cwd") == "/tmp/proyecto-vivo", "el detalle no trae el directorio")
    f(d.get("gitBranch") == "feat/pagos", "el detalle no trae la rama")
    f(d.get("lastPrompt") == "arregla el reintento del webhook",
      "el detalle no trae lo ultimo que se le pidio", repr(d.get("lastPrompt")))
    f(d.get("resp") == "voy a correr los tests",
      "el detalle no trae lo ultimo que dijo", repr(d.get("resp")))
    f("peso" not in d, "el detalle publica un peso, y la base es de todos los proyectos")
    ruta = d.get("ruta") or []
    f(len(ruta) == 2, "la traza no recoge las dos llamadas a herramienta", str(len(ruta)))
    if len(ruta) == 2:
        f(ruta[0]["pend"] is False and ruta[0]["err"] is False,
          "una llamada `completed` no puede salir pendiente ni fallida")
        f(ruta[1]["pend"] is True, "una llamada `running` tiene que salir pendiente")
        f(abs((ruta[0]["dur"] or 0) - 0.1) < 0.01,
          "la duracion no sale de `state.time`", str(ruta[0]["dur"]))

    pu = ns["_pulso_kilo"](viva)
    f(set(pu) == {"escribe", "herramienta", "cerrado", "ctx", "modelo"},
      "el pulso no publica exactamente las cinco claves", str(sorted(pu)))
    f(pu["escribe"] is True, "un ultimo assistant sin `time.completed` es escribir")
    f(pu["herramienta"] is True, "una herramienta `running` es estar en un comando")
    f(pu["cerrado"] is False, "sin `finish`, el turno no esta cerrado")
    f(pu["modelo"] == "gpt-5-codex", "el modelo no sale del ultimo assistant")
    # `ctx` va a None a proposito: los tokens constan, el TOPE de ventana no.
    f(pu["ctx"] is None, "se publica contexto sin saber contra que tope se pinta")

    # El veredicto lo compone el codigo a partir de esos hechos, no el lector.
    viva["pulso"] = pu
    f(ns["estado_estable"](viva) == "in_command",
      "los hechos del pulso no componen el estado", ns["estado_estable"](viva))

    # Una sesion que ya termino su turno: los mismos hechos al reves.
    parada = ns["sesiones_kilo"]()[0]
    parada["meta"]["_kilo_cola"] = [
        {"id": "m9", "creado": AHORA, "partes": [],
         "data": {"role": "assistant", "time": {"created": AHORA, "completed": AHORA},
                  "finish": "stop", "modelID": "claude-sonnet-4"}}]
    pu2 = ns["_pulso_kilo"](parada)
    f(pu2["escribe"] is False and pu2["cerrado"] is True and pu2["herramienta"] is False,
      "un turno terminado sigue figurando como trabajo en curso", str(pu2))

    # Y la otra mitad de `escribe`: un ultimo assistant SIN `time.completed` en una
    # sesion que lleva dias quieta no es una sesion escribiendo, es una que se murio a
    # mitad. Sin este caso, el corte por `VIVA` se podria borrar y nadie se enteraria.
    abandonada = ns["sesiones_kilo"]()[1]
    abandonada["meta"]["_kilo_cola"] = [
        {"id": "m9", "creado": AHORA - 90000000, "partes": [],
         "data": {"role": "assistant", "time": {"created": AHORA - 90000000},
                  "modelID": "claude-sonnet-4"}}]
    f(ns["_pulso_kilo"](abandonada)["escribe"] is False,
      "una sesion quieta hace dias figura como escribiendo por un mensaje sin cerrar")

    # ── el glifo, que descuadra la tabla entera si mide dos ─────────────────
    gl = ns["GLIFO_CLI"].get("kilo")
    f(gl is not None, "Kilo no tiene glifo")
    if gl:
        f(unicodedata.east_asian_width(gl) == "N",
          "el glifo de Kilo no es de ancho neutro", unicodedata.east_asian_width(gl))
        f(ns["ancho"](gl) == 1, "el glifo de Kilo no mide una columna")
        f(len(set(ns["GLIFO_CLI"].values())) == len(ns["GLIFO_CLI"]),
          "el glifo de Kilo choca con el de otro CLI")
    f("kilo" in ns["ORDEN_FUENTES"], "Kilo no tiene pestana")
    f(ns["NOMBRE_CLI"].get("kilo") == "Kilo Code", "Kilo no tiene nombre legible")
    f(ns["cli_de"]({"fuente": "kilo"}) == "kilo", "una fila de Kilo no se reconoce")

    # ── no es destino de relevo, y se dice por que ──────────────────────────
    # Mismo mecanismo que `antigravity`: esta en los CLI conocidos y NO en `ARNESES`,
    # asi que el cuadro lo pinta apagado con el motivo. Sin `kilo --help` ejecutado en
    # esta maquina, poner un lanzador seria escribirlo a ojo.
    f("kilo" not in ns["ARNESES"],
      "Kilo entro como destino de relevo sin haber comprobado su `--help`")
    fuera = dict(ns["ausentes_de_relevo"]([]))
    f(fuera.get("kilo") == ns["_"]("not checked how to seed it"),
      "Kilo no sale como ausente con el motivo correcto", repr(fuera.get("kilo")))

    # ── el briefing apunta a donde esta la historia ─────────────────────────
    # Kilo no tiene fichero por sesion: el puntero util es la base MAS el id.
    texto = ns["briefing"](ns["sesiones_kilo"]()[0])
    f(str(db) in texto, "el briefing no dice donde esta la historia de la sesion")
    f("s-viva" in texto, "el briefing no dice de que sesion de la base habla")

    del os.environ["SERENO_KILO_DB"]
    for m in fallos:
        print("FALLO:", m)
    print("ok: la base de Kilo se lee en solo lectura, se filtra y compone estado"
          if not fallos else "%d fallo(s)" % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
