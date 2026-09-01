#!/usr/bin/env python3
"""Los MB de una sesion son los suyos MAS los de sus descendientes, y contados una vez.

`rss_por_arbol` es la unica fuente del dato que ordena el modo `memory` y el que
contesta a "cual sobra": *hace cinco horas que no la tocas y ocupa 900 MB*. Un proceso
de Claude Code no es uno, es un arbol —el CLI, su tmux, los `node` que lanza—, asi que
mirar solo el RSS del pid raiz da una cifra que no se parece a la que ensena Activity
Monitor, y ordenar por ella acusa a la sesion equivocada.

Los tres fallos que se cazan aqui son de la casa:

  · **sumar de menos** — quedarse en el pid raiz, o perder un nieto;
  · **sumar de mas** — contar dos veces un pid que cuelga de dos sitios;
  · **colgarse** — `ps` puede devolver un ciclo padre-hijo (pasa con pids reciclados) y
    la recursion sin memoria de por donde ha pasado no vuelve. Un selector colgado al
    pulsar `m` es peor que un numero mal.

La salida de `ps` se inyecta a proposito en vez de mirar la maquina: un test que lee la
RAM de verdad no puede afirmar nada, porque no sabe cuanto DEBERIA salir.
"""
import pathlib
import sys
import types

RAIZ = pathlib.Path(__file__).resolve().parent.parent


class PsFalso:
    """Un `subprocess` que solo sabe devolver la salida de `ps` que se le da."""

    def __init__(self, salida):
        self.salida = salida
        self.veces = 0

    def run(self, *a, **k):
        self.veces += 1
        return types.SimpleNamespace(stdout=self.salida)


class PsRoto:
    def run(self, *a, **k):
        raise OSError("aqui no hay ps")


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    rss = ns["rss_por_arbol"]
    fallos = []

    def con(salida):
        ps = PsFalso(salida)
        ns["subprocess"] = ps
        return ps

    def caso(real, esperado, por_que):
        if real != esperado:
            fallos.append("%s: dio %r, se esperaba %r" % (por_que, real, esperado))

    # 100 -> 200 -> 300 (padre, hijo y nieto), 400 suelto, y una linea que no es de ps.
    # Los espacios de delante son los que pone `ps` de verdad al alinear la columna.
    con("  100     1  1024\n"
        "  200   100  2048\n"
        "  300   200  4096\n"
        "  400     1   512\n"
        "cabecera que no son tres numeros\n")

    # 1024 + 2048 + 4096 = 7168 KB = 7 MB. Sin los descendientes serian 1.
    caso(rss([100]), {100: 7.0}, "el arbol entero, no solo el pid raiz")
    caso(rss([200]), {200: 6.0}, "un nieto tambien cuenta")
    caso(rss([400]), {400: 0.5}, "un proceso sin hijos es su propio RSS")
    caso(rss([100, 200, 400]), {100: 7.0, 200: 6.0, 400: 0.5},
         "varios pids en la misma llamada")

    # Un mismo `ps` para todos: el coste de este dato es una llamada, no una por sesion.
    ps = con("100 1 1024\n200 100 2048\n300 100 4096\n")
    rss([100, 200, 300])
    if ps.veces != 1:
        fallos.append("se llama a `ps` %d veces para 3 pids: el coste crece con las "
                      "sesiones abiertas" % ps.veces)

    # Dos hermanos que cuelgan del mismo padre no se cuentan dos veces en el padre.
    caso(rss([100]), {100: 7.0}, "dos hijos del mismo padre suman una vez cada uno")

    # Un ciclo padre-hijo no puede colgar la interfaz. `ps` los produce con pids
    # reciclados, y sin la marca de visitados esto no vuelve nunca.
    con("100 200 10\n200 100 20\n")
    r = rss([100])
    caso(sorted(r), [100], "un ciclo devuelve algo en vez de colgarse")
    caso(round(r.get(100, 0) * 1024), 30, "un ciclo suma cada pid UNA vez (10 + 20 KB)")

    # Lo que no se puede contar no se inventa.
    con("100 1 1024\n")
    caso(rss([]), {}, "sin pids no hay nada que preguntar")
    ps = PsFalso("100 1 1024\n")
    ns["subprocess"] = ps
    rss([])
    if ps.veces:
        fallos.append("se llama a `ps` sin pids que mirar")
    con("100 1 1024\n")
    caso(rss(["abc"]), {}, "un pid que no es un numero se descarta, no revienta")
    caso(rss(["100"]), {"100": 1.0}, "un pid en texto vale igual que el entero")

    ns["subprocess"] = PsRoto()
    caso(rss([100]), {}, "sin `ps` en la maquina se devuelve vacio, no se revienta")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: los MB son los del arbol, contados una vez, y un ciclo no cuelga nada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
