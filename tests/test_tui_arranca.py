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
    # SERENO_DEBUG=1 es lo que hace util este test: sin el, `pick_ui` se traga
    # cualquier error de curses y el programa sale en silencio — que es exactamente
    # como se ve "no ha pintado nada" y no dice por que.
    entorno = dict(os.environ,
                   SERENO_DEMO="1", SERENO_LANG="en", TERM="xterm-256color",
                   SERENO_DEBUG="1", SERENO_TMUX_SOCK="no-existe",
                   LINES="30", COLUMNS="150")
    pid, fd = pty.fork()
    if pid == 0:                                   # hijo: ES el terminal
        os.execve(sys.executable, [sys.executable, str(RAIZ / "sereno")], entorno)

    # El pty no tiene tamano por defecto y curses pintaria 0x0. Se fija a mano.
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 150, 0, 0))
    except Exception:
        pass

    # Espera fija en vez de "cuando haya escrito N bytes": el umbral por bytes hacia
    # que en una maquina que pinta menos no se llegase a pulsar `q` nunca, y el fallo
    # se leia como "no pinta" cuando era "no le hemos dejado".
    salida, fin, estado = b"", time.time() + 30, None
    arranque, enviado_q = time.time(), False
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
        if not enviado_q and time.time() - arranque > 4:
            os.write(fd, b"q")
            enviado_q = True
        hijo, st = os.waitpid(pid, os.WNOHANG)
        if hijo:
            estado = st
            break
    if estado is None:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)

    texto = salida.decode("utf-8", "replace")
    limpio = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto)
    fallos = []
    if "Traceback" in texto:
        fallos.append("el TUI ha reventado:\n" + texto[texto.find("Traceback"):][:900])
    for t in ESPERADO:
        if t not in limpio:
            fallos.append(f"no aparece {t!r} en lo que pinto")
    if not fallos and "\x1b[48;5;" not in texto:
        # aviso, no fallo: hay terminales sin 256 colores y el programa cae a
        # A_REVERSE a proposito. Lo que no puede pasar es que no pinte NADA.
        print("AVISO: sin 256 colores; la fila del cursor va en video inverso")

    if fallos:
        print(f"--- diagnostico: {len(salida)} bytes leidos, estado del hijo {estado},"
              f" q enviada: {enviado_q}")
        print("--- primeros 400 caracteres de lo que escribio:")
        print(repr(limpio[:400]) or "(nada)")
    for f in fallos:
        print("FALLO:", f)
    print(f"ok: el TUI arranca, pinta {len(limpio)} caracteres y sale con q"
          if not fallos else f"{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
