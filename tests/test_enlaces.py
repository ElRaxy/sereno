#!/usr/bin/env python3
"""Ningun enlace interno de la documentacion apunta a una seccion que no existe.

Un ancla rota no rompe nada al ejecutar: el README se renderiza igual de bien y el fallo solo
aparece cuando alguien hace clic, que es justo el visitante que acaba de llegar. Este caso existe
porque el README ingles enlazaba a `#reading-without-blocking` durante varias versiones y esa
seccion solo estaba escrita en el castellano: el enlace no llevaba a ninguna parte y, de paso,
al lector ingles le faltaban tres parrafos. `test_readmes_a_la_par` no lo vio porque compara los
titulos de nivel 2 y la seccion ausente era de nivel 4.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ("README.md", "README.es.md", "CONTRIBUTING.md", "SECURITY.md")


def slug(titulo):
    """Reproduce github-slugger: minusculas, fuera todo lo que no sea \\w, espacio o guion,
    y espacios a guiones. NO recorta los extremos, por eso `## 🌙 Why` da `-why` y no `why`."""
    t = re.sub(r"`([^`]*)`", r"\1", titulo)
    t = re.sub(r"\*\*?([^*]*)\*\*?", r"\1", t)
    return re.sub(r"[^\w\s-]", "", t.lower(), flags=re.U).replace(" ", "-")


def anclas(texto):
    salida = set()
    for linea in texto.splitlines():
        m = re.match(r"^\s*#{1,6}\s+(.*)$", linea)
        if m:
            salida.add(slug(m.group(1).strip()))
    return salida


def main():
    # Control positivo: si el slug se rompe, el test dejaria de ver los enlaces malos y
    # pasaria siempre. Estos dos casos vienen de titulos reales del README.
    if slug("🌙 Why") != "-why":
        print("FALLA: el slug no reproduce el de GitHub para un titulo con emoji: "
              "%r, se esperaba '-why'" % slug("🌙 Why"))
        return 1
    if slug("The four states, and why they're hard") != "the-four-states-and-why-theyre-hard":
        print("FALLA: el slug no reproduce el de GitHub con comas y apostrofes")
        return 1

    fallos = []
    for nombre in DOCS:
        ruta = os.path.join(RAIZ, nombre)
        if not os.path.exists(ruta):
            fallos.append("%s no existe y la documentacion lo da por hecho" % nombre)
            continue
        texto = open(ruta, encoding="utf-8").read()
        propias = anclas(texto)
        for etiqueta, destino in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", texto):
            d = destino.strip()
            if d.startswith("#"):
                if d[1:] not in propias:
                    fallos.append("%s: [%s](%s) no lleva a ninguna seccion del propio fichero"
                                  % (nombre, etiqueta, d))
            elif not d.startswith(("http://", "https://", "mailto:")):
                fichero = d.split("#")[0]
                destino_abs = os.path.join(RAIZ, fichero)
                if fichero and not os.path.exists(destino_abs):
                    fallos.append("%s: [%s](%s) apunta a un fichero que no existe"
                                  % (nombre, etiqueta, d))
                elif "#" in d and fichero.endswith(".md") and os.path.exists(destino_abs):
                    otro = anclas(open(destino_abs, encoding="utf-8").read())
                    if d.split("#", 1)[1] not in otro:
                        fallos.append("%s: [%s](%s) apunta a una seccion que %s no tiene"
                                      % (nombre, etiqueta, d, fichero))

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: ningun enlace interno de la documentacion apunta al vacio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
