#!/usr/bin/env python3
"""El registro que escribe Claude Code (`~/.claude/sessions/<pid>.json`) afina el estado.

Es la tercera fuente y la unica que dice si la sesion trabaja o te espera SIN abrir el
transcript. Importa por dos casos que el `mtime` no puede ver, y los dos salen aqui:

  · una sesion tres minutos dentro de un `Bash` no escribe nada, asi que por fecha de
    modificacion figura parada justo mientras trabaja;
  · una sesion pidiendote permiso tiene un `tool_use` sin `tool_result`, asi que sereno
    decia "esperando a un comando suyo" cuando en realidad te esperaba a ti.

Y por dos formas de mentir que este test existe para impedir: un `status` que no
conocemos NO puede leerse como `idle` (un dato que falta no es un dato bueno), y un
fichero cuyo PID ya no corre NO puede seguir diciendo `busy` para siempre.
"""
import json
import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TMP = tempfile.TemporaryDirectory()
SESIONES = pathlib.Path(TMP.name) / "sessions"
SESIONES.mkdir()
# ANTES del exec: `SESIONES_CC` se calcula al importar el modulo, igual que ROOT/LIVE.
os.environ["SERENO_CLAUDE_SESSIONS_DIR"] = str(SESIONES)

ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

VIVO, MUERTO = 4242, 4343


def escribe(pid, sid, status=None, espera=None, extra=None):
    j = {"pid": pid, "sessionId": sid, "cwd": "/x", "version": "2.1.263"}
    if status is not None:
        j["status"] = status
    if espera is not None:
        j["waitingFor"] = espera
    j.update(extra or {})
    (SESIONES / ("%d.json" % pid)).write_text(json.dumps(j))


def prepara():
    """La carpeta de fixtures, y un `ps` de mentira que solo da por vivo a un PID."""
    for p in SESIONES.glob("*.json"):
        p.unlink()
    ns["pids_vivos"] = lambda pids: {p for p in pids if int(p) == VIVO}
    ns["_CACHE_CC"].clear()


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    # ── decodificacion: hechos, y `None` para lo que no se entiende ────────────
    prepara()
    f(ns["hechos_cc"]({"pid": VIVO, "sessionId": "s", "status": "busy"})["estado"]
      == "busy", "un status busy no se decodifica como busy")
    f(ns["hechos_cc"]({"pid": VIVO, "sessionId": "s", "status": "hibernating"})["estado"]
      == "idle", "hibernating deberia caer en idle: la sesion vive y no hace nada")
    sin = ns["hechos_cc"]({"pid": VIVO, "sessionId": "s"})
    f(sin["estado"] is None,
      "un fichero SIN status da %r y tiene que dar None: no consta no es parada"
      % (sin["estado"],))
    raro = ns["hechos_cc"]({"pid": VIVO, "sessionId": "s", "status": "loquesea"})
    f(raro["estado"] is None,
      "un status desconocido da %r; el formato es de otro programa y puede crecer"
      % (raro["estado"],))
    f(ns["hechos_cc"]({"sessionId": "s", "status": "busy"}) is None,
      "un fichero sin pid no se puede emparejar y deberia descartarse entero")
    f(ns["hechos_cc"]({"pid": VIVO, "status": "busy"}) is None,
      "un fichero sin sessionId no se puede emparejar y deberia descartarse entero")
    f(ns["hechos_cc"]("[]") is None, "algo que no es un objeto no deberia colar")

    # ── la carpeta entera, y el filtro por proceso vivo ────────────────────────
    prepara()
    escribe(VIVO, "aaa", "busy")
    escribe(MUERTO, "bbb", "busy")
    (SESIONES / "roto.json").write_text("{esto no es json")
    crudo = ns["lee_registro_cc"]()
    f(set(crudo) == {"aaa", "bbb"},
      "leer la carpeta deberia dar las dos sesiones y da %s" % sorted(crudo))
    vivo = ns["registro_cc"]()
    f(set(vivo) == {"aaa"},
      "el fichero de un PID muerto sigue contando: %s" % sorted(vivo))
    f(vivo["aaa"]["estado"] == "busy", "la sesion viva perdio su estado")

    # ── la cache no puede tapar un cambio de estado para siempre ───────────────
    escribe(VIVO, "aaa", "waiting", "permission prompt")
    f(ns["registro_cc"]()["aaa"]["estado"] == "busy",
      "dentro del TTL deberia servir lo cacheado")
    f(ns["registro_cc"](ahora=ns["time"].time() + ns["TTL_CC"] + 1)["aaa"]["estado"]
      == "waiting", "pasado el TTL la cache no se refresca y el estado se congela")
    f(ns["registro_cc"](ahora=ns["time"].time() + ns["TTL_CC"] + 1)["aaa"]["espera"]
      == "permission prompt", "el `waitingFor` no llega hasta arriba")

    # ── la tabla de afinado: corrige el veredicto del transcript, no lo sustituye ──
    casos = [
        # (estado del transcript, registro, parada, esperado, por que)
        ("waiting", None, False, "waiting",
         "sin registro tiene que salir exactamente lo de siempre"),
        ("in_command", None, False, "in_command",
         "sin registro tiene que salir exactamente lo de siempre"),
        ("waiting", "busy", False, "writing",
         "esta dentro de un comando largo y el mtime la da por parada"),
        ("stopped", "busy", True, "writing",
         "lleva horas sin escribir pero el CLI dice que esta trabajando"),
        ("in_command", "busy", False, "in_command",
         "`in_command` es mas concreto que `writing` y no se pierde"),
        ("in_command", "waiting", False, "waiting",
         "te esta pidiendo permiso: te espera a ti, no a un comando suyo"),
        ("writing", "waiting", False, "waiting",
         "el CLI ya dice que acabo; los 90 s del mtime son estela"),
        ("writing", "waiting", True, "stopped",
         "lleva horas parada, y eso lo dice el idle, no el registro"),
        ("writing", "idle", False, "waiting",
         "sin turno abierto no esta escribiendo"),
        ("in_command", "idle", False, "in_command",
         "registro y transcript se contradicen: gana el mas concreto"),
        ("unknown", "busy", False, "writing",
         "sin transcript legible el registro sigue sabiendo que trabaja"),
    ]
    for est, reg, parada, esperado, por_que in casos:
        sale = ns["afina_con_registro"](est, reg, parada)
        f(sale == esperado, "afinado (%r, %r, parada=%s) -> %r y se esperaba %r: %s"
          % (est, reg, parada, sale, esperado, por_que))

    # ── y de punta a punta: pulso -> estado_estable -> _fase ───────────────────
    prepara()
    escribe(VIVO, "ccc", "waiting", "permission prompt")
    t = pathlib.Path(TMP.name) / "ccc.jsonl"
    t.write_text(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "T1", "name": "Bash", "input": {"command": "ls"}}]}}) + "\n")
    pu = ns["pulso"]({"id": "ccc", "_transcript": t})
    f(pu.get("registro") == "waiting",
      "`pulso` no publica el estado del registro: %r" % (pu.get("registro"),))
    f(pu.get("herramienta") is True,
      "el fixture tenia que dejar una herramienta a medias, para que haya conflicto")
    r = {"name": "ccc", "idle": 3, "pulso": pu}
    f(ns["estado_estable"](r) == "waiting",
      "con permiso pedido, el estado deberia ser waiting y es %r"
      % ns["estado_estable"](r))
    f(ns["_fase"](r) == ns["_"]("waiting for you to allow a tool"),
      "el panel no dice que te esta pidiendo permiso: %r" % ns["_fase"](r))

    # ── y la parte de DESCUBRIR: el filtro por mtime no puede tirar una sesion que
    #    el CLI da por ocupada, que es justo la que lleva minutos sin escribir ─────
    proyectos = pathlib.Path(TMP.name) / "projects" / "-x"
    proyectos.mkdir(parents=True, exist_ok=True)
    uuid = "11111111-2222-3333-4444-555555555555"
    viejo = proyectos / (uuid + ".jsonl")
    viejo.write_text(json.dumps({"type": "assistant", "message": {"content": []}}) + "\n")
    os.utime(str(viejo), (0, ns["time"].time() - 10 * ns["VIVA"]))
    ns["PROJECTS"] = proyectos.parent
    f(ns["sesiones_de_disco"](solo_activas=True) == [],
      "una sesion callada hace rato no deberia pasar el filtro por mtime")
    salen = ns["sesiones_de_disco"](solo_activas=True, protegidos={uuid})
    f(len(salen) == 1,
      "protegida por el registro, tendria que sobrevivir al filtro y salen %d" % len(salen))

    # CONTROL POSITIVO. Sin el, un test que no mirase el registro pasaria igual: se le
    # quita el fichero a la sesion y TIENE que volver al veredicto de antes.
    for p in SESIONES.glob("*.json"):
        p.unlink()
    ns["_CACHE_CC"].clear()
    pu2 = ns["pulso"]({"id": "ccc", "_transcript": t})
    r2 = {"name": "ccc", "idle": 3, "pulso": pu2}
    f(pu2.get("registro") is None, "sin fichero, el registro deberia ser None")
    f(ns["estado_estable"](r2) == "in_command",
      "CONTROL POSITIVO: sin registro tendria que volver a in_command y da %r"
      % ns["estado_estable"](r2))

    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos else
          "ok: el registro del CLI afina el estado, no lo sustituye, y un fichero de un "
          "PID muerto no cuenta")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
