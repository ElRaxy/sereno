#!/usr/bin/env python3
"""El recorrido sale de hechos medidos y el veredicto lo compone el codigo.

Se prueba lo unico que puede mentir aqui sin dar error: que un bucle de fallos se cuente
como bucle, que un barrido sin resultados se distinga del trabajo util, que un dato que
no se pudo observar no valga por bueno, y que ninguna fila del panel escriba una columna
de mas — que en curses no revienta: envuelve el sobrante al principio de la fila
siguiente y el caracter huerfano aparece lejos del fallo que lo causo.
"""
import datetime, os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

recorrido, sintomas, alertas = ns["recorrido"], ns["sintomas"], ns["alertas"]
linea_ruta, ancho = ns["linea_ruta"], ns["ancho"]
RUTA_FIJO, MAX_EVENTOS = ns["RUTA_FIJO"], ns["MAX_EVENTOS"]

T0 = 1_756_000_000                       # un epoch cualquiera, fijo


def sello(d):
    return (datetime.datetime.fromtimestamp(T0 + d, datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.000") + "Z")


def uso(bid, nombre, t, **entrada):
    return {"type": "assistant", "timestamp": sello(t), "message": {"content": [
        {"type": "tool_use", "id": bid, "name": nombre, "input": entrada}]}}


def res(bid, t, texto, error=False):
    return {"type": "user", "timestamp": sello(t), "message": {"content": [
        {"type": "tool_result", "tool_use_id": bid, "is_error": error,
         "content": texto}]}}


def tanda(comando, veces, salida, error, desde=0):
    fuera = []
    for k in range(veces):
        fuera += [uso(f"{comando[:4]}{desde + k}", "Bash", (desde + k) * 10,
                      command=comando),
                  res(f"{comando[:4]}{desde + k}", (desde + k) * 10 + 2, salida, error)]
    return fuera


def main():
    fallos = []

    def igual(caso, dado, esperado):
        if dado != esperado:
            fallos.append(f"{caso}: {dado!r} != {esperado!r}")

    # ── emparejamiento y duracion ───────────────────────────────────────────────
    ev = recorrido([uso("a", "Bash", 0, command="npm test"), res("a", 12, "ok\n")])
    igual("un solo evento", len(ev), 1)
    igual("duracion medida", ev[0]["dur"], 12.0)
    igual("no pendiente", ev[0]["pend"], False)
    igual("resumen de _resume_tool", ev[0]["res"], "Bash · npm test")

    ev = recorrido([uso("a", "Bash", 0, command="npm test")])
    igual("sin resultado, pendiente", ev[0]["pend"], True)
    igual("sin resultado, sin duracion", ev[0]["dur"], None)

    # Un tool_result cuyo tool_use se quedo fuera de la ventana no inventa un evento.
    igual("resultado huerfano", recorrido([res("z", 1, "ok")]), [])

    # Los subagentes no son el camino de la sesion.
    lado = dict(uso("s", "Bash", 0, command="x"), isSidechain=True)
    igual("sidechain fuera", recorrido([lado]), [])

    # ── bucle: el MISMO comando fallando tres veces ─────────────────────────────
    bucle = tanda("git push origin main", 3, "Exit code 1\nrejected", True)
    s = sintomas(recorrido(bucle))
    igual("repeticiones", s["repeticiones_consecutivas"], 3)
    igual("fallos seguidos", s["fallos_seguidos"], 3)
    igual("alerta de bucle", alertas(s), ["bucle"])

    # Y el cuarto intento, aun corriendo, no borra la racha justo cuando la miras.
    s = sintomas(recorrido(bucle + [uso("gitX", "Bash", 40,
                                        command="git push origin main")]))
    igual("repeticiones con uno en vuelo", s["repeticiones_consecutivas"], 4)
    igual("fallos con uno en vuelo", s["fallos_seguidos"], 3)
    igual("sigue siendo bucle", alertas(s), ["bucle"])

    # Tres comandos DISTINTOS que fallan no son un bucle: son tres problemas.
    distintos = []
    for k in range(3):
        distintos += [uso(f"d{k}", "Bash", k, command=f"pytest tests/t{k}.py"),
                      res(f"d{k}", k + 1, "Exit code 1\nfailed", True)]
    s = sintomas(recorrido(distintos))
    igual("tres fallos distintos", s["fallos_seguidos"], 3)
    igual("y no hay bucle", alertas(s), [])

    # ── barrido: dos busquedas seguidas sin nada ────────────────────────────────
    barrido = [uso("b0", "Bash", 0, command="rg -n hipotesis src/"),
               res("b0", 1, "Exit code 1\n", True),
               uso("b1", "Bash", 2, command="LC_ALL=C grep -rn hipotesis ."),
               res("b1", 3, "(Bash completed with no output)")]
    s = sintomas(recorrido(barrido))
    igual("busquedas vacias", s["busquedas_sin_resultado"], 2)
    igual("alerta de barrido", alertas(s), ["barrido"])

    # `sudo` y `git` delante no esconden la busqueda.
    for cmd in ("sudo rg -n x .", "git grep -lP '\\bx\\b'"):
        e = recorrido([uso("c", "Bash", 0, command=cmd), res("c", 1, "", True)])[0]
        igual(f"{cmd!r} es una busqueda", e["busca"], True)

    # Una busqueda que SI encuentra corta la racha.
    s = sintomas(recorrido(barrido + [uso("b2", "Grep", 4, pattern="hipotesis"),
                                      res("b2", 5, "src/x.py:12: hipotesis")]))
    igual("racha cortada", s["busquedas_sin_resultado"], 0)
    igual("y sin barrido", alertas(s), [])

    # Un Read que devuelve poco NO es una busqueda vacia: `vacio` solo aplica a busquedas.
    ev = recorrido([uso("r", "Read", 0, file_path="/tmp/vacio.txt"),
                    res("r", 1, "(Bash completed with no output)")])
    igual("Read no busca", ev[0]["busca"], False)
    igual("y su vacio no aplica", ev[0]["vacio"], None)

    # ── sin datos: nada se da por bueno ─────────────────────────────────────────
    s = sintomas([])
    igual("sin eventos", [s[k] for k in sorted(s)], [0, 0, 0, 0, 0])
    igual("sin alertas", alertas(s), [])
    # Un sello ilegible deja la duracion en None, y None nunca cuenta como exito.
    ev = recorrido([{"type": "assistant", "timestamp": "no-es-una-fecha",
                     "message": {"content": [{"type": "tool_use", "id": "q",
                                              "name": "Bash",
                                              "input": {"command": "ls"}}]}},
                    res("q", 5, "ok")])
    igual("sin sello no hay duracion", ev[0]["dur"], None)

    # ── tope de eventos ─────────────────────────────────────────────────────────
    largo = recorrido(tanda("echo hola", MAX_EVENTOS + 5, "hola", False))
    igual("se guardan los ultimos", len(largo), MAX_EVENTOS)

    # ── tipos cerrados: la frontera LLM/codigo se sostiene si nada es prosa ──────
    TIPOS = {"nom": (str,), "res": (str,), "t0": (int, float), "dur": (int, float),
             "pend": (bool,), "err": (bool,), "cod": (int,), "bytes": (int,),
             "busca": (bool,), "vacio": (bool,)}
    for e in recorrido(barrido + bucle):
        if set(e) != set(TIPOS):
            fallos.append(f"campos inesperados: {sorted(set(e) ^ set(TIPOS))}")
        for k, tipos in TIPOS.items():
            v = e.get(k)
            if v is not None and not isinstance(v, tipos):
                fallos.append(f"{k} es {type(v).__name__}, se esperaba "
                              f"{'/'.join(t.__name__ for t in tipos)} o None")
    for k, v in sintomas(recorrido(bucle)).items():
        if not isinstance(v, int) or isinstance(v, bool):
            fallos.append(f"sintomas[{k}] es {type(v).__name__}, se esperaba int")
    for a in alertas(sintomas(recorrido(bucle))):
        if a not in ("bucle", "barrido"):
            fallos.append(f"alerta fuera del enum: {a!r}")

    # ── ancho: ninguna fila se sale del panel ───────────────────────────────────
    muestra = recorrido(barrido + bucle)
    muestra.append(dict(muestra[0],
                        res="Bash · echo \U0001f680 desplegando ahora mismo"))
    for cols in (26, 36, 40, 73, 120):
        for e in muestra:
            glifo, par, dur, texto = linea_ruta(e, cols)
            usado = RUTA_FIJO + ancho(texto)
            if usado > cols:
                fallos.append(f"a {cols} columnas la fila ocupa {usado}")
            if ancho(glifo) != 1:
                fallos.append(f"el glifo {glifo!r} ocupa {ancho(glifo)} columnas, no 1")
            if len(dur) != 4 or ancho(dur) != 4:
                fallos.append(f"la duracion {dur!r} no ocupa 4 columnas")
            if not isinstance(par, int):
                fallos.append(f"par de color no numerico: {par!r}")

    # ── el aviso en la LISTA ────────────────────────────────────────────────────
    # El enum que sale por `--json` es publico y va en ingles; el interno esta en
    # castellano como el resto del fuente. Que no se despareje sin que nada falle.
    if set(ns["_STUCK_JSON"]) != {"bucle", "barrido"}:
        fallos.append(f"el mapa a --json no cubre el enum: {ns['_STUCK_JSON']}")
    if set(ns["_TEXTO_ATASCO"]) != {"bucle", "barrido"}:
        fallos.append(f"falta la frase corta de alguna alerta: {set(ns['_TEXTO_ATASCO'])}")
    # `\u21bb` comparte columna con `\u29c9` en la fila, asi que tiene que medir lo
    # mismo: una de mas en curses no da error, envuelve el sobrante a la fila siguiente.
    for glifo in ("\u21bb", "\u29c9"):
        if ns["ancho"](glifo) != 1:
            fallos.append(f"{glifo!r} ocupa {ns['ancho'](glifo)} columnas, no 1")

    filas = ns["sesiones_demo"]()
    # La demo tiene que ensenar el simbolo en la lista, y eso exige una fila que se
    # atasque SIN chocar: cuando coinciden gana el choque, que es el que puede costar
    # trabajo perdido. Sin esa fila, la captura del README no lo enseñaria nunca.
    sola = [r for r in filas
            if (r.get("pulso") or {}).get("atasco") and not r.get("colision")]
    if not sola:
        fallos.append("ninguna fila de la demo se atasca sin chocar: el simbolo de la "
                      "lista no saldria en ninguna captura")
    for r in filas:
        at = (r.get("pulso") or {}).get("atasco")
        if at is None:
            fallos.append(f"{r['name']}: la demo no publica `atasco`")
        elif at != alertas(sintomas((r.get("_det") or {}).get("ruta") or [])):
            fallos.append(f"{r['name']}: el atasco de la lista no cuadra con el "
                          "recorrido que pinta el panel")

    # ── la demo trae recorrido, y ensena los dos casos ──────────────────────────
    if not any((r.get("_det") or {}).get("ruta") for r in filas):
        fallos.append("la demo no trae recorrido: la captura del README saldria sin el")
    vistas = set()
    for r in filas:
        vistas |= set(alertas(sintomas((r.get("_det") or {}).get("ruta") or [])))
    if vistas != {"bucle", "barrido"}:
        fallos.append(f"la demo ensena {sorted(vistas)}, deberia ensenar los dos casos")

    for f in fallos:
        print("FALLO:", f)
    print("ok: el recorrido mide, el codigo decide y ninguna fila se sale"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
