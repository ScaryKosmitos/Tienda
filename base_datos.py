import math
import os
import re
import sys
import sqlite3
from datetime import datetime

from formato import clave_orden, formatear_cambio, formatear_numero, formatear_precio, sin_tildes

# Límites de unidades y de precio por producto: evitan números tan grandes que
# SQLite no puede guardarlos o que desarman el recibo (y que casi siempre son un
# error al escribir)
STOCK_MAXIMO = 1_000_000
PRECIO_MAXIMO = 100_000_000

# Medios de pago de las ventas y de los abonos del fiado
EFECTIVO = "Efectivo"
NEQUI = "Nequi"
MEDIOS = (EFECTIVO, NEQUI)

# El cambio de una venta no puede pasar de esto. Si pasa, casi seguro se
# escaneó un código de barras en el campo del pago (ej: 7702004003501)
CAMBIO_MAXIMO = 1_000_000

# Códigos de barras: números (EAN-13, UPC...) o letras, números y guiones (Code 128)
_CODIGO_VALIDO = re.compile(r"[0-9A-Za-z-]{1,32}")

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
                    stock INTEGER NOT NULL,
                    codigo_barras TEXT
                )
            """)

            # Las bases de datos anteriores no tienen la columna 'codigo_barras'.
            # El índice impide que dos productos tengan el mismo código (los
            # productos sin código quedan en NULL, que no cuenta como repetido)
            columnas_productos = [fila[1] for fila in cursor.execute("PRAGMA table_info(productos)")]
            if "codigo_barras" not in columnas_productos:
                cursor.execute("ALTER TABLE productos ADD COLUMN codigo_barras TEXT")
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_codigo ON productos (codigo_barras)"
            )

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

            # Clientes a los que se les fía
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL
                )
            """)

            # Cuenta de cada cliente: lo fiado suma (monto positivo) y los abonos y
            # las ventas anuladas restan (monto negativo). Lo que debe es la suma de
            # los movimientos no anulados. Los abonos mal registrados se anulan, no se borran
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fiado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL REFERENCES clientes (id),
                    fecha TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    monto REAL NOT NULL,
                    recibo_id INTEGER REFERENCES recibos (id),
                    anulado INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Las ventas fiadas guardan en el recibo a quién se le fió
            columnas_recibos = [fila[1] for fila in cursor.execute("PRAGMA table_info(recibos)")]
            if "cliente_id" not in columnas_recibos:
                cursor.execute("ALTER TABLE recibos ADD COLUMN cliente_id INTEGER REFERENCES clientes (id)")

            # Medio de pago de cada venta (NULL en las fiadas) y de cada abono. Lo
            # registrado antes de que existiera se pagó en efectivo
            if "medio" not in columnas_recibos:
                cursor.execute("ALTER TABLE recibos ADD COLUMN medio TEXT")
                cursor.execute("UPDATE recibos SET medio = 'Efectivo' WHERE cliente_id IS NULL")
            columnas_fiado = [fila[1] for fila in cursor.execute("PRAGMA table_info(fiado)")]
            if "medio" not in columnas_fiado:
                cursor.execute("ALTER TABLE fiado ADD COLUMN medio TEXT")
                cursor.execute("UPDATE fiado SET medio = 'Efectivo' WHERE tipo = 'Abono'")

            # Índices: permiten buscar por fecha, recibo o cliente sin recorrer la
            # tabla entera, para que la tienda siga ágil con años de ventas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas (fecha)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_recibo ON ventas (recibo_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fiado_cliente ON fiado (cliente_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fiado_fecha ON fiado (fecha)")

            # Base: el efectivo con el que empieza la caja cada día
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caja_base (
                    fecha TEXT PRIMARY KEY,
                    monto REAL NOT NULL
                )
            """)

            # Salidas: efectivo que se saca de la caja (pagos a proveedores, gastos,
            # retiros). Las registradas por error se anulan, no se borran
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS salidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    monto REAL NOT NULL,
                    motivo TEXT NOT NULL,
                    anulada INTEGER NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_salidas_fecha ON salidas (fecha)")
    finally:
        conexion.close()

# --- OPERACIONES CRUD DE PRODUCTOS ---

def _categoria_existente(cursor, categoria, excluir_id=None):
    """
    Si ya existe una categoría igual sin importar mayúsculas ni tildes (ej:
    'lacteos' y 'Lácteos'), retorna la que ya existe para no crear duplicados.
    'excluir_id' ignora al producto que se está editando, para que pueda
    corregir la forma de escribir su propia categoría.
    """
    cursor.execute("SELECT DISTINCT categoria FROM productos WHERE id != ?", (excluir_id or -1,))
    for (existente,) in cursor.fetchall():
        if sin_tildes(existente) == sin_tildes(categoria):
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

def leer_codigo(texto):
    """
    Limpia el código de barras escrito o escaneado. Retorna (codigo, error):
    codigo es None si el campo está vacío (producto sin código).
    """
    codigo = texto.strip()
    if not codigo:
        return None, None
    if not _CODIGO_VALIDO.fullmatch(codigo):
        return None, "El código de barras solo puede tener números, letras y guiones (máximo 32)."
    return codigo, None

def codigo_repetido(codigo, excluir_id=None):
    """Si otro producto ya tiene ese código de barras, retorna su nombre; si no, None."""
    if not codigo:
        return None
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT nombre FROM productos WHERE codigo_barras = ? AND id != ?", (codigo, excluir_id or -1)
        )
        res = cursor.fetchone()
        return res["nombre"] if res else None
    finally:
        conexion.close()

def _mensaje_codigo_repetido(codigo, nombre):
    return f"El código {codigo} ya pertenece a '{nombre}'."

def buscar_por_codigo(codigo):
    """Retorna el producto con ese código de barras, o None si no está registrado."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos WHERE codigo_barras = ?", (codigo.strip(),))
        return cursor.fetchone()
    finally:
        conexion.close()

def _mensaje_repetido(existente):
    return f"Ya existe un producto llamado '{existente}'. Usa otro nombre o edita el que ya existe."

def categoria_es_nueva(categoria):
    """True si no hay ningún producto con esa categoría (sin importar mayúsculas ni tildes)."""
    return all(sin_tildes(c) != sin_tildes(categoria) for c in obtener_categorias())

def agregar_producto(nombre, categoria, precio, stock, codigo=None):
    """Retorna (exito: bool, mensaje: str). Se permite registrar un producto
    con stock 0 (por ejemplo, uno que todavía no ha llegado). 'codigo' es el
    código de barras, o None si el producto no tiene."""
    error = validar_producto(precio, stock)
    if error:
        return False, error
    codigo, error = leer_codigo(codigo or "")
    if error:
        return False, error
    otro = codigo_repetido(codigo)
    if otro:
        return False, _mensaje_codigo_repetido(codigo, otro)

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            existente = _nombre_repetido(cursor, nombre)
            if existente:
                return False, _mensaje_repetido(existente)
            categoria = _categoria_existente(cursor, categoria)
            cursor.execute("""
                INSERT INTO productos (nombre, categoria, precio, stock, codigo_barras)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, categoria, precio, stock, codigo))
            if stock > 0:
                _registrar_movimiento(cursor, cursor.lastrowid, nombre, stock, "Stock inicial")
        return True, "Producto agregado."
    finally:
        conexion.close()

def buscar_productos(texto="", categoria=None, stock_menor_a=None):
    """
    Filtra productos por nombre (texto parcial, sin importar tildes ni
    mayúsculas) o código de barras, categoría exacta y/o stock menor a un valor. Los filtros
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
        productos = [
            p for p in productos
            if buscado in sin_tildes(p["nombre"]) or (p["codigo_barras"] and texto.strip() in p["codigo_barras"])
        ]
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

def actualizar_producto(id_producto, nombre, categoria, precio, stock, codigo=None):
    """Retorna (exito: bool, mensaje: str). El stock puede quedar en 0 (agotado),
    pero nunca negativo, y el precio siempre debe ser mayor a 0. 'codigo' es el
    código de barras, o None para dejar el producto sin código."""
    error = validar_producto(precio, stock)
    if error:
        return False, error
    codigo, error = leer_codigo(codigo or "")
    if error:
        return False, error
    otro = codigo_repetido(codigo, excluir_id=id_producto)
    if otro:
        return False, _mensaje_codigo_repetido(codigo, otro)

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
                SET nombre = ?, categoria = ?, precio = ?, stock = ?, codigo_barras = ?
                WHERE id = ?
            """, (nombre, categoria, precio, stock, codigo, id_producto))

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
    """Retorna el producto (columnas id, nombre, categoria, precio, stock, codigo_barras) o None si no existe."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos WHERE id = ?", (id_producto,))
        return cursor.fetchone()
    finally:
        conexion.close()


def validar_pago(pago, total):
    """Retorna un mensaje de error si el pago no alcanza o es exagerado, o None si está bien."""
    if round(pago, 2) < round(total, 2):
        return f"Faltan {formatear_precio(total - pago)} para completar el pago."
    if pago - total > CAMBIO_MAXIMO:
        return (
            f"El cambio pasaría de {formatear_precio(CAMBIO_MAXIMO)}. "
            "¿Se escaneó un código de barras en este campo? Revisa con cuánto paga el cliente."
        )
    return None


def registrar_venta_carrito(items, pago=None, cliente_id=None, medio=EFECTIVO):
    """
    Registra la venta de varios productos a la vez. 'items' es una lista de
    (id_producto, cantidad). Verifica el stock de cada uno, lo descuenta y
    registra una línea por producto, todas con la misma fecha y hora y el
    mismo recibo. 'pago' es el dinero que entregó el cliente (None = pago exacto).
    Si se da 'cliente_id', la venta completa se le fía a ese cliente (pago = 0).
    'medio' es EFECTIVO o NEQUI; por Nequi se paga el total exacto.
    El nombre y el precio se leen de la base de datos en la misma transacción.
    Si un solo producto falla, no se registra nada: la venta es todo o nada.
    Retorna (exito: bool, mensaje: str, id_recibo: int o None).
    """
    if not items:
        return False, "El carrito está vacío.", None
    if cliente_id is not None:
        medio = None
    elif medio not in MEDIOS:
        return False, f"Medio de pago desconocido: {medio}", None

    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_venta = 0.0

            if cliente_id is not None:
                cursor.execute("SELECT 1 FROM clientes WHERE id = ?", (cliente_id,))
                if not cursor.fetchone():
                    raise _VentaRechazada("El cliente ya no existe.")

            # El total y el pago se completan al final, cuando se conoce el total
            cursor.execute(
                "INSERT INTO recibos (fecha, total, pago, cliente_id, medio) VALUES (?, 0, 0, ?, ?)",
                (fecha_actual, cliente_id, medio),
            )
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

            if cliente_id is not None:
                pago = 0
                cursor.execute(
                    "INSERT INTO fiado (cliente_id, fecha, tipo, monto, recibo_id) VALUES (?, ?, 'Fiado', ?, ?)",
                    (cliente_id, fecha_actual, total_venta, id_recibo),
                )
            elif pago is None or medio == NEQUI:
                pago = total_venta
            else:
                error = validar_pago(pago, total_venta)
                if error:
                    raise _VentaRechazada(error)
            cursor.execute("UPDATE recibos SET total = ?, pago = ? WHERE id = ?", (total_venta, pago, id_recibo))

        if cliente_id is not None:
            return True, f"Venta fiada. Total: {formatear_precio(total_venta)}", id_recibo
        if medio == NEQUI:
            return True, f"Venta pagada por Nequi. Total: {formatear_precio(total_venta)}", id_recibo
        return True, f"Venta realizada. Total: {formatear_precio(total_venta)}", id_recibo
    except _VentaRechazada as rechazo:
        return False, str(rechazo), None
    finally:
        conexion.close()


def obtener_recibo(id_recibo):
    """
    Retorna un diccionario con los datos del recibo (id, fecha, total, pago,
    medio y cliente, que es el nombre del cliente si la venta fue fiada o None) y sus
    'lineas' (nombre_producto, cantidad, total, anulada), o None si no existe.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT r.id, r.fecha, r.total, r.pago, r.medio, c.nombre AS cliente
            FROM recibos r LEFT JOIN clientes c ON c.id = r.cliente_id
            WHERE r.id = ?
        """, (id_recibo,))
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


def _filtro_fechas(desde, hasta, columna="fecha"):
    """
    Condiciones SQL y parámetros para filtrar entre dos fechas 'AAAA-MM-DD'
    (ambas incluidas). Compara el texto de la fecha y hora completa (en vez de
    usar date(...)), para que SQLite pueda usar el índice de la columna.
    """
    condiciones, parametros = [], []
    if desde:
        condiciones.append(f"{columna} >= ?")
        parametros.append(f"{desde} 00:00:00")
    if hasta:
        condiciones.append(f"{columna} <= ?")
        parametros.append(f"{hasta} 23:59:59")
    return condiciones, parametros


def obtener_ventas(desde=None, hasta=None, limite=None, despues_de=None):
    """
    Retorna las ventas ordenadas de más reciente a más antigua, con las
    columnas id, producto_id, nombre_producto, cantidad, total, fecha, anulada,
    recibo_id (None en las ventas hechas antes de que existieran los recibos),
    cliente (nombre del cliente si la venta fue fiada, o None) y medio
    (EFECTIVO o NEQUI; None si fue fiada).
    'desde' y 'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    'limite' retorna solo las más recientes (None = todas). 'despues_de' es la
    última venta ya mostrada (para el botón "Mostrar más"): se retornan las
    anteriores a ella.
    """
    condiciones, parametros = _filtro_fechas(desde, hasta, "v.fecha")
    if despues_de is not None:
        condiciones.append("(v.fecha, v.id) < (?, ?)")
        parametros += [despues_de["fecha"], despues_de["id"]]

    consulta = """
        SELECT v.id, v.producto_id, v.nombre_producto, v.cantidad, v.total, v.fecha, v.anulada, v.recibo_id,
               c.nombre AS cliente,
               CASE WHEN r.cliente_id IS NOT NULL THEN NULL ELSE COALESCE(r.medio, 'Efectivo') END AS medio
        FROM ventas v
        LEFT JOIN recibos r ON r.id = v.recibo_id
        LEFT JOIN clientes c ON c.id = r.cliente_id
    """
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)
    # Por fecha (y no solo por id) para que SQLite recorra el índice de la fecha
    # ya ordenado: si no, con un año de ventas tendría que ordenarlas todas
    consulta += " ORDER BY v.fecha DESC, v.id DESC"
    if limite is not None:
        consulta += " LIMIT ?"
        parametros.append(limite)

    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()


def resumen_ventas(desde=None, hasta=None):
    """
    Totales de las ventas del período (sin contar las anuladas): total, nequi,
    fiado y lineas (cantidad de líneas de venta). Además 'todas', la cantidad
    de líneas incluyendo las anuladas. Los calcula SQLite sin traer cada venta.
    """
    condiciones, parametros = _filtro_fechas(desde, hasta, "v.fecha")
    consulta = """
        SELECT COALESCE(SUM(CASE WHEN v.anulada = 0 THEN v.total END), 0) AS total,
               COALESCE(SUM(CASE WHEN v.anulada = 0 AND r.cliente_id IS NULL AND r.medio = 'Nequi'
                                 THEN v.total END), 0) AS nequi,
               COALESCE(SUM(CASE WHEN v.anulada = 0 AND r.cliente_id IS NOT NULL THEN v.total END), 0) AS fiado,
               COUNT(CASE WHEN v.anulada = 0 THEN 1 END) AS lineas,
               COUNT(*) AS todas
        FROM ventas v LEFT JOIN recibos r ON r.id = v.recibo_id
    """
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)

    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        return dict(cursor.fetchone())
    finally:
        conexion.close()


def obtener_mas_vendidos(desde=None, hasta=None):
    """
    Ranking de productos por unidades vendidas (sin contar ventas anuladas),
    con las columnas nombre, unidades y total, de más a menos vendido.
    'desde' y 'hasta' son fechas 'AAAA-MM-DD' opcionales (ambas incluidas).
    """
    condiciones, parametros = _filtro_fechas(desde, hasta, "v.fecha")
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
                cursor.execute("""
                    SELECT v.producto_id, v.nombre_producto, v.cantidad, v.total, v.anulada, v.recibo_id, r.cliente_id
                    FROM ventas v LEFT JOIN recibos r ON r.id = v.recibo_id
                    WHERE v.id = ?
                """, (id_venta,))
                res = cursor.fetchone()
                if not res:
                    raise _VentaRechazada(f"La venta {id_venta} no existe.")
                producto_id, nombre_producto, cantidad, total, anulada, recibo_id, cliente_id = res
                if anulada:
                    raise _VentaRechazada(f"La venta {id_venta} ({nombre_producto}) ya estaba anulada.")

                cursor.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
                (stock_actual,) = cursor.fetchone()
                if stock_actual + cantidad > STOCK_MAXIMO:
                    raise _VentaRechazada(
                        f"Al anular, '{nombre_producto}' pasaría de {formatear_numero(STOCK_MAXIMO)} unidades, "
                        "que es el máximo permitido. Corrige primero su stock."
                    )
                cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (stock_actual + cantidad, producto_id))
                cursor.execute("UPDATE ventas SET anulada = 1 WHERE id = ?", (id_venta,))
                _registrar_movimiento(cursor, producto_id, nombre_producto, cantidad, "Anulación de venta")
                # Si la venta fue fiada, lo anulado se le descuenta de la deuda al cliente
                if cliente_id is not None:
                    cursor.execute(
                        "INSERT INTO fiado (cliente_id, fecha, tipo, monto, recibo_id) VALUES (?, ?, ?, ?, ?)",
                        (cliente_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         f"Venta anulada ({nombre_producto})", -total, recibo_id),
                    )
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

def contar_entradas():
    """Cantidad total de movimientos de stock."""
    conexion = conectar()
    try:
        return conexion.execute("SELECT COUNT(*) FROM entradas").fetchone()[0]
    finally:
        conexion.close()

def obtener_entradas(limite=None, antes_de_id=None):
    """
    Retorna los movimientos de stock (entradas, stock inicial, ajustes
    manuales y anulaciones de ventas) como (id, nombre_producto, cantidad, fecha, motivo), del más
    reciente al más antiguo. 'limite' retorna solo los más recientes (None = todos).
    'antes_de_id' retorna solo los anteriores a ese movimiento (para el botón "Mostrar más").
    """
    consulta = "SELECT id, nombre_producto, cantidad, fecha, motivo FROM entradas"
    parametros = []
    if antes_de_id is not None:
        consulta += " WHERE id < ?"
        parametros.append(antes_de_id)
    consulta += " ORDER BY id DESC"
    if limite is not None:
        consulta += " LIMIT ?"
        parametros.append(limite)
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()

# --- FIADO ---

def _nombre_cliente_repetido(cursor, nombre, excluir_id=None):
    """Si ya hay otro cliente con ese nombre (sin importar mayúsculas ni tildes), retorna su nombre; si no, None."""
    cursor.execute("SELECT nombre FROM clientes WHERE id != ?", (excluir_id or -1,))
    for (existente,) in cursor.fetchall():
        if sin_tildes(existente) == sin_tildes(nombre):
            return existente
    return None

def _validar_nombre_cliente(nombre):
    if not nombre:
        return "Escribe el nombre del cliente."
    if len(nombre) > 60:
        return "El nombre no puede tener más de 60 letras."
    return None

def _leer_clientes(id_cliente=None):
    """Clientes con lo que deben (todos, o solo 'id_cliente'), sin ordenar."""
    consulta = """
        SELECT c.id, c.nombre, COALESCE(SUM(CASE WHEN f.anulado = 0 THEN f.monto END), 0) AS debe,
               MAX(f.fecha) AS ultimo
        FROM clientes c LEFT JOIN fiado f ON f.cliente_id = c.id
    """
    parametros = []
    if id_cliente is not None:
        consulta += " WHERE c.id = ?"
        parametros.append(id_cliente)
    consulta += " GROUP BY c.id"
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        # Se redondea para que las sumas de decimales no dejen deudas de $0,0000001
        return [{**dict(fila), "debe": round(fila["debe"], 2)} for fila in cursor.fetchall()]
    finally:
        conexion.close()

def obtener_clientes(texto=""):
    """
    Retorna los clientes como diccionarios con id, nombre, debe (lo que debe;
    negativo si tiene saldo a favor) y ultimo (fecha del último movimiento o
    None), de quien más debe a quien menos y luego por nombre. 'texto' filtra
    por nombre sin importar tildes ni mayúsculas.
    """
    clientes = _leer_clientes()

    if texto.strip():
        buscado = sin_tildes(texto.strip())
        clientes = [c for c in clientes if buscado in sin_tildes(c["nombre"])]
    clientes.sort(key=lambda c: (-c["debe"], clave_orden(c["nombre"])))
    return clientes

def obtener_cliente(id_cliente):
    """El cliente (como en obtener_clientes) o None si no existe."""
    clientes = _leer_clientes(id_cliente)
    return clientes[0] if clientes else None

def agregar_cliente(nombre):
    """Retorna (exito: bool, mensaje: str, id_cliente o None)."""
    nombre = " ".join(nombre.split())
    error = _validar_nombre_cliente(nombre)
    if error:
        return False, error, None
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            existente = _nombre_cliente_repetido(cursor, nombre)
            if existente:
                return False, f"Ya hay un cliente llamado '{existente}'.", None
            cursor.execute("INSERT INTO clientes (nombre) VALUES (?)", (nombre,))
            return True, f"Cliente '{nombre}' agregado.", cursor.lastrowid
    finally:
        conexion.close()

def renombrar_cliente(id_cliente, nombre):
    """Retorna (exito: bool, mensaje: str)."""
    nombre = " ".join(nombre.split())
    error = _validar_nombre_cliente(nombre)
    if error:
        return False, error
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            existente = _nombre_cliente_repetido(cursor, nombre, excluir_id=id_cliente)
            if existente:
                return False, f"Ya hay un cliente llamado '{existente}'."
            cursor.execute("UPDATE clientes SET nombre = ? WHERE id = ?", (nombre, id_cliente))
            if cursor.rowcount == 0:
                return False, "El cliente ya no existe."
        return True, "Nombre cambiado."
    finally:
        conexion.close()

def eliminar_cliente(id_cliente):
    """
    Borra un cliente que nunca tuvo movimientos (por ejemplo, uno creado por
    error). Los que tienen historial no se borran, para no perder la cuenta.
    Retorna (exito: bool, mensaje: str).
    """
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT 1 FROM fiado WHERE cliente_id = ? LIMIT 1", (id_cliente,))
            if cursor.fetchone():
                return False, "No se puede eliminar: el cliente tiene fiados o abonos registrados."
            cursor.execute("DELETE FROM clientes WHERE id = ?", (id_cliente,))
        return True, "Cliente eliminado."
    finally:
        conexion.close()

def obtener_movimientos_fiado(id_cliente, limite=None):
    """
    Movimientos de la cuenta del cliente (id, fecha, tipo, monto, recibo_id,
    anulado y medio, que solo tienen los abonos), del más reciente al más antiguo.
    'limite' retorna solo los más recientes (None = todos).
    """
    consulta = "SELECT id, fecha, tipo, monto, recibo_id, anulado, medio FROM fiado WHERE cliente_id = ? ORDER BY id DESC"
    parametros = [id_cliente]
    if limite is not None:
        consulta += " LIMIT ?"
        parametros.append(limite)
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()

def registrar_abono(id_cliente, monto, medio=EFECTIVO):
    """El cliente paga parte (o todo) lo que debe, en efectivo o por Nequi. Retorna (exito: bool, mensaje: str)."""
    if medio not in MEDIOS:
        return False, f"Medio de pago desconocido: {medio}"
    if not math.isfinite(monto) or monto <= 0:
        return False, "El abono debe ser mayor a 0."
    cliente = obtener_cliente(id_cliente)
    if not cliente:
        return False, "El cliente ya no existe."
    if cliente["debe"] <= 0:
        return False, f"{cliente['nombre']} no debe nada."
    if round(monto, 2) > cliente["debe"]:
        return False, f"{cliente['nombre']} solo debe {formatear_precio(cliente['debe'])}."

    conexion = conectar()
    try:
        with conexion:
            conexion.execute(
                "INSERT INTO fiado (cliente_id, fecha, tipo, monto, medio) VALUES (?, ?, 'Abono', ?, ?)",
                (id_cliente, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), -monto, medio),
            )
    finally:
        conexion.close()
    queda = round(cliente["debe"] - monto, 2)
    if queda <= 0:
        return True, f"Abono de {formatear_precio(monto)} registrado. {cliente['nombre']} quedó al día."
    return True, (
        f"Abono de {formatear_precio(monto)} registrado. "
        f"{cliente['nombre']} queda debiendo {formatear_precio(queda)}."
    )

def anular_abono(id_movimiento):
    """Anula un abono mal registrado: la deuda vuelve a subir. Retorna (exito: bool, mensaje: str)."""
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT tipo, monto, anulado FROM fiado WHERE id = ?", (id_movimiento,))
            res = cursor.fetchone()
            if not res or res["tipo"] != "Abono":
                return False, "Ese movimiento no es un abono."
            if res["anulado"]:
                return False, "Ese abono ya estaba anulado."
            cursor.execute("UPDATE fiado SET anulado = 1 WHERE id = ?", (id_movimiento,))
        return True, f"Se anuló el abono de {formatear_precio(-res['monto'])}."
    finally:
        conexion.close()

# --- CAJA ---

def _rango_dia(fecha):
    """('2026-09-24 00:00:00', '2026-09-24 23:59:59'): para buscar un día usando el índice de la fecha."""
    return f"{fecha} 00:00:00", f"{fecha} 23:59:59"

def validar_monto_caja(monto):
    """Retorna un mensaje de error si el monto de una base o una salida no es válido, o None."""
    if not math.isfinite(monto) or monto < 0:
        return "El monto no puede ser negativo."
    if monto > PRECIO_MAXIMO:
        return f"El monto no puede ser mayor a {formatear_precio(PRECIO_MAXIMO)}."
    return None

def obtener_base(fecha):
    """Base de la caja del día 'AAAA-MM-DD', o None si no se registró."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT monto FROM caja_base WHERE fecha = ?", (fecha,))
        res = cursor.fetchone()
        return res["monto"] if res else None
    finally:
        conexion.close()

def poner_base(fecha, monto):
    """Registra (o corrige) la base de la caja del día 'AAAA-MM-DD'. Retorna (exito: bool, mensaje: str)."""
    error = validar_monto_caja(monto)
    if error:
        return False, error
    conexion = conectar()
    try:
        with conexion:
            conexion.execute(
                "INSERT INTO caja_base (fecha, monto) VALUES (?, ?) "
                "ON CONFLICT (fecha) DO UPDATE SET monto = excluded.monto",
                (fecha, monto),
            )
        return True, f"Base registrada: {formatear_precio(monto)}."
    finally:
        conexion.close()

def registrar_salida(monto, motivo):
    """Efectivo que se saca de la caja ahora. Retorna (exito: bool, mensaje: str)."""
    motivo = " ".join(motivo.split())
    error = validar_monto_caja(monto)
    if error:
        return False, error
    if monto == 0:
        return False, "El monto debe ser mayor a 0."
    if not motivo:
        return False, "Escribe el motivo (ej: pago al proveedor de gaseosas)."
    if len(motivo) > 100:
        return False, "El motivo no puede tener más de 100 letras."
    conexion = conectar()
    try:
        with conexion:
            conexion.execute(
                "INSERT INTO salidas (fecha, monto, motivo) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monto, motivo),
            )
        return True, f"Salida de {formatear_precio(monto)} registrada."
    finally:
        conexion.close()

def obtener_salidas(fecha):
    """Salidas del día 'AAAA-MM-DD' (id, fecha, monto, motivo, anulada), de la más reciente a la más antigua."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, fecha, monto, motivo, anulada FROM salidas WHERE fecha BETWEEN ? AND ? ORDER BY id DESC",
            _rango_dia(fecha),
        )
        return cursor.fetchall()
    finally:
        conexion.close()

def anular_salida(id_salida):
    """Anula una salida registrada por error. Retorna (exito: bool, mensaje: str)."""
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT monto, anulada FROM salidas WHERE id = ?", (id_salida,))
            res = cursor.fetchone()
            if not res:
                return False, "La salida no existe."
            if res["anulada"]:
                return False, "Esa salida ya estaba anulada."
            cursor.execute("UPDATE salidas SET anulada = 1 WHERE id = ?", (id_salida,))
        return True, f"Se anuló la salida de {formatear_precio(res['monto'])}."
    finally:
        conexion.close()

def resumen_caja(fecha):
    """
    Resumen del día 'AAAA-MM-DD' para el cierre de caja. Retorna un
    diccionario con: base (None si no se registró), ventas_efectivo,
    abonos_efectivo, salidas y en_caja (lo que debería haber en efectivo:
    base + ventas y abonos en efectivo - salidas); ventas_nequi y
    abonos_nequi; fiado (lo que se fió ese día) y total_vendido.
    Las ventas anuladas no cuentan.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN r.cliente_id IS NULL AND COALESCE(r.medio, 'Efectivo') = 'Efectivo'
                                     THEN v.total END), 0) AS efectivo,
                   COALESCE(SUM(CASE WHEN r.cliente_id IS NULL AND r.medio = 'Nequi' THEN v.total END), 0) AS nequi,
                   COALESCE(SUM(CASE WHEN r.cliente_id IS NOT NULL THEN v.total END), 0) AS fiado,
                   COALESCE(SUM(v.total), 0) AS total
            FROM ventas v LEFT JOIN recibos r ON r.id = v.recibo_id
            WHERE v.anulada = 0 AND v.fecha BETWEEN ? AND ?
        """, _rango_dia(fecha))
        ventas = cursor.fetchone()
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN COALESCE(medio, 'Efectivo') = 'Efectivo' THEN -monto END), 0) AS efectivo,
                   COALESCE(SUM(CASE WHEN medio = 'Nequi' THEN -monto END), 0) AS nequi
            FROM fiado WHERE tipo = 'Abono' AND anulado = 0 AND fecha BETWEEN ? AND ?
        """, _rango_dia(fecha))
        abonos = cursor.fetchone()
        cursor.execute(
            "SELECT COALESCE(SUM(monto), 0) FROM salidas WHERE anulada = 0 AND fecha BETWEEN ? AND ?",
            _rango_dia(fecha),
        )
        salidas = cursor.fetchone()[0]
        cursor.execute("SELECT monto FROM caja_base WHERE fecha = ?", (fecha,))
        base = cursor.fetchone()
    finally:
        conexion.close()

    base = base["monto"] if base else None
    return {
        "base": base,
        "ventas_efectivo": ventas["efectivo"],
        "abonos_efectivo": abonos["efectivo"],
        "salidas": salidas,
        "en_caja": round((base or 0) + ventas["efectivo"] + abonos["efectivo"] - salidas, 2),
        "ventas_nequi": ventas["nequi"],
        "abonos_nequi": abonos["nequi"],
        "fiado": ventas["fiado"],
        "total_vendido": ventas["total"],
    }
