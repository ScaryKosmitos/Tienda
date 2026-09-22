import sqlite3
from datetime import datetime

def conectar():
    """Establece conexión con la base de datos SQLite y activa las claves foráneas."""
    conexion = sqlite3.connect("inventario.db")
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
    """Retorna (exito: bool, mensaje: str)."""
    if stock <= 0:
        return False, "El stock debe ser mayor a 0."

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
    conexion = conectar()
    try:
        with conexion:
            conexion.execute("""
                UPDATE productos
                SET nombre = ?, categoria = ?, precio = ?, stock = ?
                WHERE id = ?
            """, (nombre, categoria, precio, stock, id_producto))
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

def registrar_venta(id_producto, nombre_producto, cantidad, precio_unitario):
    """
    Verifica stock, lo descuenta de la tabla productos y registra la venta con fecha y hora.
    Si algo falla a mitad de camino, la transacción se revierte por completo.
    """
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()

            cursor.execute("SELECT stock FROM productos WHERE id = ?", (id_producto,))
            res = cursor.fetchone()
            if not res:
                return False, "Producto no encontrado."

            stock_actual = res[0]
            if stock_actual < cantidad:
                return False, f"Stock insuficiente. Solo quedan {stock_actual} unidades."

            # Descontar stock
            nuevo_stock = stock_actual - cantidad
            cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id_producto))

            # Registrar la transacción
            total = cantidad * precio_unitario
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO ventas (producto_id, nombre_producto, cantidad, total, fecha)
                VALUES (?, ?, ?, ?, ?)
            """, (id_producto, nombre_producto, cantidad, total, fecha_actual))

        return True, f"Venta realizada. Total: ${total:,.2f}"
    finally:
        conexion.close()

def obtener_ventas():
    """Retorna todas las ventas realizadas ordenadas de más reciente a más antigua."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        conexion.close()
