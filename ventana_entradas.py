"""
Ventana de entradas de mercancía: suma unidades al stock del producto
seleccionado y muestra el historial de movimientos de stock.
"""
from tkinter import messagebox

import customtkinter as ctk

import base_datos as db
from componentes import ERRORES_BD, crear_tabla, mostrar_error_bd, vaciar_tabla
from formato import formatear_cambio, formatear_numero, leer_entero


class VentanaEntradas(ctk.CTkToplevel):
    def __init__(self, padre, producto, al_registrar):
        """
        'producto' es el producto seleccionado (o None si no hay ninguno).
        'al_registrar' se llama después de cada entrada, para que la ventana
        principal actualice su tabla.
        """
        super().__init__(padre)
        self.producto = producto
        self.al_registrar = al_registrar

        self.title("Entrada de Mercancía")
        self.geometry("680x500")
        self.grab_set()

        ctk.CTkLabel(self, text="📥 Entrada de Mercancía", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.lbl_producto = ctk.CTkLabel(self, font=ctk.CTkFont(size=14))
        self.lbl_producto.pack(padx=15)
        self.mostrar_producto(producto)

        frame_registro = ctk.CTkFrame(self, fg_color="transparent")
        frame_registro.pack(pady=8)
        self.entry_cantidad = ctk.CTkEntry(
            frame_registro, width=160, placeholder_text="Unidades recibidas", font=ctk.CTkFont(size=14)
        )
        self.entry_cantidad.pack(side="left", padx=5)
        btn_registrar = ctk.CTkButton(
            frame_registro, text="Registrar Entrada", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#00838F", hover_color="#005662", command=self.registrar
        )
        btn_registrar.pack(side="left", padx=5)
        if producto:
            self.entry_cantidad.bind("<Return>", lambda _evento: self.registrar())
        else:
            self.entry_cantidad.configure(state="disabled")
            btn_registrar.configure(state="disabled")

        frame_tabla = ctk.CTkFrame(self)
        frame_tabla.pack(fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(
            self, text="Movimientos de stock (entradas, stock inicial y ajustes manuales)",
            font=ctk.CTkFont(size=13)
        ).pack(padx=15, anchor="w")

        self.tabla = crear_tabla(frame_tabla, [
            ("id", "ID", {"width": 50, "anchor": "center"}),
            ("producto", "Producto", {"width": 200}),
            ("cantidad", "Unidades", {"width": 80, "anchor": "center"}),
            ("fecha", "Fecha y Hora", {"width": 150, "anchor": "center"}),
            ("motivo", "Motivo", {"width": 110, "anchor": "center"}),
        ])
        self.cargar_movimientos()

    def mostrar_producto(self, producto):
        if producto:
            texto = f"Producto: {producto['nombre']}  ·  Stock actual: {formatear_numero(producto['stock'])}"
        else:
            texto = "Selecciona un producto en la tabla principal para registrar una entrada."
        self.lbl_producto.configure(text=texto)

    def cargar_movimientos(self):
        vaciar_tabla(self.tabla)
        for id_mov, nombre, cantidad, fecha, motivo in db.obtener_entradas():
            self.tabla.insert("", "end", values=(id_mov, nombre, formatear_cambio(cantidad), fecha, motivo))

    def registrar(self):
        try:
            cantidad = leer_entero(self.entry_cantidad.get().strip())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero positivo.", parent=self)
            return

        try:
            exito, mensaje = db.registrar_entrada(self.producto["id"], cantidad)
            if exito:
                self.cargar_movimientos()
                self.al_registrar()
                actualizado = db.obtener_producto(self.producto["id"])
        except ERRORES_BD as error:
            mostrar_error_bd(error, parent=self)
            return

        if exito:
            self.entry_cantidad.delete(0, "end")
            self.mostrar_producto(actualizado)
            messagebox.showinfo("Entrada Registrada", mensaje, parent=self)
        else:
            messagebox.showerror("Error", mensaje, parent=self)
