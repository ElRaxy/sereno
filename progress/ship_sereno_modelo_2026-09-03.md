# ship — elegir el modelo al reabrir y al relevar (sereno)

Rama pusheada: **`feat/modelo-al-reabrir`** (base `main` @ `837c35b`, commit `b7bfc32`, firmado).
Estado: **done**. 75/75 tests en verde, 161/161 mutantes muertos, sin obsoletos.
NO se ha abierto PR ni merge (por encargo).

## Resumen

Toggle `[m]` en los dos cuadros (`c` relevar y `r` reabrir) para elegir el modelo con el que
arranca la sesión nueva. `por defecto` = no pasar flag (comportamiento conservador de siempre).
Catálogo por `SERENO_MODELOS` (default `opus,sonnet,haiku`). El flag va **después de la ruta** del
binario: `claude --model <m>`, `codex -m <m>`. NO lo llevan: `cc-…`→`tmux attach` (proceso vivo)
ni `gemini` (flag no verificado). No persiste entre arranques salvo la env var.

Se siguió el PLAN (`progress/PLAN-sereno-modelo-al-reabrir-y-relevar.md`) fases F1–F3. §5
(`--fork-session`) se deja **para Alex**, no implementado (ver "Decisiones abiertas").

## Cambios por fichero

### `sereno`
- **`FLAG_MODELO` + `_con_modelo(cli, modelo)`** (nuevos, tras `bin_cli`, ~L2155): dict
  `{"claude":"--model","codex":"-m"}` y helper que devuelve los tokens del flag o `[]`. `gemini`
  no está en el dict a propósito (F1).
- **`_modelo_seg(cli, modelo)`** (nuevo, ~L2172): el flag como segmento de cadena
  (`" --model opus"` o `""`) para las lambdas de `ARNESES`, que componen con `+`.
- **`modelos_catalogo()`** (nuevo, ~L2185): lee `SERENO_MODELOS` (default `opus,sonnet,haiku`),
  no hardcodea lista que caduque.
- **`_comando_de(r, modelo=None)`** (~L2189): la rama `abrir` (codex/gemini) inserta
  `_con_modelo(cli, modelo)` tras el binario; la rama `--resume` (Claude parada) igual, ahora como
  lista+`join` (evita SyntaxError 3.8); la rama `cc-` (tmux attach) **no** lleva modelo.
- **`ARNESES`** (~L2650): las tres lambdas pasan a `lambda prompt, modelo=None:` e insertan
  `_modelo_seg(cli, modelo)` tras el binario, antes del bypass. Los substrings de bypass intactos.
- **`pestanas_de_relevo(..., modelo=None)`** (~L2735) → `compone(briefing, modelo)`.
- **`relevo(..., modelo=None)`** (~L2895) → pasa `modelo` a `pestanas_de_relevo`.
- **`pestanas_de(rows, modelo=None)`** (~L2622) → `_comando_de(r, modelo)`.
- **`_fila_admite_modelo(r)`** (nuevo, ~L2771): misma frontera que `_comando_de` (cc- y gemini no).
- **`_pide_lanzador(...)`** (~L2781): ahora **loopea** y cicla `[m]`; devuelve `(lanzador, modelo)`
  en vez de un escalar.
- **`lineas_relevo(..., modelo=None, hay_modelo=())`** (~L2864): línea `[m] modelo: {v}` tras `[k]`,
  pintada 7/4 según haya modelo; solo si `len(hay_modelo) > 1`.
- **`lineas_abrir(..., modelo=None, hay_modelo=())`** (~L2798): misma línea `[m]`.
- **i18n** (~L6126): `"model: {v}"→"modelo: {v}"`, `"default"→"por defecto"`.
- **Bucle `c`** (~L5690): computa `ciclo_m`/`hay_modelo`, cicla con `m`, pasa `modelo` a `relevo`
  **solo si hay uno** (`**({"modelo": modelo} if modelo else {})`) — para no romper la firma que
  esperan tests fuera de boundary.
- **Bucle `r`** (~L5766): `_pide_lanzador` devuelve `(donde, modelo_reabrir)`; `ejecutar` recibe el
  modelo como 4º arg **solo si hay uno** (`*(( modelo_reabrir,) if modelo_reabrir else ())`).
- **`ejecutar(verbo, sel, donde=None, modelo=None)`** (~L7253) → `pestanas_de(sel, modelo)`.
- **VERSION**: ya estaba en `1.41.0`, sin tocar.

### `tests/test_cuadros_de_eleccion.py`
- `import shlex`.
- Sección nueva **toggle de modelo**: `[m]` sale/no sale según `hay_modelo`, muestra el valor, y
  cambia de color por estado; comprobado en `lineas_relevo` y su gemelo `lineas_abrir`.
- Sección nueva **composición**: `_comando_de` y `ARNESES` llevan el modelo donde toca (Claude
  `--resume`, Codex `abrir`, relevo Claude/Codex) y **no** donde no (viva `cc-`, `gemini`, y `por
  defecto`); binario sigue siendo el primer token.
- No sube el conteo de tests (75) porque va en un fichero ya existente.

### `tests/test_mutantes.py`
- **3 anclas actualizadas** (código reescrito por la feature): la reapertura de Claude parada
  (`orden = ([bin_cli("claude")] + _con_modelo(...)`), el historial de otro CLI
  (`[bin_cli(cli)] + _con_modelo(cli, modelo) + ...`), y las dos lambdas de `ARNESES`
  (`lambda prompt, modelo=None: ... + _modelo_seg(...)`).
- **5 mutantes nuevos** (156→161), todos cazados por `test_cuadros_de_eleccion.py`:
  1. `la reapertura de una sesion de Claude deja de llevar el modelo elegido` — MUERE.
  2. `la reapertura de una sesion de Codex deja de llevar el modelo elegido` — MUERE.
  3. `el relevo a Claude deja de llevar el modelo elegido` — MUERE.
  4. `el relevo a Codex deja de llevar el modelo elegido` — MUERE.
  5. `a gemini se le cuela un modelo que no sabemos como pedirle` (mete gemini en `FLAG_MODELO`)
     — MUERE.

### Docs
- **README.md**: `[m]` en el cuadro de `c`; párrafo de `m` (catálogo, dónde aplica, no persiste);
  caveat de la barra de contexto (salida **(a)** del PLAN §4: aceptado y dicho, lee **alto** hasta
  que aterriza el `cost-state` nuevo, la guarda 5 lo corrige); fila `SERENO_MODELOS` en Config;
  conteo mutantes `one hundred and fifty-six`→`one hundred and sixty-one`.
- **README.es.md**: simétrico (`[m]`, párrafo, config); conteo `ciento cincuenta y seis`→`ciento
  sesenta y una`.
- **CONTRIBUTING.md**: dos conteos de mutantes actualizados a `one hundred and sixty-one`.
- **CHANGELOG.md**: entrada nueva al principio de `## 1.41.0`.

## Verificación

- `python3 tests/todos.py` (completo, con pty + mutantes): **`75/75 en verde (370s)`**, exit 0.
- `python3 tests/test_mutantes.py`: **`161/161 mutantes muertos (224s)`**, 0 obsoletos, 0 vivos.
- Cifras: `test_cifras_de_la_doc.py` → `ok: la documentacion dice 75 tests y 161 mutantes, y eso es
  lo que hay`.
- `test_binario_no_alias`, `test_i18n`, `test_sin_red`, `test_readmes_a_la_par`, `test_relevo`,
  `test_cuadro_relevo`, `test_donde_abrir`, `test_lanzadores`, `test_abrir_varias` → todos verde.
- Regla dura respetada: el render del TUI **no** se verificó headless; solo composers/líneas (puros).

Cifras actualizadas: **75 tests / 161 mutantes**.

## Nota de scope (leer)

El PLAN escribió la interfaz en `lineas_relevo`/`lineas_abrir` y la composición en `_comando_de`/
`ARNESES`. Cablear el toggle hasta el composer obliga a pasar `modelo` por `relevo(...)` y por
`ejecutar("reopen", ...)`, cuyas **firmas las fijan tests fuera de mi boundary**
(`test_cuadro_relevo.py`, `test_donde_abrir.py`, que mockean esas funciones con aridad fija). Para
no tocarlos, el modelo se pasa **solo cuando se ha elegido uno**; en `por defecto` la llamada
mantiene la firma de siempre. Efecto secundario conocido: en el flujo `r`, el `[m]` solo aparece
cuando hay ≥2 lanzadores (el cuadro `_pide_lanzador` solo se dibuja entonces); con un único
lanzador no hay cuadro donde ofrecerlo. Es coherente con el PLAN (§6: "solo aparece cuando hay
entre qué elegir"), pero conviene que lo sepas.

`write_launch_config` (3er sitio que compone órdenes, para huérfanas del registro) **no** se tocó:
su flujo de reabrir (`ejecutar_h`/`reanuda`) no pasa por `lineas_abrir`, así que no hay toggle que
lo alimente. Queda como posible ampliación si se quiere elegir modelo también al reanudar huérfanas
sin tmux.

## Decisiones abiertas (para Alex)

- **`--fork-session` (PLAN §5).** Reabrir la MISMA sesión con otro modelo deja dos modelos en un
  transcript, que es justo de donde sereno deduce modelo y tope. `claude --fork-session` crea un
  session-id nuevo al reanudar. NO implementado — es decisión tuya si el cambio de modelo al
  reabrir debe forzar sesión nueva.
- **Salida (b) del PLAN §4** (guardar el modelo elegido en el registro y meterlo en la cascada de
  `tope_contexto`) descartada para v1 por recomendación del propio PLAN: toca la parte más medida
  del programa. Se documentó la salida (a) en su lugar.
- **Modelo al reabrir huérfanas sin tmux** (`write_launch_config`): no cubierto, ver nota de scope.
