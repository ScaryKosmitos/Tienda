import sys
import tkinter as tk
from tkinter import messagebox

import base_datos as db
import interfaz

if __name__ == "__main__":
    try:
        db.inicializar_db()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error al iniciar", f"No se pudo inicializar la base de datos:\n{error}")
        root.destroy()
        sys.exit(1)

    interfaz.iniciar_app()

    