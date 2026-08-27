# Graba la tira de lista que lleva docs/social-preview.png.
# Los cuatro pasos completos estan en la cabecera de docs/social-preview.html.
#
# SERENO_DEMO=1 es obligatorio y va aqui dentro: la lista real lleva titulos de
# sesiones de clientes, y esta imagen acaba siendo la tarjeta publica del repo.
#
# 1900 de ancho no es capricho: con menos, el panel lateral se come las columnas de
# proyecto y memoria. Se graba ancho y luego se recorta la lista con ffmpeg.
Output "/tmp/sereno-tira.gif"

Set Shell "bash"
Set FontSize 17
Set Width 1900
Set Height 420
Set Padding 0
Set Theme "Catppuccin Mocha"
Set Framerate 12

Hide
Type "export PATH=$PWD:$PATH SERENO_DEMO=1 SERENO_LANG=en" Enter
Type "PS1='' && clear" Enter
Sleep 500ms
Type "sereno" Enter
Sleep 3000ms
Show
Sleep 1200ms
