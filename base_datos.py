import sqlite3
from datetime import datetime

def conectar():
    """Establece conexión con la base de datos SQLite."""
    return sqlite3.connect("inventario.db")

def inicializar_db():
    """Crea las tablas 'productos' y 'ventas' si no existen."""
    conexion = conectar()
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
    conexion.commit()
    conexion.close()

# --- OPERACIONES CRUD DE PRODUCTOS ---

def agregar_producto(nombre, categoria, precio, stock):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO productos (nombre, categoria, precio, stock)
        VALUES (?, ?, ?, ?)
    """, (nombre, categoria, precio, stock))
    conexion.commit()
    conexion.close()

def obtener_productos():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conexion.close()
    return productos

def buscar_producto_por_nombre(texto_busqueda):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos WHERE nombre LIKE ?", (f"%{texto_busqueda}%",))
    resultados = cursor.fetchall()
    conexion.close()
    return resultados

def actualizar_producto(id_producto, nombre, categoria, precio, stock):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE productos
        SET nombre = ?, categoria = ?, precio = ?, stock = ?
        WHERE id = ?
    """, (nombre, categoria, precio, stock, id_producto))
    conexion.commit()
    conexion.close()

def eliminar_producto(id_producto):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
    conexion.commit()
    conexion.close()

# --- MÓDULO DE VENTAS ---

def registrar_venta(id_producto, nombre_producto, cantidad, precio_unitario):
    """
    Verifica stock, lo descuenta de la tabla productos y registra la venta con fecha y hora.
    """
    conexion = conectar()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT stock FROM productos WHERE id = ?", (id_producto,))
    res = cursor.fetchone()
    if not res:
        conexion.close()
        return False, "Producto no encontrado."
    
    stock_actual = res[0]
    if stock_actual < cantidad:
        conexion.close()
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
    
    conexion.commit()
    conexion.close()
    return True, f"Venta realizada. Total: ${total:,.2f}"

def obtener_ventas():
    """Retorna todas las ventas realizadas ordenadas de más reciente a más antigua."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
    ventas = cursor.fetchall()
    conexion.close()
    return ventas