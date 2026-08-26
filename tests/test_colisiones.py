#!/usr/bin/env python3
"""Dos sesiones escribiendo en el mismo sitio se ven, y una que va sola no se inventa nada.

Un detector de colisiones falla de dos maneras y las dos son caras: si calla, el
accidente ocurre igual —te enteras leyendo el diff—; y si grita de mas, deja de mirarse
a la semana y vuelve a callar de hecho. Asi que esto comprueba las dos direcciones: que
el choque real salta, y que los tres casos que NO son choque no saltan.
"""
import json, os, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
A = "aaaaaaaa-1111-2222-3333-444444444444"
B = "bbbbbbbb-1111-2222-3333-444444444444"
CANARIO = "/Users/alex/clientes/CANARIO-CONFIDENCIAL/factura.py"


def transcript(path, cwd, toques, ahora):
    """Un transcript minimo con `toques` = [(nombre_tool, argumento)]."""
    lineas = [{"type": "user", "cwd": cwd, "gitBranch": "main",
               "timestamp": iso(ahora - 300),
               "message": {"role": "user", "content": "haz algo"}}]
    for i, (nom, arg) in enumerate(toques):
        clave = "command" if nom == "Bash" else "file_path"
        lineas.append({"type": "assistant", "cwd": cwd,
                       "timestamp": iso(ahora - 60 + i),
                       "message": {"role": "assistant", "model": "claude-opus-5",
                                   "usage": {"input_tokens": 10},
                                   "content": [{"type": "tool_use", "id": f"t{i}",
                                                "name": nom, "input": {clave: arg}}]}})
        lineas.append({"type": "user", "timestamp": iso(ahora - 60 + i),
                       "message": {"role": "user", "content": [
                           {"type": "tool_result", "tool_use_id": f"t{i}",
                            "content": "ok"}]}})
    lineas.append({"type": "assistant", "timestamp": iso(ahora - 5),
                   "message": {"role": "assistant", "model": "claude-opus-5",
                               "usage": {"input_tokens": 10},
                               "content": [{"type": "text", "text": "ya esta"}]}})
    path.write_text("\n".join(json.dumps(x) for x in lineas) + "\n")
    os.utime(path, (ahora, ahora))


def iso(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).astimezone().isoformat()


# ── 1. el parser de ordenes anchas, sobre comandos con la forma de los de verdad ──
ANCHAS = [
    ("git commit -m 'x'",                       [("repo", "", "git commit")]),
    ("git add p/H.md && git commit -q -m \"$(cat <<'EOF'\nfeat: y\nEOF\n)\"",
                                                [("repo", "", "git commit")]),
    ("cd /x && git add progress/A.md notes/b.md", []),
    ("git add -A",                              [("repo", "", "git add")]),
    ("git add .",                               [("repo", "", "git add")]),
    ("git commit -- src/a.py",                  []),
    ("git commit src/a.py -m 'x'",              []),
    ("git checkout .",                          [("repo", "", "git checkout")]),
    ("git checkout -b feat/x",                  []),
    ("git reset --hard origin/main",            [("repo", "", "git reset")]),
    ("git reset HEAD src/a.py",                 []),
    ("git clean -fd",                           [("repo", "", "git clean")]),
    ("git stash",                               [("repo", "", "git stash")]),
    ("git stash list",                          []),
    ("git push origin main",                    []),
    ("git status --short",                      []),
    ("rm -rf build/ dist/",                     [("dir", "build/", "rm -r"),
                                                 ("dir", "dist/", "rm -r")]),
    ("rm -f /tmp/r.sh",                         []),
    ("mv src/viejo.py src/nuevo.py",            [("w", "src/viejo.py", "mv"),
                                                 ("w", "src/nuevo.py", "mv")]),
    ("cp a b",                                  []),
    ("SP=/tmp/x; cp $SP/a b 2>/dev/null",       []),
    ("sudo git commit -m z",                    [("repo", "", "git commit")]),
    ("echo 'git commit -m x' > /tmp/f.sh",      []),
    ("python3 -c \"import os; os.system('rm -rf /')\"", []),
]


def prueba_anchas(ns, fallos):
    for cmd, esperado in ANCHAS:
        got = ns["_anchas"](cmd)
        if got != esperado:
            fallos.append(f"_anchas({cmd[:40]!r}) -> {got}, se esperaba {esperado}")


# ── 2. la escalera de niveles, sobre hechos escritos a mano ──
def hecho(**kw):
    base = {"mismo_fichero": False, "mismo_directorio": False, "mismo_repo": False,
            "ficheros": (), "escrituras_recientes": 0,
            "segundos_desde_la_ultima": None, "orden_ancha": "", "orden_es_mia": False}
    base.update(kw)
    return base


def prueba_niveles(ns, fallos):
    nivel = ns["nivel_colision"]
    casos = [
        (hecho(), 0),
        (hecho(mismo_repo=True), 1),
        (hecho(mismo_repo=True, mismo_directorio=True), 2),
        (hecho(mismo_repo=True, mismo_directorio=True, mismo_fichero=True), 3),
        (hecho(mismo_repo=True, orden_ancha="git commit"), 4),
        # La orden ancha gana al mismo fichero: dos editando el mismo fichero lo notas
        # al guardar; un commit sin pathspec se lleva el indice sin que nada falle.
        (hecho(mismo_fichero=True, mismo_repo=True, orden_ancha="git commit"), 4),
    ]
    for h, esperado in casos:
        if nivel(h) != esperado:
            fallos.append(f"nivel_colision({h}) = {nivel(h)}, se esperaba {esperado}")
    if ns["COLISION_MINIMA"] != 2:
        fallos.append("COLISION_MINIMA ya no es 2: 'mismo repo' volveria a avisar")


# ── 3. la cadena entera, sobre un HOME de mentira ──
def main():
    fallos = []
    ahora = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        casa = pathlib.Path(tmp)
        repo = casa / "repo"
        (repo / ".git").mkdir(parents=True)          # para que `raiz_repo` lo reconozca
        otro = casa / "otro-repo"
        (otro / ".git").mkdir(parents=True)
        proy = casa / ".claude/projects/-repo"
        proy.mkdir(parents=True)

        os.environ["HOME"] = str(casa)
        os.environ["SERENO_TMUX_SOCK"] = "no-existe-este-socket"
        os.environ.pop("SERENO_DEMO", None)
        ns = {"__name__": "sereno_test"}
        exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)

        prueba_anchas(ns, fallos)
        prueba_niveles(ns, fallos)

        def foto():
            ns["_CACHE_DISCO"].clear()
            ns["_HUELLAS"].clear()
            ns["_RAICES"].clear()
            return {r["id"]: r for r in
                    ns["filas_json"](ns["live_sessions"](fino=True, solo_activas=False))}

        # (a) MISMO FICHERO -> nivel 3, en las dos filas.
        transcript(proy / f"{A}.jsonl", str(repo),
                   [("Edit", str(repo / "src/pagos.py"))], ahora)
        transcript(proy / f"{B}.jsonl", str(repo),
                   [("Write", str(repo / "src/pagos.py"))], ahora)
        f = foto()
        if len(f) != 2:
            print(f"FALLA: el HOME de mentira da {len(f)} sesiones, no 2")
            return 1
        for sid in (A, B):
            if f[sid]["clash_level"] != 3:
                fallos.append(f"mismo fichero: {sid[:8]} sale con nivel "
                              f"{f[sid]['clash_level']}, se esperaba 3")
            if f[sid]["clash_files"] != 1:
                fallos.append(f"mismo fichero: {sid[:8]} cuenta "
                              f"{f[sid]['clash_files']} ficheros, se esperaba 1")
        if f[A]["clash_with"] != B or f[B]["clash_with"] != A:
            fallos.append("las dos filas no se apuntan la una a la otra")

        # (b) MISMO REPO, FICHEROS DISTINTOS -> no es choque.
        transcript(proy / f"{B}.jsonl", str(repo),
                   [("Write", str(repo / "docs/leeme.md"))], ahora)
        f = foto()
        for sid in (A, B):
            if f[sid]["clash_level"] >= ns["COLISION_MINIMA"]:
                fallos.append(f"mismo repo y ficheros distintos avisa "
                              f"(nivel {f[sid]['clash_level']}) y no debe")

        # (c) EL COMMIT SIN PATHSPEC sobre ese repo -> nivel 4, con su verbo.
        transcript(proy / f"{B}.jsonl", str(repo),
                   [("Bash", "git commit -m 'wip'")], ahora)
        f = foto()
        if f[A]["clash_level"] != 4:
            fallos.append(f"git commit sin pathspec da nivel {f[A]['clash_level']}, "
                          "se esperaba 4")
        if f[A]["clash_command"] != "git commit":
            fallos.append(f"clash_command es {f[A]['clash_command']!r}, "
                          "se esperaba 'git commit'")

        # (d) OTRO REPO -> no es choque, aunque el commit sea igual de ancho. Es el
        #     caso medido en vivo: un repo independiente DENTRO del monorepo.
        proy2 = casa / ".claude/projects/-otro-repo"
        proy2.mkdir(parents=True)
        (proy / f"{B}.jsonl").unlink()
        transcript(proy2 / f"{B}.jsonl", str(otro),
                   [("Bash", "git commit -m 'wip'")], ahora)
        f = foto()
        if f[A]["clash_level"] >= ns["COLISION_MINIMA"]:
            fallos.append(f"dos repos distintos avisan (nivel {f[A]['clash_level']})")

        # (e) FUERA DE LA VENTANA -> una sesion de hace tres dias no choca con nadie.
        (proy2 / f"{B}.jsonl").unlink()
        viejo = ahora - 3 * 86400
        transcript(proy / f"{B}.jsonl", str(repo),
                   [("Edit", str(repo / "src/pagos.py"))], viejo)
        f = foto()
        if f[A]["clash_level"] >= ns["COLISION_MINIMA"]:
            fallos.append("una sesion de hace tres dias sigue chocando")

        # (f) EL CANARIO: `--json` no puede llevar rutas dentro.
        transcript(proy / f"{B}.jsonl", str(repo), [("Edit", CANARIO)], ahora)
        transcript(proy / f"{A}.jsonl", str(repo), [("Write", CANARIO)], ahora)
        f = foto()
        if f[A]["clash_level"] != 3:
            fallos.append("el canario no llega a chocar, asi que no prueba nada")
        if "CANARIO-CONFIDENCIAL" in json.dumps(f, default=str):
            fallos.append("--json lleva rutas de trabajo dentro")

        # (g) EL FLANCO: se avisa cuando nace, una vez por PAR, y no se repite.
        filas = list(f.values())
        salta = ns["choques_nuevos"]({}, filas)
        if len(salta) != 1:
            fallos.append(f"el flanco da {len(salta)} avisos para un solo par")
        pares = ns["pares_choque"](filas)
        if ns["choques_nuevos"](pares, filas):
            fallos.append("repite el aviso mientras el choque sigue igual")
        # Y sube de nivel -> vuelve a ser noticia.
        subido = [dict(r, clash_level=4) for r in filas]
        if not ns["choques_nuevos"](pares, subido):
            fallos.append("pasar de nivel 3 a 4 no avisa, y deberia")

        # (h) El acumulador no crece sin tope.
        ns["_HUELLAS"].clear()
        muchos = [(ahora, "w", f"/x/f{i}.py", "Edit") for i in range(1000)]
        h = ns["recuerda_toques"]("X", muchos, ahora)
        if len(h) > ns["_TOPE_TOQUES"]:
            fallos.append(f"la huella guarda {len(h)} toques, tope {ns['_TOPE_TOQUES']}")
        if ns["recuerda_toques"]("X", [], ahora + ns["VENTANA_COL"] + 1):
            fallos.append("los toques viejos no se podan al pasar la ventana")

    if fallos:
        print("FALLA:")
        for x in fallos:
            print("  -", x)
        return 1
    print(f"ok: {len(ANCHAS)} comandos, la escalera de 5 niveles, el choque real, "
          "los cuatro casos que no lo son y el flanco")
    return 0


if __name__ == "__main__":
    sys.exit(main())
