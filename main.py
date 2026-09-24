import os
import sys

# Al abrir la tienda con el ícono de Windows (pythonw) no hay consola: si algo
# falla, el error se anota en errores.log para poder revisarlo después
if sys.stderr is None:
    ruta_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "errores.log")
    sys.stdout = sys.stderr = open(ruta_log, "a", encoding="utf-8", buffering=1)

import interfaz  # noqa: E402  (va después de preparar el registro de errores)

if __name__ == "__main__":
    interfaz.iniciar_app()
