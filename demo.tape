# Graba docs/demo.gif. `vhs demo.tape` desde la raiz del repo.
# SERENO_DEMO=1 es obligatorio: sin el, la grabacion publicaria el ultimo prompt y la
# ultima respuesta de sesiones reales.
Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1560
Set Height 720
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms
Set Framerate 24

# Todo el arranque va oculto y la grabacion empieza limpia: sin esto se cuelan
# restos del prompt anterior en el borde izquierdo (visto en la primera toma).
Hide
Type "export PATH=$PWD:$PATH SERENO_DEMO=1 SERENO_LANG=en" Enter
Type "PS1='$ ' && clear" Enter
Sleep 800ms
Show

Type "sereno"  Sleep 900ms  Enter
Sleep 2500ms

# bajar por la lista: el panel de la derecha cambia con cada sesion
Down  Sleep 1800ms
Down  Sleep 1800ms

# esta fila trae el bloque de la respuesta, y con el se ven los cuatro subrayados a la
# vez: `project`, `session` y las dos cabeceras. El subrayado es lo que dice que ese
# valor se copia al pincharlo, asi que la pausa es larga a proposito — es la unica
# forma de ensenarlo, porque vhs no sabe mandar clicks.
Down  Sleep 3200ms

# marcar dos
Up    Sleep 500ms
Space Sleep 900ms
Space Sleep 1400ms

# ordenar por lo gastado: `s` recorre actividad, contexto, proyecto, memoria y gasto.
# Cuatro pulsaciones para llegar al quinto, con una pausa en cada uno para que se vea
# que la lista se recoloca y que la cabecera dice cual esta puesto.
Type "s" Sleep 900ms
Type "s" Sleep 900ms
Type "s" Sleep 900ms
Type "s" Sleep 2400ms

# el historial de sesiones que ya no corren
Tab   Sleep 2200ms
Down  Sleep 1200ms
Down  Sleep 1600ms

# filtrar mientras escribes
Type "/"  Sleep 500ms
Type "cli" Sleep 1800ms
Escape Sleep 400ms
Backspace Backspace Backspace Sleep 800ms

# copiar el id de la sesion — el de Claude, el que come `--resume`. Pinchar el valor
# subrayado hace lo mismo; el rotulo de abajo dice siempre que ha llegado al portapapeles.
Type "y" Sleep 2600ms

# volver y abrir la ayuda
Tab Sleep 400ms
Tab Sleep 1200ms
Type "?" Sleep 3000ms
Escape Sleep 800ms

Type "q" Sleep 1200ms
