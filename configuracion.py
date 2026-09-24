"""
Preferencias de la aplicación (por ahora, el tamaño de letra), guardadas en
configuracion.json junto a inventario.db para que se recuerden al volver a abrir.
"""
import json
import os

import base_datos as db


def _ruta():
    return os.path.join(os.path.dirname(db._ruta_db()), "configuracion.json")


def leer():
    """Retorna las preferencias guardadas, o {} si no hay o el archivo está dañado."""
    try:
        with open(_ruta(), encoding="utf-8") as archivo:
            datos = json.load(archivo)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar(**cambios):
    """Guarda las preferencias indicadas, conservando las demás."""
    datos = leer()
    datos.update(cambios)
    with open(_ruta(), "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2)
