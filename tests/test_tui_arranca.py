#!/usr/bin/env python3
"""Arranca el TUI de verdad en un pseudo-terminal y comprueba que pinta y sale.

Hasta ahora el CI solo probaba `--list`, que no toca curses: el selector —que es el
programa— no se probaba en ningun sitio. Un pty vale para las dos cosas que se rompen
al cambiar de sistema: que `curses` exista (en Windows no esta en la stdlib) y que el
terminal del CI admita colores.
"""
import os, pty, re, select, signal, sys, time, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ESPERADO = ("claude", "open", "writing", "ENTER")     # trozos de la interfaz en ingles


def main():
    entorno = dict(os.environ,
                   SERENO_DEMO="1", SERENO_LANG="en", TERM="xterm-256color",
                   SERENO_TMUX_SOCK="no-existe", LINES="30", COLUMNS="150")
    pid, fd = pty.fork()
    if pid == 0:                                   # hijo: ES el terminal
        os.execve(sys.executable, [sys.executable, str(RAIZ / "sereno")], entorno)

    # El pty no tiene tamano por defecto y curses pintaria 0x0. Se fija a mano.
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 150, 0, 0))
    except Exception:
        pass

    salida, fin = b"", time.time() + 25
    enviado_q = False
    while time.time() < fin:
        r, _, _ = select.select([fd], [], [], 0.5)
        if r:
            try:
                trozo = os.read(fd, 65536)
            except OSError:
                break
            if not trozo:
                break
            salida += trozo
        if not enviado_q and len(salida) > 2000:
            time.sleep(1.5)                        # deja que pinte antes de cerrar
            os.write(fd, b"q")
            enviado_q = True
        if enviado_q and os.waitpid(pid, os.WNOHANG)[0]:
            break
    else:
        os.kill(pid, signal.SIGKILL)

    texto = salida.decode("utf-8", "replace")
    limpio = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto)
    fallos = []
    if "Traceback" in texto:
        fallos.append("el TUI ha reventado:\n" + texto[texto.find("Traceback"):][:600])
    for t in ESPERADO:
        if t not in limpio:
            fallos.append(f"no aparece {t!r} en lo que pinto")
    if "\x1b[48;5;" not in texto:
        fallos.append("no ha pintado ningun fondo de 256 colores (la fila del cursor)")
    if not enviado_q:
        fallos.append("no llego a pintar lo suficiente como para probar a salir")

    for f in fallos:
        print("FALLO:", f)
    print(f"ok: el TUI arranca, pinta {len(limpio)} caracteres y sale con q"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
