<div align="center">

<img src="docs/hero.webp" alt="Un sereno levanta el farol ante un muro de ventanas de terminal, cuatro encendidas" width="880">

# sereno

### Nueve sesiones de agente abiertas. ¿Cuál está atascada?

**Una interfaz de terminal que te dice qué está haciendo _de verdad_ cada sesión, no solo que existe.**

Un fichero de Python · cero dependencias · Claude Code, Codex, Gemini, Antigravity

<br>

[![CI](https://img.shields.io/github/actions/workflow/status/ElRaxy/sereno/ci.yml?style=flat-square&label=ci&labelColor=16161e&color=5fff5f)](https://github.com/ElRaxy/sereno/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8+-00afff?style=flat-square&labelColor=16161e)](https://www.python.org/)
[![Dependencias](https://img.shields.io/badge/dependencias-ninguna-5fff5f?style=flat-square&labelColor=16161e)](#-instalación)
[![Instalación](https://img.shields.io/badge/instalar-un%20fichero-ffaf00?style=flat-square&labelColor=16161e)](#-instalación)
[![Licencia](https://img.shields.io/badge/licencia-MIT-af87ff?style=flat-square&labelColor=16161e)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ElRaxy/sereno?style=flat-square&labelColor=16161e&color=ffaf00)](https://github.com/ElRaxy/sereno/stargazers)

[English](README.md) · **Español**

</div>

---

<div align="center">
  <img src="docs/demo.gif" alt="sereno funcionando sobre sesiones inventadas" width="880">
</div>

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
sereno
```

---

## Contenido

- [Por qué](#-por-qué)
- [Los cuatro estados](#-los-cuatro-estados-y-por-qué-cuestan)
- [Leer una fila](#-leer-una-fila)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [De dónde salen los datos](#-de-dónde-salen-los-datos)
- [Comparativa](#-comparativa)
- [Configuración](#-configuración)
- [Sobre el código](#-sobre-el-código)
- [Contribuir](#-contribuir)
- [Créditos](#-créditos)

---

## 🌙 Por qué

Un **sereno** era el vigilante nocturno que recorría las calles españolas hasta los años
setenta, con su farol y las llaves de todos los portales de su ronda. Tú dormías; él pasaba a
mirar. Si algo iba mal, era el que se enteraba.

Ahora mismo tienes nueve pestañas abiertas. Dos agentes están a media tarea. Uno lleva once
minutos bloqueado en su propio `pytest`. Otro terminó hace veinte minutos y te está esperando.
Y otro se está comiendo 900 MB por un encargo que abandonaste antes de comer.

Desde fuera las nueve son idénticas. Averiguar cuál es cuál significa entrar en las nueve, leer
la última pantalla de cada una y perder el hilo de lo que estabas haciendo.

**Un gestor de sesiones te dice que las nueve existen. `sereno` te dice qué están haciendo.**

---

## 🔎 Los cuatro estados, y por qué cuestan

|  | qué significa | por qué no sale de un `ps` |
|:--|:--|:--|
| 🟢 **escribiendo** | está redactando la respuesta ahora mismo | — |
| 🟠 **en un comando** | lanzó una herramienta y el resultado no ha vuelto | **este es el que importa** |
| ⚪ **te espera a ti** | terminó y nadie ha contestado | igualito que "se ha caído" |
| ⚫ **parada, te espera a ti** | lo mismo, pero hace rato | estas son las que conviene cerrar |

Un agente metido en un `Bash` de tres minutos **no escribe nada en su transcript**, así que por
fecha de modificación parece parado — y parado parece abandonado. `sereno` lee la cola del
transcript y comprueba si el último `tool_use` llegó a recibir su `tool_result`.

Esa comprobación es toda la diferencia entre *«se ha colgado»* y *«está trabajando, no la toques»*.

> Cada estado lo compone **el código** a partir de hechos tipados leídos del transcript. A ningún
> modelo se le pide que resuma nada, así que nada puede decirte con aplomo que una sesión va bien
> cuando no va.

---

## 📖 Leer una fila

```
 ▎ Refactor payment webhooks   ◐ checkout-api ⎇feat/webhooks   now   ▰▰▰▰▱  512 MB
 │            │                │       │           │            │       │       │
 │            │                │       │           │            │       │       └ memoria
 │            │                │       │           │            │       └ cuota sobre la mayor
 │            │                │       │           │            └ tiempo parada, con color
 │            │                │       │           └ rama de git
 │            │                │       └ proyecto
 │            │                └ ◐ en un comando · ● escribiendo · nada = te espera
 │            └ título — el que Claude se puso, o tu /rename
 └ cursor. Se pone amarillo cuando la fila está marcada.
```

El panel de la derecha enseña **el último prompt y la última respuesta** de esa sesión, para
que puedas decidir si volver a ella sin abrirla.

---

## ⚡ Instalación

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
```

O te llevas el fichero, que es un script y la librería estándar:

```bash
curl -fsSLo ~/.local/bin/sereno https://raw.githubusercontent.com/ElRaxy/sereno/main/sereno
chmod +x ~/.local/bin/sereno
```

Python 3.8 o más nuevo. Esa es la lista completa de dependencias. Ni venv, ni lock file, ni
cadena de suministro. Lo mandas por `scp` a un servidor y funciona allí también.

---

## 🕹 Uso

```bash
sereno            # el selector
sereno --list     # lista y ya, no toca nada
sereno --help
```

| tecla | |
|:--|:--|
| `↑` `↓` / `j` `k` | moverse |
| `ENTER` | abrirla |
| `SPACE` | marcar · `v` un rango · `a` todas · `i` invertir · `d` las paradas más de una hora |
| `x` | cerrar las marcadas — pregunta antes, y avisa si alguna está a media tarea |
| `/` | filtrar por título mientras escribes |
| `TAB` | Claude · historial reanudable · Codex · Gemini · todas |
| `?` | el resto |

**El ratón funciona.** Click para seleccionar, doble click para abrir, click derecho (o en la
barra del borde izquierdo) para marcar, rueda para desplazar. Las pestañas de arriba y los
botones de abajo son botones de verdad.

Ninguna acción te echa del selector. Cerrar cuatro sesiones y abrir una quinta es una visita,
no cinco.

### 🎭 Probarlo sin tocar tus datos

```bash
SERENO_DEMO=1 sereno
```

Sesiones inventadas, proyectos inventados. **Úsalo para cualquier cosa que publiques.** El panel
de detalle enseña prompts y respuestas reales, así que una captura de un gestor de sesiones es
una forma sorprendentemente eficaz de publicar el trabajo de un cliente — la primera toma del GIF
de arriba salió con nombres de clientes dentro, y por eso existen el modo demo y un test que lo
vigila.

### 🔔 Una línea al abrir la terminal

```bash
# ~/.zshrc o ~/.bashrc
sereno --hook
```

Imprime una línea cuando hay algo corriendo, y absolutamente nada cuando no.

---

## 💾 De dónde salen los datos

De `~/.claude/projects`, que lo escribe Claude Code por su cuenta. Sin configuración, sin
demonio, sin telemetría, sin nada que montar: lo instalas y ya conoce todas las sesiones que has
abierto en tu vida.

Las de Codex, Gemini y Antigravity salen de sus propias carpetas de historial y se abren con el
`resume` de su CLI. Son ficheros en disco, no procesos vivos, así que `sereno` se niega a
«cerrarlas» en vez de fingir que ha hecho algo.

<details>
<summary><strong>Opcional: tmux y Warp</strong></summary>

<br>

Si tus sesiones corren dentro de tmux, además tienes memoria en vivo por sesión, cuáles ya tienen
una terminal enganchada, y poder matarlas de verdad. En macOS con Warp, `ENTER` abre la sesión en
una **ventana nueva** en vez de quedarse con la que estás mirando.

Los dos son opcionales. Sin ellos funciona todo menos la columna de memoria, y `ENTER` hace `exec`
sobre la terminal actual.

</details>

---

## 📊 Comparativa

Casi todo lo que hay en este hueco **lanza y orquesta** sesiones. Esto las **mira**, y ese es todo
el diseño.

|  | sereno | gestores de tmux | apps de escritorio |
|:--|:--:|:--:|:--:|
| Estado en vivo por sesión | ✅ | ❌ | 🟡 |
| Último prompt y última respuesta | ✅ | ❌ | 🟡 |
| Funciona sin montar nada | ✅ | necesita su lanzador | hay que instalarla |
| Codex y Gemini también | ✅ | solo Claude | solo Claude |
| Va por SSH | ✅ | ✅ | ❌ |
| Dependencias | **ninguna** | tmux | Electron / Swift |

Si lo que quieres es *lanzar* una flota de agentes, usa uno de esos — y luego usa este para ver
qué está haciendo la flota.

---

## 🔧 Configuración

| Variable | |
|:--|:--|
| `SERENO_LANG` | `en` o `es`. Por defecto, tu locale (en macOS, `AppleLocale`) |
| `SERENO_DEMO` | `1` para sesiones falsas |
| `SERENO_TMUX_SOCK` | socket de tmux que se lee. Por defecto `claude-code` |
| `SERENO_REGISTRY` | dónde vive el registro opcional del lanzador |

---

## 🧠 Sobre el código

Un fichero, ~2.000 líneas, solo librería estándar.

Los comentarios están **en castellano** a propósito. Explican *por qué* está cada cosa como está,
casi siempre nombrando el incidente que lo provocó, y traducirlos lo aplanaría a prosa genérica.
La interfaz sí es bilingüe.

<details>
<summary><strong>Tres decisiones que merece la pena conocer</strong></summary>

<br>

**La fila del cursor cambia de fondo, no de vídeo.** `A_REVERSE` pinta la fila entera de blanco y
tira a la basura el color de cada columna —el estado, el proyecto, la memoria— justo en la única
fila que estás mirando.

**Los eventos de ratón se parsean a mano.** El ncurses que trae macOS es el 6.0 de **2015** y solo
habla el protocolo x11 de 1988, donde la columna viaja en un byte y muere en la 223. En una
ventana ancha, los clicks del panel derecho aterrizan en otro sitio. `sereno` pide SGR y lo parsea
él, sin dejar de aceptar `KEY_MOUSE` de un ncurses moderno.

**Los `agent-*.jsonl` no son sesiones.** Claude Code deja los transcripts de sus subagentes al
lado de los reales: 213 contra 1.035 en la máquina donde se construyó esto. No se reanudan y no
tienen título propio, así que la lista salía enterrada bajo veinte copias del mismo prompt de
subagente hasta que se filtraron.

</details>

---

## 🤝 Contribuir

Issues y pull requests bienvenidos, en castellano o en inglés. Dos cosas que el CI comprueba por
ti, y las dos existen porque fallan **en silencio**:

- **`tests/test_demo_aislado.py`** — el modo demo no puede devolver ni una fila que venga del disco
  de verdad. Planta un canario en un `HOME` de mentira y recorre todas las funciones que leen datos.
- **`tests/test_i18n.py`** — cada cadena que pasa por `_()` tiene traducción con los mismos
  `{huecos}`. El inglés es la clave, así que una traducción que falta no revienta: simplemente
  aparece en el idioma equivocado.

El GIF se regenera con `vhs demo.tape` ([vhs](https://github.com/charmbracelet/vhs)) — y mirando
los fotogramas antes de commitearlos.

---

## 👤 Créditos

Hecho por **[Alex Micó](https://github.com/ElRaxy)**, que tenía nueve pestañas de Claude Code
abiertas y ni idea de a cuál volver.

Escrito con **Claude Code (Opus 5)** de coautor — incluida la tarde que se fue en descubrir que
macOS trae un ncurses de 2015. Apropiado, para una herramienta cuyo trabajo es vigilar sesiones de
Claude Code.

Si te ahorra una ronda de clicks por nueve pestañas, una ⭐ ayuda a que lo encuentre más gente.

---

## 📄 Licencia

MIT — mira [LICENSE](LICENSE). Haz con esto lo que quieras.
