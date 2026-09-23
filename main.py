import sys
import tkinter as tk
from tkinter import messagebox

import base_datos as db
import interfaz
import respaldar

if __name__ == "__main__":
    try:
        db.inicializar_db()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error al iniciar", f"No se pudo inicializar la base de datos:\n{error}")
        root.destroy()
        sys.exit(1)

    # Un fallo del respaldo no debe impedir usar la tienda: solo se avisa
    try:
        respaldar.respaldo_automatico()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("Respaldo automático", f"No se pudo crear el respaldo de hoy:\n{error}")
        root.destroy()

    interfaz.iniciar_app()

    