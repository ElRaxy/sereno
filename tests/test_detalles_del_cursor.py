#!/usr/bin/env python3
"""El panel de la fila bajo el cursor dice lo que hay en la cola, y no se queda pegado.

`detalles` es lo que se lee cuando marcas una fila: el titulo que la sesion se puso, la
ultima instruccion, la rama, el peso del historial, lo ultimo que respondio y lo que
esta ejecutando ahora mismo. Es el unico sitio del programa donde se abre un transcript
para pintar UNA fila, y por eso tiene dos contratos que se rompen por separado:

  · **lo que dice** — si toma el primer valor en vez del ultimo, el panel ensena la rama
    de hace tres horas; si deja que un subagente pise la respuesta, atribuye a la sesion
    algo que dijo otro;
  · **lo que se queda en memoria** — el resultado se guarda en `r["_det"]` hasta el
    proximo refresco. Una sola linea de transcript puede pasar de 96 KB (un `tool_result`
    con un fichero entero dentro), asi que guardar las lineas crudas es pegarle esos KB
    a la fila. Por eso `ruta` guarda eventos ya resumidos, y eso se mide aqui, no se
    razona.

El caso del sidechain es el mas facil de romper sin notarlo: un subagente escribe en el
MISMO transcript, con la misma forma, y lo unico que lo distingue es una bandera.
"""
import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def escribe(path, lineas):
    path.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")


def asistente(texto=None, tool=None, **campos):
    cont = []
    if texto is not None:
        cont.append({"type": "text", "text": texto})
    if tool is not None:
        cont.append({"type": "tool_use", "id": "t1", "name": tool[0],
                     "input": {"command" if tool[0] == "Bash" else "file_path": tool[1]}})
    d = {"type": "assistant",
         "message": {"role": "assistant", "model": "claude-opus-5",
                     "usage": {"input_tokens": 10}, "content": cont}}
    d.update(campos)
    return d


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    detalles = ns["detalles"]
    fallos = []
    tmp = pathlib.Path(tempfile.mkdtemp())

    def caso(real, esperado, por_que):
        if real != esperado:
            fallos.append("%s: dio %r, se esperaba %r" % (por_que, real, esperado))

    # ── lo que dice ───────────────────────────────────────────────────────────
    t = tmp / "sesion.jsonl"
    escribe(t, [
        {"type": "user", "cwd": "/x/proyecto", "gitBranch": "main",
         "message": {"role": "user", "content": "arranca"}},
        asistente("Voy a mirarlo.", ("Bash", "ls -la"),
                  aiTitle="Arreglar el panel", gitBranch="feat/panel"),
        asistente("Ya esta hecho.", lastPrompt="lo ultimo que pedi"),
        # Un subagente escribe en el mismo fichero: no es lo que dijo ESTA sesion.
        {"type": "assistant", "isSidechain": True,
         "message": {"role": "assistant",
                     "content": [{"type": "text", "text": "SOY UN SUBAGENTE"}]}},
    ])
    d = detalles({"meta": {"_transcript": t}})

    caso(d.get("aiTitle"), "Arreglar el panel", "el titulo que la sesion se puso")
    caso(d.get("lastPrompt"), "lo ultimo que pedi", "la ultima instruccion")
    caso(d.get("gitBranch"), "feat/panel", "la rama es la ULTIMA, no la primera")
    caso(d.get("cwd"), "/x/proyecto", "el directorio de trabajo")
    caso(d.get("peso"), t.stat().st_size, "el peso es el del fichero")
    caso(d.get("resp"), "Ya esta hecho.", "lo ultimo que respondio la sesion")
    if "SUBAGENTE" in (d.get("resp") or ""):
        fallos.append("un sidechain pisa la respuesta: el panel atribuye a la sesion "
                      "algo que dijo un subagente")
    if not (d.get("tool") or "").startswith("Bash"):
        fallos.append("la herramienta en curso no sale: dio %r" % (d.get("tool"),))
    if not d.get("ruta"):
        fallos.append("el recorrido sale vacio con una llamada a herramienta dentro")

    # Sin transcript no hay nada que leer, y no se inventa.
    vacio = detalles({"meta": {}})
    for k in ("aiTitle", "resp", "peso", "ruta"):
        if k in vacio:
            fallos.append("sin transcript aparece %r en el panel" % k)

    # Un fichero que no existe: se pinta lo que se pueda, no se revienta.
    try:
        detalles({"meta": {"_transcript": tmp / "no-existe.jsonl"}})
    except Exception as e:
        fallos.append("un transcript que no existe revienta el panel: %r" % (e,))

    # ── lo que se queda en memoria ────────────────────────────────────────────
    # Una sola linea con un fichero entero dentro. Si `_det` guardara los crudos, la
    # fila arrastraria esos 200 KB hasta el proximo refresco.
    gordo = tmp / "gordo.jsonl"
    escribe(gordo, [
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "X" * 200_000}]}},
        asistente("ya"),
    ])
    dg = detalles({"meta": {"_transcript": gordo}})
    pegado = len(json.dumps(dg, default=str))
    if pegado > 8_000:
        fallos.append("`_det` se queda con %d bytes de un transcript de %d: se estan "
                      "guardando las lineas crudas" % (pegado, gordo.stat().st_size))

    # ── el cache existe y se usa ──────────────────────────────────────────────
    r = {"meta": {"_transcript": t}}
    detalles(r)
    if "_det" not in r:
        fallos.append("el resultado no se guarda en la fila: se releeria el transcript "
                      "en cada pintado")
    escribe(t, [asistente("otra cosa distinta", aiTitle="TITULO NUEVO")])
    if detalles(r).get("aiTitle") == "TITULO NUEVO":
        fallos.append("se relee el transcript aunque la fila ya tenga `_det`")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: el panel dice lo ultimo de la cola, sin subagentes, y no arrastra KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
