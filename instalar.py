"""
Instala la tienda en este computador: crea el entorno virtual (.venv),
instala las librerías, descarga el visor de Flet y, en Windows, crea los
accesos directos "Tienda" en el Escritorio y en el menú Inicio.

En Windows se ejecuta con doble clic en instalar_windows.bat. Se puede volver
a ejecutar sin problema (por ejemplo, después de actualizar los archivos de la
tienda): los datos (inventario.db, respaldos, recibos) no se tocan.
"""
import os
import subprocess
import sys
import venv

CARPETA = os.path.dirname(os.path.abspath(__file__))
CARPETA_VENV = os.path.join(CARPETA, ".venv")
ES_WINDOWS = sys.platform == "win32"

if ES_WINDOWS:
    PYTHON_VENV = os.path.join(CARPETA_VENV, "Scripts", "python.exe")
    # pythonw abre la tienda sin la ventana negra de la consola
    PYTHONW_VENV = os.path.join(CARPETA_VENV, "Scripts", "pythonw.exe")
else:
    PYTHON_VENV = PYTHONW_VENV = os.path.join(CARPETA_VENV, "bin", "python")

# Crea un acceso directo de Windows. Los datos llegan por variables de entorno
# para no tener problemas con espacios o tildes en las rutas
_CREAR_ACCESO = r"""
$carpeta = [Environment]::GetFolderPath($env:TIENDA_UBICACION)
$acceso = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $carpeta 'Tienda.lnk'))
$acceso.TargetPath = $env:TIENDA_PROGRAMA
$acceso.Arguments = '"' + $env:TIENDA_SCRIPT + '"'
$acceso.WorkingDirectory = $env:TIENDA_CARPETA
$acceso.IconLocation = $env:TIENDA_ICONO + ',0'
$acceso.Description = 'Inventario y punto de venta'
$acceso.Save()
Write-Output (Join-Path $carpeta 'Tienda.lnk')
"""


def paso(texto):
    print(f"\n==> {texto}", flush=True)


def ejecutar(*comando):
    """Ejecuta un comando mostrando su salida; si falla, detiene la instalación."""
    resultado = subprocess.run(comando)
    if resultado.returncode != 0:
        raise SystemExit(f"\nERROR: falló el paso anterior (código {resultado.returncode}).")


def crear_entorno():
    if os.path.exists(PYTHON_VENV):
        paso("El entorno de Python ya existe: se reutiliza")
        return
    paso("Creando el entorno de Python (.venv)")
    venv.create(CARPETA_VENV, with_pip=True)


def instalar_librerias():
    paso("Instalando las librerías (Flet y openpyxl). Puede tardar unos minutos...")
    ejecutar(PYTHON_VENV, "-m", "pip", "install", "--disable-pip-version-check", "--upgrade",
             "-r", os.path.join(CARPETA, "requirements.txt"))


def descargar_visor():
    # Si no se hace aquí, Flet lo descarga la primera vez que se abre la tienda,
    # sin mostrar nada, y parece que el ícono no funciona
    paso("Descargando el visor de Flet (solo la primera vez)")
    ejecutar(PYTHON_VENV, "-c", "import flet_desktop; print(flet_desktop.ensure_client_cached())")


def crear_accesos_directos():
    if not ES_WINDOWS:
        paso("Accesos directos: solo se crean en Windows. En Linux se abre con: .venv/bin/python main.py")
        return
    paso("Creando los accesos directos 'Tienda'")
    datos = {
        "TIENDA_PROGRAMA": PYTHONW_VENV,
        "TIENDA_SCRIPT": os.path.join(CARPETA, "main.py"),
        "TIENDA_CARPETA": CARPETA,
        "TIENDA_ICONO": os.path.join(CARPETA, "tienda.ico"),
    }
    for ubicacion in ("Desktop", "Programs"):  # Escritorio y menú Inicio
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _CREAR_ACCESO],
            env={**os.environ, **datos, "TIENDA_UBICACION": ubicacion},
        )
        if resultado.returncode != 0:
            raise SystemExit(f"\nERROR: no se pudo crear el acceso directo ({ubicacion}).")


def main():
    print("Instalación de la Tienda")
    print(f"Carpeta: {CARPETA}")
    if sys.version_info < (3, 10):
        raise SystemExit("ERROR: se necesita Python 3.10 o más reciente. Instálalo desde https://www.python.org")
    crear_entorno()
    instalar_librerias()
    descargar_visor()
    crear_accesos_directos()
    print("\nListo. La tienda se abre con el ícono 'Tienda' del Escritorio o del menú Inicio.")


if __name__ == "__main__":
    main()
