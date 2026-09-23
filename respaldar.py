"""
Crea una copia de seguridad de inventario.db.

Uso:
    python respaldar.py                 -> guarda el respaldo en la carpeta "respaldos"
    python respaldar.py /ruta/carpeta   -> guarda el respaldo en otra carpeta (ej: una USB)

Usa la función de respaldo de SQLite, así que la copia sale bien aunque la
aplicación esté abierta. En la carpeta "respaldos" se conservan solo los
últimos MAX_RESPALDOS; los más antiguos se borran solos.

La aplicación también llama a respaldo_automatico() al abrirse, que crea
como máximo un respaldo por día.
"""
import os
import sqlite3
import sys
from datetime import datetime

import base_datos as db

MAX_RESPALDOS = 30


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


def borrar_respaldos_viejos(carpeta):
    """Deja solo los MAX_RESPALDOS más recientes."""
    respaldos = sorted(
        f for f in os.listdir(carpeta) if f.startswith("inventario_") and f.endswith(".db")
    )
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
