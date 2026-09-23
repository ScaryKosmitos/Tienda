"""
Ventana de cobro: se escribe con cuánto paga el cliente y muestra el cambio.
"""
from tkinter import messagebox

import customtkinter as ctk

from formato import formatear_numero, formatear_precio, leer_precio

COLOR_CAMBIO = ("#2E7D32", "#66BB6A")
COLOR_FALTA = ("#C62828", "#EF5350")


class VentanaPago(ctk.CTkToplevel):
    def __init__(self, padre, total):
        super().__init__(padre)
        self.total = total
        # Dinero recibido; queda en None si se cancela
        self.pago = None

        self.title("Cobrar Venta")
        self.geometry("380x300")
        self.resizable(False, False)
        self.transient(padre)
        self.grab_set()

        ctk.CTkLabel(self, text="Total a cobrar", font=ctk.CTkFont(size=14)).pack(pady=(16, 0))
        ctk.CTkLabel(self, text=formatear_precio(total), font=ctk.CTkFont(size=28, weight="bold")).pack()

        self.entry_pago = ctk.CTkEntry(
            self, width=220, placeholder_text="Paga con ($)", font=ctk.CTkFont(size=16), justify="center"
        )
        self.entry_pago.pack(pady=(14, 6))

        self.lbl_cambio = ctk.CTkLabel(self, text="Cambio: —", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_cambio.pack(pady=4)
        self.color_normal = self.lbl_cambio.cget("text_color")

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=(14, 10))
        ctk.CTkButton(
            frame_botones, text="Cancelar", width=100, font=ctk.CTkFont(size=13),
            fg_color="#555555", hover_color="#333333", command=self.destroy
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="Pago exacto", width=110, font=ctk.CTkFont(size=13),
            fg_color="#00838F", hover_color="#005662", command=self.pago_exacto
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="💵 Cobrar", width=110, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32", hover_color="#1B5E20", command=self.confirmar
        ).pack(side="left", padx=4)

        self.entry_pago.bind("<KeyRelease>", self.actualizar_cambio)
        self.entry_pago.bind("<Return>", self.confirmar)
        self.bind("<Escape>", lambda _evento: self.destroy())
        self.after(150, self.entry_pago.focus_set)

    def leer_pago(self):
        """El monto escrito, o None si está vacío o no es un número."""
        try:
            return leer_precio(self.entry_pago.get().strip())
        except ValueError:
            return None

    def alcanza(self, pago):
        return round(pago, 2) >= round(self.total, 2)

    def actualizar_cambio(self, _evento=None):
        pago = self.leer_pago()
        if pago is None:
            self.lbl_cambio.configure(text="Cambio: —", text_color=self.color_normal)
        elif not self.alcanza(pago):
            self.lbl_cambio.configure(text=f"Faltan {formatear_precio(self.total - pago)}", text_color=COLOR_FALTA)
        else:
            self.lbl_cambio.configure(text=f"Cambio: {formatear_precio(pago - self.total)}", text_color=COLOR_CAMBIO)

    def confirmar(self, _evento=None):
        if not self.entry_pago.get().strip():
            messagebox.showwarning("Pago Vacío", "Escribe con cuánto paga el cliente.", parent=self)
            return
        pago = self.leer_pago()
        if pago is None:
            messagebox.showerror("Dato Inválido", "El pago debe ser un número (ej: 20000 o 20.000).", parent=self)
            return
        if not self.alcanza(pago):
            messagebox.showerror(
                "Pago Insuficiente", f"Faltan {formatear_precio(self.total - pago)} para completar el pago.",
                parent=self
            )
            return
        self.pago = pago
        self.destroy()

    def pago_exacto(self):
        self.entry_pago.delete(0, "end")
        self.entry_pago.insert(0, formatear_numero(self.total))
        self.confirmar()


def pedir_pago(padre, total):
    """Abre la ventana de cobro y espera a que se cierre. Retorna el dinero recibido, o None si se cancela."""
    ventana = VentanaPago(padre, total)
    padre.wait_window(ventana)
    return ventana.pago
