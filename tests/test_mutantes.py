#!/usr/bin/env python3
"""Cada guarda del programa tiene que tener un test que se ponga ROJO al romperla.

Un test verde no dice que la guarda funcione: dice que hoy nadie la ha roto. La forma de
saberlo es romperla a mano y mirar si algo se queja — y eso se hizo a mano durante dos
dias, encontrando ocho lagunas que los tests en verde no veian:

  · una decision escrita dos veces, con el test replicandola en su cuerpo en vez de
    llamarla, asi que invertirla en el codigo pasaba en verde;
  · un recuento real sustituido por `len(lista)` —el bug que la release anterior habia
    arreglado— pasando los cuarenta y cuatro tests;
  · un estado guardado como maximo historico en vez del de ahora, que mataba en silencio
    el segundo aviso de una sesion que compacta.

Esto convierte ese ritual en red fija. Cada entrada del catalogo es una guarda de verdad
del programa, con el cambio minimo que la rompe y el test que TIENE que cazarla.

Falla de dos maneras, y las dos importan:

  · **el mutante sobrevive** — hay una guarda sin red: o falta un caso, o el que hay mide
    otra cosa;
  · **el ancla ya no existe** — el codigo cambio y el mutante quedo obsoleto. No se salta
    en silencio: un catalogo que se ignora a si mismo no protege nada, y hay que
    reescribir la entrada apuntando a lo que hay ahora.

Cada mutante corre sobre una COPIA del arbol en un temporal, nunca sobre el fichero de
verdad: una tanda interrumpida a mitad dejaria el programa mutado en el disco. Ya paso.
"""
import pathlib, shutil, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# (que guarda es · ancla exacta en `sereno` · con que se sustituye · quien debe cazarlo)
MUTANTES = [
    # ── el aviso de contexto de --watch ──────────────────────────────────────
    ("el aviso de contexto se repite dentro del mismo escalon",
     'if n and n > antes.get(r["id"], 0):', 'if n and n >= antes.get(r["id"], 0):',
     "test_watch_contexto.py"),
    ("--watch avisa del contexto en la primera vuelta, sin linea base",
     "for r, pct in (() if primera else contextos_nuevos(ctxs, filas)):",
     "for r, pct in contextos_nuevos(ctxs, filas):",
     "test_watch_contexto.py"),
    ("un tope de contexto que no consta deja de frenar el aviso",
     "if not ctx or not tope or not esc:", "if not ctx or not esc:",
     "test_watch_contexto.py"),
    ("el escalon cruzado es el mas bajo en vez del mas alto",
     "return max(pasados) if pasados else 0", "return min(pasados) if pasados else 0",
     "test_watch_contexto.py"),
    ("el nivel de contexto se guarda como maximo historico",
     'ctxs = {r["id"]: nivel_ctx(r) for r in filas}',
     'ctxs = dict(ctxs, **{r["id"]: max(nivel_ctx(r), ctxs.get(r["id"], 0)) for r in filas})',
     "test_watch_contexto.py"),

    # ── reanudar huerfanas: archivar sin haber abierto es perderlas ──────────
    ("se archiva una huerfana aunque no se abriera",
     '    if hechas:\n        archive(archivar, "restored")',
     '    if True:\n        archive(archivar, "restored")',
     "test_huerfanas_no_se_archivan_sin_abrir.py"),
    ("el archive sale de la guarda y corre siempre",
     '    cual, hechas = abre_varias(pestanas, config)\n    if hechas:\n        archive(archivar, "restored")',
     '    cual, hechas = abre_varias(pestanas, config)\n    archive(archivar, "restored")',
     "test_huerfanas_no_se_archivan_sin_abrir.py"),

    # ── abrir varias: la pantalla no puede mentir sobre cuantas se abrieron ──
    ("abre_varias devuelve las pedidas en vez de las abiertas",
     "    return cual, LANZADORES[cual][1](pestanas)",
     "    LANZADORES[cual][1](pestanas)\n    return cual, len(pestanas)",
     "test_lanzadores.py"),
    ("tmux_kill vuelve a llamar al binario sin try",
     '    try:\n        subprocess.run([TMUX_BIN, "-L", SOCK] + orden, check=False)\n    except OSError:\n        pass',
     '    subprocess.run([TMUX_BIN, "-L", SOCK] + orden, check=False)',
     "test_lanzadores.py"),

    # ── --dismiss: el flag vivia detras de la bifurcacion y no llegaba nunca ─
    ("--dismiss vuelve a quedar detras de la bifurcacion de main",
     '    if "--dismiss" in argv:', '    if False and "--dismiss" in argv:',
     "test_dismiss_no_se_lo_come_la_lista.py"),

    # ── --hoy: la jornada y lo que cuenta como trabajo ───────────────────────
    ("el dia empieza a medianoche en vez de a las cinco",
     "    if t < inicio:", "    if False:", "test_hoy.py"),
    ("la jornada deja de filtrar por mtime y cuenta la vida entera",
     "        if mt >= corte:\n            cands.append((mt, p))",
     "        cands.append((mt, p))", "test_hoy.py"),
    ("el gasto que nadie midio se cuenta como cero",
     '            "turnos": u["turnos"] if u else None,',
     '            "turnos": u["turnos"] if u else 0,', "test_hoy.py"),
    ("'a medias' incluye lo que ya se dio por parado",
     'if s["estado"] in ("waiting", "writing", "in_command")]',
     'if s["estado"] in ("waiting", "writing", "in_command", "stopped")]',
     "test_hoy.py"),

    # ── lo desechable: nacido en un temporal no es trabajo ───────────────────
    ("las raices temporales casan por prefijo y no por tramo",
     '    return any(r == t or r.startswith(t + "/") for t in _raices_temporales())',
     "    return any(r.startswith(t) for t in _raices_temporales())",
     "test_de_usar_y_tirar.py"),
    ("una ruta que no consta cuenta como temporal",
     "    if not ruta:\n        return False", "    if not ruta:\n        return True",
     "test_de_usar_y_tirar.py"),
    ("TMPDIR deja de contar como temporal",
     '        crudo = [os.environ.get("TMPDIR", ""), "/tmp", "/var/tmp",',
     '        crudo = ["", "/tmp", "/var/tmp",', "test_de_usar_y_tirar.py"),
    ("el historial vuelve a ofrecer lo desechable",
     "        if de_usar_y_tirar(_proyecto_de_dir(p.parent.name)):\n            continue\n        try:\n            mt = p.stat().st_mtime",
     "        if False:\n            continue\n        try:\n            mt = p.stat().st_mtime",
     "test_de_usar_y_tirar.py"),
    ("--disk mete los proyectos temporales en el reparto",
     "            if de_usar_y_tirar(_proyecto_de_dir(d.name)):\n                n_tirar += 1",
     "            if False:\n                n_tirar += 1", "test_de_usar_y_tirar.py"),
    ("--find mira lo desechable sin decirlo",
     "        if not todo and de_usar_y_tirar(_proyecto_de_dir(p.parent.name)):",
     "        if False:", "test_de_usar_y_tirar.py"),
]

TOPE = 180          # segundos por mutante: uno colgado no cuelga la tanda entera


def main():
    fuente = (RAIZ / "sereno").read_text("utf-8")
    obsoletos, vivos = [], []
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        copia = pathlib.Path(tmp) / "arbol"
        shutil.copytree(RAIZ, copia,
                        ignore=shutil.ignore_patterns(".git", "__pycache__",
                                                      ".pytest_cache", "docs"))
        for que, ancla, reemplazo, quien in MUTANTES:
            n = fuente.count(ancla)
            if n != 1:
                obsoletos.append(f"{que}: el ancla aparece {n} veces (se esperaba 1)")
                continue
            (copia / "sereno").write_text(fuente.replace(ancla, reemplazo, 1), "utf-8")
            try:
                r = subprocess.run([sys.executable, str(copia / "tests" / quien)],
                                   capture_output=True, text=True, timeout=TOPE,
                                   cwd=str(copia))
                muerto = r.returncode != 0
            except subprocess.TimeoutExpired:
                muerto = True        # colgarse tambien es quejarse
            print(f"{'muere' if muerto else 'VIVO '}  {quien:<42} {que}")
            if not muerto:
                vivos.append(f"{que}  ->  {quien} no lo caza")
        (copia / "sereno").write_text(fuente, "utf-8")

    print(f"\n{len(MUTANTES) - len(vivos) - len(obsoletos)}/{len(MUTANTES)} mutantes "
          f"muertos ({time.time() - t0:.0f}s)")
    if obsoletos:
        print("\nANCLAS QUE YA NO EXISTEN — el catalogo se quedo viejo, hay que "
              "reescribir estas entradas apuntando al codigo de ahora:")
        for o in obsoletos:
            print("  -", o)
    if vivos:
        print("\nGUARDAS SIN RED — se puede romper esto y ningun test se entera:")
        for v in vivos:
            print("  -", v)
    return 1 if (vivos or obsoletos) else 0


if __name__ == "__main__":
    sys.exit(main())
