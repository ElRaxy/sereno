#!/usr/bin/env python3
"""Lo que escribio el usuario es solo lo que escribio el usuario, y el `cwd` sale barato.

Dos lecturas de transcript que el resto del programa da por buenas.

**`_user_texts`** alimenta `--find` y el "donde se quedo" del panel. Un transcript
guarda con `"type": "user"` mucho mas que lo que una persona teclea: los resultados de
cada herramienta, los recordatorios que el sistema inyecta, los errores del propio CLI,
los comandos que se expanden solos y lo que escriben los subagentes en su rama. Si algo
de eso pasa el filtro, `--find "factura"` empieza a casar el contenido de los ficheros
que se leyeron —no lo que se dijo— y devuelve todas las sesiones del proyecto. Ese es el
fallo que este test persigue, y por eso la mitad de los casos son de lo que NO debe
salir: un filtro solo se puede probar con lo que tiene que dejar fuera.

**`_cwd_de_cabecera`** contesta "¿este historial pertenece a algo que todavia existe?"
leyendo la CABECERA y no la cola, porque son 880 ficheros. Su contrato es el tope: si
deja de acotarse, la respuesta sigue siendo correcta y el barrido pasa de 114 ms a leer
880 ficheros enteros. El coste es parte del contrato.
"""
import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def main():
    ns = {"__name__": "sereno_test"}
    exec(compile((RAIZ / "sereno").read_text(), "sereno", "exec"), ns)
    user_texts, cwd_cabecera = ns["_user_texts"], ns["_cwd_de_cabecera"]
    fallos = []
    tmp = pathlib.Path(tempfile.mkdtemp())

    # ── 1. lo que SI escribio el usuario ──────────────────────────────────────
    def dice(linea):
        return user_texts(json.dumps(linea))

    caso = [
        ({"type": "user", "message": {"role": "user", "content": "arregla el panel"}},
         ["arregla el panel"], "un mensaje en texto plano"),
        ({"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "arregla el panel"}]}},
         ["arregla el panel"], "un mensaje en bloques"),
        ({"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "primero esto"}, {"type": "text", "text": "y esto"}]}},
         ["primero esto y esto"], "dos bloques de texto son un mensaje"),
    ]
    for linea, esperado, por_que in caso:
        real = dice(linea)
        if real != esperado:
            fallos.append("%s: dio %r, se esperaba %r" % (por_que, real, esperado))

    # ── 2. lo que NO escribio el usuario, aunque lo parezca ───────────────────
    ruido = [
        ({"type": "user", "isSidechain": True,
          "message": {"content": "esto lo pidio un subagente"}},
         "lo que un subagente pide en su rama"),
        ({"type": "assistant", "message": {"content": "esto lo dijo Claude"}},
         "una respuesta del asistente"),
        ({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": "el contenido entero de una factura"}]}},
         "el resultado de una herramienta"),
        ({"type": "user", "message": {"content": "<command-name>/compact</command-name>"}},
         "un comando que se expande solo"),
        ({"type": "user", "message": {"content":
            "ojo con esto <system-reminder> que va dentro"}},
         "un recordatorio inyectado por el sistema"),
        ({"type": "user", "message": {"content": "tool_use_id: t1 y lo que sigue"}},
         "el acuse de una herramienta"),
        ({"type": "user", "message": {"content": "Request interrupted by user"}},
         "el aviso del CLI al interrumpir"),
        ({"type": "user", "message": {"content": "API Error: 500"}},
         "un error de la API"),
        ({"type": "user", "message": {"content": "Pre-Compact Rutina: resume"}},
         "el texto que inyecta un comando"),
        ({"type": "user", "message": {"content": {"raro": 1}}},
         "un `content` que no es ni texto ni lista"),
        ({"type": "user", "message": {"content": "   "}},
         "un mensaje en blanco"),
    ]
    for linea, por_que in ruido:
        real = dice(linea)
        if real:
            fallos.append("%s se cuela como escrito por el usuario: %r" % (por_que, real))

    # Una linea rota no puede tirar la lectura del resto del fichero.
    blob = ("no soy json\n"
            + json.dumps({"type": "user", "message": {"content": "sigo aqui"}}) + "\n")
    if user_texts(blob) != ["sigo aqui"]:
        fallos.append("una linea que no es json corta la lectura del trozo entero")

    # ── 3. el `cwd` de la cabecera ────────────────────────────────────────────
    def fichero(nombre, texto):
        p = tmp / nombre
        p.write_text(texto)
        return p

    dos = fichero("dos.jsonl", '{"type":"user","cwd":"/x/uno"}\n'
                               '{"type":"user","cwd":"/x/dos"}\n')
    if cwd_cabecera(dos) != "/x/uno":
        fallos.append("no vale la PRIMERA linea que trae `cwd`: dio %r"
                      % cwd_cabecera(dos))

    meta = fichero("meta.jsonl", 'ni json ni nada\n{"meta":{"cwd":"/x/meta"}}\n')
    if cwd_cabecera(meta) != "/x/meta":
        fallos.append("no se mira `meta.cwd`, que es donde lo pone parte de los "
                      "transcripts: dio %r" % cwd_cabecera(meta))

    hueco = fichero("hueco.jsonl", '{"cwd":""}\n{"cwd":"/x/vale"}\n')
    if cwd_cabecera(hueco) != "/x/vale":
        fallos.append("un `cwd` vacio se toma por bueno y tapa al de verdad")

    # El tope es el contrato: pasada esa linea NO se sigue leyendo, aunque el dato
    # este mas abajo. Si deja de acotarse este caso empieza a contestar `/x/tarde`.
    tarde = fichero("tarde.jsonl",
                    "\n".join('{"type":"relleno"}' for _ in range(60))
                    + '\n{"cwd":"/x/tarde"}\n')
    if cwd_cabecera(tarde) != "":
        fallos.append("se lee mas alla del tope de lineas: el barrido de 880 ficheros "
                      "pasa a leerlos enteros")
    if cwd_cabecera(tarde, tope=200) != "/x/tarde":
        fallos.append("con el tope subido a mano tampoco encuentra el dato: el tope no "
                      "es lo que decide, hay otra cosa cortando")

    if cwd_cabecera(tmp / "no-existe.jsonl") != "":
        fallos.append("un fichero que no existe deberia dar cadena vacia")

    if fallos:
        print("FALLA:")
        for f in fallos:
            print("  -", f)
        return 1
    print("ok: solo sale lo que se tecleo, y el `cwd` sale de la cabecera acotada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
