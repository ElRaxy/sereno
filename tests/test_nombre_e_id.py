#!/usr/bin/env python3
"""El nombre de una sesion cabe en una linea, y su id es el que sirve para reanudarla.

Dos sintomas reales, los dos de confundir dos cosas parecidas.

El primero: sin `/rename` ni `aiTitle`, el titulo salia del primer prompt ENTERO — 1.727
caracteres en el mayor de esta maquina— y doce sesiones que empezaban con el mismo
encargo aparecian con el mismo nombre. En el panel eran la misma fila repetida.

El segundo: la etiqueta "sesion" del panel, la tecla que copia y el campo `id` de
`--json` daban `name`, que es la CLAVE de la fila: el nombre de tmux en una sesion viva
(`cc-VanguardIA-90a6fb95`) y el uuid en una del historial. Pegar el primero en un
`claude --resume` no reanuda nada.
"""
import os, pathlib, sys

os.environ["SERENO_DEMO"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
frase, id_sesion = ns["_primera_frase"], ns["id_sesion"]
desambigua, FRASE_MAX = ns["desambigua"], ns["FRASE_MAX"]

UUID_A = "90a6fb95-207d-43f5-85fb-e00835c38c5f"
UUID_B = "4a01aa4d-7d0c-453f-b9a2-857659492c8f"


def fila(name, titulo, transcript=None, id_meta=None):
    meta = {}
    if transcript:
        meta["_transcript"] = pathlib.Path(f"/tmp/x/{transcript}.jsonl")
    if id_meta:
        meta["id"] = id_meta
    return {"name": name, "title": titulo, "title_full": titulo, "meta": meta}


def main():
    fallos = []

    def igual(caso, dado, esperado):
        if dado != esperado:
            fallos.append(f"{caso}: {dado!r} != {esperado!r}")

    # ── 1. el titulo se corta por la primera frase ─────────────────────────────
    igual("corta en el punto",
          frase("Analiza estos 2 posts del cliente. Extrae estilo y voz para el plan"),
          "Analiza estos 2 posts del cliente")
    igual("corta en el salto de linea",
          frase("Arregla el login\ny luego mira el registro"), "Arregla el login")
    igual("una interrogacion tambien cierra",
          frase("Por que falla el deploy? Mira los logs de ayer"),
          "Por que falla el deploy")
    # Una frase de dos palabras no es un titulo: se sigue a la siguiente. Los prompts
    # reales empiezan asi mucho mas de lo que parece ("Hecho.", "Vale.", "Ok.").
    if not frase("Hecho. Arregla el login que no valida el email").startswith("Hecho."):
        fallos.append("una primera frase muy corta no continua con la siguiente")
    if len(frase("Hecho. Arregla el login que no valida el email")) < 25:
        fallos.append("se titula con una frase de dos palabras")

    # Un punto DENTRO de una palabra no corta: los prompts van llenos de rutas y de
    # numeros de version, y cortar ahi daba titulos de tres letras.
    for texto, trozo in (("Mira progress/x.md y dime que falta", "progress/x.md"),
                         ("Sube la version a 1.9.0 en el fichero", "1.9.0")):
        if trozo not in frase(texto):
            fallos.append(f"cortado dentro de {trozo!r}: {frase(texto)!r}")

    # ── 2. y nunca pasa del tope ───────────────────────────────────────────────
    largo = "Analiza " + "palabras y mas palabras " * 40
    salida = frase(largo)
    if len(salida) > FRASE_MAX:
        fallos.append(f"un prompt largo da {len(salida)} caracteres, tope {FRASE_MAX}")
    if not salida.endswith("…"):
        fallos.append("un titulo recortado no avisa de que se corto")
    igual("un texto vacio no revienta", frase(""), "")
    igual("ni uno de espacios", frase("   \n  "), "")

    # ── 3. el id de la sesion NO es la clave de la fila ────────────────────────
    viva = fila("cc-VanguardIA-90a6fb95", "t", transcript=UUID_A)
    igual("sesion viva: el id sale del transcript", id_sesion(viva), UUID_A)
    igual("y no es el nombre de tmux", id_sesion(viva) == viva["name"], False)
    hist = fila(UUID_B, "t", transcript=UUID_B)
    igual("sesion del historial", id_sesion(hist), UUID_B)
    # Una fila de otro CLI no tiene transcript de Claude: "" y no el nombre, que es lo
    # que haria que se copiase algo que no sirve para reanudar nada.
    igual("otro CLI no inventa un id", id_sesion({"name": "codex-3", "meta": {}}), "")
    # Un `id` del registro que no es un uuid tampoco vale: en una sesion reanudada
    # apunta al fichero viejo.
    igual("un id del registro que no es uuid se descarta",
          id_sesion({"name": "x", "meta": {"id": "cc-VanguardIA-90a6fb95"}}), "")

    # ── 4. dos sesiones con el mismo titulo se separan ─────────────────────────
    repes = [fila("cc-a-90a6fb95", "Analiza los posts", transcript=UUID_A),
             fila("cc-b-4a01aa4d", "Analiza los posts", transcript=UUID_B),
             fila("cc-c-11111111", "Otra cosa", transcript=UUID_A)]
    desambigua(repes)
    if repes[0]["title_full"] == repes[1]["title_full"]:
        fallos.append("dos filas con el mismo titulo siguen siendo indistinguibles")
    for r in repes[:2]:
        if "Analiza los posts" not in r["title_full"]:
            fallos.append(f"el titulo original se perdio: {r['title_full']!r}")
    igual("la que no se repetia no se toca", repes[2]["title_full"], "Otra cosa")
    # ── 5. y el titulo no crece a cada refresco ───────────────────────────────
    # La lista se recompone cuatro veces por segundo y `sesiones_de_disco` cachea las
    # filas: si `desambigua` escribiera sobre el dict cacheado, el sufijo se encadenaria
    # solo hasta llenar la columna. Se comprueba pidiendo la lista dos veces seguidas.
    import tempfile, json as _json, time as _t
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        for u in (UUID_A, UUID_B):
            linea = _json.dumps({"type": "user", "timestamp": "2026-08-26T10:00:00Z",
                                 "message": {"role": "user",
                                             "content": "Analiza estos 2 posts del "
                                                        "cliente. Y luego el resto"}})
            (d / f"{u}.jsonl").write_bytes((linea + "\n").encode())
        # Se pide la fila dos veces: la segunda sale de la cache, que es donde el
        # sufijo se encadenaria si `desambigua` escribiera sobre el dict guardado.
        fdt = ns["fila_de_transcript"]
        filas1 = [fdt(p2, fino=False) for p2 in sorted(d.glob("*.jsonl"))]
        desambigua(filas1)
        t1 = sorted(r["title_full"] for r in filas1)
        filas2 = [fdt(p2, fino=False) for p2 in sorted(d.glob("*.jsonl"))]
        desambigua(filas2)
        t2 = sorted(r["title_full"] for r in filas2)
        if t1 != t2:
            fallos.append(f"el titulo cambia entre refrescos: {t1} -> {t2}")
        for t in t2:
            if t.count("\u00b7") > 1:
                fallos.append(f"el sufijo se encadena al refrescar: {t!r}")
        # Y el sufijo se va cuando deja de hacer falta. Si `desambigua` escribiera sobre
        # el dict que guarda la cache, una fila arrastraria el id de por vida — tambien
        # cuando la sesion con la que chocaba ya no esta en la lista.
        sola = [fdt(sorted(d.glob("*.jsonl"))[0], fino=False)]
        desambigua(sola)
        if "\u00b7" in sola[0]["title_full"]:
            fallos.append("una fila sola conserva el sufijo: se escribio en la cache")
        # Y de paso: el primer prompt se corto por su frase, no entero.
        for t in t2:
            if "Y luego el resto" in t:
                fallos.append(f"el titulo no se corto por la primera frase: {t!r}")

    # ── 6. y en la demo ningun titulo se pasa de largo ─────────────────────────
    for r in ns["sesiones_demo"]():
        if len(r.get("title") or "") > 35:
            fallos.append(f"demo {r['name']}: titulo de {len(r['title'])} caracteres")

    # ── 7. y el panel pinta ESE id, no la clave de la fila ────────────────────
    # La comprobacion de arriba es de la funcion; esta es del cableado, que es la mitad
    # que se rompe. Se mira la matriz de celdas del doble, no un volcado del terminal.
    import contextlib, io
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from doble_curses import espia          # noqa: E402  (el path se fija arriba)
    import curses as real

    demo = ns["sesiones_demo"]()
    demo[0]["meta"] = dict(demo[0].get("meta") or {},
                           _transcript=pathlib.Path(f"/tmp/x/{UUID_A}.jsonl"))
    demo[0]["name"] = "cc-VanguardIA-90a6fb95"
    cajon = []
    sys.modules["curses"] = espia(real, 34, 170, [ord("q")], cajon, ns["ancho"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns["pick_ui"](demo)
    finally:
        sys.modules["curses"] = real
    c = cajon[0].celdas
    pant = "\n".join("".join(c.get((y, x), " ") for x in range(170)).rstrip()
                     for y in range(34))
    # La etiqueta va en la mitad derecha, detras del separador vertical: la linea
    # entera empieza por la fila de la LISTA. Buscar "sesión" en la linea suelta casa
    # con el aviso de choque ("otra sesión escribe aquí"), que no es esto.
    linea = [l.split("\u2502", 1)[1].strip() for l in pant.splitlines()
             if "\u2502" in l]
    linea = [l for l in linea if l.startswith(("sesión", "session"))]
    if not linea:
        fallos.append("el panel no pinta la fila del id de la sesion")
    elif UUID_A not in linea[0]:
        fallos.append(f"el panel no pinta el id de la sesion: {linea[0]!r}")
    elif "cc-VanguardIA" in linea[0]:
        fallos.append(f"el panel sigue pintando el nombre de tmux: {linea[0]!r}")

    for f in fallos:
        print("FALLO:", f)
    print("ok: el titulo se corta por la primera frase, las repetidas se separan y el "
          "id es el de la sesion" if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
