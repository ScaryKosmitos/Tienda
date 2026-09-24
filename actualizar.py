"""
Actualiza la tienda a la última versión publicada en GitHub, sin tocar los
datos: inventario.db, respaldos, recibos, configuracion.json y errores.log.

Uso:
    python actualizar.py                  -> descarga la última versión de GitHub
    python actualizar.py archivo.zip      -> usa un ZIP ya descargado (por ejemplo, desde una USB)
    python actualizar.py --forzar         -> reinstala aunque ya se tenga la última versión

En Windows se ejecuta con el acceso "Actualizar Tienda" del menú Inicio
(o con doble clic en actualizar_windows.bat).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime

REPOSITORIO = "ScaryKosmitos/Tienda"
RAMA = "master"

CARPETA = os.path.dirname(os.path.abspath(__file__))
# Registro de la versión instalada y de sus archivos, para saber cuáles
# borrar cuando una versión nueva ya no los trae
ARCHIVO_VERSION = os.path.join(CARPETA, ".version_instalada.json")

# Nunca se reemplazan ni se borran: son los datos y la instalación de este computador
PROTEGIDOS = {"inventario.db", "configuracion.json", "errores.log", ".version_instalada.json"}
CARPETAS_PROTEGIDAS = {"respaldos", "recibos", ".venv", ".git"}


def paso(texto):
    print(f"\n==> {texto}", flush=True)


def es_protegido(ruta_relativa):
    partes = ruta_relativa.replace("\\", "/").split("/")
    return partes[0] in CARPETAS_PROTEGIDAS or ruta_relativa in PROTEGIDOS


def leer_version_instalada():
    try:
        with open(ARCHIVO_VERSION, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return {}


def ultima_version():
    """Identificador (sha) y descripción del último cambio publicado, o (None, None) si no se pudo consultar."""
    url = f"https://api.github.com/repos/{REPOSITORIO}/commits/{RAMA}"
    try:
        with urllib.request.urlopen(url, timeout=20) as respuesta:
            datos = json.load(respuesta)
        return datos["sha"], datos["commit"]["message"].splitlines()[0]
    except Exception as error:
        print(f"(No se pudo consultar la última versión: {error})")
        return None, None


def descargar(sha, carpeta_temporal):
    referencia = sha or f"refs/heads/{RAMA}"
    url = f"https://github.com/{REPOSITORIO}/archive/{referencia}.zip"
    paso("Descargando la versión nueva")
    ruta = os.path.join(carpeta_temporal, "tienda.zip")
    try:
        with urllib.request.urlopen(url, timeout=120) as respuesta, open(ruta, "wb") as archivo:
            shutil.copyfileobj(respuesta, archivo)
    except Exception as error:
        raise SystemExit(
            "\nERROR: no se pudo descargar la versión nueva. Revisa la conexión a internet "
            f"e inténtalo de nuevo. No se cambió nada.\n(Detalle: {error})"
        )
    return ruta


def leer_zip(ruta_zip):
    """
    Retorna {ruta_relativa: contenido} con los archivos del programa que trae el ZIP.
    Los ZIP de GitHub guardan todo dentro de una carpeta (ej: 'Tienda-master/'), que se quita.
    """
    try:
        with zipfile.ZipFile(ruta_zip) as archivo_zip:
            nombres = [n for n in archivo_zip.namelist() if not n.endswith("/")]
            raiz = os.path.commonpath(nombres).replace("\\", "/") if len(nombres) > 1 else ""
            archivos = {}
            for nombre in nombres:
                relativa = nombre[len(raiz):].lstrip("/") if raiz else nombre
                # Evita rutas que intenten salirse de la carpeta de la tienda
                if not relativa or relativa.startswith("/") or ".." in relativa.split("/"):
                    continue
                archivos[relativa] = archivo_zip.read(nombre)
    except (OSError, zipfile.BadZipFile) as error:
        raise SystemExit(f"ERROR: no se pudo leer el ZIP {ruta_zip}. No se cambió nada.\n(Detalle: {error})")
    for necesario in ("main.py", "base_datos.py", "instalar.py"):
        if necesario not in archivos:
            raise SystemExit(f"ERROR: el ZIP no parece ser de la tienda (falta {necesario}). No se cambió nada.")
    return archivos


def respaldar_datos():
    """Copia de seguridad de la base de datos antes de actualizar. Si falla, no se actualiza."""
    if not os.path.exists(os.path.join(CARPETA, "inventario.db")):
        return
    paso("Haciendo un respaldo de la base de datos")
    sys.path.insert(0, CARPETA)
    import respaldar
    ruta = respaldar.crear_respaldo(respaldar.carpeta_respaldos())
    print(f"Respaldo: {ruta}")


def _mismo_contenido(ruta, contenido):
    try:
        with open(ruta, "rb") as archivo:
            return archivo.read() == contenido
    except OSError:
        return False


def instalar_archivos(archivos, anteriores):
    paso("Reemplazando los archivos del programa")
    for relativa, contenido in archivos.items():
        if es_protegido(relativa):
            continue
        destino = os.path.join(CARPETA, *relativa.split("/"))
        # Los que no cambiaron no se tocan (entre ellos, casi siempre, el .bat que
        # está ejecutando esta actualización)
        if _mismo_contenido(destino, contenido):
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        # Se escribe primero en un archivo temporal para no dejar uno a medias si algo falla
        temporal = destino + ".nuevo"
        with open(temporal, "wb") as archivo:
            archivo.write(contenido)
        os.replace(temporal, destino)

    # Archivos que instaló una actualización anterior y que la versión nueva ya no trae
    for relativa in set(anteriores) - set(archivos):
        ruta = os.path.join(CARPETA, *relativa.split("/"))
        if not es_protegido(relativa) and os.path.isfile(ruta):
            os.remove(ruta)
            print(f"Eliminado (ya no se usa): {relativa}")


def main():
    argumentos = [a for a in sys.argv[1:] if a != "--forzar"]
    forzar = "--forzar" in sys.argv[1:]

    print("Actualización de la Tienda")
    print(f"Carpeta: {CARPETA}")
    if os.path.isdir(os.path.join(CARPETA, ".git")):
        raise SystemExit("ERROR: esta carpeta es un repositorio de git (la de desarrollo). Ahí se actualiza con git.")

    instalada = leer_version_instalada()
    with tempfile.TemporaryDirectory() as carpeta_temporal:
        if argumentos:
            ruta_zip, sha, descripcion = argumentos[0], None, f"archivo {os.path.basename(argumentos[0])}"
        else:
            sha, descripcion = ultima_version()
            if sha and sha == instalada.get("sha") and not forzar:
                print(f"\nYa tienes la última versión ({sha[:7]}: {descripcion}). No hay nada que hacer.")
                return
            ruta_zip = descargar(sha, carpeta_temporal)

        archivos = leer_zip(ruta_zip)
        respaldar_datos()
        instalar_archivos(archivos, instalada.get("archivos", []))

    with open(ARCHIVO_VERSION, "w", encoding="utf-8") as archivo:
        json.dump({
            "sha": sha, "descripcion": descripcion, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "archivos": sorted(archivos),
        }, archivo, indent=2, ensure_ascii=False)

    # El instalador de la versión nueva instala librerías nuevas si las hay
    paso("Revisando las librerías")
    resultado = subprocess.run([sys.executable, os.path.join(CARPETA, "instalar.py")])
    if resultado.returncode != 0:
        raise SystemExit("\nERROR: los archivos se actualizaron, pero falló la instalación de librerías. "
                         "Revisa la conexión a internet y vuelve a ejecutar la actualización con --forzar.")

    version = f"{sha[:7]}: {descripcion}" if sha else descripcion
    print(f"\nTienda actualizada ({version}). Ya se puede abrir.")


if __name__ == "__main__":
    main()
