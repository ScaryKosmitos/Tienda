"""
Clave para las acciones delicadas (eliminar productos, cambiar precios o
stock y anular ventas). Se guarda cifrada en configuracion.json: nunca se
guarda la clave misma, solo una huella que permite comprobarla.

Si se olvida la clave, se borra la línea "clave" de configuracion.json y la
tienda vuelve a funcionar sin clave.
"""
import hashlib
import hmac
import os
import re
import time

import configuracion

# Después de escribir bien la clave, no se vuelve a pedir durante estos minutos
MINUTOS_DESBLOQUEO = 5

# La clave es de 4 a 8 números
_CLAVE_VALIDA = re.compile(r"\d{4,8}")

_desbloqueado_hasta = 0.0


def _huella(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, 200_000).hex()


def clave_valida(clave):
    """Retorna un mensaje de error si la clave no sirve, o None si está bien."""
    if not _CLAVE_VALIDA.fullmatch(clave):
        return "La clave debe tener de 4 a 8 números."
    return None


def tiene_clave():
    return isinstance(configuracion.leer().get("clave"), dict)


def poner_clave(clave):
    sal = os.urandom(16)
    configuracion.guardar(clave={"sal": sal.hex(), "huella": _huella(clave, sal)})
    desbloquear()


def quitar_clave():
    configuracion.quitar("clave")


def verificar(clave):
    """True si 'clave' es la clave guardada."""
    datos = configuracion.leer().get("clave")
    if not isinstance(datos, dict):
        return True
    try:
        esperada = datos["huella"]
        sal = bytes.fromhex(datos["sal"])
    except (KeyError, ValueError):
        return False
    return hmac.compare_digest(_huella(clave, sal), esperada)


def desbloquear():
    global _desbloqueado_hasta
    _desbloqueado_hasta = time.monotonic() + MINUTOS_DESBLOQUEO * 60


def bloquear():
    """Vuelve a pedir la clave desde ya, sin esperar los minutos de desbloqueo."""
    global _desbloqueado_hasta
    _desbloqueado_hasta = 0.0


def esta_desbloqueado():
    """True si no hay clave, o si se escribió bien hace menos de MINUTOS_DESBLOQUEO."""
    return not tiene_clave() or time.monotonic() < _desbloqueado_hasta
