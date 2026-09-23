import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

import customtkinter as ctk
from tkinter import ttk, messagebox
import base_datos as db
from formato import formatear_cambio, formatear_numero, formatear_precio, leer_entero, leer_precio


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

# Los productos con menos unidades que esto se marcan en rojo
STOCK_BAJO = 5

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
            self.frame_formulario, placeholder_text="Stock (unidades)", font=ctk.CTkFont(size=14)
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

        self.btn_entradas = ctk.CTkButton(
            self.frame_formulario, 
            text="📥 Entrada de Mercancía", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00838F", 
            hover_color="#005662",
            command=self.abrir_ventana_entradas
        )
        self.btn_entradas.pack(fill="x", padx=15, pady=5)

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

        self.menu_categoria = ctk.CTkOptionMenu(
            self.frame_busqueda, values=["Todas"], width=150, font=ctk.CTkFont(size=13),
            command=self.filtrar_productos
        )
        self.menu_categoria.pack(side="left", padx=5)

        self.check_stock_bajo = ctk.CTkCheckBox(
            self.frame_busqueda, text="Solo stock bajo", font=ctk.CTkFont(size=13),
            command=self.filtrar_productos
        )
        self.check_stock_bajo.pack(side="left", padx=(5, 0))

        self.tabla_frame = ctk.CTkFrame(self.frame_derecho)
        self.tabla_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.tabla_frame.grid_rowconfigure(0, weight=1)
        self.tabla_frame.grid_columnconfigure(0, weight=1)

        self.configurar_tabla()
        self.configurar_carrito()
        self.cargar_productos_en_tabla()

        # Enter como atajo: guardar desde el formulario, agregar al carrito desde la cantidad
        for entry in (self.entry_nombre, self.entry_categoria, self.entry_precio, self.entry_stock):
            entry.bind("<Return>", lambda _evento: self.guardar_producto())
        self.entry_cant_venta.bind("<Return>", lambda _evento: self.agregar_al_carrito())

        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    def configurar_tabla(self):
        columnas = ("id", "nombre", "categoria", "precio", "stock")
        # "browse": una sola fila a la vez, porque el formulario edita un producto
        self.tabla = ttk.Treeview(self.tabla_frame, columns=columnas, show="headings", selectmode="browse")

        # Ajuste de tamaño de fuente en la tabla
        estilo = ttk.Style()
        # El tema "clam" respeta los colores personalizados, lo que permite
        # que la tabla cambie entre modo claro y oscuro
        estilo.theme_use("clam")
        estilo.configure("Treeview", font=("TkDefaultFont", 13), rowheight=28)
        estilo.configure("Treeview.Heading", font=("TkDefaultFont", 14, "bold"))
        self.aplicar_colores_tabla()

        # Encabezados con función de ordenamiento al hacer clic
        self.titulos_columnas = {
            "id": "ID", "nombre": "Nombre", "categoria": "Categoría", "precio": "Precio ($)", "stock": "Stock"
        }
        for columna in columnas:
            self.tabla.heading(columna, command=lambda c=columna: self.ordenar_por_columna(c))
        self.actualizar_flechas_orden()

        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=200)
        self.tabla.column("categoria", width=130)
        self.tabla.column("precio", width=100, anchor="e")
        self.tabla.column("stock", width=80, anchor="center")

        # Alerta visual en rojo para productos con stock bajo
        self.tabla.tag_configure("stock_bajo", foreground="#FF3333")
        self.tabla.bind("<<TreeviewSelect>>", self.cargar_producto_en_formulario)

        scrollbar = ttk.Scrollbar(self.tabla_frame, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscroll=scrollbar.set)
        
        self.tabla.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    @manejar_errores_bd
    def cargar_productos_en_tabla(self):
        """Recarga la tabla respetando la búsqueda, la categoría y el filtro de stock bajo."""
        self.actualizar_menu_categorias()

        categoria = self.menu_categoria.get()
        lista_productos = db.buscar_productos(
            texto=self.entry_buscar.get().strip(),
            categoria=None if categoria == "Todas" else categoria,
            stock_menor_a=STOCK_BAJO if self.check_stock_bajo.get() else None,
        )

        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for id_producto, nombre, categoria, precio, stock in lista_productos:
            valores = (id_producto, nombre, categoria, formatear_precio(precio), formatear_numero(stock))
            etiquetas = ("stock_bajo",) if stock < STOCK_BAJO else ()
            self.tabla.insert("", "end", iid=str(id_producto), values=valores, tags=etiquetas)

        # Recargar la tabla (tras una venta, búsqueda, etc.) no pierde el orden elegido
        self.aplicar_orden()

        # El formulario solo debe editar un producto que se ve seleccionado:
        # si la búsqueda lo ocultó, se limpia para no sobrescribirlo por error
        if self.id_producto_seleccionado:
            iid = str(self.id_producto_seleccionado)
            if self.tabla.exists(iid):
                self.tabla.selection_set(iid)
                self.tabla.see(iid)
            else:
                self.limpiar_formulario()

    def actualizar_menu_categorias(self):
        """Mantiene el menú de categorías al día con los productos existentes."""
        categorias = ["Todas"] + db.obtener_categorias()
        self.menu_categoria.configure(values=categorias)
        if self.menu_categoria.get() not in categorias:
            self.menu_categoria.set("Todas")

    def configurar_carrito(self):
        self.frame_carrito = ctk.CTkFrame(self.frame_derecho)
        self.frame_carrito.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.frame_carrito.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.frame_carrito, text="🧺 Carrito", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(6, 4), sticky="w")

        self.lbl_total_carrito = ctk.CTkLabel(
            self.frame_carrito, text="Total: $0", font=ctk.CTkFont(size=16, weight="bold")
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

    def ordenar_por_columna(self, columna):
        """Clic en un encabezado: la primera vez ordena de menor a mayor; otro clic invierte el orden."""
        if columna == self.columna_ordenada:
            self.orden_ascendente = not self.orden_ascendente
        else:
            self.columna_ordenada = columna
            self.orden_ascendente = True
        self.aplicar_orden()

    def aplicar_orden(self):
        """Ordena las filas según la columna y dirección elegidas (si hay alguna)."""
        columna = self.columna_ordenada
        if columna:
            filas = [(self.tabla.set(k, columna), k) for k in self.tabla.get_children("")]

            if columna == "precio":
                clave = lambda x: leer_precio(x[0])
            elif columna in ("stock", "id"):
                clave = lambda x: leer_entero(str(x[0]))
            else:
                clave = lambda x: str(x[0]).lower()
            filas.sort(key=clave, reverse=not self.orden_ascendente)

            for index, (_valor, k) in enumerate(filas):
                self.tabla.move(k, "", index)

        self.actualizar_flechas_orden()

    def actualizar_flechas_orden(self):
        """▲ = de menor a mayor, ▼ = de mayor a menor, ↕ = columna sin ordenar."""
        for columna, titulo in self.titulos_columnas.items():
            if columna == self.columna_ordenada:
                flecha = "▲" if self.orden_ascendente else "▼"
            else:
                flecha = "↕"
            self.tabla.heading(columna, text=f"{titulo} {flecha}")

    def cargar_producto_en_formulario(self, event):
        item_seleccionado = self.tabla.selection()
        if not item_seleccionado:
            return

        valores = self.tabla.item(item_seleccionado[0], "values")
        # Si es el mismo producto que ya está en el formulario (se volvió a
        # seleccionar tras una búsqueda), no se pisan los cambios sin guardar
        if str(valores[0]) == str(self.id_producto_seleccionado):
            return
        self.id_producto_seleccionado = valores[0]

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, valores[1])

        self.entry_categoria.delete(0, "end")
        self.entry_categoria.insert(0, valores[2])

        self.entry_precio.delete(0, "end")
        self.entry_precio.insert(0, valores[3].lstrip("$"))

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
            precio = leer_precio(precio_str)
            stock = leer_entero(stock_str)
        except ValueError:
            messagebox.showerror(
                "Dato Inválido",
                "El precio debe ser un número (ej: 1500, 1.500 o 1.500,50) y el stock un número entero."
            )
            return

        # Validar antes de preguntar por la categoría, para no preguntar en vano
        error = db.validar_producto(precio, stock)
        if error:
            messagebox.showerror("Dato Inválido", error)
            return

        if db.categoria_es_nueva(categoria) and not messagebox.askyesno(
            "Categoría Nueva",
            f"La categoría '{categoria}' no existe todavía.\n\n"
            f"Categorías actuales: {', '.join(db.obtener_categorias()) or '(ninguna)'}\n\n"
            "¿Crear esta categoría nueva?"
        ):
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
        self.refrescar_carrito()

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
            cantidad = leer_entero(cant_str)
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
                f"Solo quedan {formatear_numero(stock)} unidades de '{nombre}' "
                f"y ya hay {formatear_numero(en_carrito)} en el carrito."
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
                values=(linea["nombre"], formatear_numero(linea["cantidad"]), formatear_precio(linea["precio"]), formatear_precio(subtotal))
            )
        self.lbl_total_carrito.configure(text=f"Total: {formatear_precio(total)}")

    def refrescar_carrito(self):
        """
        Vuelve a leer nombre y precio de cada producto del carrito, para que el
        total mostrado coincida con lo que se va a cobrar. Quita los productos
        que ya no existen. Retorna una lista de textos con los cambios hechos.
        """
        cambios = []
        for id_producto, linea in list(self.carrito.items()):
            producto = db.obtener_producto(id_producto)
            if not producto:
                cambios.append(f"'{linea['nombre']}' ya no existe y se quitó del carrito.")
                del self.carrito[id_producto]
                continue
            _, nombre, _, precio, _ = producto
            if precio != linea["precio"]:
                cambios.append(f"'{nombre}': precio {formatear_precio(linea['precio'])} → {formatear_precio(precio)}")
            linea["nombre"], linea["precio"] = nombre, precio
        self.actualizar_carrito()
        return cambios

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

        cambios = self.refrescar_carrito()
        total = sum(linea["cantidad"] * linea["precio"] for linea in self.carrito.values())
        if cambios:
            if not self.carrito:
                messagebox.showwarning("Carrito Actualizado", "\n".join(cambios))
                return
            if not messagebox.askyesno(
                "Carrito Actualizado",
                "Algunos productos cambiaron desde que se agregaron:\n\n"
                + "\n".join(cambios)
                + f"\n\nNuevo total: {formatear_precio(total)}\n¿Cobrar la venta?"
            ):
                return

        pago = self.pedir_pago(total)
        if pago is None:
            return

        items = [(id_producto, linea["cantidad"]) for id_producto, linea in self.carrito.items()]
        exito, mensaje = db.registrar_venta_carrito(items)

        if exito:
            messagebox.showinfo(
                "Venta Realizada",
                f"{mensaje}\n\nRecibido: {formatear_precio(pago)}\nCambio: {formatear_precio(pago - total)}"
            )
            self.carrito.clear()
            self.actualizar_carrito()
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()
        else:
            messagebox.showerror("Error en Venta", mensaje)

    def pedir_pago(self, total):
        """
        Ventana para escribir con cuánto paga el cliente; muestra el cambio
        mientras se escribe. Retorna el dinero recibido, o None si se cancela.
        """
        ventana = ctk.CTkToplevel(self)
        ventana.title("Cobrar Venta")
        ventana.geometry("380x300")
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()
        resultado = {"pago": None}

        ctk.CTkLabel(ventana, text="Total a cobrar", font=ctk.CTkFont(size=14)).pack(pady=(16, 0))
        ctk.CTkLabel(
            ventana, text=formatear_precio(total), font=ctk.CTkFont(size=28, weight="bold")
        ).pack()

        entry_pago = ctk.CTkEntry(
            ventana, width=220, placeholder_text="Paga con ($)", font=ctk.CTkFont(size=16), justify="center"
        )
        entry_pago.pack(pady=(14, 6))

        lbl_cambio = ctk.CTkLabel(ventana, text="Cambio: —", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_cambio.pack(pady=4)
        color_normal = lbl_cambio.cget("text_color")

        def leer_pago():
            """El monto escrito, o None si está vacío o no es un número."""
            try:
                return leer_precio(entry_pago.get().strip())
            except ValueError:
                return None

        def actualizar_cambio(_evento=None):
            pago = leer_pago()
            if pago is None:
                lbl_cambio.configure(text="Cambio: —", text_color=color_normal)
            elif round(pago, 2) < round(total, 2):
                lbl_cambio.configure(
                    text=f"Faltan {formatear_precio(total - pago)}", text_color=("#C62828", "#EF5350")
                )
            else:
                lbl_cambio.configure(
                    text=f"Cambio: {formatear_precio(pago - total)}", text_color=("#2E7D32", "#66BB6A")
                )

        def confirmar(_evento=None):
            if not entry_pago.get().strip():
                messagebox.showwarning("Pago Vacío", "Escribe con cuánto paga el cliente.", parent=ventana)
                return
            pago = leer_pago()
            if pago is None:
                messagebox.showerror(
                    "Dato Inválido", "El pago debe ser un número (ej: 20000 o 20.000).", parent=ventana
                )
                return
            if round(pago, 2) < round(total, 2):
                messagebox.showerror(
                    "Pago Insuficiente", f"Faltan {formatear_precio(total - pago)} para completar el pago.",
                    parent=ventana
                )
                return
            resultado["pago"] = pago
            ventana.destroy()

        def pago_exacto():
            entry_pago.delete(0, "end")
            entry_pago.insert(0, formatear_numero(total))
            confirmar()

        frame_botones = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_botones.pack(pady=(14, 10))
        ctk.CTkButton(
            frame_botones, text="Cancelar", width=100, font=ctk.CTkFont(size=13),
            fg_color="#555555", hover_color="#333333", command=ventana.destroy
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="Pago exacto", width=110, font=ctk.CTkFont(size=13),
            fg_color="#00838F", hover_color="#005662", command=pago_exacto
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            frame_botones, text="💵 Cobrar", width=110, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32", hover_color="#1B5E20", command=confirmar
        ).pack(side="left", padx=4)

        entry_pago.bind("<KeyRelease>", actualizar_cambio)
        entry_pago.bind("<Return>", confirmar)
        ventana.bind("<Escape>", lambda _evento: ventana.destroy())
        ventana.after(150, entry_pago.focus_set)

        # Esperar a que se cierre la ventana antes de seguir con la venta
        self.wait_window(ventana)
        return resultado["pago"]

    @manejar_errores_bd
    def abrir_ventana_ventas(self):
        ventana_ventas = ctk.CTkToplevel(self)
        ventana_ventas.title("Historial de Ventas")
        ventana_ventas.geometry("820x600")
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

        # Dos pestañas que comparten los filtros de fecha
        pestanas = ctk.CTkTabview(ventana_ventas)
        pestanas.pack(fill="both", expand=True, padx=15, pady=(4, 10))
        tab_ventas = pestanas.add("Ventas")
        tab_ranking = pestanas.add("🏆 Más vendidos")

        frame_tabla = ctk.CTkFrame(tab_ventas)
        frame_tabla.pack(fill="both", expand=True, pady=(0, 8))

        columnas = ("id", "producto", "cantidad", "total", "fecha", "estado")
        tabla_ventas = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        tabla_ventas.tag_configure("anulada", foreground="#888888")

        tabla_ventas.heading("id", text="ID Venta")
        tabla_ventas.heading("producto", text="Producto")
        tabla_ventas.heading("cantidad", text="Cant.")
        tabla_ventas.heading("total", text="Total ($)")
        tabla_ventas.heading("fecha", text="Fecha y Hora")
        tabla_ventas.heading("estado", text="Estado")

        tabla_ventas.column("id", width=60, anchor="center")
        tabla_ventas.column("producto", width=180)
        tabla_ventas.column("cantidad", width=60, anchor="center")
        tabla_ventas.column("total", width=90, anchor="e")
        tabla_ventas.column("fecha", width=160, anchor="center")
        tabla_ventas.column("estado", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_ventas.yview)
        tabla_ventas.configure(yscroll=scrollbar.set)

        tabla_ventas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        lbl_total_acumulado = ctk.CTkLabel(
            tab_ventas, 
            text="", 
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#2E7D32"
        )
        lbl_total_acumulado.pack(pady=(0, 4))

        # Pestaña de productos más vendidos
        frame_ranking = ctk.CTkFrame(tab_ranking)
        frame_ranking.pack(fill="both", expand=True, pady=(0, 8))

        columnas_ranking = ("puesto", "producto", "unidades", "total", "porcentaje")
        tabla_ranking = ttk.Treeview(frame_ranking, columns=columnas_ranking, show="headings")
        tabla_ranking.heading("puesto", text="#")
        tabla_ranking.heading("producto", text="Producto")
        tabla_ranking.heading("unidades", text="Unidades Vendidas")
        tabla_ranking.heading("total", text="Total ($)")
        tabla_ranking.heading("porcentaje", text="% de lo Vendido")
        # Las columnas de números no se encogen, para que sus títulos no se corten;
        # si la ventana cambia de tamaño, la que se ajusta es la de Producto
        tabla_ranking.column("puesto", width=40, minwidth=40, stretch=False, anchor="center")
        tabla_ranking.column("producto", width=200, minwidth=120)
        tabla_ranking.column("unidades", width=195, minwidth=195, stretch=False, anchor="center")
        tabla_ranking.column("total", width=110, minwidth=110, stretch=False, anchor="e")
        tabla_ranking.column("porcentaje", width=175, minwidth=175, stretch=False, anchor="center")

        scrollbar_ranking = ttk.Scrollbar(frame_ranking, orient="vertical", command=tabla_ranking.yview)
        tabla_ranking.configure(yscroll=scrollbar_ranking.set)
        tabla_ranking.pack(side="left", fill="both", expand=True)
        scrollbar_ranking.pack(side="right", fill="y")

        lbl_resumen_ranking = ctk.CTkLabel(tab_ranking, text="", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_resumen_ranking.pack(pady=(0, 4))

        def poner_fechas(desde, hasta):
            for entry, valor in ((entry_desde, desde), (entry_hasta, hasta)):
                entry.delete(0, "end")
                if valor:
                    entry.insert(0, valor.strftime("%Y-%m-%d"))
            cargar_ventas()

        def cargar_ventas():
            fechas = []
            for entry in (entry_desde, entry_hasta):
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
                        "Fecha Inválida", f"'{texto}' no es una fecha válida. Usa el formato AAAA-MM-DD.",
                        parent=ventana_ventas
                    )
                    return
                entry.delete(0, "end")
                entry.insert(0, fecha)
                fechas.append(fecha)
            desde, hasta = fechas
            if desde and hasta and desde > hasta:
                messagebox.showerror(
                    "Rango Inválido", "La fecha 'Desde' no puede ser posterior a 'Hasta'.", parent=ventana_ventas
                )
                return

            for tabla in (tabla_ventas, tabla_ranking):
                for item in tabla.get_children():
                    tabla.delete(item)

            try:
                ventas = db.obtener_ventas(desde, hasta)
                ranking = db.obtener_mas_vendidos(desde, hasta)
            except (sqlite3.Error, OSError) as error:
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"Ocurrió un problema al acceder a la base de datos:\n{error}",
                    parent=ventana_ventas
                )
                return

            dinero_total = 0.0
            lineas_validas = 0
            for v in ventas:
                id_venta, prod_id, nombre_prod, cant, total, fecha, anulada = v
                if anulada:
                    tabla_ventas.insert(
                        "", "end", iid=str(id_venta), tags=("anulada",),
                        values=(id_venta, nombre_prod, formatear_numero(cant), formatear_precio(total), fecha, "Anulada")
                    )
                else:
                    dinero_total += total
                    lineas_validas += 1
                    tabla_ventas.insert(
                        "", "end", iid=str(id_venta),
                        values=(id_venta, nombre_prod, formatear_numero(cant), formatear_precio(total), fecha, "OK")
                    )

            if desde or hasta:
                periodo = f"{desde or 'el inicio'} a {hasta or 'hoy'}"
            else:
                periodo = "todo el historial"
            lbl_total_acumulado.configure(
                text=f"Total Recaudado ({periodo}): {formatear_precio(dinero_total)}  ·  {lineas_validas} líneas de venta"
            )

            total_ranking = sum(total for _, _, total in ranking)
            for puesto, (nombre_prod, unidades, total) in enumerate(ranking, start=1):
                porcentaje = f"{total / total_ranking * 100:.1f} %".replace(".", ",") if total_ranking else "—"
                tabla_ranking.insert(
                    "", "end",
                    values=(puesto, nombre_prod, formatear_numero(unidades), formatear_precio(total), porcentaje)
                )
            if ranking:
                lbl_resumen_ranking.configure(
                    text=f"{len(ranking)} producto(s) vendidos ({periodo})  ·  "
                         f"Más vendido: {ranking[0][0]} ({formatear_numero(ranking[0][1])} unidades)"
                )
            else:
                lbl_resumen_ranking.configure(text=f"No hay ventas en este período ({periodo}).")

        def anular_seleccionadas():
            seleccion = tabla_ventas.selection()
            if not seleccion:
                messagebox.showwarning(
                    "Selección Requerida", "Selecciona una o más ventas para anular.", parent=ventana_ventas
                )
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"¿Anular {len(seleccion)} línea(s) de venta? Las unidades volverán al stock.",
                parent=ventana_ventas
            ):
                return

            try:
                exito, mensaje = db.anular_ventas([int(iid) for iid in seleccion])
            except (sqlite3.Error, OSError) as error:
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"Ocurrió un problema al acceder a la base de datos:\n{error}",
                    parent=ventana_ventas
                )
                return

            if exito:
                messagebox.showinfo("Venta Anulada", mensaje, parent=ventana_ventas)
                cargar_ventas()
                self.limpiar_formulario()
                self.cargar_productos_en_tabla()
            else:
                messagebox.showerror("No se pudo anular", mensaje, parent=ventana_ventas)

        ctk.CTkButton(
            tab_ventas, text="↩ Anular Venta Seleccionada", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#D32F2F", hover_color="#B71C1C", command=anular_seleccionadas
        ).pack(before=lbl_total_acumulado, pady=(0, 8))

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

        for entry in (entry_desde, entry_hasta):
            entry.bind("<Return>", lambda _evento: cargar_ventas())

        cargar_ventas()

    @manejar_errores_bd
    def abrir_ventana_entradas(self):
        """Registra la llegada de mercancía para el producto seleccionado y muestra el historial de entradas."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Entrada de Mercancía")
        ventana.geometry("680x500")
        ventana.grab_set()

        ctk.CTkLabel(
            ventana, text="📥 Entrada de Mercancía", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        producto = db.obtener_producto(self.id_producto_seleccionado) if self.id_producto_seleccionado else None
        if producto:
            texto_producto = f"Producto: {producto[1]}  ·  Stock actual: {formatear_numero(producto[4])}"
        else:
            texto_producto = "Selecciona un producto en la tabla principal para registrar una entrada."
        lbl_producto = ctk.CTkLabel(ventana, text=texto_producto, font=ctk.CTkFont(size=14))
        lbl_producto.pack(padx=15)

        frame_registro = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_registro.pack(pady=8)
        entry_cantidad = ctk.CTkEntry(
            frame_registro, width=160, placeholder_text="Unidades recibidas", font=ctk.CTkFont(size=14)
        )
        entry_cantidad.pack(side="left", padx=5)
        btn_registrar = ctk.CTkButton(
            frame_registro, text="Registrar Entrada", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#00838F", hover_color="#005662"
        )
        btn_registrar.pack(side="left", padx=5)
        if not producto:
            entry_cantidad.configure(state="disabled")
            btn_registrar.configure(state="disabled")

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(
            ventana, text="Movimientos de stock (entradas, stock inicial y ajustes manuales)",
            font=ctk.CTkFont(size=13)
        ).pack(padx=15, anchor="w")

        columnas = ("id", "producto", "cantidad", "fecha", "motivo")
        tabla_entradas = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        tabla_entradas.heading("id", text="ID")
        tabla_entradas.heading("producto", text="Producto")
        tabla_entradas.heading("cantidad", text="Unidades")
        tabla_entradas.heading("fecha", text="Fecha y Hora")
        tabla_entradas.heading("motivo", text="Motivo")
        tabla_entradas.column("id", width=50, anchor="center")
        tabla_entradas.column("producto", width=200)
        tabla_entradas.column("cantidad", width=80, anchor="center")
        tabla_entradas.column("fecha", width=150, anchor="center")
        tabla_entradas.column("motivo", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_entradas.yview)
        tabla_entradas.configure(yscroll=scrollbar.set)
        tabla_entradas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def cargar_entradas():
            for item in tabla_entradas.get_children():
                tabla_entradas.delete(item)
            for id_mov, nombre, cantidad, fecha, motivo in db.obtener_entradas():
                tabla_entradas.insert("", "end", values=(id_mov, nombre, formatear_cambio(cantidad), fecha, motivo))

        def registrar():
            cant_str = entry_cantidad.get().strip()
            try:
                cantidad = leer_entero(cant_str)
                if cantidad <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Error", "La cantidad debe ser un número entero positivo.", parent=ventana
                )
                return

            try:
                exito, mensaje = db.registrar_entrada(producto[0], cantidad)
                if exito:
                    cargar_entradas()
                    # El formulario tendría el stock anterior: se limpia para no sobrescribirlo
                    self.limpiar_formulario()
                    self.cargar_productos_en_tabla()
                    actualizado = db.obtener_producto(producto[0])
            except (sqlite3.Error, OSError) as error:
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"Ocurrió un problema al acceder a la base de datos:\n{error}",
                    parent=ventana
                )
                return

            if exito:
                entry_cantidad.delete(0, "end")
                lbl_producto.configure(
                    text=f"Producto: {actualizado[1]}  ·  Stock actual: {formatear_numero(actualizado[4])}"
                )
                messagebox.showinfo("Entrada Registrada", mensaje, parent=ventana)
            else:
                messagebox.showerror("Error", mensaje, parent=ventana)

        btn_registrar.configure(command=registrar)
        if producto:
            entry_cantidad.bind("<Return>", lambda _evento: registrar())
        cargar_entradas()

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
                cambios = self.refrescar_carrito()
                if cambios:
                    messagebox.showinfo("Carrito Actualizado", "\n".join(cambios))
            else:
                messagebox.showerror("No se pudo eliminar", mensaje)

    def filtrar_productos(self, _evento=None):
        self.cargar_productos_en_tabla()

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


    def cerrar_aplicacion(self):
        if self.carrito and not messagebox.askyesno(
            "Carrito Pendiente",
            f"Hay {len(self.carrito)} producto(s) en el carrito sin cobrar.\n¿Cerrar de todas formas?"
        ):
            return
        self.destroy()


def iniciar_app():
    app = AplicacionInventario()
    app.mainloop()