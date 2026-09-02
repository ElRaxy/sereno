#!/usr/bin/env python3
"""El `/rename` del usuario manda sobre el titulo que Claude Code se pone solo.

Sintoma real (2026-09-02): una sesion renombrada con `/rename Borrar1` seguia saliendo
en el selector con su aiTitle viejo ("F13 Telegram outbound"). Claude Code NO guarda el
rename en el transcript, sino en un fichero aparte —`<id>/custom-title.json`— que Sereno
no leia. Por eso el aiTitle, que si esta en el transcript, seguia ganando.

Aqui se fija el contrato: si existe ese fichero, su `customTitle` es el titulo, por encima
del aiTitle y del primer mensaje. Y si no existe, no pasa nada: se sigue con lo de antes.
"""
import json, os, pathlib, sys, tempfile

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
custom_title = ns["custom_title"]
fila_de_transcript = ns["fila_de_transcript"]


def _sesion(tmp, sid, lineas, custom=None):
    """Crea <slug>/<sid>.jsonl y, si custom, <slug>/<sid>/custom-title.json."""
    slug = tmp / "-Users-alex-Desktop-VanguardIA"
    slug.mkdir(parents=True, exist_ok=True)
    trans = slug / (sid + ".jsonl")
    trans.write_text("\n".join(json.dumps(l) for l in lineas), "utf-8")
    if custom is not None:
        d = slug / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / "custom-title.json").write_text(json.dumps({"customTitle": custom}), "utf-8")
    return trans


def main():
    fallos = []

    def igual(caso, dado, esperado):
        if dado != esperado:
            fallos.append("%s: %r != %r" % (caso, dado, esperado))

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        # Un transcript con aiTitle propio Y un /rename encima.
        lineas = [
            {"type": "user", "message": {"role": "user",
             "content": [{"type": "text", "text": "haz la feature F13"}]}},
            {"aiTitle": "F13 Telegram outbound"},
        ]
        con_rename = _sesion(tmp, "11111111-1111-1111-1111-111111111111",
                             lineas, custom="Borrar1")
        sin_rename = _sesion(tmp, "22222222-2222-2222-2222-222222222222", lineas)
        vacio = _sesion(tmp, "33333333-3333-3333-3333-333333333333",
                        lineas, custom="   ")   # customTitle en blanco no cuenta

        # ── 1. custom_title() lee el fichero ─────────────────────────────────────
        igual("lee el customTitle", custom_title({"_transcript": con_rename}), "Borrar1")
        igual("sin fichero, cadena vacia", custom_title({"_transcript": sin_rename}), "")
        igual("customTitle en blanco no cuenta",
              custom_title({"_transcript": vacio}), "")
        igual("sin transcript, cadena vacia", custom_title({}), "")

        # ── 2. el titulo de la fila usa el /rename por encima del aiTitle ─────────
        f1 = fila_de_transcript(con_rename)
        igual("la fila renombrada sale con el /rename", f1["title_full"], "Borrar1")
        f2 = fila_de_transcript(sin_rename)
        igual("sin /rename, sigue el aiTitle", f2["title_full"], "F13 Telegram outbound")

        # ── 3. un /rename largo se recorta en `title` pero no en `title_full` ─────
        largo = "Un nombre larguisimo que el usuario le puso a mano y no cabe en la fila"
        fl = _sesion(tmp, "44444444-4444-4444-4444-444444444444", lineas, custom=largo)
        fila_l = fila_de_transcript(fl)
        igual("title_full no recorta el /rename", fila_l["title_full"], largo)
        if len(fila_l["title"]) > 34:
            fallos.append("title no se recorto a 34: %r" % fila_l["title"])
        if not fila_l["title"].endswith("…"):
            fallos.append("title recortado no acaba en puntos suspensivos")

    if fallos:
        print("FALLA test_rename:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: el /rename (custom-title.json) manda sobre el aiTitle, y se recorta igual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
