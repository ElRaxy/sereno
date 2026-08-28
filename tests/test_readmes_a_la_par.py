#!/usr/bin/env python3
"""Los dos README cuentan lo mismo. Si uno crece, el otro tiene que crecer con el.

Existe por reincidencia, no por pulcritud. Ha pasado dos veces:

- la **1.13.0** anadio al ingles la seccion de copiar del panel y al espanol no. Lo arreglo
  la 1.13.1, con la version ya publicada.
- la **1.12.0** anadio "las que nunca arrancaron" solo al ingles, y ahi siguio **seis semanas**,
  hasta que se descubrio de casualidad escribiendo su gemela. En la misma pasada aparecio que al
  espanol le faltaba ademas el procedimiento de publicar entero.

Las dos veces se encontro mirando, no fallando. Un lector en espanol no se entera de que le falta
un trozo: lee lo que hay y se queda tan tranquilo.

**Que se compara y que no.** Los titulos estan traducidos, asi que compararlos seria comparar
idiomas. Lo que se compara es el ESQUELETO —la secuencia de niveles de encabezado, en orden— y los
EMOJIS de las secciones de primer nivel, que son los mismos en los dos y no dependen del idioma.
Una seccion anadida a uno solo desordena la secuencia y salta aqui.

Y ademas los comandos: lo que el README promete que puedes teclear tiene que estar en los dos, con
las mismas letras. Un `brew install` documentado solo en ingles es media instalacion.

Lo que este test NO puede ver, y conviene saberlo: que un parrafo se quede sin traducir dentro de
una seccion que si existe. Cubre el hueco de una seccion entera, que es la forma que tomo las dos
veces.
"""
import pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EN, ES = RAIZ / "README.md", RAIZ / "README.es.md"

# Lo que el README promete que puedes teclear. Si aparece en uno, tiene que estar en el otro.
COMANDOS = [
    "brew install elraxy/tap/sereno",
    "curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh",
    "./release.sh",
    "sereno --json",
    "sereno --watch",
    "sereno --usage",
    "sereno --find",
    "vhs demo.tape",
    "SERENO_DEMO=1",
]
EMOJI = re.compile(r"^[\U0001F300-\U0001FAFF☀-➿⬀-⯿]")


def esqueleto(texto):
    """(nivel, titulo) de cada encabezado ## y ###, en el orden en que salen."""
    fuera = []
    for linea in texto.splitlines():
        if linea.startswith("### "):
            fuera.append((3, linea[4:].strip()))
        elif linea.startswith("## "):
            fuera.append((2, linea[3:].strip()))
    return fuera


def comprueba(en_texto, es_texto, f):
    en, es = esqueleto(en_texto), esqueleto(es_texto)
    if len(en) != len(es):
        # El diagnostico importa mas que el fallo: sin decir DONDE se descuadra, arreglarlo
        # es releer dos ficheros de 40 KB a mano.
        for i, (a, b) in enumerate(zip(en, es)):
            if a[0] != b[0]:
                f(False, "se descuadran en la seccion %d: EN tiene '%s' (nivel %d) y ES '%s' "
                         "(nivel %d)" % (i + 1, a[1][:40], a[0], b[1][:40], b[0]))
                break
        else:
            sobra, falta = ("EN", "ES") if len(en) > len(es) else ("ES", "EN")
            cola = (en if len(en) > len(es) else es)[min(len(en), len(es)):]
            f(False, "%s tiene %d secciones y %s %d. A %s le falta el final: %r"
                     % (sobra, max(len(en), len(es)), falta, min(len(en), len(es)),
                        falta, [t for _, t in cola][:4]))
        return

    for i, (a, b) in enumerate(zip(en, es)):
        if a[0] != b[0]:
            f(False, "seccion %d: en EN es nivel %d ('%s') y en ES nivel %d ('%s')"
                     % (i + 1, a[0], a[1][:40], b[0], b[1][:40]))
        # Los emojis no se traducen: son la unica parte del titulo que se puede comparar.
        ea, eb = EMOJI.match(a[1]), EMOJI.match(b[1])
        if bool(ea) != bool(eb) or (ea and eb and ea.group() != eb.group()):
            f(False, "seccion %d: los emojis no casan — EN %r vs ES %r"
                     % (i + 1, a[1][:30], b[1][:30]))

    for cmd in COMANDOS:
        en_esta, es_esta = cmd in en_texto, cmd in es_texto
        if en_esta != es_esta:
            solo = "solo en ingles" if en_esta else "solo en espanol"
            f(False, "el comando %r esta %s" % (cmd, solo))


def main():
    fallos = []

    def f(cond, msg):
        if not cond:
            fallos.append(msg)

    en_texto, es_texto = EN.read_text(), ES.read_text()
    comprueba(en_texto, es_texto, f)

    # CONTROL POSITIVO. Sin esto, un test que no comparase nada pasaria igual: se le quita al
    # espanol una seccion entera y tiene que saltar, diciendo cual.
    mutado = es_texto.replace("### `--watch`", "")
    de_mentira = []
    comprueba(en_texto, mutado, lambda c, m: de_mentira.append(m) if not c else None)
    if not de_mentira:
        fallos.append("CONTROL POSITIVO: quitandole una seccion al espanol, el test no se entero")
    elif "--watch" not in " ".join(de_mentira) and "descuadran" not in " ".join(de_mentira):
        fallos.append("CONTROL POSITIVO: salto, pero sin decir donde: %r" % de_mentira[:2])

    # Y el otro control: un comando que solo este en uno.
    de_mentira2 = []
    comprueba(en_texto, es_texto.replace("brew install elraxy/tap/sereno", "brew install otra-cosa"),
              lambda c, m: de_mentira2.append(m) if not c else None)
    if not de_mentira2:
        fallos.append("CONTROL POSITIVO: un comando presente solo en ingles no salto")

    for m in fallos:
        print("FALLO:", m)
    print("%d fallo(s)" % len(fallos) if fallos
          else "ok: los dos README tienen el mismo esqueleto, los mismos emojis de seccion y "
               "los mismos comandos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
