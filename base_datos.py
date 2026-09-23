import math
import os
import sys
import sqlite3
import unicodedata
from datetime import datetime

from formato import formatear_numero, formatear_precio

# Límite de unidades por producto: evita números tan grandes que SQLite no
# puede guardarlos (y que casi siempre son un error al escribir)
STOCK_MAXIMO = 1_000_000

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
    """Crea las tablas 'productos', 'ventas' y 'entradas' si no existen, y
    actualiza las bases de datos creadas con versiones anteriores."""
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
                    anulada INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (producto_id) REFERENCES productos (id)
                )
            """)

            # Las bases de datos anteriores no tienen la columna 'anulada'
            columnas_ventas = [fila[1] for fila in cursor.execute("PRAGMA table_info(ventas)")]
            if "anulada" not in columnas_ventas:
                cursor.execute("ALTER TABLE ventas ADD COLUMN anulada INTEGER NOT NULL DEFAULT 0")

            # Movimientos de stock: entradas de mercancía, stock inicial y ajustes manuales
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entradas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    nombre_producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    fecha TEXT NOT NULL,
                    motivo TEXT NOT NULL DEFAULT 'Entrada',
                    FOREIGN KEY (producto_id) REFERENCES productos (id)
                )
            """)

            # Las bases de datos anteriores no tienen la columna 'motivo'
            columnas_entradas = [fila[1] for fila in cursor.execute("PRAGMA table_info(entradas)")]
            if "motivo" not in columnas_entradas:
                cursor.execute("ALTER TABLE entradas ADD COLUMN motivo TEXT NOT NULL DEFAULT 'Entrada'")
    finally:
        conexion.close()

# --- OPERACIONES CRUD DE PRODUCTOS ---

def _categoria_existente(cursor, categoria, excluir_id=None):
    """
    Si ya existe una categoría igual sin importar mayúsculas (ej: 'salsas'
    y 'Salsas'), retorna la que ya existe para no crear duplicados.
    'excluir_id' ignora al producto que se está editando, para que pueda
    corregir la forma de escribir su propia categoría.
    """
    cursor.execute("SELECT DISTINCT categoria FROM productos WHERE id != ?", (excluir_id or -1,))
    for (existente,) in cursor.fetchall():
        if existente.casefold() == categoria.casefold():
            return existente
    return categoria

def _registrar_movimiento(cursor, id_producto, nombre_producto, cantidad, motivo):
    """Deja constancia de un cambio de stock en la tabla 'entradas'."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO entradas (producto_id, nombre_producto, cantidad, fecha, motivo)
        VALUES (?, ?, ?, ?, ?)
    """, (id_producto, nombre_producto, cantidad, fecha_actual, motivo))

def validar_producto(precio, stock):
    """Retorna un mensaje de error si el precio o el stock no son válidos, o None si están bien."""
    if not math.isfinite(precio) or precio <= 0:
        return "El precio debe ser mayor a 0."
    if stock < 0:
        return "El stock no puede ser negativo."
    if stock > STOCK_MAXIMO:
        return f"El stock no puede ser mayor a {formatear_numero(STOCK_MAXIMO)}."
    return None

def _sin_tildes(texto):
    """'Jabón LÁCTEO' -> 'jabon lacteo', para buscar sin importar tildes ni mayúsculas."""
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

def categoria_es_nueva(categoria):
    """True si no hay ningún producto con esa categoría (sin importar mayúsculas)."""
    return all(c.casefold() != categoria.casefold() for c in obtener_categorias())

def agregar_producto(nombre, categoria, precio, stock):
    """Retorna (exito: bool, mensaje: str). Se permite registrar un producto
    con stock 0 (por ejemplo, uno que todavía no ha llegado)."""
    error = validar_producto(precio, stock)
    if error:
        return False, error

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            categoria = _categoria_existente(cursor, categoria)
            cursor.execute("""
                INSERT INTO productos (nombre, categoria, precio, stock)
                VALUES (?, ?, ?, ?)
            """, (nombre, categoria, precio, stock))
            if stock > 0:
                _registrar_movimiento(cursor, cursor.lastrowid, nombre, stock, "Stock inicial")
        return True, "Producto agregado."
    finally:
        conexion.close()

def buscar_productos(texto="", categoria=None, stock_menor_a=None):
    """
    Filtra productos por nombre (texto parcial, sin importar tildes ni
    mayúsculas), categoría exacta y/o stock menor a un valor. Los filtros
    vacíos o None se ignoran.
    """
    condiciones, parametros = [], []
    if categoria:
        condiciones.append("categoria = ?")
        parametros.append(categoria)
    if stock_menor_a is not None:
        condiciones.append("stock < ?")
        parametros.append(stock_menor_a)

    consulta = "SELECT * FROM productos"
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)

    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        productos = cursor.fetchall()
    finally:
        conexion.close()

    # El LIKE de SQLite no ignora tildes ni mayúsculas en letras como 'Á',
    # así que el filtro por nombre se hace aquí
    if texto:
        buscado = _sin_tildes(texto)
        productos = [p for p in productos if buscado in _sin_tildes(p[1])]
    return productos

def obtener_categorias():
    """Retorna la lista de categorías distintas, en orden alfabético."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT DISTINCT categoria FROM productos ORDER BY categoria COLLATE NOCASE")
        return [fila[0] for fila in cursor.fetchall()]
    finally:
        conexion.close()

def actualizar_producto(id_producto, nombre, categoria, precio, stock):
    """Retorna (exito: bool, mensaje: str). El stock puede quedar en 0 (agotado),
    pero nunca negativo, y el precio siempre debe ser mayor a 0."""
    error = validar_producto(precio, stock)
    if error:
        return False, error

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT stock FROM productos WHERE id = ?", (id_producto,))
            res = cursor.fetchone()
            if not res:
                return False, "Producto no encontrado."

            categoria = _categoria_existente(cursor, categoria, excluir_id=id_producto)
            cursor.execute("""
                UPDATE productos
                SET nombre = ?, categoria = ?, precio = ?, stock = ?
                WHERE id = ?
            """, (nombre, categoria, precio, stock, id_producto))

            # Un cambio de stock hecho a mano queda registrado como ajuste
            diferencia = stock - res[0]
            if diferencia:
                _registrar_movimiento(cursor, id_producto, nombre, diferencia, "Ajuste manual")

        if diferencia:
            return True, f"Producto actualizado. Se registró un ajuste de stock de {diferencia:+d}."
        return True, "Producto actualizado."
    finally:
        conexion.close()

def eliminar_producto(id_producto):
    """
    Elimina un producto junto con sus movimientos de stock. Si tiene ventas
    asociadas, rechaza el borrado para no dejar referencias rotas en el
    historial de ventas.
    Retorna (exito: bool, mensaje: str).
    """
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT COUNT(*) FROM ventas WHERE producto_id = ?", (id_producto,))
            if cursor.fetchone()[0] > 0:
                return False, "No se puede eliminar: el producto tiene ventas registradas en el historial."
            cursor.execute("DELETE FROM entradas WHERE producto_id = ?", (id_producto,))
            cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
        return True, "Producto eliminado."
    except sqlite3.IntegrityError:
        return False, "No se puede eliminar: el producto tiene movimientos registrados en el historial."
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

        return True, f"Venta realizada. Total: {formatear_precio(total_venta)}"
    except _VentaRechazada as rechazo:
        return False, str(rechazo)
    finally:
        conexion.close()


def obtener_ventas(desde=None, hasta=None):
    """
    Retorna las ventas ordenadas de más reciente a más antigua, como
    (id, producto_id, nombre_producto, cantidad, total, fecha, anulada).
    'desde' y 'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    """
    condiciones, parametros = [], []
    if desde:
        condiciones.append("date(fecha) >= ?")
        parametros.append(desde)
    if hasta:
        condiciones.append("date(fecha) <= ?")
        parametros.append(hasta)

    consulta = "SELECT id, producto_id, nombre_producto, cantidad, total, fecha, anulada FROM ventas"
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


def anular_ventas(ids_venta):
    """
    Anula una o varias líneas de venta: devuelve las unidades al stock y las
    marca como anuladas (no se borran, para que quede registro).
    Todo ocurre en una sola transacción. Retorna (exito: bool, mensaje: str).
    """
    if not ids_venta:
        return False, "No hay ventas seleccionadas."

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            total_devuelto = 0.0
            for id_venta in ids_venta:
                cursor.execute(
                    "SELECT producto_id, nombre_producto, cantidad, total, anulada FROM ventas WHERE id = ?",
                    (id_venta,)
                )
                res = cursor.fetchone()
                if not res:
                    raise _VentaRechazada(f"La venta {id_venta} no existe.")
                producto_id, nombre_producto, cantidad, total, anulada = res
                if anulada:
                    raise _VentaRechazada(f"La venta {id_venta} ({nombre_producto}) ya estaba anulada.")

                cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, producto_id))
                cursor.execute("UPDATE ventas SET anulada = 1 WHERE id = ?", (id_venta,))
                total_devuelto += total

        cantidad_lineas = len(ids_venta)
        return True, (
            f"Se anularon {cantidad_lineas} línea(s) de venta por {formatear_precio(total_devuelto)}. "
            "Las unidades volvieron al stock."
        )
    except _VentaRechazada as rechazo:
        return False, str(rechazo)
    finally:
        conexion.close()

# --- ENTRADAS DE MERCANCÍA ---

def registrar_entrada(id_producto, cantidad):
    """
    Suma unidades al stock de un producto (llegada de un pedido) y deja
    registro en la tabla 'entradas'. Retorna (exito: bool, mensaje: str).
    """
    if cantidad <= 0:
        return False, "La cantidad debe ser mayor a 0."

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre, stock FROM productos WHERE id = ?", (id_producto,))
            res = cursor.fetchone()
            if not res:
                return False, "Producto no encontrado."

            nombre_producto, stock_actual = res
            if stock_actual + cantidad > STOCK_MAXIMO:
                return False, (
                    f"Con esa entrada, '{nombre_producto}' pasaría de "
                    f"{formatear_numero(STOCK_MAXIMO)} unidades, que es el máximo permitido."
                )
            cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (stock_actual + cantidad, id_producto))
            _registrar_movimiento(cursor, id_producto, nombre_producto, cantidad, "Entrada")

        return True, f"Entrada registrada: +{cantidad} de '{nombre_producto}'. Stock nuevo: {stock_actual + cantidad}."
    finally:
        conexion.close()

def obtener_entradas():
    """
    Retorna los movimientos de stock (entradas, stock inicial y ajustes
    manuales) como (id, nombre_producto, cantidad, fecha, motivo), del más
    reciente al más antiguo.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_producto, cantidad, fecha, motivo FROM entradas ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        conexion.close()
