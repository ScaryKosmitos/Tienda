import math
import os
import sys
import sqlite3
from datetime import datetime

from formato import clave_orden, formatear_cambio, formatear_numero, formatear_precio, sin_tildes

# Límites de unidades y de precio por producto: evitan números tan grandes que
# SQLite no puede guardarlos o que desarman el recibo (y que casi siempre son un
# error al escribir)
STOCK_MAXIMO = 1_000_000
PRECIO_MAXIMO = 100_000_000

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
    """
    Establece conexión con la base de datos SQLite y activa las claves foráneas.
    Las filas se pueden leer por posición (producto[4]) o por nombre de
    columna (producto["stock"]), que es más fácil de entender.
    """
    conexion = sqlite3.connect(_ruta_db())
    conexion.row_factory = sqlite3.Row
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

            # Un recibo agrupa las líneas de una misma venta y guarda con cuánto pagó el cliente
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recibos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    total REAL NOT NULL,
                    pago REAL NOT NULL
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
                    recibo_id INTEGER REFERENCES recibos (id),
                    FOREIGN KEY (producto_id) REFERENCES productos (id)
                )
            """)

            # Las bases de datos anteriores no tienen las columnas 'anulada' y 'recibo_id'
            # (las ventas hechas antes de que existieran los recibos quedan sin recibo)
            columnas_ventas = [fila[1] for fila in cursor.execute("PRAGMA table_info(ventas)")]
            if "anulada" not in columnas_ventas:
                cursor.execute("ALTER TABLE ventas ADD COLUMN anulada INTEGER NOT NULL DEFAULT 0")
            if "recibo_id" not in columnas_ventas:
                cursor.execute("ALTER TABLE ventas ADD COLUMN recibo_id INTEGER REFERENCES recibos (id)")

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
    if precio > PRECIO_MAXIMO:
        return f"El precio no puede ser mayor a {formatear_precio(PRECIO_MAXIMO)}."
    if stock < 0:
        return "El stock no puede ser negativo."
    if stock > STOCK_MAXIMO:
        return f"El stock no puede ser mayor a {formatear_numero(STOCK_MAXIMO)}."
    return None

def _nombre_repetido(cursor, nombre, excluir_id=None):
    """
    Si ya hay otro producto con ese nombre (sin importar mayúsculas ni tildes:
    'Jabon' y 'Jabón' se consideran iguales), retorna su nombre; si no, None.
    'excluir_id' ignora al producto que se está editando.
    """
    buscado = sin_tildes(nombre)
    cursor.execute("SELECT nombre FROM productos WHERE id != ?", (excluir_id or -1,))
    for (existente,) in cursor.fetchall():
        if sin_tildes(existente) == buscado:
            return existente
    return None

def nombre_repetido(nombre, excluir_id=None):
    """Versión para la interfaz: permite avisar antes de preguntar por la categoría."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        if excluir_id is not None:
            # Si el producto ya se llamaba así, no es un nombre nuevo: se permite
            # editarlo aunque existiera un repetido de antes de esta validación
            cursor.execute("SELECT nombre FROM productos WHERE id = ?", (excluir_id,))
            actual = cursor.fetchone()
            if actual and sin_tildes(actual["nombre"]) == sin_tildes(nombre):
                return None
        return _nombre_repetido(cursor, nombre, excluir_id)
    finally:
        conexion.close()

def _mensaje_repetido(existente):
    return f"Ya existe un producto llamado '{existente}'. Usa otro nombre o edita el que ya existe."

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
            existente = _nombre_repetido(cursor, nombre)
            if existente:
                return False, _mensaje_repetido(existente)
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
        buscado = sin_tildes(texto)
        productos = [p for p in productos if buscado in sin_tildes(p["nombre"])]
    return productos

def obtener_categorias():
    """Retorna la lista de categorías distintas, en orden alfabético español."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT DISTINCT categoria FROM productos")
        # SQLite no ordena bien las tildes ni la ñ, así que se ordena aquí
        return sorted((fila[0] for fila in cursor.fetchall()), key=clave_orden)
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
            cursor.execute("SELECT nombre, stock FROM productos WHERE id = ?", (id_producto,))
            res = cursor.fetchone()
            if not res:
                return False, "Producto no encontrado."

            # Solo se revisa si cambia el nombre, para poder seguir editando
            # productos repetidos que existieran antes de esta validación
            if sin_tildes(nombre) != sin_tildes(res["nombre"]):
                existente = _nombre_repetido(cursor, nombre, excluir_id=id_producto)
                if existente:
                    return False, _mensaje_repetido(existente)

            categoria = _categoria_existente(cursor, categoria, excluir_id=id_producto)
            cursor.execute("""
                UPDATE productos
                SET nombre = ?, categoria = ?, precio = ?, stock = ?
                WHERE id = ?
            """, (nombre, categoria, precio, stock, id_producto))

            # Un cambio de stock hecho a mano queda registrado como ajuste
            diferencia = stock - res["stock"]
            if diferencia:
                _registrar_movimiento(cursor, id_producto, nombre, diferencia, "Ajuste manual")

        if diferencia:
            return True, f"Producto actualizado. Se registró un ajuste de stock de {formatear_cambio(diferencia)}."
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
    """Retorna el producto (columnas id, nombre, categoria, precio, stock) o None si no existe."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos WHERE id = ?", (id_producto,))
        return cursor.fetchone()
    finally:
        conexion.close()


def registrar_venta_carrito(items, pago=None):
    """
    Registra la venta de varios productos a la vez. 'items' es una lista de
    (id_producto, cantidad). Verifica el stock de cada uno, lo descuenta y
    registra una línea por producto, todas con la misma fecha y hora y el
    mismo recibo. 'pago' es el dinero que entregó el cliente (None = pago exacto).
    El nombre y el precio se leen de la base de datos en la misma transacción.
    Si un solo producto falla, no se registra nada: la venta es todo o nada.
    Retorna (exito: bool, mensaje: str, id_recibo: int o None).
    """
    if not items:
        return False, "El carrito está vacío.", None

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_venta = 0.0

            # El total y el pago se completan al final, cuando se conoce el total
            cursor.execute("INSERT INTO recibos (fecha, total, pago) VALUES (?, 0, 0)", (fecha_actual,))
            id_recibo = cursor.lastrowid

            for id_producto, cantidad in items:
                cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = ?", (id_producto,))
                res = cursor.fetchone()
                if not res:
                    raise _VentaRechazada(f"Un producto del carrito (ID {id_producto}) ya no existe.")

                nombre_producto, precio_unitario, stock_actual = res
                if stock_actual < cantidad:
                    raise _VentaRechazada(
                        f"Stock insuficiente de '{nombre_producto}'. Solo quedan {formatear_numero(stock_actual)} unidades."
                    )

                cursor.execute(
                    "UPDATE productos SET stock = ? WHERE id = ?", (stock_actual - cantidad, id_producto)
                )
                total = cantidad * precio_unitario
                total_venta += total
                cursor.execute("""
                    INSERT INTO ventas (producto_id, nombre_producto, cantidad, total, fecha, recibo_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_producto, nombre_producto, cantidad, total, fecha_actual, id_recibo))

            if pago is None:
                pago = total_venta
            elif round(pago, 2) < round(total_venta, 2):
                raise _VentaRechazada(
                    f"El pago ({formatear_precio(pago)}) no alcanza para el total ({formatear_precio(total_venta)})."
                )
            cursor.execute("UPDATE recibos SET total = ?, pago = ? WHERE id = ?", (total_venta, pago, id_recibo))

        return True, f"Venta realizada. Total: {formatear_precio(total_venta)}", id_recibo
    except _VentaRechazada as rechazo:
        return False, str(rechazo), None
    finally:
        conexion.close()


def obtener_recibo(id_recibo):
    """
    Retorna un diccionario con los datos del recibo (id, fecha, total, pago) y
    sus 'lineas' (nombre_producto, cantidad, total, anulada), o None si no existe.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, fecha, total, pago FROM recibos WHERE id = ?", (id_recibo,))
        recibo = cursor.fetchone()
        if not recibo:
            return None
        cursor.execute(
            "SELECT nombre_producto, cantidad, total, anulada FROM ventas WHERE recibo_id = ? ORDER BY id",
            (id_recibo,)
        )
        return {**dict(recibo), "lineas": cursor.fetchall()}
    finally:
        conexion.close()


def _filtro_fechas(desde, hasta):
    """Condiciones SQL y parámetros para filtrar ventas entre dos fechas 'AAAA-MM-DD' (ambas incluidas)."""
    condiciones, parametros = [], []
    if desde:
        condiciones.append("date(fecha) >= ?")
        parametros.append(desde)
    if hasta:
        condiciones.append("date(fecha) <= ?")
        parametros.append(hasta)
    return condiciones, parametros


def obtener_ventas(desde=None, hasta=None):
    """
    Retorna las ventas ordenadas de más reciente a más antigua, con las
    columnas id, producto_id, nombre_producto, cantidad, total, fecha, anulada
    y recibo_id (None en las ventas hechas antes de que existieran los recibos).
    'desde' y 'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    """
    condiciones, parametros = _filtro_fechas(desde, hasta)

    consulta = "SELECT id, producto_id, nombre_producto, cantidad, total, fecha, anulada, recibo_id FROM ventas"
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


def obtener_mas_vendidos(desde=None, hasta=None):
    """
    Ranking de productos por unidades vendidas (sin contar ventas anuladas),
    con las columnas nombre, unidades y total, de más a menos vendido.
    'desde' y 'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    """
    condiciones, parametros = _filtro_fechas(desde, hasta)
    condiciones.insert(0, "v.anulada = 0")

    # Se usa el nombre actual del producto, para que una venta hecha antes de
    # renombrarlo se sume en la misma fila
    consulta = f"""
        SELECT COALESCE(p.nombre, MAX(v.nombre_producto)) AS nombre,
               SUM(v.cantidad) AS unidades, SUM(v.total) AS total
        FROM ventas v LEFT JOIN productos p ON p.id = v.producto_id
        WHERE {" AND ".join(condiciones)}
        GROUP BY v.producto_id
        ORDER BY unidades DESC, total DESC
    """

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

        return True, (
            f"Entrada registrada: {formatear_cambio(cantidad)} de '{nombre_producto}'. "
            f"Stock nuevo: {formatear_numero(stock_actual + cantidad)}."
        )
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
