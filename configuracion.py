"""
Preferencias de la aplicación (tamaño de letra y clave), guardadas en
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
    _escribir(datos)


def quitar(nombre):
    """Borra una preferencia guardada (si existe)."""
    datos = leer()
    if datos.pop(nombre, None) is not None:
        _escribir(datos)


def _escribir(datos):
    with open(_ruta(), "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2)
