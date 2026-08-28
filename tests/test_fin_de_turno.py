#!/usr/bin/env python3
"""Una sesion que acaba de terminar te espera, aunque su transcript este caliente.

`escribe` es "el fichero se toco hace menos de 90 s", y eso sigue siendo verdad durante
los 90 segundos siguientes a que la sesion conteste: justo la ventana en la que quieres
saber cual te esta esperando. Medido el 2026-08-28 contra el pane real de Claude Code
—la verdad la dice su propio spinner— 10 de 35 muestras en estado `writing` eran
sesiones paradas. Ninguna al reves.

Lo que corta fino es el `stop_reason` que escribe el CLI, y por eso los cuatro casos de
aqui se juegan TODOS con el mtime recien tocado: es el unico sitio donde las dos reglas
discrepan. El caso 3 es el que impide pasarse de listo: sin `stop_reason` no se inventa
un veredicto, se decide como siempre.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
UUID = "0123abcd-4567-89ef-0123-456789abcdef"

PROMPT = {"type": "user", "cwd": "/tmp/proyecto", "gitBranch": "main",
          "message": {"role": "user", "content": "haz algo que se vea"}}

# Las dos formas reales, medidas sobre los transcripts de esta maquina: de 87
# interrupciones, 78 traen el campo `interruptedMessageId` y 9 solo el texto. Se prueban
# por separado y no juntas: con las dos senales en el mismo caso, apagar media funcion
# seguia dando verde — comprobado.
#
# Por eso el caso del campo lleva un texto que NO es ninguna de las marcas. Ademas dice
# por que el campo es el dato bueno: si el CLI traduce o reescribe esa frase, es lo unico
# que queda.
INTERRUPCION_CAMPO = {"type": "user", "interruptedMessageId": "msg_x",
                      "message": {"role": "user", "content": [
                          {"type": "text",
                           "text": "[Solicitud interrumpida por el usuario]"}]}}
INTERRUPCION_TEXTO = {"type": "user",
                      "message": {"role": "user", "content": [
                          {"type": "text",
                           "text": "[Request interrupted by user for tool use]"}]}}



def respuesta(stop):
    m = {"role": "assistant", "model": "claude-opus-5",
         "usage": {"cache_read_input_tokens": 120000, "input_tokens": 20},
         "content": [{"type": "text", "text": "ya esta"}]}
    if stop is not None:
        m["stop_reason"] = stop
    return {"type": "assistant", "message": m}


def main():
    fallos = []
    casos = [
        # (nombre, lineas, estado esperado)
        ("turno cerrado y transcript caliente",
         [PROMPT, respuesta("end_turn")], "waiting"),
        ("un prompt nuevo reabre el turno",
         [PROMPT, respuesta("end_turn"), dict(PROMPT, message={
             "role": "user", "content": "y ahora esto otro"})], "writing"),
        ("sin stop_reason se decide como siempre",
         [PROMPT, respuesta(None)], "writing"),
        ("un turno cortado por longitud no es un turno cerrado",
         [PROMPT, respuesta("max_tokens")], "writing"),
        # Pulsar ESC no reabre el turno, lo CIERRA: la sesion te espera a ti. Sin esto
        # figuraba como "escribiendo" los 90 s siguientes, que es cuando la miras.
        ("un ESC con su campo tipado cierra el turno",
         [PROMPT, respuesta("tool_use"), INTERRUPCION_CAMPO], "waiting"),
        ("un ESC sin el campo, solo con su texto, tambien",
         [PROMPT, respuesta("tool_use"), INTERRUPCION_TEXTO], "waiting"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        proy = casa / ".claude/projects/-tmp-proyecto"
        proy.mkdir(parents=True)
        t = proy / f"{UUID}.jsonl"
        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
        filas_json, live, trans = ns["filas_json"], ns["live_sessions"], ns["transiciones"]

        vistas = {}
        for nombre, lineas, quiero in casos:
            t.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")
            os.utime(t, None)                      # caliente: el mtime es AHORA
            ns["_CACHE_DISCO"].clear()
            v = filas_json(live(fino=True, solo_activas=False))
            if len(v) != 1:
                print(f"FALLA: el HOME de mentira da {len(v)} sesiones, no 1")
                return 1
            vistas[nombre] = v
            if v[0]["state"] != quiero:
                fallos.append(f"{nombre}: estado {v[0]['state']!r}, "
                              f"se esperaba {quiero!r}")
            # El hecho crudo viaja al JSON aparte del veredicto, para quien componga
            # el suyo. `null` cuando el transcript no lo dice.
            esperado = {"turno cerrado y transcript caliente": True,
                        "un prompt nuevo reabre el turno": False,
                        "sin stop_reason se decide como siempre": None,
                        "un turno cortado por longitud no es un turno cerrado": False,
                        "un ESC con su campo tipado cierra el turno": True,
                        "un ESC sin el campo, solo con su texto, tambien": True}[nombre]
            if v[0]["turn_closed"] is not esperado:
                fallos.append(f"{nombre}: turn_closed={v[0]['turn_closed']!r}, "
                              f"se esperaba {esperado!r}")

        # Y el flanco de `--watch` salta AL CERRAR el turno, no 90 s despues: las dos
        # fotos tienen el mtime igual de caliente, asi que la regla vieja no veria nada.
        salta = trans({r["id"]: r["state"] for r in vistas["un prompt nuevo reabre el turno"]},
                      vistas["turno cerrado y transcript caliente"])
        if len(salta) != 1:
            fallos.append(f"--watch no avisa al cerrarse el turno: {len(salta)} avisos")

    for f in fallos:
        print("FALLA:", f)
    print("OK: test_fin_de_turno" if not fallos else f"{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
