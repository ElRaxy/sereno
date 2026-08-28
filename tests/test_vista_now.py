#!/usr/bin/env python3
"""La pantalla de `n` se abre, pinta y se cierra, tambien en una ventana pequena.

Un overlay de curses es donde aparecen los fallos que no se ven leyendo el codigo: un
`addnstr` una columna larga no da error, escribe el sobrante al principio de la fila
SIGUIENTE y parece suciedad del terminal. Y con la ventana pequena el recuadro puede
salirse de la pantalla, que ahi si aborta el programa entero.

Corre el TUI de verdad en un pseudo-terminal, con `SERENO_DEMO=1`: sesiones inventadas,
ningun transcript real abierto.
"""
import os, pty, re, select, signal, sys, time, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
# Tres, no siete: la rejilla de tamanos la barre `geometria()` en milisegundos y sin
# curses. Lo que hace falta en un pty de verdad son los extremos —donde el recuadro
# roza los bordes— y uno normal. Cada arranque cuesta ~10 s y esto corre en seis
# combinaciones de CI.
TAMANOS = ((30, 150), (14, 60), (12, 40))
TITULO = "What they are all running"


def prueba(filas, cols):
    entorno = dict(os.environ, SERENO_DEMO="1", SERENO_LANG="en",
                   TERM="xterm-256color", SERENO_DEBUG="1",
                   SERENO_TMUX_SOCK="no-existe",
                   LINES=str(filas), COLUMNS=str(cols))
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(sys.executable, [sys.executable, str(RAIZ / "sereno")], entorno)
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", filas, cols, 0, 0))
    except Exception:
        pass

    # `n` abre la pantalla, cualquier tecla la cierra, `q` sale. Por tiempo y no por
    # bytes: en una maquina lenta el umbral por bytes no llega y el fallo se lee como
    # "no pinta" cuando era "no le hemos dejado".
    guion = [(3, b"n"), (5.5, b" "), (7, b"q")]
    salida, arranque, fin, estado = b"", time.time(), time.time() + 30, None
    while time.time() < fin:
        r, _, _ = select.select([fd], [], [], 0.4)
        if r:
            try:
                trozo = os.read(fd, 65536)
            except OSError:
                break
            if not trozo:
                break
            salida += trozo
        pasado = time.time() - arranque
        while guion and pasado > guion[0][0]:
            os.write(fd, guion.pop(0)[1])
        hijo, st = os.waitpid(pid, os.WNOHANG)
        if hijo:
            estado = st
            break
    if estado is None:
        for _ in range(20):
            hijo, st = os.waitpid(pid, os.WNOHANG)
            if hijo:
                estado = st
                break
            time.sleep(0.1)
    if estado is None:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)

    texto = salida.decode("utf-8", "replace")
    limpio = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto)
    v, fallos = f"[{cols}x{filas}]", []
    if "Traceback" in texto:
        fallos.append(f"{v} el TUI ha reventado al abrir la pantalla:\n"
                      + texto[texto.find("Traceback"):][:900])
    # El titulo se recorta con la ventana, asi que se exige lo que quepa de el.
    cabe = TITULO[:max(0, min(len(TITULO), cols - 10))]
    if cabe and cabe not in limpio:
        fallos.append(f"{v} la pantalla no llega a pintarse: no sale {cabe!r}")
    if estado is None or (os.WIFEXITED(estado) and os.WEXITSTATUS(estado) not in (0, 1)):
        fallos.append(f"{v} no sale limpio: estado {estado}")
    return fallos


def geometria():
    """El recuadro cabe en la pantalla, en TODOS los tamanos.

    Esto no se puede comprobar mirando la pantalla: medido el 2026-08-28 en un pty de 40
    columnas, ncurses acepta un `newwin` mas ancho que el terminal y un `addnstr` que se
    sale, sin dar error ninguno de los dos. El recuadro simplemente pierde el borde
    derecho. Por eso la geometria vive en una funcion pura y se prueba aqui.
    """
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    caja_now, fallos = ns["caja_now"], []
    for h in (3, 4, 5, 8, 12, 14, 24, 30, 60):
        for w in (20, 30, 40, 60, 92, 112, 150, 400):
            for n in (0, 1, 6, 21, 200):
                alto, ancho, y, x, caben = caja_now(h, w, n)
                donde = f"h={h} w={w} n={n}"
                if ancho > w or x + ancho > w:
                    fallos.append(f"{donde}: el recuadro se sale por la derecha "
                                  f"(x={x} ancho={ancho})")
                if alto > h or y + alto > h:
                    fallos.append(f"{donde}: el recuadro se sale por abajo "
                                  f"(y={y} alto={alto})")
                # Las lineas se pintan desde la fila 3; la ultima no puede caer
                # sobre el borde de abajo.
                if caben and 3 + caben > alto - 1:
                    fallos.append(f"{donde}: {caben} lineas no caben en un recuadro "
                                  f"de {alto} filas: la ultima pisa el borde")
                if min(alto, ancho) < 3:
                    fallos.append(f"{donde}: recuadro degenerado {ancho}x{alto}")
    # Control: con la pantalla enorme el recuadro NO crece sin freno, que es lo que
    # hace ilegible una lista de nueve sesiones en un monitor de 400 columnas.
    if caja_now(60, 400, 200)[1] > 110:
        fallos.append("en una pantalla enorme el recuadro crece sin tope")
    return fallos


def main():
    fallos = geometria()
    for filas, cols in TAMANOS:
        fallos += prueba(filas, cols)
    for f in fallos:
        print("FALLO:", f)
    print(f"ok: la pantalla de `n` abre y cierra en {len(TAMANOS)} tamanos"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
