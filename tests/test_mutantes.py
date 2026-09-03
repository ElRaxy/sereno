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
    # ── lo tecleado en el cuadro de cerrar ───────────────────────────────────
    ("el rango se materializa entero antes de recortarlo",
     "            a, b = max(a, 1), min(b, len(rows))",
     "            a, b = a, b",
     "test_parse_sel.py"),
    ("una palabra que no es atajo se ignora en vez de invalidar la seleccion",
     "        else:\n            return None                # una palabra que no es atajo: no adivinar",
     "        else:\n            continue                   # una palabra que no es atajo: no adivinar",
     "test_parse_sel.py"),
    ("una fila sin estado observado cuenta como parada y se cerraria",
     'return [i for i, r in enumerate(rows) if r["working"] is False]',
     'return [i for i, r in enumerate(rows) if not r["working"]]',
     "test_parse_sel.py"),
    ("no entender lo tecleado se confunde con no seleccionar nada",
     "    return out or None", "    return out",
     "test_parse_sel.py"),

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

    # ── el raton SGR, que el ncurses de macOS no sabe leer ───────────────────
    ("un sitio se queda llamando a leer_sgr con la firma de cuando estaba dentro",
     "                sgr = leer_sgr(stdscr, curses.ungetch, espera)",
     "                sgr = leer_sgr(stdscr)",
     "test_raton_en_la_tui.py"),
    ("las coordenadas del raton llegan sin restar el uno de la esquina",
     '                return b, mx - 1, my - 1, k == ord("M")',
     '                return b, mx, my, k == ord("M")',
     "test_raton_sgr.py"),
    ("una secuencia a medias devuelve coordenadas en vez de descartarse",
     "                if len(campos) != 3 or not all(c.isdigit() for c in campos):",
     "                    if False:",
     "test_raton_sgr.py"),
    ("soltar el boton se confunde con pulsarlo",
     '            elif k in (ord("M"), ord("m")):',
     '            elif k in (ord("M"),):',
     "test_raton_sgr.py"),
    ("la tecla que no era del raton se la come el parser",
     '        if k != ord("["):\n            if k != -1:\n                ungetch(k)',
     '        if k != ord("["):\n            if False:\n                ungetch(k)',
     "test_raton_sgr.py"),
    ("la espera corta de leer la secuencia se queda puesta",
     "        win.timeout(espera if restaurar is None else restaurar)",
     "            pass",
     "test_raton_sgr.py"),
    ("el bucle que lee los campos deja de estar acotado",
     "        for _ in range(24):", "            while True:",
     "test_raton_sgr.py"),

    # ── la orden lleva la RUTA del CLI, no su nombre ─────────────────────────
    # Warp escribe el comando en una shell INTERACTIVA, donde mandan los alias. Con el
    # nombre pelado, `claude` puede ser un wrapper que anade flags que Sereno no pide —
    # paso el 2026-09-01 con `--allow-dangerously-skip-permissions`. Son TRES sitios los
    # que componen ordenes y basta uno mal para que el alias vuelva a colarse, asi que
    # hay un mutante por sitio: uno solo no probaria que estan los tres.
    ("la sesion de Claude parada se reabre por el nombre y no por la ruta",
     'orden = ([bin_cli("claude")] + _con_modelo("claude", modelo)',
     'orden = (["claude"] + _con_modelo("claude", modelo)',
     "test_binario_no_alias.py"),
    ("el historial de otro CLI se reabre por el nombre y no por la ruta",
     '        orden = [bin_cli(cli)] + _con_modelo(cli, modelo) + list(r["abrir"][1:])',
     '        orden = list(r["abrir"])',
     "test_binario_no_alias.py"),
    ("las huerfanas del registro se reabren por el nombre y no por la ruta",
     '        cmd = " ".join([shlex.quote(bin_cli("claude")), "--resume", e["id"]]',
     '        cmd = " ".join(["claude", "--resume", e["id"]]',
     "test_binario_no_alias.py"),
    ("el relevo a Codex arranca por el nombre y no por la ruta",
     '    "codex": lambda prompt, modelo=None: shlex.quote(bin_cli("codex")) + _modelo_seg("codex", modelo) + " --dangerously-bypass-approvals-and-sandbox " + shlex.quote(prompt),',
     '    "codex": lambda prompt, modelo=None: "codex" + _modelo_seg("codex", modelo) + " --dangerously-bypass-approvals-and-sandbox " + shlex.quote(prompt),',
     "test_binario_no_alias.py"),
    ("el relevo a Claude arranca por el nombre y no por la ruta",
     '    "claude": lambda prompt, modelo=None: shlex.quote(bin_cli("claude")) + _modelo_seg("claude", modelo) + " --permission-mode bypassPermissions " + shlex.quote(prompt),',
     '    "claude": lambda prompt, modelo=None: "claude" + _modelo_seg("claude", modelo) + " --permission-mode bypassPermissions " + shlex.quote(prompt),',
     "test_binario_no_alias.py"),

    # ── el relevo entrega el destino en Bypass Permissions ──────────────────
    # El flag va POR DEFECTO y explicito (no por alias). Si alguien lo quita, el relevo
    # arranca frenando en cada permiso y deja de ser un traspaso util: lo mata la
    # asercion positiva de test_binario_no_alias.py.
    ("el relevo a Codex deja de entregar en bypass",
     ' + " --dangerously-bypass-approvals-and-sandbox " + ',
     ' + " " + ',
     "test_binario_no_alias.py"),
    ("el relevo a Claude deja de entregar en bypass",
     ' + " --permission-mode bypassPermissions " + ',
     ' + " " + ',
     "test_binario_no_alias.py"),

    # ── el relevo es un traspaso: lleva con que seguir, y lee a Codex ────────
    # Un relevo sin el ultimo intercambio deja a quien lo recibe sin saber que se
    # estaba haciendo — el fallo que se vio relevando Codex a Claude. Por defecto va;
    # `SERENO_RELEVO=seco` es la unica salida, para trabajo de cliente.
    ("el briefing deja de llevar el ultimo intercambio por defecto",
     '    if _env("RELEVO") != "seco":', '    if False:',
     "test_relevo.py"),
    # Y leer a Codex es lo que hace que el briefing DESDE Codex no salga vacio: sin la
    # ultima respuesta, el receptor no tiene el plan ni el siguiente paso.
    ("relevar desde Codex se queda sin la ultima respuesta de la sesion",
     '                d["resp"] = _sin_tabla(txt)\n', '                pass\n',
     "test_codex_rollout.py"),

    # ── las pastillas del pie: donde pinchas es lo que se ejecuta ────────────
    ("el pie se pinta pero sus pastillas dejan de poder pincharse",
     '                zonas.append((y + 2, px, pxf, "tecla", cod))',
     '                pass',
     "test_click_en_el_pie.py"),
    ("las zonas del pie se comen la separacion entre pastillas",
     '                zonas.append((y + 2, px, pxf, "tecla", cod))',
     '                zonas.append((y + 2, px, pxf + 2, "tecla", cod))',
     "test_click_en_el_pie.py"),
    # `r` (abre VARIAS a la vez) y `c` (releva a otro CLI) son las dos teclas que solo
    # actuan sobre lo marcado. Las dos vivieron escondidas en la ayuda —`c` hasta que el
    # pie se hizo sensible al contexto— y su caida no rompe nada VISIBLE: vuelven a ser
    # invisibles, que es como estaban. Por eso cada una necesita su mutante. El de `r`
    # borra su linea de la rama SIN marcar, donde va detras de `/ filtrar`; el par `/`+`r`
    # solo sale ahi, asi que el ancla es unica pese a que `r` aparezca en las dos ramas.
    ("la tecla que abre varias a la vez desaparece del pie",
     '                 ("/", _("filter"), ord("/")),\n'
     '                 ("r", _("reopen"), ord("r")),\n',
     '                 ("/", _("filter"), ord("/")),\n',
     "test_zonas_del_pie.py"),
    ("la tecla que releva a otro CLI desaparece del pie con marcadas",
     '                 ("c", _("relay"), ord("c")),\n', '',
     "test_zonas_del_pie.py"),
    # La ayuda `?` explica los simbolos de fila, no solo las teclas. Que se caiga esa
    # seccion es la misma clase de regresion silenciosa que `c` fuera del pie.
    ("la ayuda deja de explicar los simbolos de cada fila",
     '                    (_("symbols"), "\\u25cf " + _("writing a reply")),\n', '',
     "test_tui_arranca.py"),
    # El /rename del usuario (custom-title.json) tiene que ganar al aiTitle. Si se deja
    # de leer ese fichero, una sesion renombrada vuelve a salir con su titulo viejo y
    # nadie se entera: es exactamente el bug que esto arreglo.
    ("deja de leer el /rename y la sesion sale con su titulo viejo",
     "    ct = custom_title(fila[\"meta\"])", '    ct = ""',
     "test_rename.py"),
    ("las zonas de las pastillas del pie se solapan con la vecina",
     "        out.append((tecla, txt, cod, hx, hx + ancho(pastilla) - 1))",
     "        out.append((tecla, txt, cod, hx, hx + ancho(pastilla) + 1))",
     "test_zonas_del_pie.py"),
    ("las pastillas se pintan pegadas y su zona se come la de al lado",
     "        hx += ancho(pastilla) + sep", "        hx += ancho(pastilla)",
     "test_zonas_del_pie.py"),
    ("el pie sigue pintando pastillas que no caben en la ventana",
     "        if hx + ancho(pastilla) >= w - 2:\n            break",
     "        if False:\n            break",
     "test_zonas_del_pie.py"),
    ("un click cuenta para la zona de la fila de al lado",
     "    return next((z for z in zonas if z[0] == my and z[1] <= mx <= z[2]), None)",
     "    return next((z for z in zonas if z[1] <= mx <= z[2]), None)",
     "test_zonas_del_pie.py"),
    ("la ultima columna de una zona deja de contar como suya",
     "    return next((z for z in zonas if z[0] == my and z[1] <= mx <= z[2]), None)",
     "    return next((z for z in zonas if z[0] == my and z[1] <= mx < z[2]), None)",
     "test_zonas_del_pie.py"),

    # ── los cinco que encontro el barrido de mutacion del 2026-09-01 ─────────
    ("`git clean` se anuncia sin mirar si lleva -f, o un -f de otro subcomando lo dispara",
     '            elif sub == "clean" and any(re.match(r"-[a-zA-Z]*f", a) for a in resto):',
     '            elif sub == "clean" or any(re.match(r"-[a-zA-Z]*f", a) for a in resto):',
     "test_colisiones.py"),
    ("el escalon de contexto se cruza al pasarse, no al llegar",
     "    pasados = [e for e in esc if lleno >= e]",
     "    pasados = [e for e in esc if lleno > e]",
     "test_watch_contexto.py"),
    ("la hora 23 deja de valer como inicio de jornada",
     "    hora = int(crudo) if crudo.isdigit() and 0 <= int(crudo) <= 23 else HORA_JORNADA",
     "    hora = int(crudo) if crudo.isdigit() and 0 <= int(crudo) < 23 else HORA_JORNADA",
     "test_hoy.py"),
    ("la duracion de cada paso del recorrido sale siempre a cero",
     '    secs = int(secs or 0)\n    if secs < 60:',
     '    secs = int(secs and 0)\n    if secs < 60:',
     "test_recorrido.py"),
    ("se pregunta a un tmux que no esta instalado, o no se pregunta al que si esta",
     "    if not pathlib.Path(TMUX_BIN).exists():\n        return []",
     "    if pathlib.Path(TMUX_BIN).exists():\n        return []",
     "test_lo_que_ve_tmux.py"),
    ("sin tmux, la lista de sesiones vivas se la inventa en vez de venir vacia",
     "    if r.returncode != 0:\n        return []                      # sin servidor = sin sesiones, no es error",
     "    if False:\n        return []                      # sin servidor = sin sesiones, no es error",
     "test_lo_que_ve_tmux.py"),

    # ── la fila de "(nada coincide)" no es una sesion ────────────────────────
    ("las teclas de seleccion llegan a la fila que no es una sesion",
     '            if rows and rows[0].get("_vacio"):\n                if c in (ord("q"), ord("Q")):',
     '            if False:\n                if c in (ord("q"), ord("Q")):',
     "test_lista_vacia.py"),
    ("con la lista vacia la guarda se come tambien la tecla de salir",
     '                if c in (ord("q"), ord("Q")):\n                    return\n                if c in (curses.KEY_BACKSPACE, 127, 8):\n                    filtro = ""',
     '                if c in (curses.KEY_BACKSPACE, 127, 8):\n                    filtro = ""',
     "test_lista_vacia.py"),
    ("con la lista vacia ya no se puede deshacer el filtro",
     '                if c in (curses.KEY_BACKSPACE, 127, 8):\n                    filtro = ""\n                continue',
     '                continue',
     "test_lista_vacia.py"),

    # ── nada de codigo que no llama nadie ────────────────────────────────────
    ("vuelve a colarse una funcion que no llama nadie",
     "def hook_line(rows, items):",
     "def _fecha_corta(epoch):\n    return \"?\"\n\n\ndef hook_line(rows, items):",
     "test_sin_codigo_muerto.py"),

    # ── los MB de una sesion: el arbol, contado una vez y sin colgarse ───────
    ("los MB de una sesion son solo los del pid raiz, sin sus descendientes",
     "        return rss.get(pid, 0) + sum(suma(h, visto) for h in hijos.get(pid, ()))",
     "        return rss.get(pid, 0)",
     "test_ram_por_arbol.py"),
    ("la recursion de la RAM pierde la marca de por donde ha pasado",
     "        if pid in visto:\n            return 0\n        visto.add(pid)",
     "        if pid in visto:\n            return 0",
     "test_ram_por_arbol.py"),
    ("un pid que no es un numero llega a int() y revienta la vista",
     '    return {p: suma(int(p), set()) / 1024 for p in pids if str(p).isdigit()}',
     "    return {p: suma(int(p), set()) / 1024 for p in pids}",
     "test_ram_por_arbol.py"),

    # ── el panel de la fila bajo el cursor ───────────────────────────────────
    ("un subagente pisa lo que respondio la sesion en el panel",
     '            if j.get("isSidechain") or j.get("type") != "assistant":',
     '            if j.get("type") != "assistant":',
     "test_detalles_del_cursor.py"),
    ("el panel se queda con las lineas crudas del transcript pegadas a la fila",
     '        d["ruta"] = recorrido(crudos)', '        d["ruta"] = crudos',
     "test_detalles_del_cursor.py"),
    ("el panel vuelve a abrir el transcript aunque la fila ya tenga el dato",
     '    if "_det" in r:\n        return r["_det"]', '    if False:\n        return r["_det"]',
     "test_detalles_del_cursor.py"),

    # ── lo dicho por el usuario, y el cwd que sale de la cabecera ────────────
    ("lo que escribe un subagente cuenta como escrito por el usuario",
     '        if d.get("type") != "user" or d.get("isSidechain"):',
     '        if d.get("type") != "user":',
     "test_lo_dicho_y_la_cabecera.py"),
    ("los comandos que se expanden solos cuentan como lo que se tecleo",
     '        if not t or t.startswith("<"):', "        if not t:",
     "test_lo_dicho_y_la_cabecera.py"),
    ("la cabecera deja de acotarse y el barrido lee 880 ficheros enteros",
     "                if i > tope:\n                    break",
     "                if False:\n                    break",
     "test_lo_dicho_y_la_cabecera.py"),

    # ── abrir varias: la pantalla no puede mentir sobre cuantas se abrieron ──
    ("abre_varias devuelve las pedidas en vez de las abiertas",
     "    return cual, LANZADORES[cual][1](pestanas)",
     "    LANZADORES[cual][1](pestanas)\n    return cual, len(pestanas)",
     "test_lanzadores.py"),
    ("tmux_kill vuelve a llamar al binario sin try",
     '    try:\n        subprocess.run([TMUX_BIN, "-L", SOCK] + orden, check=False)\n    except OSError:\n        pass',
     '    subprocess.run([TMUX_BIN, "-L", SOCK] + orden, check=False)',
     "test_lanzadores.py"),
    # Dentro de tmux, el relevo tiene que abrir "donde ya estas": si tmux deja de pasar al
    # frente, vuelve a caer en Warp —ventana nueva— y se pierde el "mismo Warp".
    ("dentro de tmux, tmux deja de ponerse el primero de los lanzadores",
     '            nombres = ["tmux"] + [n for n in nombres if n != "tmux"]\n',
     '            pass\n',
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

    ("'a medias' vuelve a salir en el orden del mtime",
     '        key=lambda s: (s["estado"] == "waiting", s["idle"] if s["idle"] is not None else 1e9))',
     "        key=lambda s: 0)", "test_hoy.py"),

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

    # ── que comparten dos sesiones: los hechos, uno a uno ───────────────────
    ("dos sesiones fuera de todo repo pasan a compartirlo",
     '    mismo_repo = bool(mia["repo"]) and mia["repo"] == otra["repo"]',
     '    mismo_repo = mia["repo"] == otra["repo"]',
     "test_hechos_colision.py"),
    ("un rm -r salta aunque no pise nada de la otra sesion",
     '            elif clase == "dir" and any(f.startswith(ruta.rstrip("/") + "/")\n                                        for f in ajenos):',
     '            elif clase == "dir":',
     "test_hechos_colision.py"),
    ("la carpeta compartida deja de contar como terreno comun",
     '    terreno = comunes or ({r for r in fotra if os.path.dirname(r) in dmia}\n                          if dmia & dotra else set())',
     '    terreno = comunes',
     "test_hechos_colision.py"),
    ("un tiempo que no se pudo medir se cuenta como cero segundos",
     '        "segundos_desde_la_ultima": int(ahora - max(calientes)) if calientes else None,',
     '        "segundos_desde_la_ultima": int(ahora - max(calientes)) if calientes else 0,',
     "test_hechos_colision.py"),
    ("las ordenes anchas dejan de contar como actividad reciente",
     '    calientes = [ts for (c, r, _v), ts in otra["toques"].items()\n                 if (c == "w" and r in terreno) or (c != "w" and mismo_repo)]',
     '    calientes = [ts for (c, r, _v), ts in otra["toques"].items()\n                 if (c == "w" and r in terreno)]',
     "test_hechos_colision.py"),
    ("el aviso dice que la orden ancha es del otro cuando es tuya",
     '    for suya, quien, ajenos in ((True, mia, fotra), (False, otra, fmia)):',
     '    for suya, quien, ajenos in ((False, mia, fotra), (True, otra, fmia)):',
     "test_hechos_colision.py"),
    ("el aviso lista los ficheros de la otra sesion en vez de los comunes",
     '        "ficheros": tuple(sorted(comunes)),',
     '        "ficheros": tuple(sorted(fotra)),',
     "test_hechos_colision.py"),

    # ── la cola del transcript, que es el bucle vivo del selector ────────────
    ("la cola para en la primera vuelta: vuelve el bug de la linea que no cabe",
     '                if saltos > cuantas or pos == 0:', '                if True:',
     "test_ultimas_lineas.py"),
    ("se descarta la primera linea aunque no venga partida",
     "    if pos > 0 and lineas:", "    if lineas:", "test_ultimas_lineas.py"),
    ("no se descarta la linea partida por el retroceso",
     "    if pos > 0 and lineas:\n        lineas = lineas[1:]",
     "    if False:\n        lineas = lineas[1:]", "test_ultimas_lineas.py"),
    ("el hueco del salto final se come una de las lineas pedidas",
     "    utiles = [l for l in lineas if l.strip()][-cuantas:]",
     "    utiles = [l for l in lineas[-cuantas:] if l.strip()]",
     "test_ultimas_lineas.py"),
    ("se vuelve a releer desde el nuevo tope hasta el final en cada vuelta",
     "                b = f.read(cuanto)\n                trozos.append(b)",
     "                b = f.read(size - pos)\n                trozos = [b]",
     "test_ultimas_lineas.py"),
    ("el tope de lectura desaparece: una linea enorme se trae entera",
     "            while pos > 0 and leido < tope:", "            while pos > 0:",
     "test_ultimas_lineas.py"),
    ("un transcript que desaparece a mitad revienta en vez de devolver nada",
     '    except OSError:\n        return []\n    lineas = b"".join',
     '    except OSError:\n        raise\n    lineas = b"".join',
     "test_ultimas_lineas.py"),

    # ── el contrato de --json, que leen scripts de otros ─────────────────────
    ("--json deja de anunciar la version de su contrato",
     '    print(json.dumps({"sereno": VERSION, "schema": ESQUEMA_JSON,\n                      "sessions": filas_json(rows)},',
     '    print(json.dumps({"sereno": VERSION, "sessions": filas_json(rows)},',
     "test_json_sin_conversacion.py"),
    ("el numero de contrato se mueve sin que nadie lo declare",
     "ESQUEMA_JSON = 1", "ESQUEMA_JSON = 2", "test_json_sin_conversacion.py"),

    # ── los dos cuadros que preguntan antes de abrir ventanas ────────────────
    ("relevo: el singular/plural del titulo se invierte",
     '    out = [(_("Hand over {n} session to:", n=len(sel)) if len(sel) == 1',
     '    out = [(_("Hand over {n} session to:", n=len(sel)) if len(sel) != 1',
     "test_cuadros_de_eleccion.py"),
    ("abrir: el singular/plural del titulo se invierte",
     '    out = [(_("Open {n} session in:", n=len(sel)) if len(sel) == 1',
     '    out = [(_("Open {n} session in:", n=len(sel)) if len(sel) != 1',
     "test_cuadros_de_eleccion.py"),
    ("relevo: la lista se recorta sin decir cuantas quedan fuera",
     '    if len(sel) > tope:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    out.append(("   ".join',
     '    if False:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    out.append(("   ".join',
     "test_cuadros_de_eleccion.py"),
    ("abrir: la lista se recorta sin decir cuantas quedan fuera",
     '    if len(sel) > tope:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    for i, n in enumerate(lanzadores):',
     '    if False:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    for i, n in enumerate(lanzadores):',
     "test_cuadros_de_eleccion.py"),
    ("relevo: los CLI que no se pueden ofrecer se esconden",
     "    for motivo, nombres in porque.items():", "    for motivo, nombres in []:",
     "test_cuadros_de_eleccion.py"),
    ("relevo: los ausentes se agrupan bajo un motivo que no es el suyo",
     "        porque.setdefault(motivo, []).append(nombre)",
     '        porque.setdefault("", []).append(nombre)',
     "test_cuadros_de_eleccion.py"),
    ("relevo: se pregunta donde abrir habiendo un solo sitio",
     "    if len(hay_donde) > 1:", "    if hay_donde:",
     "test_cuadros_de_eleccion.py"),
    ("relevo: el toggle se pinta igual activo que apagado",
     '                           v=_("yes") if con_conv else _("no")), 7 if con_conv else 4))',
     '                           v=_("yes") if con_conv else _("no")), 7))',
     "test_cuadros_de_eleccion.py"),
    ("relevo: no se avisa de que la conversacion se escribe a disco",
     '    if con_conv:\n        out.append(("    " + _("it is written to Warp\'s config, on disk"), 2))',
     '    if False:\n        out.append(("    " + _("it is written to Warp\'s config, on disk"), 2))',
     "test_cuadros_de_eleccion.py"),
    ("relevo: el titulo no se recorta y estira el cuadro",
     '        out.append(("\\u00b7 " + recorta(r.get("title_full") or r.get("name") or "",\n                                        ancho - 6), 0))\n    if len(sel) > tope:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    out.append(("   ".join',
     '        out.append(("\\u00b7 " + (r.get("title_full") or r.get("name") or ""), 0))\n    if len(sel) > tope:\n        out.append(("  " + _("and {n} more", n=len(sel) - tope), 4))\n    out.append(("", 0))\n    out.append(("   ".join',
     "test_cuadros_de_eleccion.py"),

    # ── la vista de todas: el texto es lo unico que sobrevive a una tuberia ──
    ("el reparto trabajando/esperando se invierte",
     '    trabajando = sum(1 for f in filas if f["estado"] in TRABAJANDO)',
     '    trabajando = sum(1 for f in filas if f["estado"] not in TRABAJANDO)',
     "test_lineas_now.py"),
    ("el estado deja de ir en texto y solo queda el color",
     '        cola = ESTADO_LARGO(f["estado"])', '        cola = ""',
     "test_lineas_now.py"),
    ("el 'hace tanto' sale tambien en las que estan trabajando",
     '        if f["estado"] not in TRABAJANDO and f["idle"]:', '        if f["idle"]:',
     "test_lineas_now.py"),
    ("el titulo de la vista de todas no se recorta",
     '        out.append(("%s  %s" % (rellena(recorta(cabeza, ancho_t), ancho_t), cola), 0))',
     '        out.append(("%s  %s" % (cabeza, cola), 0))', "test_lineas_now.py"),
    ("el proyecto deja de pegarse al titulo y gasta un renglon",
     '        if f["proyecto"]:\n            cabeza += "  \\u00b7  " + f["proyecto"]',
     '        if False:\n            cabeza += "  \\u00b7  " + f["proyecto"]',
     "test_lineas_now.py"),
    ("una sesion sin llamadas queda muda en vez de decirlo",
     '        if not f["eventos"]:', "        if False:", "test_lineas_now.py"),
    ("las alertas de atasco no se pintan",
     '        for clave in f["atasco"]:', "        for clave in []:",
     "test_lineas_now.py"),
    ("la cuenta de vivas sale del numero de las que trabajan",
     '              n=len(filas), t=trabajando, e=len(filas) - trabajando), 6)]',
     '              n=trabajando, t=trabajando, e=len(filas) - trabajando), 6)]',
     "test_lineas_now.py"),

    # ── el indice de Codex, que solo crece ───────────────────────────────────
    ("una sesion repetida en el indice de Codex sale dos veces",
     '                vistos[j["id"]] = j', '                vistos[len(vistos)] = j',
     "test_sesiones_codex.py"),
    ("de una sesion de Codex gana la linea vieja en vez de la ultima",
     '                vistos[j["id"]] = j', '                vistos.setdefault(j["id"], j)',
     "test_sesiones_codex.py"),
    ("las sesiones de Codex dejan de ordenarse por fecha",
     '    out.sort(key=lambda r: -(r["created"] or 0))', "    out.sort(key=lambda r: 0)",
     "test_sesiones_codex.py"),
    ("el orden de Codex se invierte y quedan las mas viejas",
     '    out.sort(key=lambda r: -(r["created"] or 0))',
     '    out.sort(key=lambda r: (r["created"] or 0))', "test_sesiones_codex.py"),
    ("el limite de sesiones de Codex desaparece",
     "    out = out[:limite]", "    out = out", "test_sesiones_codex.py"),
    ("una linea a medias del indice tumba la lectura entera",
     '            except Exception:\n                continue\n            if j.get("id"):',
     '            except Exception:\n                raise\n            if j.get("id"):',
     "test_sesiones_codex.py"),
    ("una sesion de Codex sin titulo se pinta sin nada",
     '                                 j.get("thread_name") or "(sin nombre)",',
     '                                 j.get("thread_name") or "",',
     "test_sesiones_codex.py"),
    ("se lee el indice de Codex entero en vez de su cola",
     '        for linea in _tail(CODEX_INDEX, 512 * 1024).decode("utf-8", "replace").splitlines():',
     '        for linea in CODEX_INDEX.read_bytes().decode("utf-8", "replace").splitlines():',
     "test_sesiones_codex.py"),

    # ── --disk: lo que recuperarias, no solo lo que ocupa ────────────────────
    ("los tramos de antiguedad no acumulan y solo cuenta el mas alto",
     "            for dias in _CORTES_EDAD:\n                if edad is not None and edad >= dias * 86400:",
     "            for dias in _CORTES_EDAD[-1:]:\n                if edad is not None and edad >= dias * 86400:",
     "test_disk.py"),
    ("una fecha que no se pudo leer cuenta como sesion vieja",
     "                if edad is not None and edad >= dias * 86400:",
     "                if edad is None or edad >= dias * 86400:", "test_disk.py"),
    ("el corte de antiguedad compara segundos contra dias",
     "                if edad is not None and edad >= dias * 86400:",
     "                if edad is not None and edad >= dias:", "test_disk.py"),
    ("los tramos se invierten y sale lo RECIENTE en vez de lo viejo",
     "                if edad is not None and edad >= dias * 86400:",
     "                if edad is not None and edad <= dias * 86400:", "test_disk.py"),
    ("el tramo cuenta sesiones pero no suma su peso",
     "                    cortes[dias][1] += tam", "                    cortes[dias][1] += 0",
     "test_disk.py"),
    ("los cortes de antiguedad se quedan en uno solo",
     "_CORTES_EDAD = (7, 30, 90, 365)", "_CORTES_EDAD = (7,)", "test_disk.py"),

    # ── medir en columnas: si esto falla, la fila se sale y curses no avisa ──
    ("el selector de variacion deja de contarse y el emoji mide una columna",
     "    if siguiente == _VS16:\n        return 2", "    if False:\n        return 2",
     "test_ancho_en_columnas.py"),
    ("los combinantes vuelven a ocupar columna",
     '    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Cf"):\n        return 0',
     "    if False:\n        return 0", "test_ancho_en_columnas.py"),
    ("el ancho doble se mide como uno",
     '    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1',
     "    return 1", "test_ancho_en_columnas.py"),
    ("recorta mira el caracter anterior en vez del siguiente",
     '        w = _columnas(ch, s[i + 1] if i + 1 < len(s) else "")',
     '        w = _columnas(ch, s[i - 1] if i else "")', "test_ancho_en_columnas.py"),
    ("ancho deja de mirar el caracter siguiente",
     '    return sum(_columnas(ch, s[i + 1] if i + 1 < len(s) else "")\n               for i, ch in enumerate(s))',
     "    return sum(_columnas(ch) for ch in s)", "test_ancho_en_columnas.py"),
    ("recorta se pasa una columna del ancho pedido",
     "        if usado + w > cols - 1:", "        if usado + w > cols:",
     "test_ancho_en_columnas.py"),
    ("rellena cuenta caracteres en vez de columnas",
     '    return s + " " * max(0, cols - ancho(s))',
     '    return s + " " * max(0, cols - len(s))', "test_ancho_en_columnas.py"),
    # ── el reparto del panel lateral ─────────────────────────────────────────
    ("el recorrido no reserva su sitio y se lo come lo de arriba",
     "    base_ruta = base_campos - alto_ruta", "    base_ruta = base_campos",
     "test_panel_lateral.py"),
    ("los pasos del recorrido no se acotan al sitio que queda",
     "min(RUTA_VISIBLE, n_ruta_total, sitio)", "min(RUTA_VISIBLE, n_ruta_total)",
     "test_panel_lateral.py"),
    ("un bloque puede quedarse con cero lineas bajo su cabecera",
     "else max(1, min(q, round(libre * q / max(1, total))))",
     "else min(q, round(libre * q / max(1, total)))",
     "test_panel_lateral.py"),
    ("los campos ceden por abajo y se salen del area",
     "fondo - n_campos + 1", "fondo - n_campos + 3", "test_panel_lateral.py"),
    ("un recorrido que no cabe pinta su cabecera sola",
     "        hay_ruta = n_ruta > 0", "        hay_ruta = True",
     "test_panel_lateral.py"),
    ("los campos sin valor llegan al panel como etiquetas en blanco",
     "    return [c for c in campos if c[1]]", "    return list(campos)",
     "test_panel_lateral.py"),
    ("'ahora mismo' se pinta ademas del recorrido, diciendo lo mismo dos veces",
     'if (not hay_ruta and (r.get("pulso") or {}).get("herramienta"))',
     'if ((r.get("pulso") or {}).get("herramienta"))', "test_panel_lateral.py"),
    ("los bloques sin texto se pintan como cabeceras huecas",
     "    ) if b and b[1]]", "    ) if b]", "test_panel_lateral.py"),
    ("el choque deja de ir el primero de todos",
     '    return [b for b in (\n        ((_("\\u25b8 another session is writing here too"),\n          _texto_colision(cl), 5, 3, False) if cl else None),\n',
     "    return [b for b in (\n", "test_panel_lateral.py"),
    # ── abrir varias por tmux, la unica via fuera de macOS ───────────────────
    # Anclado por la funcion que le SIGUE, que es lo unico que distingue estos cuatro
    # cuerpos identicos. Cuando se metieron iTerm2 y kitty entre medias, este mutante
    # paso a romper kitty sin que nadie lo notara: seguia muriendo, pero por otro test.
    ("cuenta como abierta una ventana que tmux rechazo",
     "        hechas += r.returncode == 0\n    return hechas\n\n\ndef _abre_en_iterm",
     "        hechas += 1\n    return hechas\n\n\ndef _abre_en_iterm",
     "test_tmux_de_verdad.py"),
    ("el guion de la pestana no se borra antes del exec",
     '"rm -f -- %s\\n"', '"true %s\\n"', "test_tmux_de_verdad.py"),
    ("el titulo de la sesion no llega al nombre de la ventana",
     '"-n", str(titulo)[:40],\n                                "sh %s"',
     '"-n", "x",\n                                "sh %s"', "test_tmux_de_verdad.py"),
    # ── iTerm2 y kitty: la forma exacta salio de medir, no del --help ────────
    ("kitty vuelve a --single-instance y solo se abre una de las tres",
     '["open", "-na", "kitty.app", "--args",', '["open", "-1a", "kitty.app", "--args",',
     "test_lanzadores.py"),
    ("kitty se lanza directo y se queda en primer plano bloqueando el selector",
     '["open", "-na", "kitty.app", "--args",\n                                "-d", cwd, "-T", str(titulo)[:40],',
     '["kitty",\n                                "-d", cwd, "-T", str(titulo)[:40],',
     "test_lanzadores.py"),
    ("a iTerm2 se le manda `do script`, que es la orden de Terminal.app",
     "'tell application \"iTerm\" to create window with default profile '\n                 'command %s' % json.dumps(orden)",
     "'tell application \"iTerm\" to do script %s' % json.dumps(orden)",
     "test_lanzadores.py"),
    ("kitty pierde el directorio de la sesion",
     '                                "-d", cwd, "-T", str(titulo)[:40],',
     '                                "-T", str(titulo)[:40],', "test_lanzadores.py"),
    ("iTerm2 cuenta como abierta una ventana que el sistema rechazo",
     "        hechas += r.returncode == 0\n    return hechas\n\n\ndef _abre_en_kitty",
     "        hechas += 1\n    return hechas\n\n\ndef _abre_en_kitty",
     "test_lanzadores.py"),
    ("iTerm2 y kitty se declaran disponibles fuera de macOS",
     '    return sys.platform == "darwin" and any(\n        (base / nombre).is_dir()',
     '    return any(\n        (base / nombre).is_dir()', "test_lanzadores.py"),
    ("un lanzador se queda sin decir que abre en el cuadro de elegir",
     '    "kitty": lambda: _("a kitty window each"),\n', '',
     "test_lanzadores.py"),
    ("_QUE_ABRE describe un lanzador que ya no esta en la tabla",
     '    "kitty": (hay_kitty, _abre_en_kitty),\n', '', "test_lanzadores.py"),

    # ── cmd_add: guardas de argv para no volcar un traceback ni registrar basura ─
    # `--add` leia argv sin comprobar limites y sin mirar QUE leia. Cada guarda
    # protege una cosa distinta y hay un mutante por sub-condicion: los mata
    # test_cmd_add.py comprobando que la rama devuelve 2 (o no revienta) y que no
    # se escribio ningun .env. Un mutante que aflojara una sola pasaria sin red.
    ("el id de --add se acepta aunque sea una cadena vacia o solo espacios",
     '    if not argv or not argv[0].strip() or argv[0].startswith("-"):',
     '    if not argv or argv[0].startswith("-"):',
     "test_cmd_add.py"),
    ("el id de --add se acepta aunque sea un token de opcion",
     '    if not argv or not argv[0].strip() or argv[0].startswith("-"):',
     '    if not argv or not argv[0].strip():',
     "test_cmd_add.py"),
    ("--cwd como ultimo token se lee fuera de rango en vez de rechazarse",
     '        if argv[i] == "--cwd":\n            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):',
     '        if argv[i] == "--cwd":\n            if i + 1 > len(argv) or argv[i + 1].startswith("--"):',
     "test_cmd_add.py"),
    ("--cwd se traga la siguiente opcion como si fuera una ruta",
     '        if argv[i] == "--cwd":\n            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):',
     '        if argv[i] == "--cwd":\n            if i + 1 >= len(argv):',
     "test_cmd_add.py"),
    ("--title como ultimo token se lee fuera de rango en vez de rechazarse",
     '        elif argv[i] == "--title":\n            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):',
     '        elif argv[i] == "--title":\n            if i + 1 > len(argv) or argv[i + 1].startswith("--"):',
     "test_cmd_add.py"),
    ("--title se traga la siguiente opcion como si fuera un valor",
     '        elif argv[i] == "--title":\n            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):',
     '        elif argv[i] == "--title":\n            if i + 1 >= len(argv):',
     "test_cmd_add.py"),

    # ── la tecla que confirma cerrar sesiones, la unica accion irreversible ──
    ("una tecla de menos en el contrato de cierre y `y` deja de cerrar",
     '    return tecla in (ord("s"), ord("S"), ord("y"), ord("Y"))',
     '    return tecla in (ord("s"), ord("S"))',
     "test_cuadros_de_eleccion.py"),

    # ── el traceback de un crash dentro de curses ────────────────────────────
    ("un crash del TUI se traga sin dejar la traza en el log",
     "        _vuelca_crash()",
     "        pass",
     "test_crash_log.py"),

    # ── SERENO_ARNES fuerza un arnes, y el prefijo lo pone _env ───────────────
    ("el prefijo se mete dentro del nombre y SERENO_ARNES deja de leerse",
     '    forzado = _env("ARNES")',
     '    forzado = _env("SERENO_ARNES")',
     "test_relevo.py"),

    # ── el modelo elegido llega a la orden, y SOLO donde tiene sentido ────────
    # El flag va DONDE arranca una sesion nueva —Claude parada (`--resume`), Codex del
    # historial, y el relevo a los dos— y NO donde no: una viva (`cc-`) se reengancha a
    # un proceso ya echado, y a gemini no sabemos pedirselo. Un mutante por sitio que lo
    # lleva —quitarselo—, y uno que mete a gemini en el diccionario —ponerselo a quien no
    # debe—. Los mata `test_cuadros_de_eleccion.py`, que compone las cuatro ordenes.
    ("la reapertura de una sesion de Claude deja de llevar el modelo elegido",
     '[bin_cli("claude")] + _con_modelo("claude", modelo)',
     '[bin_cli("claude")] + []',
     "test_cuadros_de_eleccion.py"),
    ("la reapertura de una sesion de Codex deja de llevar el modelo elegido",
     '[bin_cli(cli)] + _con_modelo(cli, modelo)',
     '[bin_cli(cli)] + []',
     "test_cuadros_de_eleccion.py"),
    ("el relevo a Claude deja de llevar el modelo elegido",
     '_modelo_seg("claude", modelo)', '""',
     "test_cuadros_de_eleccion.py"),
    ("el relevo a Codex deja de llevar el modelo elegido",
     '_modelo_seg("codex", modelo)', '""',
     "test_cuadros_de_eleccion.py"),
    ("a gemini se le cuela un modelo que no sabemos como pedirle",
     'FLAG_MODELO = {"claude": "--model", "codex": "-m"}',
     'FLAG_MODELO = {"claude": "--model", "codex": "-m", "gemini": "--model"}',
     "test_cuadros_de_eleccion.py"),
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
