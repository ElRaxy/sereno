#!/usr/bin/env python3
"""El evento del raton llega desde el terminal hasta el programa, con curses de por medio.

`test_raton_sgr.py` prueba el parser con una ventana de mentira: dice que la secuencia
se entiende. Lo que no puede decir es que el programa la reciba — el parser se llama
desde el bucle de teclas pasandole `curses.ungetch` y la espera de la lista, y esos dos
argumentos no los ve ningun test unitario. Si un cambio de firma deja un sitio sin
actualizar, el parser sigue en verde y la interfaz revienta al primer click.

Asi que aqui se abre un pseudo-terminal de verdad, se le escribe la secuencia SGR tal y
como la escribiria el terminal —`ESC [ < boton ; columna ; fila M`— y se comprueba que
el programa la digiere y sigue vivo. Se prueban tambien las dos rutas que comparten el
ESC inicial, porque son la misma tecla: el click, y el ESC a secas que en la interfaz
no es un raton a medias sino una tecla con su significado.

Con `SERENO_DEBUG=1` porque sin el `pick_ui` se traga los errores de curses y sale en
silencio, que es indistinguible de "todo bien".
"""
import os
import pathlib
import pty
import re
import select
import signal
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent

CLICK = b"\x1b[<0;12;6M\x1b[<0;12;6m"      # pulsar y soltar en la columna 12, fila 6
RUEDA = b"\x1b[<64;12;6M"                  # rueda hacia arriba
ESC_SOLO = b"\x1b"                         # la tecla, no un raton


def main():
    fallos = []
    for nombre, teclas in (("un click", CLICK), ("la rueda", RUEDA),
                           ("un ESC suelto", ESC_SOLO),
                           ("basura detras del ESC", b"\x1b[<0;a;b M")):
        fallos += prueba(nombre, teclas)
    for f in fallos:
        print("FALLO:", f)
    print("ok: el raton llega del terminal al programa y no lo tumba"
          if not fallos else "%d fallo(s)" % len(fallos))
    return 1 if fallos else 0


def prueba(nombre, teclas):
    entorno = dict(os.environ,
                   SERENO_DEMO="1", SERENO_LANG="en", TERM="xterm-256color",
                   SERENO_DEBUG="1", SERENO_TMUX_SOCK="no-existe",
                   LINES="30", COLUMNS="150")
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(sys.executable, [sys.executable, str(RAIZ / "sereno")], entorno)
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 150, 0, 0))
    except Exception:
        pass

    salida, estado = b"", None
    arranque, fin = time.time(), time.time() + 30
    mandado, cerrado = False, False
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
        ahora = time.time() - arranque
        if not mandado and ahora > 4:
            os.write(fd, teclas)             # el terminal habla: aqui hay un raton
            mandado = True
        if mandado and not cerrado and ahora > 6:
            os.write(fd, b"q")               # y despues, la tecla de salir
            cerrado = True
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
    vivo = estado is None
    if vivo:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)

    texto = salida.decode("utf-8", "replace")
    fallos = []
    if "Traceback" in texto:
        fallos.append("%s: el programa revento\n%s"
                      % (nombre, texto[texto.find("Traceback"):][:900]))
    if not re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto).strip():
        fallos.append("%s: no llego a pintar nada" % nombre)
    # Que salga por su propio pie es la mitad del veredicto: si el parser se traga la
    # `q` creyendo que era parte de un evento, esto se queda colgado hasta el SIGKILL.
    if vivo:
        fallos.append("%s: sigue vivo tras pedirle salir — alguien se comio la tecla"
                      % nombre)
    return fallos


if __name__ == "__main__":
    sys.exit(main())
