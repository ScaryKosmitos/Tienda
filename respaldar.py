"""
Crea una copia de seguridad de inventario.db.

Uso:
    python respaldar.py                 -> guarda el respaldo en la carpeta "respaldos"
    python respaldar.py /ruta/carpeta   -> guarda el respaldo en otra carpeta (ej: una USB)

Usa la función de respaldo de SQLite, así que la copia sale bien aunque la
aplicación esté abierta. En la carpeta "respaldos" se conservan solo los
últimos MAX_RESPALDOS; los más antiguos se borran solos.

La aplicación también llama a respaldo_automatico() al abrirse, que crea
como máximo un respaldo por día, y copiar_a_nube(), que copia el respaldo
más reciente a la carpeta de Google Drive (u otra) elegida en la tienda.
"""
import os
import shutil
import sqlite3
import string
import sys
from datetime import datetime

import base_datos as db
import configuracion

MAX_RESPALDOS = 30

# Dentro de la carpeta de la nube, los respaldos van en esta subcarpeta
SUBCARPETA_NUBE = "Respaldos Tienda"


def crear_respaldo(carpeta_destino):
    """Copia la base de datos a carpeta_destino y retorna la ruta del respaldo."""
    ruta_origen = db._ruta_db()
    if not os.path.exists(ruta_origen):
        raise FileNotFoundError(f"No se encontró la base de datos en {ruta_origen}")

    os.makedirs(carpeta_destino, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_respaldo = os.path.join(carpeta_destino, f"inventario_{fecha}.db")

    origen = sqlite3.connect(ruta_origen)
    destino = sqlite3.connect(ruta_respaldo)
    try:
        origen.backup(destino)
        resultado = destino.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        destino.close()
        origen.close()

    if resultado != "ok":
        os.remove(ruta_respaldo)
        raise RuntimeError(f"El respaldo salió dañado ({resultado}); no se guardó.")
    return ruta_respaldo


def _respaldos_en(carpeta):
    """Nombres de los respaldos de una carpeta, del más antiguo al más reciente."""
    if not os.path.isdir(carpeta):
        return []
    return sorted(f for f in os.listdir(carpeta) if f.startswith("inventario_") and f.endswith(".db"))


def borrar_respaldos_viejos(carpeta):
    """Deja solo los MAX_RESPALDOS más recientes."""
    respaldos = _respaldos_en(carpeta)
    for viejo in respaldos[:-MAX_RESPALDOS]:
        os.remove(os.path.join(carpeta, viejo))


def carpeta_respaldos():
    """Carpeta 'respaldos' junto a inventario.db."""
    return os.path.join(os.path.dirname(db._ruta_db()), "respaldos")


def respaldo_automatico():
    """
    Se llama al abrir la aplicación. Crea como máximo un respaldo por día, para
    que abrir la tienda muchas veces no desplace los respaldos de días anteriores.
    Retorna la ruta del respaldo creado, o None si hoy ya había uno.
    """
    carpeta = carpeta_respaldos()
    hoy = datetime.now().strftime("%Y-%m-%d")
    if os.path.isdir(carpeta) and any(f.startswith(f"inventario_{hoy}") for f in os.listdir(carpeta)):
        return None

    ruta = crear_respaldo(carpeta)
    borrar_respaldos_viejos(carpeta)
    return ruta


# --- RESPALDO EN LA NUBE (Google Drive para escritorio, OneDrive, una USB...) ---

def carpeta_nube():
    """Carpeta de la nube elegida en la tienda, o None si no se ha elegido."""
    carpeta = configuracion.leer().get("carpeta_nube")
    return carpeta if isinstance(carpeta, str) and carpeta else None


def poner_carpeta_nube(carpeta):
    """Guarda la carpeta de la nube (None = dejar de copiar los respaldos a la nube)."""
    if carpeta:
        configuracion.guardar(carpeta_nube=carpeta)
    else:
        configuracion.quitar("carpeta_nube")


def buscar_google_drive():
    """
    Busca la carpeta 'Mi unidad' de Google Drive para escritorio. En Windows
    suele ser una unidad aparte (G:\\Mi unidad). Retorna la ruta o None.
    """
    nombres = ("Mi unidad", "My Drive")
    candidatas = []
    if sys.platform == "win32":
        candidatas += [f"{letra}:\\{nombre}" for letra in string.ascii_uppercase[3:] for nombre in nombres]
    inicio = os.path.expanduser("~")
    candidatas += [os.path.join(inicio, "Google Drive", nombre) for nombre in nombres]
    candidatas += [os.path.join(inicio, nombre) for nombre in nombres + ("Google Drive",)]
    return next((c for c in candidatas if os.path.isdir(c)), None)


def es_carpeta_de_la_tienda(carpeta):
    """True si 'carpeta' es la de la tienda o está dentro de ella (no protege nada si el computador se daña)."""
    tienda = os.path.normcase(os.path.abspath(os.path.dirname(db._ruta_db())))
    elegida = os.path.normcase(os.path.abspath(carpeta))
    return elegida == tienda or elegida.startswith(tienda + os.sep)


def ultimo_respaldo_nube():
    """Fecha y hora ('2026-09-24 09:11') del respaldo más reciente en la nube, o None si no hay."""
    carpeta = carpeta_nube()
    respaldos = _respaldos_en(os.path.join(carpeta, SUBCARPETA_NUBE)) if carpeta else []
    if not respaldos:
        return None
    # inventario_2026-09-24_09-11-18.db -> 2026-09-24 09:11
    fecha, hora = respaldos[-1][len("inventario_"):-len(".db")].split("_")
    return f"{fecha} {hora[:5].replace('-', ':')}"


def copiar_a_nube():
    """
    Copia el respaldo local más reciente a la carpeta de la nube, si todavía no
    está allí, y deja solo los MAX_RESPALDOS más recientes. Retorna la ruta de
    la copia, o None si no había nada que copiar (o no se eligió carpeta).
    Lanza OSError si la carpeta no está disponible (ej: Google Drive cerrado).
    """
    carpeta = carpeta_nube()
    if not carpeta:
        return None
    if not os.path.isdir(carpeta):
        raise FileNotFoundError(
            f"No se encontró la carpeta {carpeta}. ¿Está abierto Google Drive en este computador?"
        )
    locales = _respaldos_en(carpeta_respaldos())
    if not locales:
        return None

    destino = os.path.join(carpeta, SUBCARPETA_NUBE)
    os.makedirs(destino, exist_ok=True)
    ruta = os.path.join(destino, locales[-1])
    if os.path.exists(ruta):
        return None
    # Se copia con otro nombre y se renombra al final, para que Google Drive
    # nunca suba un respaldo copiado a medias
    temporal = ruta + ".copiando"
    shutil.copyfile(os.path.join(carpeta_respaldos(), locales[-1]), temporal)
    os.replace(temporal, ruta)
    borrar_respaldos_viejos(destino)
    return ruta


def respaldar_ahora():
    """Respaldo nuevo en este momento (aunque ya hubiera uno hoy) y su copia en la nube. Retorna la ruta en la nube."""
    carpeta = carpeta_respaldos()
    crear_respaldo(carpeta)
    borrar_respaldos_viejos(carpeta)
    return copiar_a_nube()


if __name__ == "__main__":
    carpeta_por_defecto = carpeta_respaldos()
    carpeta = sys.argv[1] if len(sys.argv) > 1 else carpeta_por_defecto

    try:
        ruta = crear_respaldo(carpeta)
    except Exception as error:
        print(f"Error: no se pudo crear el respaldo.\n{error}")
        sys.exit(1)

    if carpeta == carpeta_por_defecto:
        borrar_respaldos_viejos(carpeta)

    print(f"Respaldo creado: {ruta}")
