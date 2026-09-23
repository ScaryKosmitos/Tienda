"""
Ventana del historial de ventas, con dos pestañas que comparten los filtros
de fecha: el historial (donde se pueden ver los recibos y anular ventas) y el
ranking de productos más vendidos. También exporta el período a Excel.
"""
import os
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox

import customtkinter as ctk

import base_datos as db
from componentes import ERRORES_BD, STOCK_BAJO, crear_tabla, mostrar_error_bd, vaciar_tabla
from formato import describir_periodo, formatear_numero, formatear_precio
from recibo import numero_recibo
from ventana_recibo import VentanaRecibo


class VentanaVentas(ctk.CTkToplevel):
    def __init__(self, padre, al_anular):
        """'al_anular' se llama después de anular ventas, para que la ventana
        principal actualice el stock que muestra."""
        super().__init__(padre)
        self.al_anular = al_anular
        # Período que se está mostrando; es el que se exporta a Excel
        self.desde = None
        self.hasta = None

        self.title("Historial de Ventas")
        self.geometry("820x640")
        self.grab_set()

        ctk.CTkLabel(
            self, text="📜 Historial de Transacciones", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        self.crear_filtros()

        pestanas = ctk.CTkTabview(self)
        pestanas.pack(fill="both", expand=True, padx=15, pady=(4, 10))
        self.crear_pestana_ventas(pestanas.add("Ventas"))
        self.crear_pestana_ranking(pestanas.add("🏆 Más vendidos"))

        ctk.CTkButton(
            self, text="📊 Exportar a Excel", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2E7D32", hover_color="#1B5E20", command=self.exportar_a_excel
        ).pack(before=pestanas, side="bottom", pady=(0, 12))

        self.cargar()

    # --- CONSTRUCCIÓN DE LA VENTANA ---

    def crear_filtros(self):
        frame_filtros = ctk.CTkFrame(self, fg_color="transparent")
        frame_filtros.pack(fill="x", padx=15)

        ctk.CTkLabel(frame_filtros, text="Desde:", font=ctk.CTkFont(size=13)).pack(side="left")
        self.entry_desde = ctk.CTkEntry(frame_filtros, width=110, placeholder_text="AAAA-MM-DD")
        self.entry_desde.pack(side="left", padx=(4, 10))
        ctk.CTkLabel(frame_filtros, text="Hasta:", font=ctk.CTkFont(size=13)).pack(side="left")
        self.entry_hasta = ctk.CTkEntry(frame_filtros, width=110, placeholder_text="AAAA-MM-DD")
        self.entry_hasta.pack(side="left", padx=(4, 10))

        hoy = date.today()
        botones_rapidos = (
            ("Filtrar", self.cargar),
            ("Hoy", lambda: self.poner_fechas(hoy, hoy)),
            ("Esta semana", lambda: self.poner_fechas(hoy - timedelta(days=hoy.weekday()), hoy)),
            ("Este mes", lambda: self.poner_fechas(hoy.replace(day=1), hoy)),
            ("Todo", lambda: self.poner_fechas(None, None)),
        )
        for texto, comando in botones_rapidos:
            ctk.CTkButton(
                frame_filtros, text=texto, width=80, font=ctk.CTkFont(size=13), command=comando
            ).pack(side="left", padx=2)

        for entry in (self.entry_desde, self.entry_hasta):
            entry.bind("<Return>", lambda _evento: self.cargar())

    def crear_pestana_ventas(self, pestana):
        frame_tabla = ctk.CTkFrame(pestana)
        frame_tabla.pack(fill="both", expand=True, pady=(0, 8))
        self.tabla_ventas = crear_tabla(frame_tabla, [
            ("id", "ID Venta", {"width": 60, "anchor": "center"}),
            ("recibo", "Recibo", {"width": 70, "anchor": "center"}),
            ("producto", "Producto", {"width": 180}),
            ("cantidad", "Cant.", {"width": 60, "anchor": "center"}),
            ("total", "Total ($)", {"width": 90, "anchor": "e"}),
            ("fecha", "Fecha y Hora", {"width": 160, "anchor": "center"}),
            ("estado", "Estado", {"width": 90, "anchor": "center"}),
        ])
        self.tabla_ventas.tag_configure("anulada", foreground="#888888")

        frame_botones = ctk.CTkFrame(pestana, fg_color="transparent")
        frame_botones.pack(pady=(0, 8))
        ctk.CTkButton(
            frame_botones, text="🧾 Ver Recibo", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00838F", hover_color="#005662", command=self.ver_recibo
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="↩ Anular Venta Seleccionada", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#D32F2F", hover_color="#B71C1C", command=self.anular_seleccionadas
        ).pack(side="left", padx=4)

        self.lbl_total = ctk.CTkLabel(
            pestana, text="", font=ctk.CTkFont(size=17, weight="bold"), text_color="#2E7D32"
        )
        self.lbl_total.pack(pady=(0, 4))

    def crear_pestana_ranking(self, pestana):
        frame_tabla = ctk.CTkFrame(pestana)
        frame_tabla.pack(fill="both", expand=True, pady=(0, 8))
        # Las columnas de números no se encogen, para que sus títulos no se corten;
        # si la ventana cambia de tamaño, la que se ajusta es la de Producto
        self.tabla_ranking = crear_tabla(frame_tabla, [
            ("puesto", "#", {"width": 40, "minwidth": 40, "stretch": False, "anchor": "center"}),
            ("producto", "Producto", {"width": 200, "minwidth": 120}),
            ("unidades", "Unidades Vendidas", {"width": 195, "minwidth": 195, "stretch": False, "anchor": "center"}),
            ("total", "Total ($)", {"width": 110, "minwidth": 110, "stretch": False, "anchor": "e"}),
            ("porcentaje", "% de lo Vendido", {"width": 175, "minwidth": 175, "stretch": False, "anchor": "center"}),
        ])

        self.lbl_resumen_ranking = ctk.CTkLabel(pestana, text="", font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_resumen_ranking.pack(pady=(0, 4))

    # --- FILTROS Y CARGA DE DATOS ---

    def poner_fechas(self, desde, hasta):
        for entry, valor in ((self.entry_desde, desde), (self.entry_hasta, hasta)):
            entry.delete(0, "end")
            if valor:
                entry.insert(0, valor.strftime("%Y-%m-%d"))
        self.cargar()

    def leer_fechas(self):
        """
        Lee y valida las fechas de los filtros. Retorna (desde, hasta) como
        'AAAA-MM-DD' o None si el campo está vacío; si hay un error, lo muestra
        y retorna None.
        """
        fechas = []
        for entry in (self.entry_desde, self.entry_hasta):
            texto = entry.get().strip()
            if not texto:
                fechas.append(None)
                continue
            try:
                # Se reescribe con ceros (2026-9-1 -> 2026-09-01), porque la
                # base de datos compara las fechas como texto
                fecha = datetime.strptime(texto, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Fecha Inválida", f"'{texto}' no es una fecha válida. Usa el formato AAAA-MM-DD.", parent=self
                )
                return None
            entry.delete(0, "end")
            entry.insert(0, fecha)
            fechas.append(fecha)

        desde, hasta = fechas
        if desde and hasta and desde > hasta:
            messagebox.showerror("Rango Inválido", "La fecha 'Desde' no puede ser posterior a 'Hasta'.", parent=self)
            return None
        return desde, hasta

    def cargar(self):
        """Recarga las dos pestañas con el período de los filtros."""
        fechas = self.leer_fechas()
        if fechas is None:
            return
        desde, hasta = fechas

        vaciar_tabla(self.tabla_ventas)
        vaciar_tabla(self.tabla_ranking)
        try:
            ventas = db.obtener_ventas(desde, hasta)
            ranking = db.obtener_mas_vendidos(desde, hasta)
        except ERRORES_BD as error:
            mostrar_error_bd(error, parent=self)
            return

        self.desde, self.hasta = desde, hasta
        periodo = describir_periodo(desde, hasta)
        self.mostrar_ventas(ventas, periodo)
        self.mostrar_ranking(ranking, periodo)

    def mostrar_ventas(self, ventas, periodo):
        dinero_total = 0.0
        lineas_validas = 0
        for venta in ventas:
            if venta["anulada"]:
                estado, etiquetas = "Anulada", ("anulada",)
            else:
                estado, etiquetas = "OK", ()
                dinero_total += venta["total"]
                lineas_validas += 1
            recibo = numero_recibo(venta["recibo_id"]) if venta["recibo_id"] else "—"
            self.tabla_ventas.insert(
                "", "end", iid=str(venta["id"]), tags=etiquetas,
                values=(
                    venta["id"], recibo, venta["nombre_producto"], formatear_numero(venta["cantidad"]),
                    formatear_precio(venta["total"]), venta["fecha"], estado
                )
            )

        self.lbl_total.configure(
            text=f"Total Recaudado ({periodo}): {formatear_precio(dinero_total)}  ·  {lineas_validas} líneas de venta"
        )

    def mostrar_ranking(self, ranking, periodo):
        total_ranking = sum(fila["total"] for fila in ranking)
        for puesto, fila in enumerate(ranking, start=1):
            porcentaje = f"{fila['total'] / total_ranking * 100:.1f} %".replace(".", ",") if total_ranking else "—"
            self.tabla_ranking.insert("", "end", values=(
                puesto, fila["nombre"], formatear_numero(fila["unidades"]), formatear_precio(fila["total"]), porcentaje
            ))

        if ranking:
            primero = ranking[0]
            self.lbl_resumen_ranking.configure(
                text=f"{len(ranking)} producto(s) vendidos ({periodo})  ·  "
                     f"Más vendido: {primero['nombre']} ({formatear_numero(primero['unidades'])} unidades)"
            )
        else:
            self.lbl_resumen_ranking.configure(text=f"No hay ventas en este período ({periodo}).")

    # --- ACCIONES ---

    def ver_recibo(self):
        seleccion = self.tabla_ventas.selection()
        if not seleccion:
            messagebox.showwarning("Selección Requerida", "Selecciona una venta para ver su recibo.", parent=self)
            return

        # La columna muestra el número con ceros (000007) o "—" si la venta no tiene recibo
        recibos = {self.tabla_ventas.set(iid, "recibo") for iid in seleccion}
        if len(recibos) > 1:
            messagebox.showwarning(
                "Varios Recibos", "Las líneas seleccionadas son de recibos distintos. Selecciona una sola venta.",
                parent=self
            )
            return
        numero = recibos.pop()
        if not numero.isdigit():
            messagebox.showinfo(
                "Sin Recibo", "Esta venta se registró antes de que existieran los recibos, así que no tiene uno.",
                parent=self
            )
            return

        try:
            recibo = db.obtener_recibo(int(numero))
        except ERRORES_BD as error:
            mostrar_error_bd(error, parent=self)
            return
        VentanaRecibo(self, recibo)

    def anular_seleccionadas(self):
        seleccion = self.tabla_ventas.selection()
        if not seleccion:
            messagebox.showwarning("Selección Requerida", "Selecciona una o más ventas para anular.", parent=self)
            return
        if not messagebox.askyesno(
            "Confirmar", f"¿Anular {len(seleccion)} línea(s) de venta? Las unidades volverán al stock.", parent=self
        ):
            return

        try:
            exito, mensaje = db.anular_ventas([int(iid) for iid in seleccion])
        except ERRORES_BD as error:
            mostrar_error_bd(error, parent=self)
            return

        if exito:
            messagebox.showinfo("Venta Anulada", mensaje, parent=self)
            self.cargar()
            self.al_anular()
        else:
            messagebox.showerror("No se pudo anular", mensaje, parent=self)

    def exportar_a_excel(self):
        try:
            # Se importa aquí para que la tienda funcione aunque falte openpyxl
            import exportar
        except ImportError:
            messagebox.showerror(
                "Falta una Librería",
                "Para exportar a Excel hay que instalar 'openpyxl':\n\nsudo pacman -S python-openpyxl",
                parent=self
            )
            return

        desde, hasta = self.desde, self.hasta
        if desde or hasta:
            nombre_sugerido = f"Reporte_Tienda_{desde or 'inicio'}_a_{hasta or date.today()}.xlsx"
        else:
            nombre_sugerido = f"Reporte_Tienda_completo_{date.today()}.xlsx"
        ruta = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar reporte de Excel",
            initialdir=os.path.expanduser("~"),
            initialfile=nombre_sugerido,
            defaultextension=".xlsx",
            filetypes=[("Libro de Excel", "*.xlsx")],
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".xlsx"):
            ruta += ".xlsx"

        try:
            cantidad_ventas, cantidad_productos = exportar.exportar_excel(ruta, desde, hasta, STOCK_BAJO)
        except PermissionError:
            messagebox.showerror(
                "No se pudo guardar",
                "No se pudo escribir el archivo. Si lo tienes abierto en Excel o LibreOffice, "
                "ciérralo e inténtalo de nuevo.",
                parent=self
            )
            return
        except ERRORES_BD as error:
            messagebox.showerror("No se pudo exportar", f"Ocurrió un problema:\n{error}", parent=self)
            return

        messagebox.showinfo(
            "Reporte Exportado",
            f"Se guardó el reporte ({describir_periodo(desde, hasta)}):\n{ruta}\n\n"
            f"Hojas: Ventas ({cantidad_ventas} líneas), Más vendidos e Inventario ({cantidad_productos} productos).",
            parent=self
        )
