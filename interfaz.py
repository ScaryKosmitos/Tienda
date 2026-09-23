import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

import customtkinter as ctk
from tkinter import ttk, messagebox
import base_datos as db


def manejar_errores_bd(func):
    """Evita que un error inesperado de la base de datos (archivo bloqueado,
    permisos, etc.) cierre la aplicación sin explicación: muestra un aviso
    claro en su lugar."""
    @wraps(func)
    def envoltorio(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Error de Base de Datos",
                f"Ocurrió un problema al acceder a la base de datos:\n{error}"
            )
    return envoltorio

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

         
class AplicacionInventario(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema CRUD y Gestión de Inventario")
        self.geometry("1100x650")
        self.minsize(900, 600)

        # Variables internas de selección
        self.id_producto_seleccionado = None
        self.orden_ascendente = True
        self.columna_ordenada = None
        # Carrito: id_producto -> {"nombre", "precio", "cantidad"}
        self.carrito = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL IZQUIERDO: FORMULARIO Y CONTROLES ---
        self.frame_formulario = ctk.CTkFrame(self, width=320, corner_radius=10)
        self.frame_formulario.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # SECCIÓN INVENTARIO
        self.lbl_titulo = ctk.CTkLabel(
            self.frame_formulario, text="📦 Registro / Edición", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_titulo.pack(padx=10, pady=(12, 6))

        self.entry_nombre = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Nombre del producto", font=ctk.CTkFont(size=14)
        )
        self.entry_nombre.pack(fill="x", padx=15, pady=5)

        self.entry_categoria = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Categoría (ej: Lácteos)", font=ctk.CTkFont(size=14)
        )
        self.entry_categoria.pack(fill="x", padx=15, pady=5)

        self.entry_precio = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Precio ($)", font=ctk.CTkFont(size=14)
        )
        self.entry_precio.pack(fill="x", padx=15, pady=5)

        self.entry_stock = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Stock inicial", font=ctk.CTkFont(size=14)
        )
        self.entry_stock.pack(fill="x", padx=15, pady=5)

        self.btn_guardar = ctk.CTkButton(
            self.frame_formulario, 
            text="Guardar Producto", 
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.guardar_producto
        )
        self.btn_guardar.pack(fill="x", padx=15, pady=6)

        # SECCIÓN VENTAS POS
        self.lbl_venta = ctk.CTkLabel(
            self.frame_formulario, text="🛒 Venta", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_venta.pack(padx=10, pady=(12, 6))

        self.entry_cant_venta = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Cantidad a vender", font=ctk.CTkFont(size=14)
        )
        self.entry_cant_venta.pack(fill="x", padx=15, pady=5)

        self.btn_vender = ctk.CTkButton(
            self.frame_formulario, 
            text="Agregar al Carrito", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32", 
            hover_color="#1B5E20",
            command=self.agregar_al_carrito
        )
        self.btn_vender.pack(fill="x", padx=15, pady=5)

        # ACCIONES SECUNDARIAS
        self.btn_ver_ventas = ctk.CTkButton(
            self.frame_formulario, 
            text="📋 Historial de Ventas", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#7B1FA2", 
            hover_color="#4A148C",
            command=self.abrir_ventana_ventas
        )
        self.btn_ver_ventas.pack(fill="x", padx=15, pady=5)

        self.btn_limpiar = ctk.CTkButton(
            self.frame_formulario, 
            text="Limpiar Campos", 
            font=ctk.CTkFont(size=15),
            fg_color="#555555", 
            hover_color="#333333",
            command=self.limpiar_formulario
        )
        self.btn_limpiar.pack(fill="x", padx=15, pady=3)

        self.btn_eliminar = ctk.CTkButton(
            self.frame_formulario, 
            text="Eliminar Producto", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#D32F2F", 
            hover_color="#B71C1C",
            command=self.eliminar_producto
        )
        self.btn_eliminar.pack(fill="x", padx=15, pady=3)

        self.switch_modo = ctk.CTkSwitch(
            self.frame_formulario, text="Modo Oscuro", font=ctk.CTkFont(size=13), command=self.cambiar_modo
        )
        self.switch_modo.pack(side="bottom", padx=15, pady=12)
        if ctk.get_appearance_mode() == "Dark":
            self.switch_modo.select()

        # --- PANEL DERECHO: BUSCADOR Y TABLA ---
        self.frame_derecho = ctk.CTkFrame(self, corner_radius=10)
        self.frame_derecho.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.frame_derecho.grid_rowconfigure(1, weight=1)
        self.frame_derecho.grid_columnconfigure(0, weight=1)

        self.frame_busqueda = ctk.CTkFrame(self.frame_derecho, fg_color="transparent")
        self.frame_busqueda.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.entry_buscar = ctk.CTkEntry(
            self.frame_busqueda, 
            placeholder_text="🔍 Buscar producto por nombre...", 
            font=ctk.CTkFont(size=14)
        )
        self.entry_buscar.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_buscar.bind("<KeyRelease>", self.filtrar_productos)

        self.tabla_frame = ctk.CTkFrame(self.frame_derecho)
        self.tabla_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.tabla_frame.grid_rowconfigure(0, weight=1)
        self.tabla_frame.grid_columnconfigure(0, weight=1)

        self.configurar_tabla()
        self.configurar_carrito()
        self.cargar_productos_en_tabla()

    def configurar_tabla(self):
        columnas = ("id", "nombre", "categoria", "precio", "stock")
        self.tabla = ttk.Treeview(self.tabla_frame, columns=columnas, show="headings")

        # Ajuste de tamaño de fuente en la tabla
        estilo = ttk.Style()
        # El tema "clam" respeta los colores personalizados, lo que permite
        # que la tabla cambie entre modo claro y oscuro
        estilo.theme_use("clam")
        estilo.configure("Treeview", font=("TkDefaultFont", 13), rowheight=28)
        estilo.configure("Treeview.Heading", font=("TkDefaultFont", 14, "bold"))
        self.aplicar_colores_tabla()

        # Encabezados con función de ordenamiento al hacer clic
        self.tabla.heading("id", text="ID ↕", command=lambda: self.ordenar_por_columna("id", 0))
        self.tabla.heading("nombre", text="Nombre ↕", command=lambda: self.ordenar_por_columna("nombre", 1))
        self.tabla.heading("categoria", text="Categoría ↕", command=lambda: self.ordenar_por_columna("categoria", 2))
        self.tabla.heading("precio", text="Precio ($) ↕", command=lambda: self.ordenar_por_columna("precio", 3))
        self.tabla.heading("stock", text="Stock ↕", command=lambda: self.ordenar_por_columna("stock", 4))

        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=200)
        self.tabla.column("categoria", width=130)
        self.tabla.column("precio", width=100, anchor="e")
        self.tabla.column("stock", width=80, anchor="center")

        # Alerta visual en rojo para productos con stock < 5
        self.tabla.tag_configure("stock_bajo", foreground="#FF3333")
        self.tabla.bind("<<TreeviewSelect>>", self.cargar_producto_en_formulario)

        scrollbar = ttk.Scrollbar(self.tabla_frame, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscroll=scrollbar.set)
        
        self.tabla.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    @manejar_errores_bd
    def cargar_productos_en_tabla(self, lista_productos=None):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        if lista_productos is None:
            lista_productos = db.obtener_productos()

        for prod in lista_productos:
            if prod[4] < 5:
                self.tabla.insert("", "end", values=prod, tags=("stock_bajo",))
            else:
                self.tabla.insert("", "end", values=prod)

    def configurar_carrito(self):
        self.frame_carrito = ctk.CTkFrame(self.frame_derecho)
        self.frame_carrito.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.frame_carrito.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.frame_carrito, text="🧺 Carrito", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(6, 4), sticky="w")

        self.lbl_total_carrito = ctk.CTkLabel(
            self.frame_carrito, text="Total: $0.00", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_total_carrito.grid(row=0, column=1, padx=10, pady=(6, 4), sticky="e")

        columnas = ("producto", "cantidad", "precio", "subtotal")
        self.tabla_carrito = ttk.Treeview(self.frame_carrito, columns=columnas, show="headings", height=4)
        self.tabla_carrito.heading("producto", text="Producto")
        self.tabla_carrito.heading("cantidad", text="Cant.")
        self.tabla_carrito.heading("precio", text="Precio ($)")
        self.tabla_carrito.heading("subtotal", text="Subtotal ($)")
        self.tabla_carrito.column("producto", width=220)
        self.tabla_carrito.column("cantidad", width=60, anchor="center")
        self.tabla_carrito.column("precio", width=100, anchor="e")
        self.tabla_carrito.column("subtotal", width=110, anchor="e")
        self.tabla_carrito.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")

        frame_botones = ctk.CTkFrame(self.frame_carrito, fg_color="transparent")
        frame_botones.grid(row=2, column=0, columnspan=2, padx=10, pady=8, sticky="ew")

        ctk.CTkButton(
            frame_botones, text="Quitar", width=90, font=ctk.CTkFont(size=13),
            fg_color="#555555", hover_color="#333333", command=self.quitar_del_carrito
        ).pack(side="left")
        ctk.CTkButton(
            frame_botones, text="Vaciar", width=90, font=ctk.CTkFont(size=13),
            fg_color="#D32F2F", hover_color="#B71C1C", command=self.vaciar_carrito
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            frame_botones, text="💵 Cobrar Venta", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32", hover_color="#1B5E20", command=self.cobrar_carrito
        ).pack(side="right")

    def aplicar_colores_tabla(self):
        """Ajusta los colores de las tablas (inventario e historial) al modo actual."""
        if ctk.get_appearance_mode() == "Dark":
            fondo, texto, fondo_encabezado, seleccion = "#2b2b2b", "#e8e8e8", "#3a3a3a", "#1f538d"
        else:
            fondo, texto, fondo_encabezado, seleccion = "#ffffff", "#1a1a1a", "#e3e3e3", "#3a7ebf"

        estilo = ttk.Style()
        estilo.configure("Treeview", background=fondo, fieldbackground=fondo, foreground=texto)
        estilo.map("Treeview", background=[("selected", seleccion)], foreground=[("selected", "#ffffff")])
        estilo.configure("Treeview.Heading", background=fondo_encabezado, foreground=texto)
        estilo.map("Treeview.Heading", background=[("active", seleccion)], foreground=[("active", "#ffffff")])

    def ordenar_por_columna(self, columna, indice):
        # Al cambiar de columna, el primer clic siempre ordena de menor a mayor
        if columna != self.columna_ordenada:
            self.orden_ascendente = True
            self.columna_ordenada = columna

        filas = [(self.tabla.set(k, columna), k) for k in self.tabla.get_children("")]

        if columna in ("precio", "stock", "id"):
            filas.sort(key=lambda x: float(x[0]), reverse=not self.orden_ascendente)
        else:
            filas.sort(key=lambda x: x[0].lower(), reverse=not self.orden_ascendente)

        for index, (val, k) in enumerate(filas):
            self.tabla.move(k, "", index)

        self.orden_ascendente = not self.orden_ascendente

    def cargar_producto_en_formulario(self, event):
        item_seleccionado = self.tabla.selection()
        if not item_seleccionado:
            return

        valores = self.tabla.item(item_seleccionado, "values")
        self.id_producto_seleccionado = valores[0]

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, valores[1])

        self.entry_categoria.delete(0, "end")
        self.entry_categoria.insert(0, valores[2])

        self.entry_precio.delete(0, "end")
        self.entry_precio.insert(0, valores[3])

        self.entry_stock.delete(0, "end")
        self.entry_stock.insert(0, valores[4])

        self.btn_guardar.configure(text="Actualizar Producto", fg_color="#2E7D32", hover_color="#1B5E20")

    @manejar_errores_bd
    def guardar_producto(self):
        nombre = self.entry_nombre.get().strip()
        categoria = self.entry_categoria.get().strip()
        precio_str = self.entry_precio.get().strip()
        stock_str = self.entry_stock.get().strip()

        if not nombre or not categoria or not precio_str or not stock_str:
            messagebox.showwarning("Campos Vacíos", "Por favor completa todos los campos.")
            return

        try:
            precio = float(precio_str)
            stock = int(stock_str)
        except ValueError:
            messagebox.showerror("Dato Inválido", "El precio debe ser un número decimal y el stock un entero.")
            return

        if self.id_producto_seleccionado:
            exito, mensaje = db.actualizar_producto(self.id_producto_seleccionado, nombre, categoria, precio, stock)
        else:
            exito, mensaje = db.agregar_producto(nombre, categoria, precio, stock)

        if not exito:
            messagebox.showerror("Dato Inválido", mensaje)
            return

        messagebox.showinfo("Éxito", mensaje)
        self.limpiar_formulario()
        self.cargar_productos_en_tabla()

    @manejar_errores_bd
    def agregar_al_carrito(self):
        if not self.id_producto_seleccionado:
            messagebox.showwarning("Selección Requerida", "Selecciona un producto de la tabla para vender.")
            return

        cant_str = self.entry_cant_venta.get().strip()
        if not cant_str:
            messagebox.showwarning("Cantidad Vacía", "Ingresa la cantidad a vender.")
            return

        try:
            cantidad = int(cant_str)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero positivo.")
            return

        producto = db.obtener_producto(self.id_producto_seleccionado)
        if not producto:
            messagebox.showerror("Error", "El producto ya no existe.")
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()
            return

        id_producto, nombre, _, precio, stock = producto
        en_carrito = self.carrito.get(id_producto, {}).get("cantidad", 0)
        if en_carrito + cantidad > stock:
            messagebox.showerror(
                "Stock Insuficiente",
                f"Solo quedan {stock} unidades de '{nombre}' y ya hay {en_carrito} en el carrito."
            )
            return

        self.carrito[id_producto] = {"nombre": nombre, "precio": precio, "cantidad": en_carrito + cantidad}
        self.actualizar_carrito()
        self.limpiar_formulario()

    def actualizar_carrito(self):
        for item in self.tabla_carrito.get_children():
            self.tabla_carrito.delete(item)

        total = 0.0
        for id_producto, linea in self.carrito.items():
            subtotal = linea["cantidad"] * linea["precio"]
            total += subtotal
            self.tabla_carrito.insert(
                "", "end", iid=str(id_producto),
                values=(linea["nombre"], linea["cantidad"], f"{linea['precio']:,.2f}", f"{subtotal:,.2f}")
            )
        self.lbl_total_carrito.configure(text=f"Total: ${total:,.2f}")

    def quitar_del_carrito(self):
        seleccion = self.tabla_carrito.selection()
        if not seleccion:
            messagebox.showwarning("Selección Requerida", "Selecciona un producto del carrito para quitarlo.")
            return
        for iid in seleccion:
            self.carrito.pop(int(iid), None)
        self.actualizar_carrito()

    def vaciar_carrito(self):
        if self.carrito and messagebox.askyesno("Confirmar", "¿Vaciar el carrito?"):
            self.carrito.clear()
            self.actualizar_carrito()

    @manejar_errores_bd
    def cobrar_carrito(self):
        if not self.carrito:
            messagebox.showwarning("Carrito Vacío", "Agrega productos al carrito antes de cobrar.")
            return

        items = [(id_producto, linea["cantidad"]) for id_producto, linea in self.carrito.items()]
        exito, mensaje = db.registrar_venta_carrito(items)

        if exito:
            messagebox.showinfo("Venta Realizada", mensaje)
            self.carrito.clear()
            self.actualizar_carrito()
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()
        else:
            messagebox.showerror("Error en Venta", mensaje)

    @manejar_errores_bd
    def abrir_ventana_ventas(self):
        ventana_ventas = ctk.CTkToplevel(self)
        ventana_ventas.title("Historial de Ventas")
        ventana_ventas.geometry("820x560")
        ventana_ventas.grab_set()

        lbl_titulo = ctk.CTkLabel(
            ventana_ventas, text="📜 Historial de Transacciones", font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_titulo.pack(pady=10)

        # Filtros de fecha
        frame_filtros = ctk.CTkFrame(ventana_ventas, fg_color="transparent")
        frame_filtros.pack(fill="x", padx=15)

        ctk.CTkLabel(frame_filtros, text="Desde:", font=ctk.CTkFont(size=13)).pack(side="left")
        entry_desde = ctk.CTkEntry(frame_filtros, width=110, placeholder_text="AAAA-MM-DD")
        entry_desde.pack(side="left", padx=(4, 10))
        ctk.CTkLabel(frame_filtros, text="Hasta:", font=ctk.CTkFont(size=13)).pack(side="left")
        entry_hasta = ctk.CTkEntry(frame_filtros, width=110, placeholder_text="AAAA-MM-DD")
        entry_hasta.pack(side="left", padx=(4, 10))

        frame_tabla = ctk.CTkFrame(ventana_ventas)
        frame_tabla.pack(fill="both", expand=True, padx=15, pady=10)

        columnas = ("id", "producto", "cantidad", "total", "fecha")
        tabla_ventas = ttk.Treeview(frame_tabla, columns=columnas, show="headings")

        tabla_ventas.heading("id", text="ID Venta")
        tabla_ventas.heading("producto", text="Producto")
        tabla_ventas.heading("cantidad", text="Cant.")
        tabla_ventas.heading("total", text="Total ($)")
        tabla_ventas.heading("fecha", text="Fecha y Hora")

        tabla_ventas.column("id", width=60, anchor="center")
        tabla_ventas.column("producto", width=180)
        tabla_ventas.column("cantidad", width=60, anchor="center")
        tabla_ventas.column("total", width=90, anchor="e")
        tabla_ventas.column("fecha", width=160, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_ventas.yview)
        tabla_ventas.configure(yscroll=scrollbar.set)

        tabla_ventas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        lbl_total_acumulado = ctk.CTkLabel(
            ventana_ventas, 
            text="", 
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#2E7D32"
        )
        lbl_total_acumulado.pack(pady=10)

        def poner_fechas(desde, hasta):
            for entry, valor in ((entry_desde, desde), (entry_hasta, hasta)):
                entry.delete(0, "end")
                if valor:
                    entry.insert(0, valor.strftime("%Y-%m-%d"))
            cargar_ventas()

        def cargar_ventas():
            desde = entry_desde.get().strip() or None
            hasta = entry_hasta.get().strip() or None
            for fecha in (desde, hasta):
                if fecha:
                    try:
                        datetime.strptime(fecha, "%Y-%m-%d")
                    except ValueError:
                        messagebox.showerror(
                            "Fecha Inválida", f"'{fecha}' no es una fecha válida. Usa el formato AAAA-MM-DD.",
                            parent=ventana_ventas
                        )
                        return

            for item in tabla_ventas.get_children():
                tabla_ventas.delete(item)

            try:
                ventas = db.obtener_ventas(desde, hasta)
            except (sqlite3.Error, OSError) as error:
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"Ocurrió un problema al acceder a la base de datos:\n{error}",
                    parent=ventana_ventas
                )
                return

            dinero_total = 0.0
            for v in ventas:
                id_venta, prod_id, nombre_prod, cant, total, fecha = v
                dinero_total += total
                tabla_ventas.insert("", "end", values=(id_venta, nombre_prod, cant, f"${total:,.2f}", fecha))

            if desde or hasta:
                periodo = f"{desde or 'el inicio'} a {hasta or 'hoy'}"
            else:
                periodo = "todo el historial"
            lbl_total_acumulado.configure(
                text=f"Total Recaudado ({periodo}): ${dinero_total:,.2f}  ·  {len(ventas)} líneas de venta"
            )

        hoy = date.today()
        botones_rapidos = (
            ("Filtrar", cargar_ventas),
            ("Hoy", lambda: poner_fechas(hoy, hoy)),
            ("Esta semana", lambda: poner_fechas(hoy - timedelta(days=hoy.weekday()), hoy)),
            ("Este mes", lambda: poner_fechas(hoy.replace(day=1), hoy)),
            ("Todo", lambda: poner_fechas(None, None)),
        )
        for texto, comando in botones_rapidos:
            ctk.CTkButton(
                frame_filtros, text=texto, width=80, font=ctk.CTkFont(size=13), command=comando
            ).pack(side="left", padx=2)

        cargar_ventas()

    @manejar_errores_bd
    def eliminar_producto(self):
        if not self.id_producto_seleccionado:
            messagebox.showwarning("Selección Requerida", "Selecciona un producto de la tabla.")
            return

        if messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar '{self.entry_nombre.get()}'?"):
            exito, mensaje = db.eliminar_producto(self.id_producto_seleccionado)
            if exito:
                self.limpiar_formulario()
                self.cargar_productos_en_tabla()
            else:
                messagebox.showerror("No se pudo eliminar", mensaje)

    @manejar_errores_bd
    def filtrar_productos(self, event):
        texto = self.entry_buscar.get().strip()
        if texto == "":
            self.cargar_productos_en_tabla()
        else:
            resultados = db.buscar_producto_por_nombre(texto)
            self.cargar_productos_en_tabla(resultados)

    def cambiar_modo(self):
        if self.switch_modo.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")
        self.aplicar_colores_tabla()

    def limpiar_formulario(self):
        self.id_producto_seleccionado = None
        # Quitar la selección de la tabla para que al volver a hacer clic
        # en la misma fila se carguen de nuevo sus datos en el formulario
        self.tabla.selection_remove(self.tabla.selection())
        self.entry_nombre.delete(0, "end")
        self.entry_categoria.delete(0, "end")
        self.entry_precio.delete(0, "end")
        self.entry_stock.delete(0, "end")
        self.entry_cant_venta.delete(0, "end")
        self.btn_guardar.configure(text="Guardar Producto", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#325882", "#14375e"])


def iniciar_app():
    app = AplicacionInventario()
    app.mainloop()