"""
Piezas de interfaz que comparten la ventana principal y las ventanas secundarias.
"""
import sqlite3
from functools import wraps
from tkinter import messagebox, ttk

# Los productos con menos unidades que esto se marcan en rojo
STOCK_BAJO = 5

# Errores que se muestran como "Error de Base de Datos" (archivo bloqueado, permisos, etc.)
ERRORES_BD = (sqlite3.Error, OSError)


def mostrar_error_bd(error, parent=None):
    """Aviso claro cuando falla el acceso a la base de datos."""
    messagebox.showerror(
        "Error de Base de Datos",
        f"Ocurrió un problema al acceder a la base de datos:\n{error}",
        parent=parent
    )


def manejar_errores_bd(func):
    """Evita que un error inesperado de la base de datos cierre la aplicación
    sin explicación: muestra un aviso claro en su lugar."""
    @wraps(func)
    def envoltorio(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ERRORES_BD as error:
            mostrar_error_bd(error, parent=self)
    return envoltorio


def crear_tabla(padre, columnas, **opciones):
    """
    Crea una tabla (Treeview) con barra de desplazamiento dentro de 'padre'.
    'columnas' es una lista de (clave, título, opciones_de_columna), por ejemplo:
        ("total", "Total ($)", {"width": 90, "anchor": "e"})
    Retorna la tabla.
    """
    tabla = ttk.Treeview(padre, columns=[clave for clave, _, _ in columnas], show="headings", **opciones)
    for clave, titulo, opciones_columna in columnas:
        tabla.heading(clave, text=titulo)
        tabla.column(clave, **opciones_columna)

    scrollbar = ttk.Scrollbar(padre, orient="vertical", command=tabla.yview)
    tabla.configure(yscroll=scrollbar.set)
    tabla.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return tabla


def vaciar_tabla(tabla):
    """Quita todas las filas de una tabla."""
    tabla.delete(*tabla.get_children())
