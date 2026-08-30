#!/usr/bin/env python3
"""`--disk` cuenta lo que hay en disco, y no toca nada.

Nace de un numero que no estaba en ninguna parte y resulto ser grande: en la maquina
donde se escribio esto, **3.469 MB en 595 sesiones**, con 3.464 de ellos en un solo
proyecto y **403 MB en cinco sesiones**. El panel dice el peso de la fila bajo el cursor
y nada mas, asi que el reparto no se veia.

Lo que este test vigila, y por que cada cosa:

1. **Las cuentas cuadran** con lo que hay en el directorio de mentira: bytes, numero de
   sesiones, y los subagentes contados APARTE. Si `agent-*.jsonl` entrara en el reparto
   por proyecto, el numero de ficheros subiria sin mover un MB — en la maquina real son
   285 ficheros y 436 KB.
2. **Lo irrecuperable se marca**, con la misma definicion que usa la lista: su directorio
   de trabajo ya no existe.
3. **No escribe.** Es la promesa del README —"nunca va a escribir en un transcript, ni en
   nada que sea de una sesion"— y aqui es facil romperla sin querer, porque este comando
   es el unico que se pasea por los 595 ficheros. Se comprueba comparando mtime y tamano
   de todos ANTES y DESPUES, que es lo unico que distingue "no escribio" de "no quise
   escribir".
4. **El formateo no dice 0.** `_mb` redondea a entero y todo lo pequeno salia como "0 MB",
   que es justo lo que se lee como "no ocupa" mientras se esta contando peso.
5. **Lo que se recuperaria, por antiguedad.** El total dice lo que OCUPA; la pregunta de
   quien mira este comando es cuanto ganaria. Los tramos son ANIDADOS —lo de mas de 90
   dias esta dentro de lo de mas de 30— y esto lo comprueba envejeciendo ficheros a mano,
   porque sumarlos seria contar dos veces la misma sesion.
"""
import contextlib, io, json, os, pathlib, shutil, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ns = {"__name__": "sereno_test"}
exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

UUIDS = ["%08d-1111-2222-3333-444444444444" % i for i in range(1, 6)]


def monta(base, vivo, muerto):
    """Un `~/.claude/projects` de mentira: dos proyectos, uno de ellos ya borrado."""
    proyectos = base / "projects"
    def escribe(carpeta, nombre, cwd, relleno):
        d = proyectos / carpeta
        d.mkdir(parents=True, exist_ok=True)
        # El prompt tiene que pasar de 25 caracteres: es el minimo que `first_user_text`
        # exige para que algo valga como titulo, y con uno corto el test comprobaba que
        # hay titulo contra una funcion que nunca iba a darlo.
        lineas = [json.dumps({"type": "user", "cwd": cwd,
                              "message": {"role": "user",
                                          "content": "Vamos a revisar el " + nombre[:8]
                                                     + " que quedo a medias ayer"}})]
        lineas += [json.dumps({"type": "assistant", "x": "y" * 60})] * relleno
        (d / (nombre + ".jsonl")).write_text("\n".join(lineas) + "\n")
        return (d / (nombre + ".jsonl")).stat().st_size

    tam = {}
    tam["grande"] = escribe("-vivo", UUIDS[0], str(vivo), 400)
    tam["mediana"] = escribe("-vivo", UUIDS[1], str(vivo), 100)
    tam["muerta"] = escribe("-muerto", UUIDS[2], str(muerto), 50)
    # un subagente: cuenta aparte, no en el reparto por proyecto
    tam["subagente"] = escribe("-vivo", "agent-" + UUIDS[3], str(vivo), 10)
    return proyectos, tam


def foto(raiz):
    """mtime y tamano de cada fichero: la unica forma de saber que nadie escribio."""
    return {str(p): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(raiz.rglob("*.jsonl"))}


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    base = pathlib.Path(tempfile.mkdtemp())
    vivo = base / "un-proyecto-que-existe"
    vivo.mkdir()
    muerto = base / "un-proyecto-borrado"      # se crea y se borra: el cwd apunta a nada
    muerto.mkdir(); shutil.rmtree(str(muerto))
    try:
        proyectos, tam = monta(base, vivo, muerto)
        guardado = ns["PROJECTS"]
        ns["PROJECTS"] = proyectos
        ns["_CACHE_SITIO"].clear()
        try:
            # Envejecidas a mano: la maquina donde se escribio esto no tiene un solo
            # transcript de mas de 28 dias, asi que sin esto los tramos salen a cero y
            # el test aprobaria una funcion que no se ejecuta.
            ahora = time.time()
            edades = {UUIDS[0]: 400, UUIDS[1]: 60, UUIDS[2]: 2}
            for jl in proyectos.rglob("*.jsonl"):
                dias = edades.get(jl.stem)
                if dias:
                    os.utime(str(jl), (ahora - dias * 86400, ahora - dias * 86400))

            antes = foto(proyectos)
            h = ns["peso_historial"]()

            f(h["sesiones"] == 3, "tres sesiones, dijo %r" % h["sesiones"])
            f(h["subagentes"] == 1, "un subagente aparte, dijo %r" % h["subagentes"])
            esperado = tam["grande"] + tam["mediana"] + tam["muerta"]
            f(h["bytes"] == esperado,
              "los bytes tienen que ser %d y dijo %d" % (esperado, h["bytes"]))
            f(h["bytes_subagentes"] == tam["subagente"],
              "el subagente pesa %d, dijo %d" % (tam["subagente"], h["bytes_subagentes"]))
            f(h["sin_sitio"] == 1, "una sin sitio, dijo %r" % h["sin_sitio"])
            f(h["bytes_sin_sitio"] == tam["muerta"],
              "los bytes sin sitio son %d, dijo %d" % (tam["muerta"], h["bytes_sin_sitio"]))

            # la mas gorda va primera, y trae de que sesion es
            f(h["mayores"] and h["mayores"][0]["bytes"] == tam["grande"],
              "la primera tiene que ser la mas gorda: %r" % (h["mayores"][:1]))
            f(h["mayores"][0].get("titulo"), "la mas gorda tiene que decir cual es")
            f(all("_path" not in e for e in h["mayores"]),
              "no se filtran objetos internos en los hechos")

            # 5. lo que se recuperaria, por antiguedad
            por_edad = {e["dias"]: e for e in h["por_edad"]}
            f(sorted(por_edad) == list(ns["_CORTES_EDAD"]),
              "los tramos son %r y el programa dice %r"
              % (list(ns["_CORTES_EDAD"]), sorted(por_edad)))
            esperado_edad = {7: (2, tam["grande"] + tam["mediana"]),
                             30: (2, tam["grande"] + tam["mediana"]),
                             90: (1, tam["grande"]),
                             365: (1, tam["grande"])}
            for dias, (n_ses, n_bytes) in esperado_edad.items():
                e = por_edad.get(dias) or {}
                f(e.get("sesiones") == n_ses,
                  "mas de %dd: %r sesiones, se esperaban %d"
                  % (dias, e.get("sesiones"), n_ses))
                f(e.get("bytes") == n_bytes,
                  "mas de %dd: %r bytes, se esperaban %d"
                  % (dias, e.get("bytes"), n_bytes))
            # Anidados: apurar mas nunca puede devolver MAS. Si esto falla, las cifras se
            # estarian pudiendo sumar, y sumarlas cuenta dos veces la misma sesion.
            serie = [por_edad[d] for d in sorted(por_edad)]
            f(all(a["sesiones"] >= b["sesiones"] and a["bytes"] >= b["bytes"]
                  for a, b in zip(serie, serie[1:])),
              "los tramos no van de mas a menos: %r"
              % [(e["dias"], e["sesiones"]) for e in serie])
            # La de dos dias no entra en ninguno: el corte mas bajo son siete.
            f(por_edad[min(por_edad)]["bytes"] < h["bytes"],
              "el tramo mas bajo se lleva TODO el historial, incluida la de anteayer")

            # Una edad que no se pudo medir NO es una sesion vieja. Pasa de verdad:
            # el fichero se lee dos veces —tamano y fecha— y entre las dos puede
            # desaparecer. Contarla como vieja la mete en la lista de lo borrable por
            # no haber podido mirarla, que es lo contrario de lo que hay que hacer con
            # un dato que falta.
            real = pathlib.Path.stat
            visto = {}

            def stat_que_se_va(self, *a, **kw):
                if str(self) == str(sin_fecha):
                    visto[str(self)] = visto.get(str(self), 0) + 1
                    if visto[str(self)] > 1:
                        raise OSError("desaparecio entre un stat y el siguiente")
                return real(self, *a, **kw)

            sin_fecha = proyectos / "-vivo" / (UUIDS[1] + ".jsonl")
            pathlib.Path.stat = stat_que_se_va
            try:
                h2 = ns["peso_historial"]()
            finally:
                pathlib.Path.stat = real
            por_edad2 = {e["dias"]: e for e in h2["por_edad"]}
            f(por_edad2[7]["sesiones"] == 1,
              "una sesion cuya fecha no se pudo leer cuenta como vieja: mas de 7d dice "
              "%r sesiones y solo deberia quedar una" % por_edad2[7]["sesiones"])

            # 3. NO ESCRIBE. Ni un mtime, ni un byte.
            f(foto(proyectos) == antes,
              "el comando TOCO ficheros de sesion: %r" %
              [k for k, v in foto(proyectos).items() if antes.get(k) != v])

            # y el comando entero pinta sin reventar, en los dos idiomas
            for lang in ("en", "es"):
                ns["LANG"] = lang
                cap = io.StringIO()
                with contextlib.redirect_stdout(cap):
                    cod = ns["cmd_disk"]()
                salida = cap.getvalue()
                f(cod == 0, "cmd_disk en %s salio con %r" % (lang, cod))
                f(str(tam["grande"] // 1024) in salida or "KB" in salida or "MB" in salida,
                  "en %s no dijo ningun peso: %r" % (lang, salida[:120]))
                # 4. nada de "0 MB" para algo que si ocupa
                f(" 0 MB" not in salida,
                  "en %s hay un '0 MB' para algo que ocupa: %r" % (lang, salida[:200]))
        finally:
            ns["PROJECTS"] = guardado

        # CONTROL POSITIVO del punto 3: la foto SI cambia cuando alguien escribe de
        # verdad. Sin esto, `foto(x) == antes` pasaria igual con un directorio vacio.
        victima = next(proyectos.rglob("*.jsonl"))
        antes2 = foto(proyectos)
        with victima.open("a") as fh:
            fh.write("{}\n")
        f(foto(proyectos) != antes2,
          "CONTROL POSITIVO: la foto no detecta ni una escritura de verdad")
    finally:
        shutil.rmtree(str(base), ignore_errors=True)

    # el formateador, en aislado: el caso que motivo no reusar `_mb`
    _peso = ns["_peso"]
    f(_peso(800 * 1024) == "800 KB", "800 KB salieron como %r" % _peso(800 * 1024))
    f(_peso(int(1.5 * 1024 ** 2)) == "1.5 MB", "1,5 MB salieron como %r" % _peso(int(1.5 * 1024 ** 2)))
    f(_peso(int(3.4 * 1024 ** 3)) == "3.4 GB", "3,4 GB salieron como %r" % _peso(int(3.4 * 1024 ** 3)))
    f(_peso(10) == "1 KB", "un fichero diminuto no puede salir como 0: %r" % _peso(10))

    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos
          else "ok: las cuentas cuadran, los subagentes van aparte, lo irrecuperable se "
               "marca, nada por debajo de 1 MB sale como 0, y no se toca un solo fichero")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
