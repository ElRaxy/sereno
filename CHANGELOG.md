# Changelog

## 1.39.0

**El relevo (`c`) ya entrega a Gemini.** Antes solo iba entre Claude y Codex; ahora una
sesion se puede relevar tambien a Gemini, y en los dos sentidos. La orden se compone con
`gemini -i <briefing>` —el flag que "ejecuta el prompt y sigue en modo interactivo",
verificado contra `gemini --help`— y por la ruta absoluta del binario (`bin_cli`), no por
el nombre pelado, para que ningun alias del `.zshrc` se cuele como en el #71.

**Antigravity sigue fuera de `ARNESES`, y ahora es el ejemplo de por que.** No es un
olvido: no tiene binario que arrancar con un prompt inicial, solo un directorio de
conversaciones que sereno lee para reanudarlas. El cuadro lo sigue mostrando en gris con
su motivo ("no comprobado como sembrarlo"), distinto del de "no instalado" que le toca a
un CLI que si esta en `ARNESES` pero falta en el PATH.

## 1.38.1

**`--stop` y `--stop-all` no llegaban a ejecutarse.** Los dos flags tenian su handler
completo, pero nunca se registraron en `_FLAGS`. El guard de flags desconocidos corre
primero, asi que ambos salian con `exit 2` "opcion desconocida" ANTES de tocar su codigo.
La ayuda (`--help`) y el CHANGELOG los daban por vivos: un handler escrito y jamas
enganchado. Ahora estan en la tabla, documentados en el docstring y en los dos README.

Y `--stop` leia `argv[index+1]` sin red: `sereno --stop` sin nombre reventaba con
`IndexError`. Cae en un mensaje limpio y `exit 2`, como ya hacian `--stop-sel` y
`--close-sel`.

La grieta se colo porque el test de flags solo miraba en una direccion: docstring ->
tabla. Se anade la inversa —los `--x` despachados en el cuerpo de `main()` tienen que
estar en `_FLAGS`— que falla en rojo contra el codigo viejo nombrando exactamente estos
dos, y blinda la clase entera: un handler nuevo cuyo flag nadie registre.

**Y el modal de confirmar cierre no acotaba su alto a la pantalla**, el unico de los
modales que no lo hacia. En un terminal de menos de ~11 filas, pulsar `x` con varias
sesiones marcadas hacia un `newwin` mas alto que la pantalla -> `curses.error`, que el
wrapper traga como "No changes" justo al cerrar. Ahora clampa a la altura y recorta la
muestra, como los modales de ayuda y relevo.

## 1.38.0

**Las ordenes llevan la RUTA del CLI, no su nombre.** Sereno no ejecuta lo que compone:
la orden acaba dentro de la launch configuration de Warp, y **Warp la escribe en una
shell interactiva**, donde mandan los alias del `.zshrc` que un `sh -c` no llega a ver.
Comprobar "esto es el binario" desde el proceso de Sereno no dice nada sobre lo que se
ejecutara alli.

Encontrado abriendo tres sesiones del historial con `r` el 2026-09-01: salieron
corriendo con `--allow-dangerously-skip-permissions`, que Sereno **no pide en ningun
sitio**. `claude` era un alias a un wrapper que lo anadia. El YAML estaba limpio
(`claude --resume <id>`) y el `ps` no — un fallo que no se ve en lo que escribe el
programa, solo en lo que acaba corriendo.

`bin_cli()` resuelve el nombre a su ruta absoluta, y por ahi pasan **los tres** sitios
que componen ordenes: `_comando_de` (historial de Claude y de los otros CLI),
`write_launch_config` (las huerfanas del registro) y `ARNESES` (el relevo). Los tres o
ninguno: basta uno con el nombre pelado para que el alias vuelva a colarse, y por eso
hay **un mutante por sitio** en vez de uno solo.

Si el CLI no esta en el PATH se sigue devolviendo el nombre pelado, que es lo que habia
antes: peor que la ruta, pero mejor que no abrir nada. Mismo patron que `TMUX_BIN`.

**Y de paso, tres afirmaciones de la documentacion que el codigo desmentia**, encontradas
releyendo el README con esto en la mano:

- *"Lo unico que escribe es un fichero de arranque de Warp, y solo cuando pulsas ENTER"*.
  Falso: tambien con `r` y con `c`, tambien un `preferencias.json` con tu orden y tu ultimo
  lanzador, y tambien un guion de usar y tirar en `~/.sereno/lanzar/` cuando las pestanas van
  a tmux o a Terminal.app.
- *"No crea configuracion, ni cache, ni carpeta de estado propia"*, en la pregunta de como
  desinstalarlo. Crea las dos cosas de arriba. Ahora la respuesta trae las tres ordenes que
  lo dejan todo limpio, y dice que la primera basta para que deje de existir.
- El `rm ~/.local/bin/sereno` de esa respuesta no era el inverso del `brew install` que
  ensena el propio README dos pantallas antes.

`SECURITY.md` recoge los dos ficheros que faltaban en su lista de escrituras y la frase de
"no hay fichero de configuracion", que era verdad a medias.

**El test falsifica el PATH a proposito.** Comparar contra el literal `"claude"` pasaria
en verde en cualquier maquina sin Claude instalada —el CI, sin ir mas lejos—, donde
`bin_cli` devuelve justo el nombre pelado: verde sin haber comprobado nada. Se planta un
`claude` de mentira en un temporal, se pone delante del PATH y se exige ESA ruta; el
control negativo, con el PATH vacio, exige la caida al nombre pelado.

## 1.37.2

**`/ filtrar` vuelve delante de `r reabrir`.** La 1.37.0 metio `r` la quinta y eso
empujaba al filtro fuera del pie a 80 columnas en castellano. Filtrar es de todos los
dias; abrir varias marcadas, no. Orden: `ENTER · SPACE · x · ? · / · r · s · TAB · q`.

**El precio esta medido y se dice:** en castellano a 80 columnas `r` no sale, y vuelve a
partir de 90. En ingles cabe ya a 80. El test comprueba las **seis** primeras por su
nombre —no cuantas caben—, porque el orden es una decision y no el resultado de sumar
anchos: `/` delante a proposito, y `r` sin poder caer mas atras.

## 1.37.1

**Dos comentarios que afirmaban de mas.** Decian que `warpctrl` "no existe en esta
version". Revisado el 2026-09-01 sobre v0.2026.08.26: el binario **si** lo lleva dentro
—su parser entero sale por `strings`, y la app trae hasta su skill en
`Resources/bundled/skills/warpctrl/`—, pero **no se puede llamar**: invocarlo cae al
parser de URLs, el modo de control local viene apagado en los canales publicos y la
ultima puerta es un toggle de ajustes. Y aunque se encendiera no valdria para esto: su
propia skill dice que `input insert` solo DEJA ESCRITO el texto y que no hay accion que
lo ejecute.

El comentario no cambia ni una linea de codigo, y por eso importa: "no existe" invita a
no volver a mirar, y aqui lo que hay es "existe, no se puede llamar, y no haria lo que se
le pediria" — tres cosas distintas, cada una con su fecha de caducidad.

De paso queda escrito por que cada ENTER abre ventana y no pestana: `warp://launch/`
**nunca** reutiliza la ventana viva (medido, dos llamadas seguidas: 3 -> 4 -> 5), y
`warp://action/new_tab` si anade pestana pero no admite comando. Para juntarlas esta `r`.

## 1.37.0

**El rotulo decia lo contrario de lo que hace.** Al abrir varias sesiones a la vez, el
cuadro que pregunta donde anunciaba `warp — una ventana de verdad para cada una`. Es
falso desde que existe: la launch configuration que escribe Sereno declara **una ventana
con una pestana por sesion**, y eso es exactamente lo que abre Warp.

Medido el 2026-09-01 antes de tocar nada, que es como se descubrio: config de tres
pestanas, ventanas de Warp de 2 a 3, y la nueva con las tres dentro — mirada en la
barra lateral, no deducida del YAML. De paso quedan dos hechos mas sobre Warp:
`warp://launch/` **siempre** abre ventana nueva y no reutiliza ninguna (dos llamadas
seguidas, 3 -> 4 -> 5), y `warp://action/new_tab` si anade pestana a la ventana viva
pero **no admite un comando**, asi que no sirve para lanzar una sesion.

**Y por eso parecia una funcion que faltaba.** La tecla que hace eso es `r`, existe
desde antes de la 1.18.0 y vivia **solo dentro de la ayuda**: no tenia pastilla en el pie. Entre
un rotulo que promete lo contrario y una tecla que no se ve, la conclusion razonable es
que el programa no sabe hacerlo. Ahora `r reabrir` sale en el pie, la quinta, delante de
`/ filtrar`: es la unica tecla que abre VARIAS de una vez, y filtrar y ordenar se buscan
cuando ya conoces el programa.

A 80 columnas —media flota— entran cinco pastillas y `r` es una de ellas; el test las
comprueba **por su nombre** y no por cuantas caben, porque el orden de las primeras es
una decision y no el resultado de sumar anchos.

- `_QUE_ABRE["warp"]` -> "una ventana de Warp, con una pestana para cada una".
- Los dos README repetian la misma mentira en su tabla de lanzadores: Warp es el **unico** que
  las junta.
- Mutante nuevo (134): quitar `r` del pie. No rompe nada visible — solo la vuelve
  invisible, que es como estaba.

## 1.36.7

**Y ahora se pincha el boton de verdad.** La 1.36.6 saco las dos piezas puras del pie y
probo que ninguna pastilla pisa a la vecina. Lo que ninguna pieza pura puede ver es el
**cableado**: que lo que `pastillas_pie` calcula sea lo mismo que se pinta, que sus zonas
acaben en la tabla, y que el codigo que devuelve `zona_en` se ejecute como si lo hubieras
tecleado. Las tres cosas se rompen sin que un test puro se entere — la pieza sigue verde
y el boton deja de funcionar.

`test_click_en_el_pie.py` abre un pseudo-terminal, arranca el programa y le escribe un
click SGR como lo escribiria el terminal, sobre ` ? help `: un boton que abre un cuadro
que se ve desde fuera y no toca ninguna sesion.

**Con su reverso, que es la mitad que cuesta acertar.** Un click en el HUECO entre dos
pastillas no puede abrir nada. Y el hueco tiene que ser el de la DERECHA de la pastilla
que se mira: buscandolo a la izquierda, ampliar las zonas lo tapa ` x close `, que abre
otra cosa, y el caso pasa en verde sin haber comprobado nada. Se descubrio rompiendo el
codigo a proposito y viendo que el test no se quejaba.

Los dos fallos son ahora mutantes fijos: el pie que se pinta pero deja de poder
pincharse, y las zonas que se comen la separacion.

**69 tests y 133 mutantes**, los 133 muertos.

## 1.36.6

**La tabla de zonas sale de `pick_ui`, y con ella el ultimo hueco que quedaba dicho.**
Las pastillas del pie —`ENTER abrir`, `x cerrar`, `q salir`— no son texto: son botones,
se pinchan y hacen lo que su tecla. Cada una apunta una zona clicable en una tabla, y
esa tabla vivia dentro de la funcion de mil lineas, donde no se puede mirar desde fuera.
Resultado: **nada impedia que dos zonas se pisaran**, y cambiar el `- 1` que calcula la
ultima columna por un `+ 1` pasaba los 66 tests en verde.

No es un fallo cosmetico. Un solape mete dos columnas de una pastilla dentro de la
vecina, todo se sigue pintando igual, y un click en ese borde ejecuta la tecla de al
lado. Entre esas teclas esta cerrar sesiones.

Salen dos piezas puras, con el patron de `lineas_now` y `leer_sgr`:

| | qué hace |
|---|---|
| `pastillas_pie(w)` | las pastillas que CABEN en `w` columnas, cada una con su sitio: `(tecla, texto, codigo, x, x_final)` |
| `zona_en(zonas, mx, my)` | traduce "donde has pinchado" a "que has pinchado" — lo unico que decide tanto el click como el pasar por encima |

`pick_ui` baja a **1.078 lineas**. Y `test_zonas_del_pie.py` comprueba en **once anchos
de ventana** (de 200 a 4 columnas) que ninguna pastilla pisa a la siguiente, que ninguna
se sale de la pantalla, que su zona mide exactamente lo que se pinta, y que un click en
**cualquier** columna de una pastilla devuelve su tecla y no la de al lado. `zona_en` se
prueba aparte con una tabla escrita a mano, porque es la otra mitad: unas zonas
perfectas con un resolutor que se equivoca de fila dan el mismo click en el sitio que no
era.

**Cinco mutantes, y uno costo un caso mas.** Pintar las pastillas pegadas —quitandoles
la separacion— no solapa ninguna zona y sobrevivio a la primera version del test. No es
un fallo de clicks pero si de lectura: el fondo de una entra en el de la siguiente y el
pie deja de leerse como botones para parecer una barra continua. La separacion es parte
del dibujo, no un margen que sobre, y ahora esta escrito.

De paso, `test_cifras_de_la_doc.py` aprende a leer cuatro palabras: "ciento treinta y
una" se le escapaba al patron de dos, el mismo escalon que ya tapo "cien" al cruzar
el 99.

**68 tests y 131 mutantes**, los 131 muertos.

## 1.36.5

**Cuatro guardas que se podian romper sin que nadie se enterase.** No salieron de leer el
codigo: salieron de un **barrido de mutacion automatico**. Se cambia una cosa minima —un
`>=` por un `>`, un `and` por un `or`, un `not` que desaparece— y se mira si algun test
se queja. El que no se queja de nada senala una guarda sin red: no dice que haya un bug,
dice que si lo hubiera nadie lo veria.

De 200 mutantes generados sobre lineas que los tests SI ejecutan, 95 sobrevivieron a una
primera pasada y 80 a correr todos los tests que tocan su linea. La mayoria son
equivalentes —cambios que no alteran nada observable— asi que el triaje fue a mano, por
lo que costaria que se rompieran de verdad:

| lo que se podia romper | y nadie lo veia |
|---|---|
| **`git clean`** en el aviso de choque | con un `or`, `git push -f` se anunciaba como `git clean` y un `git clean -n` —que no borra nada, solo lista— tambien. La tabla solo tenia el caso positivo (`git clean -fd`) |
| **el escalon de contexto** | `>=` por `>` y el aviso del 80% no sale hasta el 80,1%. Los casos probaban con 85% y 95%: la frontera exacta no la miraba nadie |
| **la duracion de cada paso** | `int(secs or 0)` por `and 0` pinta "0s" en todas las filas: se lee como "todo fue instantaneo" y tapa justo la llamada que lleva dos minutos colgada |
| **`SERENO_JORNADA=23`** | un `<=` por un `<` y la hora 23 deja de valer en silencio, cayendo a la de casa |

Los cuatro tienen ahora caso y mutante.

**Y una que el barrido acuso en falso, que tambien cuenta.** Dijo que la guarda de
`tmux_list` estaba sin red; corriendo la bateria ENTERA, `test_tmux_de_verdad` la caza.
El barrido excluye los tests lentos para poder probar 200 mutantes, y ese es uno de
ellos: **lo que un barrido rapido llama "sin red" es una sospecha, no un hecho**, y hay
que confirmarla contra todo antes de escribir nada. De rebote salio algo que si faltaba:
el **parseo de `list-panes`** no tenia un solo test. Ahora lo tiene —el titulo del panel,
el hostname que se descarta por generico, el adorno del principio, el segundo panel de
la misma sesion que no cuenta dos veces, y una llamada que devolvio error cuyas sesiones
no pueden acabar en la lista.

**Uno queda sin red, y se dice:** las zonas clicables de las pastillas del pie
(`" ENTER abrir "`, `" x cerrar "`…) se calculan restando uno, y sumarlo las solapa dos
columnas con la vecina — un click en el borde ejecutaria la tecla de al lado, y una de
esas teclas es cerrar. Probarlo exige leer la tabla de zonas desde fuera del bucle, que
hoy no se puede sin partir `pick_ui`.

**67 tests y 126 mutantes**, los 126 muertos.

## 1.36.4

**La fila de "(nada coincide)" tenia una guarda sin red.** Cuando el filtro no casa con
nada, la lista no se queda sin filas: se pinta una de mentira que lo dice. Eso evita
dividir por cero al mover el cursor, pero pone al alcance del dedo una fila que no es una
sesion, con el `name` vacio. Marcarla mete una cadena vacia en la seleccion, y a partir
de ahi el programa cree que tienes algo marcado: deja de avisarte de que marques y los
contadores cuentan un fantasma.

La guarda que lo impide ya estaba, y esta bien puesta. Lo que no estaba era la red:
**romperla dejaba los 65 tests en verde**. Ahora tiene tres mutantes, y por sus dos
lados, porque descartar de mas es igual de malo que descartar de menos — si se come la
`q` te quedas encerrado en una lista sin nada, y si se come el borrar no puedes deshacer
el filtro que te dejo ahi: la unica salida seria matar el proceso.

**Con reloj, ademas.** El doble de curses devuelve `q` cuando se le acaban las teclas,
asi que el mutante que se come esa tecla dejaba el bucle dando vueltas hasta el tope de
300 s del catalogo. Moria —colgarse tambien es quejarse— pero tardaba cinco minutos, y
eso lo pagan doce jobs en cada pull request. Con una alarma de diez segundos el catalogo
entero baja de **247 s a 74 s**, y el fallo dice ademas que se colgo, que es un
diagnostico distinto de "no marco lo que debia".

**66 tests y 120 mutantes**, los 120 muertos.

## 1.36.3

**El parser del raton sale de `pick_ui` y por fin se puede probar.** `leer_sgr` vivia
dentro de la funcion de 1.132 lineas, y ahi dentro no habia forma de darle una secuencia
de teclas y mirar que entiende: de sus 27 lineas ejecutables, los tests tocaban **una**.
Ahora esta a nivel de modulo con **27 de 27**, dos tests y siete mutantes encima.
`pick_ui` baja a **1.094 lineas** y el fichero entero sube del 75,6% al **76,6%**.

Es la misma operacion que se hizo con `lineas_now` y con el reparto del panel: sacar una
pieza pura y probarla sin curses. La unica diferencia esta en la firma — `ungetch` y
`espera` se le pasan en vez de tomarlos del entorno, porque **`curses.ungetch` exige un
`initscr()` previo** y llamandolo por su cuenta la funcion no se puede probar sin
arrancar una interfaz de verdad. Quien la llama ya tiene las dos cosas a mano.

**Por que importa lo que hace esa funcion.** El ncurses que trae macOS es el 6.0 de 2015
y solo conoce el raton x11: un evento SGR le llega como teclas sueltas y se pierde
entero. El terminal si habla SGR, asi que el programa lo pide y lo parsea a mano. Y
corre **detras de un ESC**, que es tambien la tecla que cierra un dialogo: si se traga
la tecla siguiente creyendo que era un raton, la interfaz se come pulsaciones; si
devuelve coordenadas de una secuencia a medias, el click cae en la fila equivocada — y
en esta lista la fila equivocada es la sesion equivocada.

**Dos tests, y el segundo existe por lo que el primero no puede ver:**

- `test_raton_sgr.py` le da secuencias a una ventana de mentira: los cinco eventos que
  si son un evento —incluida una columna que el protocolo viejo no sabe decir, que es
  justo por lo que se pide SGR— y ocho que no lo son y no pueden inventarse. Ademas
  vigila que la tecla ajena vuelva al buffer y que la espera corta de 30 ms se restaure
  siempre, tambien cuando la secuencia esta rota.
- `test_raton_en_la_tui.py` abre un pseudo-terminal, arranca el programa y le **escribe
  la secuencia como la escribiria el terminal**. Es lo unico que comprueba el enlace:
  los argumentos que el bucle de teclas le pasa no los ve ningun test unitario, asi que
  un cambio de firma que deje un sitio sin actualizar pasaria con el parser en verde y
  reventaria al primer click. Probado: con un solo sitio en la firma vieja, el test cae
  con la traza.

**65 tests y 117 mutantes**, los 117 muertos.

## 1.36.2

**Fuera `_fecha_corta`.** Once lineas que no llamaba nadie: entraron con el volcado
inicial de la 1.0.0 y no han tenido un solo llamador en toda la historia publica del
repo. Formateaba una fecha como "hoy" / "ayer" / `dd/mm`, y donde el programa pinta
fechas usa otras funciones.

Salio de recorrer el AST buscando definiciones sin uso mientras se median los huecos de
cobertura de la 1.36.1 — un barrido que cuesta lo mismo y contesta la otra pregunta: no
"que no se prueba", sino **que no se ejecuta porque no existe quien lo llame**. Era la
unica del fichero.

No se le escribio test a proposito: un test sobre codigo muerto lo convierte en codigo
vivo que nadie usa, y ata la mano al que venga a borrarlo.

**Y la red para que no vuelva:** `tests/test_sin_codigo_muerto.py` recorre el arbol de
sintaxis y falla si alguna funcion se queda sin quien la llame. Cuenta como uso hasta
una mencion del nombre dentro de una cadena —hay tablas que despachan por nombre—: es
laxo a proposito, porque la unica forma de que se equivoque es dando por viva una
muerta, nunca al reves, y un test que acusa en falso se acaba desactivando. Lo que el
programa no llama pero existe por algo va en `PERMITIDAS` con su motivo escrito, y la
lista tambien se vigila: si nadie usa ya lo que hay ahi, el test lo dice.

**63 tests y 110 mutantes**, los 110 muertos.

## 1.36.1

**Red para los cuatro huecos que el criterio por nombre no veia.** Tres tests nuevos y
nueve mutantes sobre `rss_por_arbol`, `detalles`, `_cwd_de_cabecera` y `_user_texts`.

Lo que cambio no fue el codigo, fue **como se busca lo que falta**. Hasta ahora "esta
funcion no tiene test" queria decir "su nombre no aparece en `tests/`", y eso mide otra
cosa: de las seis funciones que ese criterio senalaba como descubiertas, cinco
—`_troceado`, `_clave_orden`, `recorta`, `reparto`, `_ausente`— estaban al **100%**,
probadas por sus llamadores. Medida la ejecucion de verdad, los huecos eran otros
cuatro que ese criterio daba por cubiertos.

| | antes | ahora |
|---|---|---|
| `rss_por_arbol` | 1/21 | 21/21 |
| `detalles` | 3/36 | 33/36 |
| `_cwd_de_cabecera` | 10/16 | 16/16 |
| `_user_texts` | 21/26 | 26/26 |
| el fichero entero | 74,0% | **75,6%** |

**Lo que protege cada uno:**

- **`rss_por_arbol`** son los MB que ordenan el modo `memory` y contestan a "cual
  sobra". Un proceso de Claude Code no es uno, es un arbol, asi que la cifra buena es la
  suma de los descendientes: mirar solo el pid raiz da 1 MB donde Activity Monitor
  ensena 7, y ordena acusando a la sesion equivocada. Los tres fallos con red propia son
  sumar de menos, contar dos veces un pid que cuelga de dos sitios, y **colgarse**: `ps`
  devuelve ciclos padre-hijo con los pids reciclados, y sin la marca de por donde ha
  pasado la recursion no vuelve. La salida de `ps` se inyecta a proposito — un test que
  lee la RAM de la maquina no puede afirmar nada, porque no sabe cuanto deberia salir.
- **`detalles`** es el panel de la fila bajo el cursor, y tiene dos contratos que se
  rompen por separado: **lo que dice** (la rama es la ultima de la cola, no la primera; y
  un subagente escribe en el MISMO transcript, con la misma forma, distinguido solo por
  una bandera — si se cuela, el panel atribuye a la sesion algo que dijo otro) y **lo que
  se queda en memoria**, que se mide: un transcript con una linea de 200 KB dentro tiene
  que dejar en `_det` menos de 8 KB, porque ese objeto se queda pegado a la fila hasta el
  proximo refresco.
- **`_cwd_de_cabecera`** contesta "¿este historial pertenece a algo que todavia existe?"
  leyendo la cabecera y no la cola, porque son 880 ficheros. Su contrato es **el tope**:
  si deja de acotarse la respuesta sigue siendo correcta y el barrido pasa de 114 ms a
  leerlos enteros. El coste es parte del contrato.
- **`_user_texts`** decide que cuenta como escrito por una persona, y alimenta `--find`.
  Un transcript guarda con `"type": "user"` mucho mas que lo que alguien teclea: los
  resultados de cada herramienta, los recordatorios inyectados, los errores del propio
  CLI y lo que piden los subagentes. Si algo de eso pasa el filtro, `--find "factura"`
  empieza a casar el CONTENIDO de los ficheros que se leyeron y devuelve el proyecto
  entero. Por eso once de los catorce casos son de lo que NO debe salir: un filtro solo
  se puede probar con lo que tiene que dejar fuera.

**Y `test_hoy.py`, que fallaba segun la hora a la que se corriera.** Su caso del orden
dejaba una tercera sesion arrastrando el mtime de un caso anterior: cuanto llevaba
parada dependia del reloj, asi que entraba en "a medias" entre las cinco y las diez de
la manana y no el resto del dia. Pasaba por la tarde en la maquina de casa y fallaba en
CI, que corre en UTC. Probado en los dos sentidos —sin el arreglo pasa en dos husos
horarios y falla en el tercero; con el arreglo pasa en los tres—, porque un fallo que
depende del reloj se lee como intermitente y se acaba ignorando.

**62 tests y 109 mutantes**, los 109 muertos.

## 1.36.0

**iTerm2 y kitty abren sesiones.** Eran dos de los tres que el codigo llevaba meses
anunciando como "una linea AQUI", con la condicion de que la forma exacta de pedirles una
ventana con una orden dentro se midiera antes. Se ha medido, y la linea son dos.

| | que abre | necesita |
|---|---|---|
| **iTerm2** | una ventana por sesion | macOS con iTerm2 |
| **kitty** | una ventana por sesion, con su titulo y su directorio | macOS con kitty |

Van detras de Warp y delante de tmux: abren ventanas de verdad y no arrastran la
restauracion de ventanas de Terminal.app. iTerm2 antes que kitty porque reutiliza su
proceso.

**Las dos cosas que solo salen probandolo, no leyendo el `--help`:**

- **kitty lleva `-n` y NO `--single-instance`.** Con `-1`, la segunda llamada y la tercera
  se las traga la instancia que ya esta viva: **`open` devuelve 0 en las tres y se abre
  una sola ventana**. Un `open` que sale bien no prueba que haya pasado nada — es el mismo
  fallo que la 1.24.0 arreglo en otra puerta. El precio de `-n` es una instancia de kitty
  por ventana, y se paga: la alternativa es el control remoto (`kitty @ launch`), que exige
  que el usuario haya activado `allow_remote_control` en su configuracion, y un lanzador
  que solo funciona si te han configurado la maquina no es un lanzador.
- **Va por `open` y no llamando a `kitty`.** Lanzado directo se queda en primer plano hasta
  que su orden termina, asi que `subprocess.run` colgaria el selector entero mientras
  hubiera una sesion abierta.

iTerm2 no entiende `do script` —esa es la orden de Terminal.app— sino `create window with
default profile command`. Y va sin nombre de ventana a proposito: `set name of current
session` se acepta y devuelve `missing value`, y ademas el titulo lo pisa el proceso que
lanza el guion en cuanto arranca.

**Verificado abriendo ventanas de verdad**, llamando a las funciones del programa y no a
un comando suelto: tres pestañas por lanzador, las seis abiertas, cada orden ejecutandose
**en el directorio que se pidio**, y cero guiones sin borrar. iTerm2 3.6.11 y kitty 0.48.2,
macOS, 2026-08-31.

- **Ocho mutantes nuevos** en el catalogo (92 -> 100), y uno **reanclado**: el que rompe el
  contador de tmux apuntaba al cuerpo por lo que venia detras, y al meter estos dos entre
  medias paso a romper kitty sin que nadie lo notara. Seguia muriendo, pero por otro test.
  Ahora `tests/test_lanzadores.py` fija ademas la forma exacta de cada orden, que es lo que
  se midio, y que **todo lanzador de la tabla diga que abre**: el cuadro de elegir tira de
  `_QUE_ABRE` con un `.get()`, asi que a uno sin texto no le pasa nada — sale con el nombre
  pelado, sin explicacion, en la unica pantalla donde hay que elegir.

**Un test que solo funcionaba en la maquina donde se escribio.** El caso que comprueba
que iTerm2 y kitty no se ofrecen fuera de macOS falseaba la plataforma pero no la
existencia de las carpetas, asi que en una maquina sin las dos apps —el CI, sin ir mas
lejos— el `is_dir()` ya devolvia False por su cuenta: el guard se aprobaba sin haberlo
ejercitado. Lo canto el propio catalogo al correr en el CI, con el mutante VIVO en los
seis jobs y muerto en local. Ahora se falsean las dos cosas, y ademas se comprueba el
contraste —con la plataforma de verdad y la carpeta delante, los de macOS dicen que si—,
sin el cual un `return False` pelado tambien pasaria.

**Y `tests/test_cifras_de_la_doc.py` aprendio a contar hasta mas de cien.** El catalogo
cruzo los 99 con esta tanda y el lector de numeros en letras se quedaba corto: "cien" no
era un numero que supiera leer, asi que la doc se quedaba sin vigilante justo al pasar la
cifra redonda — y el aviso, encima, se leia como que alguien habia reescrito la frase.

**gnome-terminal sigue fuera**, y por la misma regla que hasta hoy dejaba fuera a estos
dos: no se pone a ojo, y para medirlo hace falta una maquina Linux con escritorio.

## 1.35.3

**Abrir varias por tmux ya se prueba llamando a tmux.** Era la unica pieza del programa
que decia funcionar fuera de macOS y que nadie habia visto correr nunca:
`test_lanzadores.py` cubre la tabla que decide a quien llamar y el guion que va por
delante, pero a tmux le pasa un `lambda: True` o le cambia `subprocess` por un doble. En
Linux eso deja el camino ENTERO sin comprobar, porque alli warp y Terminal.app no existen
y tmux es lo unico que queda.

`tests/test_tmux_de_verdad.py` levanta un servidor tmux propio, abre tres pestañas y mira
que paso: que la tabla elige tmux y **solo** tmux en Linux, que aparecen tres ventanas con
los nombres pedidos, que la orden de cada una llega a correr —deja su huella en disco— y
que corre en el directorio que se pidio. Una ventana abierta en `~` con la orden dentro se
ve igual de bien en una captura, y es justo el bug que el guion existe para no tener.

Comprobado en las dos plataformas: **macOS y Linux** (contenedor Ubuntu sobre
`python:3.12-slim`, tmux 3.5a), con la bateria entera corriendo en el segundo.

Tres decisiones que no son de estilo:

- **El servidor de pruebas va en un socket aparte** (`-L sereno-tests`). Sin eso, correr
  la bateria en la maquina de alguien que trabaja dentro de tmux —que es justo para quien
  se escribio este programa— le abriria tres ventanas en mitad de sus sesiones de verdad.
- **Sin tmux el test FALLA, no se salta.** Un test que se calla cuando le falta su
  dependencia no protege nada, solo lo parece; el CI ahora lo instala antes de la bateria
  para que el fallo, si lo hay, sea el de tmux faltando y no un test mudo.
- **Se comprueba tambien lo que pasa SIN ningun tmux**: la funcion tiene que decir que
  abrio cero, no tres. Devuelve hechos —cuantas salieron— y de ahi sale el mensaje que
  lee el usuario.

**Y un hallazgo que se deja escrito porque el test no puede protegerlo:** el `-c cwd` de
`new-window` y el `cd` del guion hacen lo mismo, asi que quitar cualquiera de los dos deja
la otra via corrigiendo y **desde fuera no hay diferencia observable**. El mutante que
borra el `-c` sobrevive, y no por un hueco del test. El `cd` si tiene red propia en
`test_lanzadores.py`, que ejecuta el guion suelto.

- **Tres mutantes nuevos** en el catalogo (89 -> 92): contar como abierta una ventana que
  tmux rechazo, no borrar el guion antes del `exec`, y perder el titulo de la sesion por
  el camino.

Sigue sin cubrirse lo que no existe: iTerm2, kitty y gnome-terminal no estan en la tabla
—anadirlos es una linea, pero la forma exacta de pedirles una ventana con una orden dentro
se comprueba antes, no se pone a ojo— y para eso hace falta una maquina con ellos.

## 1.35.2

**El panel lateral se reparte donde se puede leer.** Las tres piezas que lo componen
vivian dentro de `pick_ui`, que son 1.200 lineas de curses, y la mas cara de las tres es
la aritmetica que decide QUE SE VE cuando no cabe todo: si el recorrido entra, cuantos de
sus pasos, y cuanto del prompt y de la respuesta sobrevive al recorte. Es la operacion
que ya funciono con `lineas_now()` y `caja_now()`, repetida aqui:

- **`reparto_panel()`** — donde empieza cada zona y cuantas lineas se lleva cada bloque.
- **`campos_panel()`** — los pares etiqueta/valor, en orden y sin los vacios.
- **`bloques_panel()`** — los bloques de texto, en el orden en que se leen.

El bloque `if lateral:` baja de **203 a 94 lineas** y `pick_ui` de 1.241 a 1.132.

**No cambia una sola cosa de lo que se pinta, y eso no se razona.** Se comparo lo que la
interfaz escribe en un pseudo-terminal, **byte a byte, en seis tamaños de ventana** —de
40x200 a 12x40, que son los que encienden y apagan el panel y el recorrido— antes y
despues de cada uno de los tres pasos. Cero diferencias en las dieciocho comparaciones.

- **`tests/test_panel_lateral.py`** — el reparto se comprueba por barrido, **77.824
  combinaciones** de altura, campos, bloques y recorrido, y no con un puñado de casos:
  basta que falle una para que algo se pinte fuera del area, y curses no avisa cuando eso
  pasa. Fija que las tres zonas no se pisan, que un recorrido que se anuncia trae al menos
  un paso, que ninguna cabecera se queda sin una linea debajo, y que los campos ceden por
  arriba antes que salirse por abajo.

- **Nueve mutantes nuevos** en el catalogo (80 -> 89). Y aqui esta la razon de que el
  test exista: de esos nueve cambios minimos, **cinco pasaban la bateria anterior en
  verde** — un bloque quedandose con cero lineas bajo su cabecera, un recorrido sin sitio
  pintando su cabecera sola, los campos vacios llegando al panel como etiquetas en blanco,
  y "ahora mismo" repitiendo lo que el recorrido ya cuenta. Los cuatro que si se cazaban
  no se cazaban como lo que son: `test_panel_geometria.py` los veia como un desbordamiento
  del marco, que es el sintoma, no el reparto equivocado que lo causa.

Alcance, dicho antes de que lo pregunte nadie: esto fija el REPARTO y la COMPOSICION.
Que lo repartido acabe en la pantalla sin solaparse lo sigue cubriendo
`test_panel_geometria.py`, con su doble de curses, y que la interfaz arranque de verdad,
`test_tui_arranca.py`.

## 1.35.1

**Los emoji que se escriben con dos piezas ya no descuadran la fila.** El ancho del texto
se medi­a en columnas y no en caracteres —un ideograma o un emoji valen dos—, pero se le
escapaba una familia entera: los que se forman con el selector de variacion U+FE0F. `\u26a0`
es de una columna por su `east_asian_width` y `\u26a0\ufe0f` se pinta a dos, asi que cada
⚠️ ❤️ ▶️ ☑️ de un titulo desplazaba la fila una columna a la derecha. Son los mas
frecuentes en ingles tecnico.

**Aviso de alcance: esto no se observo aqui.** Se busco en los 605 titulos de esta maquina
y en las primeras 60 lineas de 250 transcripts, y no aparece ni uno. Se arregla igual: los
titulos los escribe el CLI con lo que diga cada cual, y "en mi maquina no pasa" no es un
argumento en un repo que instala gente que no conocemos. Comprobado sobre 4.000 cadenas con
CJK, emoji, combinantes e invisibles: **cero diferencias con la version anterior** fuera de
los casos con selector.

- **`tests/test_ancho_en_columnas.py`** — fija la propiedad de la que depende todo el
  pintado y que ninguna funcion decia en voz alta: **lo recortado a N columnas nunca mide
  mas de N**. Se comprueba sobre 3.006 cadenas por siete anchos, no sobre un puñado de
  casos, porque basta que falle una vez para que la fila se salga de la ventana — y curses
  no avisa cuando eso pasa: devuelve bien y el texto se pierde.

- **Siete mutantes nuevos** en el catalogo (73 -> 80).

## 1.35.0

**`--disk` dice ahora lo que RECUPERARIAS, no solo lo que ocupa.** Son preguntas
distintas, y solo la segunda es la razon por la que uno lanza este comando alguna vez.
El total decia "3,2 GB en 478 sesiones" y ahi se acababa: quien lo miraba seguia sin
saber por donde empezar.

```
lo que recuperarias, segun lo que lleve sin tocarse
  mas de 7d        337      2.5 GB
  mas de 30d       210      1.9 GB
  mas de 90d        95    788.0 MB
  cada tramo incluye los de abajo · borrar un transcript deja esa sesion fuera de --resume para siempre
```

Tres decisiones que no son de estilo:

- **Los tramos van anidados** —lo de mas de 90 dias esta dentro de lo de mas de 30— para
  que se lean como "y si apuro un poco mas, cuanto mas". Sumarlos contaria dos veces la
  misma sesion, y el test lo comprueba: apurar nunca puede devolver mas.
- **El corte mas bajo es una semana y no un mes.** En la maquina donde se escribio esto
  hay 3,2 GB de historial y NADA pasa de 30 dias —lo mas viejo son 28—, asi que unos
  cortes que empezaran en el mes dejaban el bloque vacio justo donde mas pesa. Se pintan
  solo los tramos con algo dentro: una maquina con anos ve cuatro lineas y esta ve una.
- **Una sesion cuya fecha no se pudo leer no entra en ninguno.** El fichero se mira dos
  veces —tamano y fecha— y entre las dos puede desaparecer; que no se haya podido mirar
  no es prueba de que sea vieja, y contarla como tal la mete en la lista de lo borrable
  por el motivo contrario al que deberia.

Sigue sin borrar nada, sin ofrecerse a hacerlo y sin llamar basura a nada. Lo unico que
se anade es la advertencia de que un transcript borrado deja esa sesion fuera de
`--resume` para siempre — dicha una vez, porque quien lee esto esta a punto de borrar a
mano.

- **Seis mutantes nuevos** en el catalogo (67 -> 73), y `tests/test_disk.py` envejece
  ficheros a mano para probarlo: sin eso los tramos salen a cero en esta maquina y el
  test aprobaria una funcion que no se ejecuta.

## 1.34.0

**`--json` dice ahora la version de su CONTRATO, que no es la del programa.** El sobre
anunciaba `sereno: "1.33.3"` y nada mas, y esa version sube por un color, un texto o un
arreglo interno: quien consume la salida no podia deducir de ahi si sus campos seguian
ahi. Ahora lleva ademas `schema`, que se mueve **solo** cuando un campo cambia de nombre,
de tipo o desaparece. Anadir uno nuevo no lo sube —nadie se rompe por recibir de mas—,
asi que la regla de uso es: **fija `schema`, no `sereno`**.

```json
{ "sereno": "1.34.0", "schema": 1, "sessions": [ ... ] }
```

El numero por si solo seria una promesa sin vigilante. La cumple
`tests/test_json_sin_conversacion.py`, que ademas de los 32 campos de la fila que ya
congelaba cubre el **sobre** —ni una clave de mas donde un script hace
`for s in d["sessions"]`—, comprueba que el programa y el test describen el mismo
esquema, y cuando un campo desaparece lo dice con el arreglo escrito en el propio fallo.

**Y red para los tres compositores de texto que no la tenian.** Los tres componen lo
unico que sobrevive a una tuberia: cuando el color se pierde, un estado que solo viviera
en el par de color deja nueve lineas identicas. Medido por mutacion antes de escribir
nada, de los cambios minimos aplicados a los tres **todos menos uno pasaban los 53 tests
en verde**.

- **`tests/test_cuadros_de_eleccion.py`** — `lineas_relevo` y su gemelo `lineas_abrir`
  comparten la mitad de arriba palabra por palabra: el titulo con su plural, las cinco
  primeras filas y el "y N mas". Van juntos a proposito, porque un arreglo en uno que no
  llegue al otro es justo el fallo que esa duplicidad invita a cometer. Fija lo que el
  cuadro tiene que DECIR antes de abrir ventanas de otro CLI: cuantas se entregan, que
  una lista recortada avisa de lo que deja fuera, y que cada CLI ausente sale con SU
  motivo — uno se arregla instalandolo y el otro no.

- **`tests/test_lineas_now.py`** — el estado va escrito y no solo en color, el reparto de
  la cabecera —cuantas trabajan, cuantas te esperan— no se invierte, el "hace tanto" no
  sale en las que estan trabajando, y una sesion sin llamadas lo dice en vez de quedarse
  muda.

- **`tests/test_sesiones_codex.py`** — el indice de Codex solo crece, asi que la misma
  sesion aparece muchas veces: se deduplica por id quedandose con lo ULTIMO. Una linea a
  medias —Codex escribiendo mientras leemos— se salta en vez de dejar la lista vacia, y
  se lee la cola y no el fichero entero, que es la razon de leer el indice en vez de los
  rollouts.

- **Veintiseis mutantes nuevos** en el catalogo (41 -> 67).

## 1.33.3

**La cola del transcript deja de releerse a si misma.** `ultimas_lineas` retrocedia en
bloques de 256 KB, pero cada vuelta volvia a leer desde el nuevo tope **hasta el final**
del fichero, asi que lo ya leido se leia otra vez. En un transcript de 8 MB con lineas
enormes eso son **135 MB de disco por 8 MB de fichero, dieciseis veces**, y no en un
sitio cualquiera: `pulso()` la llama con 80 lineas por CADA sesion en CADA refresco de la
lista. Leyendo solo el trozo nuevo y uniendo al final: **de 44,7 ms a 5,8 ms, y de x16,5
a x1,00** — ningun byte se lee dos veces. En un transcript normal no cambia nada (ya
leia 256 KB de 4 MB); el caso malo es justo el que la funcion existe para cubrir.

**Y devolvia una linea menos de las pedidas.** El filtro de blancos corria *despues* del
corte, asi que el hueco que deja el salto de linea final del fichero —que estos
transcripts siempre traen— se comia una plaza: `pulso()` pedia 80 y recibia 79. Con
lineas en blanco por medio se comia una por cada una. Comprobado sobre 1.500
combinaciones de fichero y numero de lineas: **cero discrepancias**, lo que devolvia
antes es siempre el final de lo que devuelve ahora, y en 1.022 de las 1.500 ahora
devuelve la linea que faltaba.

- **`tests/test_ultimas_lineas.py`** — la funcion no tenia ni un caso propio, y de siete
  cambios minimos aplicados a ella **los cuatro probados pasaban los 52 tests en verde**,
  incluido volver al bug que le dio origen: una linea de `tool_result` de 96 KB dejaba al
  lector sin nada que mirar y la sesion figuraba como parada. Fija que las lineas son las
  ultimas y estan completas, que la primera no se pierde cuando el fichero cabe entero,
  que un transcript que desaparece entre el `stat` y el `open` —la carrera de verdad con
  una sesion viva— no tumba el repintado, y **mide el coste ademas del resultado**.

- **`tests/test_hechos_colision.py`** — los ocho hechos que se le ensenan a una sesion
  sobre la de al lado, uno a uno. Estaban cubiertos solo por los dos mas gruesos: de diez
  cambios minimos a la funcion, **siete pasaban en verde**. Dos sesiones fuera de todo
  repo pasaban a compartirlo —y con el, las ordenes anchas de cualquiera—; un `rm -r`
  sobre una carpeta que no toca nadie mas gritaba igual; un tiempo que no se pudo medir
  se leia como "hace cero segundos"; y la lista de ficheros del aviso podia sacar a
  pantalla rutas de la sesion de al lado, que ademas de falso es trabajo de otro cliente.

- **Catorce mutantes nuevos** en el catalogo (25 -> 39).

## 1.33.2

**Un rango absurdo en el cuadro de cerrar ya no se come la RAM.** `parse_sel` recortaba
el rango *despues* de generarlo, asi que `1-50000000` sobre tres sesiones devolvia la
respuesta correcta tras **2,8 s y 2,3 GB de memoria**. En un equipo de 8 GB eso es la
interfaz colgada por un dedo torpe, y el cuadro donde pasa es justo el que decide que
sesiones se matan. Recortado antes de generarlo: **de 1.835 ms a 0,034 ms**, mismo
resultado. Comprobado sobre 294 combinaciones de entrada y numero de filas: **cero
discrepancias** con la version anterior.

- **`tests/test_parse_sel.py`** — la funcion que traduce lo tecleado a filas que se van
  a cerrar no tenia ni un caso, y es la de consecuencias mas caras del programa. Fija sus
  dos fallos opuestos (entender de menos deja vivo lo que se queria cerrar, entender de
  mas mata una sesion que trabajaba), que `None` no es `[]`, que la cuenta es de uno, que
  una palabra desconocida invalida la seleccion entera en vez de adivinar, que los tres
  atajos valen en los dos idiomas, y que **una fila cuyo estado no se pudo observar no
  cuenta como parada**. Tambien vigila el coste, no solo el resultado.

- **`tests/test_cifras_de_la_doc.py`** — las cifras que la documentacion afirma sobre si
  misma se comprueban contra la realidad. El README llego a anunciar veintitres tests
  habiendo cuarenta y ocho, y veinte mutantes habiendo veintiuno: nadie miente, la cifra
  se escribe una vez y el siguiente test la deja atras, y encima va en letras, donde no
  la ve ningun grep. Lee "forty-eight", "cuarenta y ocho" y "veinticinco", y lleva su
  propio control positivo: si el conversor se rompe, se delata en vez de aprobarlo todo.

- **Cuatro mutantes nuevos** en el catalogo (21 -> 25), los cuatro sobre `parse_sel`.

## 1.33.1

**`--hoy` se lee mejor.** No cambia lo que mide; cambia cómo se ve, que ayer se resolvió deprisa.

- **Su propia rejilla.** Reutilizaba la de `--disk`, donde el número son ficheros (tres cifras)
  seguidos de un peso. Aquí es una sola cifra, y la fila salía con treinta columnas de blanco
  entre el nombre del proyecto y el número.
- **El ancho del título sale del título más largo** que se va a pintar, con suelo y techo, en vez
  de un 38 fijo que abría un río de blanco hasta el estado.
- **El proyecto tiene su columna**, y solo aparece cuando la jornada tocó más de uno: repetir el
  mismo nombre en todas las líneas es tinta que no distingue nada.
- **Orden en «a medias»**: lo que sigue corriendo arriba, y debajo lo que te espera, por lo más
  reciente. Antes salía en el del `mtime` de los ficheros, que mezcla las dos cosas.

El caso que fija ese orden tuvo que cruzar estado y recencia —la que corre, tocada **antes**; la
que espera, **después**— porque el barrido ya devuelve por `mtime` descendente y cualquier orden
habría pasado. Dos intentos antes de que el mutante muriera: en el primero las dos filas eran
"waiting" y no separaban nada; en el segundo, una tocada hace un minuto cuenta como *escribiendo*,
porque por debajo de noventa segundos el transcript sigue caliente.

## 1.33.0

**The mutation ritual is now a test.**

A green test doesn't say the guard works. It says nobody broke it today. The way to know is to
break it on purpose and see whether anything complains — and doing that by hand over two days
found eight guards with no net at all, every one of them behind a suite that was fully green:

- a decision written **twice**, with the test replicating it in its own body instead of calling
  it, so inverting it in the code passed;
- a real count replaced by `len(list)` — the exact bug the previous release had fixed — passing
  all forty-four tests;
- a level stored as the highest ever seen instead of the current one, silently killing the second
  alert of any session that compacts and fills up again.

`tests/test_mutantes.py` holds twenty of those breakages as a catalogue: the guard, the minimal
change that breaks it, and the test that has to catch it. Each one runs against a **copy** of the
tree in a temp dir, never the real file — an interrupted run once left the program mutated on
disk, and that is not a thing you want to discover later.

It fails two ways, and both matter. **A mutant survives**: some guard has no net, either the case
is missing or the one that exists measures something else. **An anchor no longer exists**: the
code moved and the entry went stale — it is not skipped quietly, because a catalogue that ignores
itself protects nothing.

Twenty out of twenty die, in two seconds, so it runs in CI with everything else.

## 1.32.0

**46 of the 200 rows in the history were nobody's sessions.**

A skill optimiser launching itself: twenty-two *"Score how well the response satisfies…"* and
twenty-two *"Complete the following task…"*. They took the real ones' place in the list, counted
as work in `--hoy`, and put projects named `skillopt_sleep_claude_ylulwmwr` into `--disk`'s
breakdown. Here, 78 of them in total.

They are recognised by **where they were born**, not by what they say. Their working directory
hangs off the system temp dir (`$TMPDIR`, `/tmp`, `/var/folders`…) — somewhere nobody resumes
anything from, because tomorrow it is gone. Filtering on the title would be guessing, and it would
break with the next version of whatever script launches them.

- Not offered for resuming, and not counted as work in `--hoy`.
- `--disk` still reports what they weigh, on its own line, exactly as it does for subagents: the
  weight is real even when the work isn't yours.
- `--find` skips them **and says so** — a search that stays quiet about what it skipped answers
  "never said" when the truth is "never looked". `--all` looks at them, because `--all` means
  look at everything.

**The price, stated plainly:** a session genuinely started inside `/tmp` no longer shows up. The
rare case gives way to the one that happens every day.

Ten test files stopped using `/tmp/proyecto` as their pretend working directory — under the new
rule that stands for a throwaway session, which is not what those cases mean. Six mutants, all
red, including the one that matters: matching the temp roots by plain prefix instead of by path
segment, which would swallow `/var/folders2`.

## 1.31.0

**`--hoy`: what today added up to, by project.** (`--today` works too.)

`--now` is the snapshot of this instant. `--disk` is the accumulated weight. Neither answers the
question you actually ask at the end of the day — what did I do today, and what is still hanging.

```
Today · since 05:00 · 5 sessions in 4 projects
  first at 10:07, last at 10:42

by project
  VanguardIA                         2     18m ago
  sereno                             1         now

still open
  ● SEO maratelierdeestilo.com and Treatwell  writing            now   35%
  ○ Warp error review                         waiting on you 35m ago   14%
```

**The day starts at five in the morning.** Someone closing at half past one is asking about the
work they just did; a midnight cutoff would answer *"nothing touched today"* exactly when they
look hardest — and that failure reads as a plausible answer, not as an error. `SERENO_JORNADA=7`
moves the hour.

The `mtime` filter runs before anything is opened, so the command stays cheap: out of 877
transcripts here, a normal day touches fewer than twenty. `--hoy --usage` adds replies and active
time per project, and that one does read whole transcripts. Without it those fields are `null`,
never `0`: nobody measured them, and a zero would read as "did no work".

Same split as `--disk`: `jornada()` observes and returns typed facts, `cmd_hoy()` only prints
them. And *still open* reuses the list's own cutoff instead of inventing a second one — a mutant
proved the private threshold was dead code hiding behind `estado_estable`, and two thresholds
would have meant two different answers to the same question.

## 1.30.2

**`--dismiss` did nothing on any machine that had a session open.**

The flag is in `--help` and it discards the registry entries whose process is gone. It lived
**after** the fork in `main()`, so with one session running — which is to say, always — the
program printed the list of live sessions and exited **0 without discarding anything**.

An option that doesn't exist gets reported (`test_flags.py`). This one existed and was
swallowed in silence, which is worse: you have no reason to check.

Discarding an orphan has nothing to do with whether other sessions are alive — an orphan is an
entry whose process is dead — so the flag now answers before the fork, and it says so when
there is nothing to discard instead of announcing that it discarded zero.

The test calls `main()`, not `orphans()`: what was broken was not the function but where it was
written, and a case against the function would have stayed green the whole time the bug was
live. It also runs a real live process whose command line mentions `claude`, because
`alive()` requires that on top of the pid — parking the guard would have tested nothing.

## 1.30.1

**An adversarial audit of 1.22.0 → 1.29.0 found three things the tests were not holding.**

Nothing user-visible changed. What changed is that three claims made by earlier releases are now
actually defended, and one latent crash is closed.

### The CI ran 27 of 44 test files

`ci.yml` listed each test by hand, one `run:` per file — and **not one of the eleven files written
between 1.22.0 and 1.29.0 was ever added**. Seventeen of forty-four never ran, and the twelve
checks per PR were six jobs × two triggers over the same subset. Green the whole time.

A hand-written list is a list you forget. `tests/todos.py` now collects the folder, runs each file
in its own process (they all move `HOME` around) and prints the sentence from each docstring —
which is exactly what the step names used to say. The workflow calls it once and cannot drift.

### A session archived without being opened

*"An orphan that doesn't open is no longer archived as resumed"* (1.27.0) could be undone by
flipping one `if`, with every test green. The decision lived **twice** — once in the picker, once
on the command line — and the test replicated it in its own body rather than calling it, so both
`if True:` and `if False:` survived. The compensating source check anchored on the wrong lines.

There is one copy now, `reanuda()`, and both routes call it. The test calls it too, instead of
reimplementing it, and a case fails if a second copy ever appears.

### The screen could go back to lying about how many tabs opened

`abre_varias` returning the real count is the whole of 1.24.0. Replacing it with `len(pestanas)` —
the bug it fixed — passed all 44 tests: one test measures "no launcher at all", another measures
the opener, nobody measured the link in between propagating the zero. It does now, and `reopen`
is checked to exit 1 without announcing anything.

### And the last binary called bare

`tmux_kill` had `check=False`, which ignores an exit code but does **not** protect against the
binary being absent — that is a `FileNotFoundError`, and inside curses it takes the program with
it. It was the twin of the crash fixed across 1.24–1.27, still standing, protected only by the
fact that without tmux there are no rows to kill. Two lines, and a case that fails without them.

## 1.30.0

**`--watch` now also tells you when a session is running out of context.**

The watcher reported three transitions: a session stopping, two sessions starting to write in
the same place, and one starting to go in circles. All three are about what a session **does**.
The fourth is about what it has left to keep doing it — and it is the only one you answer by
compacting rather than by looking.

```
22:03  ▰ Refactor payment webhooks is at 90% of its context  (strev-api)
```

It fires at **80%** and again at **90%**, and — like the other three — **on the crossing, not on
the state**: half an hour sitting at 92% is one line, not one per poll. If the session compacts,
the level drops on its own and the next climb is news again. A session whose ceiling is not known
says nothing at all: `null` there means *not measured*, and treating it as full would invent an
alert out of a missing number.

```bash
SERENO_CTX_AVISO=70,85 sereno --watch   # your own thresholds
SERENO_CTX_AVISO=0 sereno --watch       # no context alerts at all
```

The decision is a pure function (`contextos_nuevos`), like the other three, for the same reason:
the loop cannot be tested and this can. Six mutants, each turning the case red — including one
that at first did **not**: storing the highest level ever seen instead of the current one would
have silently killed the second alert of any session that compacts and fills up again. It only
showed up once the test ran the actual loop.

## 1.29.0

**Which CLI a session belongs to, and a handover box that remembers.**

### The tab bar was mixing two different things

`claude · historial · codex · gemini · todas`. But **`historial` is not a CLI** — it is Claude
sessions that stopped, a *state*. Having it as a tab put two axes on one bar, and left the real
question unanswered: in the `todas` view **no row said whose it was**.

Now each CLI has a glyph, and it appears **only when the list actually mixes them**:

```
 ✦ claude  ◆ codex  todas    10 en total  ·  ● 1 escribiendo  ·  6 reanudables
 ─────────────────────────────────────────────────────────────────────────────
 ▎ ◐⧉ ✦ Refactor payment webhooks              ahora ▰▰▰▰▱  88%
      ✦ Draft release notes v2.4             hace 7m ▰▰▰▱▱  64%
      ◆ Shrink the docker image              hace 2d
      ◆ Name the new billing events          hace 4d
```

The tab carries its own glyph, so it **is** the legend — no help line nobody reads. In a
single-CLI tab the column disappears and the title gets its two columns back: repeating the same
symbol eight times only says what the active tab already said. `historial` folds into `claude`,
at the bottom, which is where `ordena()` already put it, and its count moved to the header as
*resumable*.

The four glyphs measure **one column** (`east_asian_width` 'N') and none was already in use —
`▪`, the obvious pick for codex, is the *has a tab open* marker. An emoji would take two and
quietly skew the whole table.

**And a copy that had drifted:** the bar computed the CLI list one way and the Tab cycle another —
one looked at `fuente`, the other at the CLI — so Tab stopped on a tab the bar never drew and the
list came out empty. One `clis_presentes()` now, and a test that fails if a second copy appears.

### The handover box

- **Where the windows open** is now part of it: `w` cycles it, the same question `r` asks.
- **It remembers.** Last destination goes to the front, last place stays put. Whoever hands over
  to Codex once hands over to Codex always; starting from the top of the list every time is making
  them type the same thing again.
- **It says what it cannot offer.** With only Codex installed the box showed one option and
  nothing else — no way to find out this works with more CLIs. The others are listed greyed out,
  grouped by **their own reason**, which is not the same one: one is fixed by installing it, the
  other needs checking in its `--help` how a starting prompt is passed, which is why `gemini` is
  not in `ARNESES` and never was an oversight.
- And `sesión(es)` is gone: one and many are two strings, in both languages.

Eleven mutants across the two areas, each turning a case red — including two that at first did
**not**: the box remembering was only tested through its helper, not through the box.

## 1.28.0

**A session you just closed came back a few seconds later, marked as live.**

Reported by Alex: mark several, close them, they close — and seconds later they are in the list
again, as if running.

The list has two sources: what tmux shows, and a sweep of `~/.claude/projects` for whatever tmux
does **not** show. The second one excludes the first. So killing a session took it out of tmux,
which took it out of that exclusion list, and it **walked straight back in from disk**: its
transcript had been touched seconds ago, so `idle` was near zero, so it was drawn as alive. With
the uuid for a name instead of its own, which is why it did not even look like the same row.

What was closed is now written down, and the sweep skips it. Three things about that note:

- **It goes on disk, not in memory.** Reopening the picker is another process, and the fright
  would repeat there.
- **It records the id and the transcript's stem.** A resumed session is not named after its id —
  with only the id, it comes back through the other door. That case is in the test because
  removing the stem passed everything else: in the straightforward case the two are equal and
  distinguish nothing.
- **It expires after `VIVA` seconds**, the same threshold that already drops a quiet session. A
  note that never expired would hide a session that genuinely came back to life.

`--stop-all` and `--stop` write it too: neither goes through `stop_rows`, and without it the bug
survived by those two doors.

The test carries a **positive control** — a session nobody closed still comes out of the sweep.
Without it, breaking the sweep altogether would pass. Four mutants, each turning a case red.

## 1.27.0

**An orphan that did not open was filed away as resumed — and stopped being offered.**

Found by applying, immediately, the lesson 1.26.0 had just written down: **grep the call, not the
function.** Two more copies of the raw `open` were left, both in the orphan flow — the sessions
that survived closing Warp. And in both, the order was backwards:

```
path = write_launch_config(elegidas)
archive(elegidas, "restored")          # first
subprocess.run(["open", ...])          # and then, without looking
```

Archiving an orphan means *this one is dealt with*, and from then on **it is not offered again**.
So an `open` that failed — a Mac without Warp, a Linux where that binary does not even exist —
left them marked as restored without having opened them: not resumed, and gone from the list. Not
a wrong message. Losing them.

Now they are archived **after** opening and only if something opened, in both the picker and the
command line. When nothing opens, nothing is filed, and tomorrow the list still has them.

**There is now exactly one `subprocess.run(["open", …])` in the file**, inside `_abre_en_warp` —
checked with the grep this time, not by eye. The other five have been going one per version since
1.24.0, which is what happens when you fix the function you have in front of you instead of
counting the callers first.

The test watches the source order too, not only the behaviour: its behaviour case has to replicate
the decision, so on its own an inversion in the program would keep it green. Two mutants — filing
before opening, and never filing — each turn a case red.

## 1.26.0

**`r` asks where to open them.**

1.25.0 gave sereno three ways to open several sessions at once and then picked one for you — the
first available. The only way to say otherwise was `SERENO_LANZADOR`, an environment variable,
which is exactly the complaint 1.23.0 made about the handover: *an environment variable is not a
way to offer something*.

```
Abrir 2 sesión(es) en:

· Fix flaky login test
· Migrate CI to reusable workflows

[1] warp  —  una ventana de verdad para cada una
[2] tmux  —  una ventana de tmux para cada una, donde ya estás
[3] terminal  —  una ventana de Terminal.app para cada una

[1-9] abrir ahí    [otra tecla] cancelar
```

Each line says what that launcher actually opens: *tmux* on its own does not tell you whether the
windows are the system's or tmux's. With only one launcher around there is no box — a box with a
single option is just one more keypress.

**And the fix in 1.24.0 never reached the key people actually press.** `r` inside the picker had
its own copy of the raw `open` call — the fourth in the file — so neither the guard that stopped
the Linux crash nor the launcher table went anywhere near it. It reported the tabs it *asked for*,
and on any Linux it still took the program down. That copy is gone: it goes through `abre_varias`
like everything else, and reports what opened.

**One bug caught by the tests, not by reading:** the demo's `ejecutar` is a two-parameter lambda
and the picker now passes three, so `r` in `--demo` raised. It has a default now, and a test
watches the signature.

Five mutants — always the first launcher, `donde` not passed through, a box shown for a single
option, cancel that opens anyway, and the demo lambda back to two parameters — each turn a case
red. And checked in a real pty: mark, press `r`, and the box comes out with its three lines.

## 1.25.0

**Opening several at once stops being a Warp thing — and a macOS thing.**

1.24.0 made `r` and `c` admit they could not do it without Warp. This gives them two more ways,
in preference order:

| | what it opens | needs |
|---|---|---|
| **Warp** | a real window per session | macOS with Warp |
| **tmux** | a tmux window per session, in the session you are already in | being *inside* tmux — **the only one that works off macOS** |
| **Terminal.app** | a Terminal window per session | macOS |

Terminal.app is last on purpose: macOS **restores** its windows on reboot, so a day of handovers
leaves windows coming back at startup. `SERENO_LANZADOR` forces one. iTerm2, kitty and
gnome-terminal are one line each — but none is installed on this machine and none goes in by
guesswork: how you ask a terminal for a window with an order inside gets checked first, the way
these three were.

**The order travels in a script on disk, not inline.** `do script` and `tmux new-window` take the
order as one string, and a handover briefing has newlines, single quotes and double quotes in it:
inline is the same bug that used to break Warp's YAML, in a different suit. The script does three
things, each measured rather than assumed:

- `cd` to the session's directory and **abort** if it is gone — not carry on in `~`;
- `unset TMUX`, because reattaching is `tmux attach`, which inside tmux refuses with *sessions
  should be nested with care* (verified: with `TMUX` set it fails, empty it works);
- **delete itself before the `exec`** — a deleted file is still readable through the descriptor
  `sh` already holds, so everything after the `rm` still runs (verified) and the briefing does not
  stay on disk. It lives in `~/.sereno/lanzar`, `0700`, deliberately not in `/tmp`, which every
  user on the machine can read.

**And the count is the truth now.** `reopen` reports how many windows actually opened, not how
many were asked for, and says so when some did not.

Checked end to end on both new launchers, with a briefing carrying newlines, `it's` and `"raro"`
and accents: it arrives whole, the working directory is the session's, `TMUX` reaches the child
empty, and no script is left behind. Five mutants — no `unset`, a `cd` that does not abort, a
script that does not delete itself, `0755` on the script, and the table reordered — each turn a
case red.

## 1.24.0

**On a machine without Warp, `r` and `c` took the whole program down.**

`open` is a macOS command. On Linux `subprocess.run(["open", ...])` raises
`FileNotFoundError` — and it was called with `check=False`, which only ignores the *exit code*,
not a missing binary. So on any Linux, marking two sessions and pressing `r` crashed sereno from
inside curses. Sereno is published for anyone; this needed no exotic setup, just not being on a
Mac with Warp.

The other half is the same failure without the crash: on **macOS without Warp** nothing raised,
`open warp://…` failed quietly, and the screen still announced *"Reattaching 3 tabs"*. Three tabs
that do not exist.

One `_abre_en_warp()` now makes that call, in the three places that made it, and returns **a
fact** — whether it happened — instead of taking the call for granted. Without Warp it says so,
and says what does work: `ENTER` opens one at a time, on any terminal, and always did.

The test carries a **positive control**: with Warp and with `open`, the same rows *are* reported
open. Without it a blunt `return 1` would pass both of the cases above.

## 1.23.0

**`c` pregunta a dónde va, en vez de coger el primero del PATH.**

Handing a session over opened windows of another CLI on a single keypress, with no confirmation
and without saying which one it was going to: it took whichever came first out of `arneses_disponibles()`.
With one installed nobody notices; with two it decided for you. And the conversation — the last
prompt and the last answer — was asked for with an environment variable, `SERENO_RELEVO=completo`,
which nobody finds without reading the README.

Both now live in the same box, over the list:

```
Entregar 1 sesión(es) a:

· Refactor payment webhooks

[1] codex   [2] claude
[k] incluir la conversación: no

[1-9] entregar    [otra tecla] cancelar
```

The origin CLI is not offered — but only when it is the origin of **every** marked row: with a
mixed selection both appear, because some row can go to each. `k` toggles the conversation and
says, while it is on, that it ends up written to Warp's configuration on disk. Any other key
cancels, which is new: until now `c` had no way back.

The box is composed by `lineas_relevo()`, apart from the drawing, for the reason 1.19.0 learned
the hard way — **curses does not complain when a box does not fit**, so the geometry is checked
on the lines, without a terminal in the middle. And the test double grew a `newwin`: it returned
a plain `0`, so no test could press a key that opened a box. Neither this one nor the close
confirmation was reachable.

**And the same empty-path guard, deduplicated.** `abrir_sesion` had its own copy of the check
1.22.0 fixed — the version that lets `""` through. One `_dir_util()` now decides it in both
places: it does not survive as two.

## 1.22.0

**The handover went one way, and its guard did not hold.**

Three defects in `c`, found by asking what it does for someone who is not me.

`Path("").is_dir()` returns **`True`**: Python reads the empty path as `.`. The guard that
existed to stop a handover starting in the wrong directory therefore let through every row with
no recorded `cwd` — which is every Codex row, they carry `""` — and opened the other CLI wherever
the process happened to be standing, announcing *1 handed over*. It is the exact failure the
guard was written to prevent, passing as a success. The check now asks for an **absolute** path,
so a relative one is out too: it exists relative to the process, not to the session.

**Nothing hands a session to the CLI it is already running under.** A Codex row handed to Codex
opened a blank session and counted it as a handover.

**And it goes both ways now.** `claude` is in the table beside `codex` (`claude [PROMPT]` starts
an interactive session with a seed, checked against its own `--help`), the briefing names the CLI
it comes from instead of always saying *"a Claude Code session"* — false for a Codex row — and
with nothing chosen the destination is whichever available CLI is not the origin. So a Codex
session is handed to Claude without picking anything.

**And a Codex row now knows where it lives.** Its index carries `{id, thread_name,
updated_at}` and nothing else, so every Codex session arrived with an empty directory — which,
once the guard above holds, means none of them could be handed over at all: the other half of the
handover would have shipped implemented and dead. The header of its rollout does carry it, in
`payload.cwd`. Only the rows about to be drawn are opened, and only their first line: **9 of 11
resolved in 7 ms** on this machine, against 699 rollouts on disk. The two without one keep an
empty directory rather than inheriting a neighbour's, and the project column fills in for the
rest.

Ten new cases across `test_relevo.py` and `test_cwd_codex.py`, each checked by mutation: the old
guard, the missing same-CLI filter, the fixed briefing, splitting the uuid on hyphens and sharing
one `cwd` between rows were each put back, and each one turned a case red.

**Checked by opening the window, not by reading the YAML.** A real Codex row was handed over:
Warp opened, `claude` started in `/Users/alex/Desktop/VanguardIA` — the directory read from that
session's rollout — and its transcript's first prompt is the briefing, whole, saying it comes
from a Codex session. Warp reports nothing when a launch does not happen, so the first attempt
was confirmed against a positive control (a trivial configuration that writes a file) before
concluding anything about this one.

## 1.21.0

**Two places where it filled a gap in instead of leaving it empty.**

`--find` looks at the 200 most recent transcripts. There are 601 on this machine, so a plain
search reads a third of them and the header said only *"searching 200 transcripts"* — which reads
as *that is all there is*. It now says how many older ones it skipped and that `--all` includes
them. A "you never said that" which is really "it wasn't in the third I read" is the worst answer
a search can give. On stderr, like the size notice, so a piped run stays clean.

`--list` printed `open for ?` for any session with no tmux entry — every session not launched
through the alias, which the picker reads from `~/.claude/projects`. The panel leaves that field
blank; the list filled it with a question mark. Same fact, two treatments, and the ugly one
asserts the field and pads it with a symbol. It is left out now, and the row no longer trails
whitespace either.

Neither is a crash. Both are the list saying something it does not know.

## 1.20.0

**A session you just interrupted stops calling itself busy.**

1.16.0 taught the state to read `stop_reason`, and made one rule out of it: any later `user` line
reopens the turn. Pressing ESC writes a `user` line, so an interrupted session read as `writing`
for the next ninety seconds — and that is the worst case of the lot, because you interrupt a
session precisely when you are about to type into it.

The CLI marks it two ways, counted over this machine's transcripts: 87 interruptions, **78 with
an `interruptedMessageId` field and 9 with only the English text**. Both are read. The field is
the real signal — typed, and it survives that sentence being reworded or translated; the text
catches the nine that arrive without it.

The two are tested **apart**, with the field case deliberately carrying a text that is not one of
the markers. With both signals in one case, turning off either half of the detector still passed
green — measured, not assumed.

**And `--watch` was verified end to end for the first time**, against real sessions rather than a
unit test: it fired on `lesbainsdeazahara.net imágenes home`, whose turn closed at 14:51:46, at
14:51, and on `BioOnline` (14:52:37) at 14:52. Same minute, inside the polling interval — not the
ninety seconds late it would have been before 1.16.0.

## 1.19.0

**`n`: the `--now` view, without leaving the picker.**

1.17.0 added `--now` — what every live session is running, in one screen — and left it in the
shell. The picker is where you actually are, so getting it meant quitting and typing a command.
Now `n` opens the same screen over the list, and any key closes it.

One composer builds both (`lineas_now()`). Two of them writing the same facts is how a screen and
a terminal end up disagreeing about the same nine sessions, which is the thing this program
exists not to do.

**A bug found by testing it, not by reading it:** in a window under six rows tall the box came
out taller than the screen. It never showed up because **ncurses does not complain** — measured
in a 40-column pty, a `newwin` wider than the terminal returns fine and an `addnstr` past the
edge returns fine too. The box just loses its right edge, silently, forever.

So the geometry now lives in its own function with no curses in it (`caja_now`), and a test
sweeps 9 heights x 8 widths x 5 lengths in milliseconds, checking the box stays inside the screen
and the last line does not land on the bottom border. The on-screen test could not have caught
this; that one runs the real TUI in a pty and checks the screen opens, paints and closes — three
window sizes, because the grid is covered for free by the pure one.

## 1.18.0

**Open the marked ones at once — and hand them to another CLI.**

`r` ("reopen the marked ones as tabs") already existed and **was broken outside tmux.** There
were three copies of the same Warp YAML in the file — open one, reopen several, restore the
orphans — and the middle one had the command hardcoded to `tmux attach`. Marking five history
sessions and pressing `r` opened five tabs that all failed: `tmux attach -t <uuid>` is not a
thing. `_comando_de()` already knew the right command for all three cases and nobody asked it.

Now there is **one** writer of that YAML and **one** place that decides the command, so a fourth
copy cannot bring the bug back. Also in the picker:

- `r` now requires marking. With nothing marked it used to open **every visible row at once**,
  and it sits next to the arrow keys.
- The notice says what was left out and why — already had a tab, or cannot be opened from here.
  They used to be dropped in silence.

**`c` hands the marked sessions over to another CLI.** A handover, not a migration: a Claude
session's context lives in its own transcript and no other CLI can pick it up. So `c` opens a
**new** session of the other CLI in the same directory and branch, with a briefing of where the
Claude one got to — project, branch, title, state and its last tool calls.

Facts only. No prompt and no reply of yours goes in there: the briefing travels inside Warp's
launch configuration, which stays on disk. `SERENO_RELEVO=completo` adds the conversation, and
is never the default. A session whose directory no longer exists is left out instead of starting
in `~`, because a handover that begins in the wrong place looks like it worked.

Only CLIs actually on your `PATH` are offered — today that table holds `codex`, whose
`codex [PROMPT]` was checked against its `--help`. `gemini` is not in it because it is not
installed here and its flag would have been a guess.

Found while testing this and worth its own line: **a command with newlines broke the YAML.** The
briefing has them, `- exec: <command>` spilled them loose, and the file came out invalid — the
window simply does not open and nothing in the program errors. It is written as a literal block
now, and a test unwraps it back.

## 1.17.0

**`sereno --now` — what all of them are running, in one screen.**

The panel already drew the trail of tool calls: glyph per call, timer, failures marked, and the
stuck-detection on top. Of **one** session — the row under the cursor. So finding out what nine
sessions were doing meant moving the cursor down nine times, and in practice you went back to
attaching to each one, which is the thing this program exists to avoid.

```
4 live · 2 working, 2 waiting on you

Refactor payment webhooks  ·  checkout-api                  in a command
  ! the same command has failed 3 times
    ✗  31s  Bash · pytest tests/webhooks -x -q
    ✗  33s  Bash · pytest tests/webhooks -x -q
    ◐   1m  Bash · pytest tests/webhooks -x -q
```

No new column and no fight for width: the row layout is untouched. It reads exactly what the
panel reads — the tail of each transcript — so it opens nothing extra beyond what each row
already needs, and it is the live sessions only, never the 595 in the history.

The header is counted **from the rows underneath**, not on its own, and a test fails if the two
ever disagree: a summary nobody recomputes while reading it is a summary that drifts.

## 1.16.0

**The one that has already finished stops calling itself busy.**

`writing` was decided by the transcript's mtime: touched in the last 90 seconds. That stays true
for a minute and a half **after** a session answers you — precisely the window in which you want
to know which of the nine is now waiting. Sampled against Claude Code's own spinner on
2026-08-28, across nine live sessions and 90 readings, **16 of the 48 that said `writing` were
sessions that had already stopped** — a third of them. None the other way round, so the error had
a direction: it hid the ones asking for you.

The transcript already said so and nobody was reading it. The CLI writes `stop_reason` on every
reply, and `end_turn` means the turn is closed. A later `user` line — a new prompt, or the result
of the command it was waiting on — reopens it. Both facts come out of the same pass `pulso()`
already makes over the last 80 lines: **no extra read, no extra file opened**.

- `--watch` now fires when the turn actually closes, not up to 90 s later.
- `--json` gains `turn_closed`, next to `writing` and `tool_pending`. It is `null` when the
  transcript does not say — an old transcript, another CLI — and there the state is decided
  exactly as before. A missing fact is not a good fact.
- Verified by turning the mechanism off: with the guard removed, or with `turn_closed` forced
  true, `tests/test_fin_de_turno.py` goes red in both directions.

**What it does not fix, measured on the same bench: 4 of 26.** A session whose last line is a
`tool_result` that never got an answer — interrupted, or dead mid-turn — still reads `writing`
until the 90 s run out. From the transcript that is indistinguishable from a reply about to
arrive, and inventing the difference would be guessing. Down from a third to one in six, not to
zero.

## 1.15.0

**`sereno --disk` — what the transcripts weigh, and where that weight is.**

The panel gives the size of the row under the cursor and nothing else, so the split was invisible.
On the machine this was written on it turned out to be **3.4 GB across 595 sessions**, with
3,464 MB of it in a single project and **403 MB in five sessions** — none of which was visible
anywhere, on a laptop whose disk sits at 97%.

```
3.4 GB in 595 sessions · /Users/you/.claude/projects
  plus 285 subagent transcripts, 436 KB

by project
  VanguardIA                       442      3.4 GB
  and 56 more projects, 3.8 MB between them

the heaviest sessions
     85.2 MB  25d ago  Rebuild the atelier landing page       445cdc22
     …

102 of them (2.9 MB) have no place to go back to.
```

**It deletes nothing, offers to delete nothing, and calls nothing garbage.** `sereno` writes to
nothing that belongs to a session — a heavy history is a fact, not a problem, and what to do about
it is not the tool's call. The facts come out of one function and the printing out of another, so
the numbers can be checked without reading the layout.

340ms for 595 sessions: a `stat` on each, the `cwd` read from each header — the cheapest thing that
answers *does this history still belong to something that exists* — and the title only of the
handful it prints. Subagent transcripts are counted apart, because 285 of them here weigh 436 KB:
folding them into the split would move the file count without moving a megabyte.

Two things measured on the way in, and worth knowing before you go looking for space: **the
irrecoverable sessions weigh nothing** (102 of them, 2.9 MB — the ones with nowhere to go back to,
sunk in the list since 1.14.0), and neither do subagent transcripts. The weight is in long sessions
of the project you actually work on.

## 1.14.2

**Closes the four minor findings the 1.14.1 audit left open on purpose.**

- **`bump-tap.sh` now checks the fact, not the shape.** It validated that a sha *looked* like a sha
  and that the formula had exactly one url and one sha256 — never that the release existed. Handed a
  version that was never published it exited 0 and left the tap pointing at a 404, with only the
  tap's weekly cron to notice, up to seven days later. It now downloads the asset and compares its
  sha against the one it was told to write, so the guarantee belongs to the script instead of to the
  order in which `release.sh` happens to call it.
- **A formula carrying an explicit `version` stanza is refused.** That stanza is a third copy of the
  version number this script does not touch: Homebrew would use the old one while downloading the
  new asset, the `install` guard would `odie`, and `brew install` would be broken for everyone.
  Reproduced before fixing.
- **The header arithmetic has a test.** A row that never started *and* lost its directory is counted
  once, under *never started*, which is what makes the labels add up to the number of rows. Removing
  that condition used to keep the suite green; now it fails.
- **`SERENO_SIN_TAP`, `SERENO_TAP_REMOTO` and `SERENO_ASSET_BASE` are documented** in both READMEs.

`test_bump_tap.py` gained three cases — a version that is not published, a sha that is not the
published asset's, and the `version` stanza — and now serves assets over `file://`, so it exercises
the network check end to end without a network.

## 1.14.1

**An audit of 1.14.0 refuted one of its claims and found six mechanisms whose tests passed with the
mechanism switched off.** Nothing was broken; several things were less proven than they read.

- **`hay_sitio()` marked a directory that exists.** It used `os.path.isdir`, which swallows the
  error inside and returns False, so a permission denied or a symlink loop came out as *the
  directory is gone* — the exact absence the guard claimed to prevent, and its `except OSError` was
  dead code that never ran. Now `os.stat` + `S_ISDIR`, with `FileNotFoundError` separated from *could
  not look*. Reproduced: a directory whose parent is `chmod 000` used to sink its row, and does not
  any more.
- **The TTL was never tested.** The test cleared the cache by hand instead of letting it expire, so a
  cache that never expired — a row that would never revive — passed green. It now moves the clock.
- **`release.sh` calling the tap bump was checked for existence, not position.** The whole guarantee
  is positional: `bump-tap.sh` validates the *shape* of a sha, never the *fact* that the asset
  exists, so what protects the tap is that the call sits behind the verify-by-download. Moving it
  earlier kept the test green. Now the order itself is asserted.
- **The zero that meant no accounting.** The CLI writes `cost-state` with `totalCostUSD: 0` and an
  empty `modelUsage` on a subscription plan; that is not *this session cost nothing*, it is *nobody
  is counting*. It was stored as `0.0`, telling a statusline the work was free. Measured across the
  878 transcripts on this machine: 40 lines with a real cost, 8 with that undocumented zero, and
  **none** with a legitimate zero — so telling them apart loses no real case.
- **The privacy paragraph named a list of imports it called complete, and it wasn't.** `base64`
  joined in 1.13.0 with OSC 52 and the list never said so. `test_sin_red.py` now checks the list in
  both READMEs against the imports the program actually has.
- **Two published numbers were wrong** and are corrected in the 1.14.0 entry: caching per path saves
  3 stats out of 40 on a cold start, not 36, and the claim that the `stat` cannot block the TUI is
  false — the reload is synchronous with painting, so a hung mount freezes the list.

The full audit is in the repo history of the PR that fixed this.

## 1.14.0

**Sessions you cannot go back to stop competing for the top of the list.**

A session whose working directory no longer exists cannot be resumed in any useful sense: it drops
you into a `cd` to a place that is not there. Those now sort below everything, print in grey, and
the header counts them apart — `6 resumable · 40 with nowhere to go back to`.

It is the twin of what 1.12.0 did for sessions that never started, asking the same question from
the other side. Those never answered; these answered plenty and lost their destination, so the two
counts never overlap.

On the machine this was written on it was **40 of the 46 history rows**. That number is inflated by
53 sessions an optimiser had left behind that same morning, so here it is without them: still **28
of 37**, in two very specific flavours — worktrees already deleted (10 of 15) and temporary
directories (18 of 18, every single one).

**They are sunk, never hidden.** A directory missing today may be a worktree you recreate or a disk
you remount. The check is cached per path with a 30-second TTL, so a row revives on its own without
a restart.

Two guards, both because a missing directory is not always a missing directory: a session with no
recorded `cwd` is never marked (flagging a row over an absent field is the mistake this fixes), and
a live session is never marked, since its process is running inside that directory.

The `stat` deliberately does not live in `ordena()`, which is pure and runs four times a second: it
is resolved once when the row is built, which brings the amortised cost down to roughly one `stat`
per distinct path every 30 seconds.

**That reduces repetition, not blocking**, and the first cut of this entry claimed otherwise. The
reload runs synchronously in the loop that paints, so on a hung mount — where a `stat` never returns
— the list freezes: no repaint, no keys. Measured by injecting 1s of latency per `stat`: the first
pass takes 37.4s. Two numbers from that first cut were wrong too, and are corrected here: caching
per path saves 3 stats out of 40 on a cold start (40 rows are 36 distinct paths, not four), and what
it actually saves is the repeat between refreshes — 37 stats down to 1.

`--json` grows one field, `cwd_exists`, so a statusline can filter for what is genuinely resumable
instead of guessing from the project name.

Also: the Spanish README was missing the "sessions that never started" section that 1.12.0 added to
the English one. Both are in now.

## 1.13.1

**Same program as 1.13.0. Use this one: the file published under 1.13.0 is not the program.**

The release procedure extracted the file with `git show $SHA:sereno`. Under zsh that does not
extract anything: `$SHA:sereno` starts with `:s`, the substitution modifier, so the shell eats the
suffix and leaves the bare sha — the command becomes `git show <sha>`, which prints the commit
log. No error, exit 0. The asset published under v1.13.0 was that log, and GitHub releases are
immutable, so it could not be replaced.

The trap only springs when the path starts with `s` (`$V:foo` expands fine) and the file in this
repo is called `sereno`, so it is not something to remember. Releases now go through
`./release.sh <version>`, which uses braces and — more to the point — **refuses to publish** if
what it extracted does not start with the shebang or does not report the version being released,
and re-downloads the published asset to check it before saying OK.

Also: the Spanish README was missing the click-to-copy section that 1.13.0 added to the English
one.

## 1.13.0

**The values you were going to retype are one click away.**

Until now a single thing could be copied — the session id, with `y`. Everything else in the panel
you had to read and type again, and while sereno is running you cannot even drag-select it: mouse
reporting is on, so the terminal hands the drag to the app instead of selecting text.

Four values now carry a copy zone, marked with an **underline**: the project, the session id, and
the headers of *what you last said* and *what it last replied*. Click one and it goes to the
clipboard, over OSC 52 — no new binary, and it works over SSH.

Two of the four copy something you could **not** read on screen:

- **`project`** shows `docs-site · main` and copies `/Users/you/code/docs-site`. On the 40 history
  sessions of the machine this was written on, the full path was visible **0 times out of 40** — a
  click that copied what was painted would copy exactly what you had just finished reading.
- **the reply header** copies the whole reply, not the part that fitted. **15 of 37** replies were
  painted truncated.

The status line always says what actually landed on the clipboard, so a value that differs from its
label is never a silent surprise. Fields with nothing worth pasting — status, memory, context,
model, spend — are not underlined and do not react.

## 1.12.0

**Sessions that never got a reply stop competing for the top of the list.**

On the machine this was written on, **21 of the 39 history rows** were sessions that had never
received a single reply — and 16 of those were the same one, launched over and over and dying
instantly with `API Error: 401 · Please run /login`, zero tokens each. Because they had just died,
they were the *most recent* rows, so the default sort put them first. More than half of a list whose
whole job is "which one do I go back to" was sessions you cannot go back to.

They now sort below everything, in grey, and the header counts them separately: `3 resumable ·
1 never started` instead of `4 resumable`. Resuming one hands you its startup error and nothing else,
so counting it as resumable was a claim the tool could not keep.

The fact is deliberately narrow: **no reply anywhere in the session consumed a token**. `pico` is the
largest context the session ever held, so a zero can only come from zero real replies — and it is
only read once the transcript has been read whole, because a partial zero means "not known yet".

**A live session is never marked**, even at zero. One you just launched has not answered yet and is
exactly the row you want at the top; there was one 23 seconds old when this was measured.

## 1.11.0

**The context bar remembers where the session has been.**

Compacting resets the number but not the session, and the list was reading backwards because of
it. On the machine this was written on: a session on its 716th turn that had compacted twice drew
**11%** and looked like the freshest of the nine, while an untouched one on turn 246 drew **36%**
and looked heavier. It is the reading you use to decide whether a session takes another task, and
it was pointing the wrong way for four of nine rows.

The peak was already computed (1.8.0) and already survived compacting — it just lived in the panel,
one row at a time, which is no use for comparing nine of them. It is now in the bar: filled cells
in colour are what the session holds now, filled cells in grey are where it has been, hollow cells
it never reached. The percentage is untouched — a peak that inflated it would say the session is
full, which is the opposite of true.

Not drawn when the terminal has no colour: colour is the only thing separating "holds" from "held",
and without it a fuller bar just lies upwards. Not drawn either until the transcript has been read
whole — the peak is `0` until then, and `0` draws nothing.

## 1.10.0

**Three fixes to how a session is named and identified.**

**The id shown is the session's id.** The panel's `session` row, the key that copies, and the
`id` field in `--json` were all handing out `name` — which is the row's *key*: the tmux session
name (`cc-VanguardIA-90a6fb95`) for a live one, the uuid for one from history. Pasting the first
into `claude --resume` resumes nothing. The panel and the copy key now give the Claude session id,
and `--json` gained `session_id` alongside `id`, which keeps its meaning.

**A title is a line, not a prompt.** With no `/rename` and no `aiTitle`, the title came from the
first user message *in full* — 1,727 characters in the longest one here — so twelve of the forty
rows in this machine's history showed the same name, and in the panel they were the same row
repeated. It is now cut at the first sentence, capped at 60 characters, and rows that still match
get their short id appended. A sentence under twelve characters ("Done.", "Ok.") is skipped rather
than used as a name, and a dot inside `progress/x.md` or `1.9.0` does not cut.

**The demo has session ids now**, one per row and fixed, so the panel and the copy key show
something shaped like the real thing instead of falling back to the row name (`demo-infra-3`).
They are paths that do not exist and nothing opens them. The recording was redone on top of that
and it now walks through the sort by spend and the copy key as well.

**The list refreshes while you are typing.** The refresh only ran on the `getch` timeout, so a
`/rename` done in another window did not show up until you left the keyboard alone for 2.5 s.
The clock is now checked on every turn, same period. Same cost — the refresh was not extra work,
it was postponed work.

## 1.9.0

**The picker stopped reading transcripts in one bite.** Each turn of the loop spends a 25 ms budget
on whatever is missing, starting with the row you are looking at and staying on it until it is done.

That read is what pays for `--usage`, for the peak behind the context bar, and for sorting by spend.
Before, arriving at a large session cost a 120 ms stall, and entering the spend sort cost 389 ms in
one go. Across the 40 sessions here it is now 12 turns of at most 38 ms instead of 345 ms at once,
and 0.002 ms once everything is read.

What comes back half-read says so, and is not painted as a total: the panel shows "reading…" where
the figures go. The **peak** is the one exception and is used mid-read — it can only grow, so a
partial falls short but never overshoots. On the 89 MB transcript it crosses 200k on the very first
turn, so the context bar corrects itself right away rather than after the whole file.

Because of that, the context bar of **every row in the list** now benefits from the peak, not just
the row under the cursor. Sorting by spend takes no partials — that would sort by how much has been
read — so a half-read row waits at the bottom and moves up once, when it finishes.

## 1.8.0

**The context guard now has memory.** It already refused to put the ceiling below the context a
session was holding; it now also looks at the **peak** that session ever reached.

Compacting destroys the evidence: the window drops to 16k and a one-million session starts being
drawn against the standard one. Across the 524 transcripts on this machine that misreads **30**
of them (5.7%), always the same way — one read 171k against 200k, an 86% that says "compact now",
when it was 171k of a million, a 17%.

The peak is rebuilt from the transcript `sereno` already reads end to end for `--usage`: the
`usage` of every reply, and the `preTokens` of every compaction. That field is context and not a
running total — checked against the reply just before each boundary, median +0.4% and 165 of 169
within ±5%. As coverage it beats the alternative by a lot: `preTokens` appears in 107 of 524
transcripts, `cost-state` in 13.

It costs nothing extra — those two lines were already being parsed — and it is exposed as
`peak_context_tokens` in `--json --usage`. Reading the whole file is what it needs, so today the
panel and `--usage` have it and the plain list does not.

**What is still not possible: proving a session is *not* on the big window.** Beyond `cost-state`
there is no evidence in the transcript — across those 524 there is not one auto-compaction, which
would give away the threshold, and not a single `message.model` carrying the `[1m]` suffix.

## 1.7.0

**`s` has a fifth sort: by what each session has burned.** New input plus output, heaviest first,
alongside activity, context, project and memory.

It is not the context bar wearing another hat, and the case that separates them is compacting:
it empties the window and does not give back what was already spent. Measured across the 40
sessions on this machine, the three that had compacted ranked 2nd, 3rd and 4th by spend and 5th,
7th and 8th by context. Against activity there is no resemblance at all — rho 0.13.

It is the only one of the five that sorts on something it has to go and read, so it reads once,
on entering the mode: 94 ms for 8 live sessions, 389 ms for the 40 in history, then nothing. The
other four cost the same as before, and `ordena()` still touches no disk — a separate pass loads
what it will need.

Which figure to sort on barely matters: `out`, `input+output` and `cache read` correlate at
rho >= 0.98 across those transcripts and share the same top 5, so it takes the one that fits in a
line. Money is out for a different reason — `totalCostUSD` is only written on exit, so it was
present in 16 of 40 sessions and in none of the live ones.

`SERENO_SORT=spend` leaves it on, `-spend` inverts it.

## 1.6.0

**`--watch` has a third thing to tell you: a session that starts going in circles.** It already
reported one stopping and two starting to write in the same place; the counts behind `↻` were
being computed for every row anyway, so this cost nothing to add.

Like the other two it fires on the transition, not the state: twenty minutes of the same loop is
one line, not one per poll. A session already looping when you start `--watch` is baseline, not
news — and if it then *also* starts sweeping, that is new and gets said.

## 1.5.0

**"Which one is stuck?" is answered in the list now, not one row at a time.** The two counts the
panel already made — the same command failing three times, two searches in a row finding nothing
— are now computed for every row on screen and show up as `↻` next to the state, with the wording
in `--list` and a `stuck` enum in `--json`.

It reuses the objects the status pass already parsed, so it reads nothing extra: 5 ms of CPU
across sixteen real rows, against the 49 that pass already costs.

The warning column is shared with the clash marker, and the clash wins it. Not because it is
more common — because missing it can cost you overwritten work, while missing the other costs
minutes. Both are shown in full in the panel and in `--list`.

**It is expected to stay quiet**, and that is measured: across 10,375 real tool calls from the
twelve largest transcripts here, the loop warning fires on zero windows and the sweep on one.
The thresholds were not loosened to produce a livelier number.

## 1.4.0

**The context ceiling now listens to the session before the machine.** `SERENO_CTX_MAX` still
wins, but under it the order flipped: what *this* session says — the `cost-state` line, then a
`[1m]` suffix in the transcript — now overrules the `model` in your global `settings.json`,
which a session launched with a different `--model` does not obey anyway.

The point of the flip is the direction that was impossible before: a session the CLI recorded
**without** the suffix can now bring the ceiling back down to the standard window. On a machine
configured for the big window, a 200k session used to be drawn against a million — 6% where 30%
was due.

A guard sits above all of it: the ceiling can never end up below the context already seen, so
lowering it can never produce a bar over 100%. And the Haiku the CLI runs for titles is ignored
when reading `cost-state` — counting it would let a throwaway conversation talk the ceiling
down on its own.

## 1.3.0

**The panel shows the path, not just the last step.** Under the prompt and the reply there is
now a trail of the last tool calls — what each one was, how long it took, and how it ended:
done, error, a search that found nothing, or still running with the clock ticking. It comes out
of the same tail of the transcript the panel already reads, only for the row under the cursor.

Two things in that trail are called out, and both are counted rather than sensed: the same
command failing three times in a row, and two searches in a row that come back empty. Anything
else in between resets the count — two empty greps with an edit between them are work, not a
sweep. "Twenty minutes on one call" gets no line of its own: `status` already says that, and
the same fact twice is not a second opinion.

**The context ceiling now has one fact about the session itself.** It used to be worked out
from your global `settings.json` and from how much context had already been seen — nothing that
knew whether *this* session was launched on the one-million window. The `cost-state` line the
CLI writes when it closes keys its `modelUsage` by `claude-opus-5[1m]`, suffix included. It is
rare (15 of 517 transcripts here) and it only ever raises the ceiling, but when it is there it
settles the question, and it costs no extra reading.

**What a session has burned, with `--usage`.** The context bar says how full the window is right
now; it says nothing about the twelve hours already spent, because a session that compacted three
times reads 20%. The new flag adds tokens in and out, cache read, replies, compactions and the
minutes actually worked — to `--list`, to `--json`, and to the detail panel, which now also shows
the compaction count pinned to the context percentage that it explains.

Four figures and no total. Cache read is the same material being read again, and it runs a
hundred times larger than everything else put together; adding it to the input gives a number
that means nothing. The four parts stay apart.

It is off by default: the figure is spread across the whole transcript, so the file has to be
read end to end — 0.11 ms for the median one here, 223 ms for the largest on disk. Inside the
picker it is read for the row under the cursor and cached, so a refresh costs 2.6 ms.

**No price table.** `sereno` does not work out money. When the CLI leaves its own `cost-state`
line, that `totalCostUSD` is relayed as-is in `api_cost_usd`, and only in `--json --usage` — never
in the TUI, where on a subscription plan it would be money you did not pay.

Said plainly in the README because it changes how you read the number: subagent turns and the
CLI's own Haiku calls leave no line in the transcript, so a session that delegated a lot
under-reports.

## 1.2.1

**`--list` shows the four states, like the picker does.** It used to say only "running" or
"idle", collapsing four into two and losing the one that matters — a session stuck inside a
three-minute command, which by file date is indistinguishable from an abandoned one. It also
shows the context percentage now, and durations past two days read as `7d 2h` instead of
`170h 26m`.

**The Spanish interface is now written in Spanish.** Of 245 strings exactly one carried an
accent: the whole UI read like it had been typed on a keyboard without them. All of them are
fixed, and the i18n test now fails on any string containing a word that always takes an accent.

## 1.2.0

**The title is the last thing to be cut.** It was the first: at 70 columns the list showed
"Refactor pa…" next to a "checkout-api" with its whole branch, sacrificing the one thing that
tells two rows apart to keep a value that repeats on every line and appears in full in the panel
anyway. Now the title is served first and the support columns light up with what's left, in
order: context, project, memory.

**The state marker moved to the left, next to the title.** It used to be painted after the title,
which is padded out to the longest one on screen — so a short title left fifteen blanks between
the sentence and the dot telling you whether that session is alive.

**A column with nothing to say now takes no space.** No tmux means no memory column at all rather
than eight blanks per row; a Codex tab drops the context column the same way.

Resizing can no longer shrink a column. Widening the window used to *narrow* the title, because
the project column came back and took the room — found by the new test, not by looking.

### Fixed

- The memory needle is gone: it drew the same fact as the figure right next to it, with less
  precision. The figure stays, coloured by the same threshold.
- `fijas`, the width of everything that isn't the title, was a hardcoded 38 that was already off
  by one. It's now derived from the columns themselves, in a pure function with its own test.

## 1.1.0

**Context used, per session.** A bar in the list and the exact figures in the panel. The number
comes from the `usage` that every reply leaves in the transcript, so nothing is estimated and no
API is called.

The ceiling is the one thing Claude Code does not write down: a session running the 1M window
records itself as `claude-opus-5`, exactly like a 200k one. It is worked out from `SERENO_CTX_MAX`,
a `[1m]` suffix, your `settings.json`, and finally the context already observed. That last rule is
what keeps the bar from reading above 100%, and a test fails if it ever does.

**`--watch`** sits there and tells you the moment a session stops working and waits on you. The
transition, not the state: most sessions are idle most of the time. Desktop notification plus a
line on stdout. The first pass is silent, so starting it does not announce what you already knew.

**`--find "text"`** searches what was said, skipping tool output and the `CLAUDE.md` the CLI
pastes into every session, then opens the picker with only the matching sessions. Over 506
transcripts here, 287 files contained a given word and 25 had it in something anyone said.

**`--json`**, with a stable `state` enum, for statuslines and scripts. It carries no
conversation: no prompt, no reply. `--all` adds the resumable history.

**`--demo`**, the environment variable written short, for a first look with no sessions of your
own.

**Model** shown per session, from the same place as the context.

### Fixed

- The detail panel measured itself one column too wide, and curses wraps the overflow to the
  start of the next line. A stray character sat against the left edge, including in the README
  GIF, and looked like terminal dirt.
- The recovery branch after a crash was in Spanish regardless of language, and two of its
  messages named a command that is not the program. The i18n test now walks the AST and fails on
  any phrase printed without going through the translator.
- `--find` opened the picker on the live tab, which hid its own results behind "nothing matches".
- An unknown flag was swallowed: `sereno --jsonn` opened the picker, so a script asking for JSON
  got a TUI waiting for keys. It now says so, and suggests the closest real flag.
- A resumed session was read from the transcript it stopped writing to, so one that was working
  showed as idle, and sometimes twice. On resume the new transcript copies the old lines, and
  those lines keep their original `session_id` while the line's own `sessionId` is the new one:
  that pair is an exact link to the successor, so there is no guessing by timestamps.
- Selection shortcuts (`idle`, `detached`, `all`) work in both languages.
- With no sessions at all, the first screen says what to do next, and if `~/.claude/projects` is
  missing it says that too: the CLI writes that folder, so its absence is a diagnosis.

## 1.0.0

First public release. Picker with mouse support, four session states read from the transcript,
discovery without tmux, isolated demo mode, English and Spanish.
