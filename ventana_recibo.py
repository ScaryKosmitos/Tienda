"""
Ventana que muestra el recibo de una venta y permite abrirlo en el navegador
para imprimirlo o guardarlo como PDF.
"""
import webbrowser
from pathlib import Path
from tkinter import font as tkfont, messagebox

import customtkinter as ctk

import recibo as rec


class VentanaRecibo(ctk.CTkToplevel):
    def __init__(self, padre, recibo):
        """'recibo' es lo que retorna db.obtener_recibo()."""
        super().__init__(padre)
        self.recibo = recibo

        self.title(f"Recibo N° {rec.numero_recibo(recibo['id'])}")
        self.resizable(False, False)
        self.transient(padre)
        self.grab_set()

        texto = rec.texto_recibo(recibo)
        filas = texto.count("\n") + 1
        # Letra de ancho fijo para que las columnas del recibo queden alineadas.
        # El tamaño de la caja se calcula con la letra real, para que no se corte el borde derecho
        familia = tkfont.nametofont("TkFixedFont").actual("family")
        letra = tkfont.Font(family=familia, size=14)
        ancho = letra.measure("0" * rec.ANCHO) + 40
        alto = min(letra.metrics("linespace") * filas + 30, 560)
        caja = ctk.CTkTextbox(
            self, width=ancho, height=alto, font=ctk.CTkFont(family=familia, size=14),
            fg_color=("#ffffff", "#ffffff"), text_color=("#000000", "#000000"), wrap="none"
        )
        caja.insert("1.0", texto)
        caja.configure(state="disabled")
        caja.pack(padx=16, pady=(16, 10))

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=(0, 14))
        ctk.CTkButton(
            frame_botones, text="🖨 Abrir para imprimir o guardar", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00838F", hover_color="#005662", command=self.abrir_en_navegador
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="Cerrar", width=90, font=ctk.CTkFont(size=13),
            fg_color="#555555", hover_color="#333333", command=self.destroy
        ).pack(side="left", padx=4)

        self.bind("<Escape>", lambda _evento: self.destroy())

    def abrir_en_navegador(self):
        try:
            ruta = rec.guardar_html(self.recibo)
        except OSError as error:
            messagebox.showerror("No se pudo guardar", f"No se pudo crear el recibo:\n{error}", parent=self)
            return
        if not webbrowser.open(Path(ruta).as_uri()):
            messagebox.showinfo(
                "Recibo Guardado", f"No se pudo abrir el navegador. El recibo quedó guardado en:\n{ruta}", parent=self
            )
