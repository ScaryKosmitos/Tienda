import math
import os
import sys
import sqlite3
from datetime import datetime

def _ruta_db():
    """
    Ubica inventario.db junto al ejecutable (o al script), sin importar
    desde qué carpeta se haya lanzado la aplicación. Esto es necesario
    para que un .exe empaquetado (PyInstaller) siempre use la misma
    base de datos en vez de crear una nueva vacía por accidente.
    """
    if getattr(sys, "frozen", False):
        carpeta = os.path.dirname(sys.executable)
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(carpeta, "inventario.db")

def conectar():
    """Establece conexión con la base de datos SQLite y activa las claves foráneas."""
    conexion = sqlite3.connect(_ruta_db())
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def inicializar_db():
    """Crea las tablas 'productos' y 'ventas' si no existen."""
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()

            # Tabla de Inventario de Productos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    precio REAL NOT NULL,
                    stock INTEGER NOT NULL
                )
            """)

            # Tabla de Historial de Ventas (POS)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    nombre_producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    total REAL NOT NULL,
                    fecha TEXT NOT NULL,
                    FOREIGN KEY (producto_id) REFERENCES productos (id)
                )
            """)
    finally:
        conexion.close()

# --- OPERACIONES CRUD DE PRODUCTOS ---

def agregar_producto(nombre, categoria, precio, stock):
    """Retorna (exito: bool, mensaje: str). Se permite registrar un producto
    con stock 0 (por ejemplo, uno que todavía no ha llegado)."""
    if not math.isfinite(precio) or precio <= 0:
        return False, "El precio debe ser mayor a 0."
    if stock < 0:
        return False, "El stock no puede ser negativo."

    conexion = conectar()
    try:
        with conexion:
            conexion.execute("""
                INSERT INTO productos (nombre, categoria, precio, stock)
                VALUES (?, ?, ?, ?)
            """, (nombre, categoria, precio, stock))
        return True, "Producto agregado."
    finally:
        conexion.close()

def obtener_productos():
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos")
        return cursor.fetchall()
    finally:
        conexion.close()

def buscar_producto_por_nombre(texto_busqueda):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos WHERE nombre LIKE ?", (f"%{texto_busqueda}%",))
        return cursor.fetchall()
    finally:
        conexion.close()

def actualizar_producto(id_producto, nombre, categoria, precio, stock):
    """Retorna (exito: bool, mensaje: str). El stock puede quedar en 0 (agotado),
    pero nunca negativo, y el precio siempre debe ser mayor a 0."""
    if not math.isfinite(precio) or precio <= 0:
        return False, "El precio debe ser mayor a 0."
    if stock < 0:
        return False, "El stock no puede ser negativo."

    conexion = conectar()
    try:
        with conexion:
            conexion.execute("""
                UPDATE productos
                SET nombre = ?, categoria = ?, precio = ?, stock = ?
                WHERE id = ?
            """, (nombre, categoria, precio, stock, id_producto))
        return True, "Producto actualizado."
    finally:
        conexion.close()

def eliminar_producto(id_producto):
    """
    Elimina un producto. Si tiene ventas asociadas en el historial,
    rechaza el borrado para no dejar referencias rotas en 'ventas'.
    Retorna (exito: bool, mensaje: str).
    """
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT COUNT(*) FROM ventas WHERE producto_id = ?", (id_producto,))
            if cursor.fetchone()[0] > 0:
                return False, "No se puede eliminar: el producto tiene ventas registradas en el historial."
            cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
        return True, "Producto eliminado."
    except sqlite3.IntegrityError:
        return False, "No se puede eliminar: el producto tiene ventas registradas en el historial."
    finally:
        conexion.close()

# --- MÓDULO DE VENTAS ---

class _VentaRechazada(Exception):
    """Se lanza dentro de la transacción para revertirla por completo."""


def obtener_producto(id_producto):
    """Retorna (id, nombre, categoria, precio, stock) o None si no existe."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos WHERE id = ?", (id_producto,))
        return cursor.fetchone()
    finally:
        conexion.close()


def registrar_venta_carrito(items):
    """
    Registra la venta de varios productos a la vez. 'items' es una lista de
    (id_producto, cantidad). Verifica el stock de cada uno, lo descuenta y
    registra una línea por producto, todas con la misma fecha y hora.
    El nombre y el precio se leen de la base de datos en la misma transacción.
    Si un solo producto falla, no se registra nada: la venta es todo o nada.
    Retorna (exito: bool, mensaje: str).
    """
    if not items:
        return False, "El carrito está vacío."

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_venta = 0.0

            for id_producto, cantidad in items:
                cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = ?", (id_producto,))
                res = cursor.fetchone()
                if not res:
                    raise _VentaRechazada(f"Un producto del carrito (ID {id_producto}) ya no existe.")

                nombre_producto, precio_unitario, stock_actual = res
                if stock_actual < cantidad:
                    raise _VentaRechazada(
                        f"Stock insuficiente de '{nombre_producto}'. Solo quedan {stock_actual} unidades."
                    )

                cursor.execute(
                    "UPDATE productos SET stock = ? WHERE id = ?", (stock_actual - cantidad, id_producto)
                )
                total = cantidad * precio_unitario
                total_venta += total
                cursor.execute("""
                    INSERT INTO ventas (producto_id, nombre_producto, cantidad, total, fecha)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_producto, nombre_producto, cantidad, total, fecha_actual))

        return True, f"Venta realizada. Total: ${total_venta:,.2f}"
    except _VentaRechazada as rechazo:
        return False, str(rechazo)
    finally:
        conexion.close()


def obtener_ventas(desde=None, hasta=None):
    """
    Retorna las ventas ordenadas de más reciente a más antigua. 'desde' y
    'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    """
    condiciones, parametros = [], []
    if desde:
        condiciones.append("date(fecha) >= ?")
        parametros.append(desde)
    if hasta:
        condiciones.append("date(fecha) <= ?")
        parametros.append(hasta)

    consulta = "SELECT * FROM ventas"
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)
    consulta += " ORDER BY id DESC"

    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()
