import customtkinter as ctk
from tkinter import ttk, messagebox

import base_datos as db
from componentes import STOCK_BAJO, manejar_errores_bd
from formato import clave_orden, formatear_numero, formatear_precio, leer_entero, leer_precio
from ventana_entradas import VentanaEntradas
from ventana_pago import pedir_pago
from ventana_recibo import VentanaRecibo
from ventana_ventas import VentanaVentas

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class AplicacionInventario(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema CRUD y Gestión de Inventario")
        self.geometry("1100x650")
        self.minsize(900, 640)

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

        # No lleva el atajo de Enter: el lector escribe el código y "presiona" Enter,
        # y eso guardaría el producto antes de terminar de llenar el formulario
        self.entry_codigo = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Código de barras (opcional)", font=ctk.CTkFont(size=14)
        )
        self.entry_codigo.pack(fill="x", padx=15, pady=5)

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

        # El cursor empieza en el campo de escanear, para vender apenas se abre la tienda
        self.after(200, self.entry_escanear.focus_set)

        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    def configurar_tabla(self):
        columnas = ("id", "nombre", "categoria", "precio", "stock", "codigo")
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
            "id": "ID", "nombre": "Nombre", "categoria": "Categoría", "precio": "Precio ($)", "stock": "Stock",
            "codigo": "Código"
        }
        for columna in columnas:
            self.tabla.heading(columna, command=lambda c=columna: self.ordenar_por_columna(c))
        self.actualizar_flechas_orden()

        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=180)
        self.tabla.column("categoria", width=120)
        self.tabla.column("precio", width=100, anchor="e")
        self.tabla.column("stock", width=80, anchor="center")
        self.tabla.column("codigo", width=130, anchor="center")

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

        for p in lista_productos:
            valores = (
                p["id"], p["nombre"], p["categoria"], formatear_precio(p["precio"]), formatear_numero(p["stock"]),
                p["codigo_barras"] or ""
            )
            etiquetas = ("stock_bajo",) if p["stock"] < STOCK_BAJO else ()
            self.tabla.insert("", "end", iid=str(p["id"]), values=valores, tags=etiquetas)

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

        # Venta con lector de códigos de barras: cada escaneo suma 1 unidad al carrito
        self.entry_escanear = ctk.CTkEntry(
            self.frame_carrito, width=230, placeholder_text="📷 Escanear código de barras", font=ctk.CTkFont(size=14)
        )
        self.entry_escanear.grid(row=0, column=1, padx=(10, 6), pady=(6, 4))
        self.entry_escanear.bind("<Return>", lambda _evento: self.escanear_codigo())

        self.lbl_escaneo = ctk.CTkLabel(self.frame_carrito, text="", font=ctk.CTkFont(size=13))
        self.lbl_escaneo.grid(row=0, column=2, padx=6, pady=(6, 4), sticky="w")

        self.lbl_total_carrito = ctk.CTkLabel(
            self.frame_carrito, text="Total: $0", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_total_carrito.grid(row=0, column=3, padx=10, pady=(6, 4), sticky="e")

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
        self.tabla_carrito.grid(row=1, column=0, columnspan=4, padx=10, sticky="ew")

        frame_botones = ctk.CTkFrame(self.frame_carrito, fg_color="transparent")
        frame_botones.grid(row=2, column=0, columnspan=4, padx=10, pady=8, sticky="ew")

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
                clave = lambda x: clave_orden(str(x[0]))
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

    @manejar_errores_bd
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

        # El código se lee de la base de datos y no de la tabla, porque la tabla
        # podría convertirlo en número y quitarle los ceros iniciales (0123... -> 123...)
        producto = db.obtener_producto(self.id_producto_seleccionado)
        self.entry_codigo.delete(0, "end")
        if producto and producto["codigo_barras"]:
            self.entry_codigo.insert(0, producto["codigo_barras"])

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
        existente = db.nombre_repetido(nombre, excluir_id=self.id_producto_seleccionado)
        if existente:
            messagebox.showerror(
                "Producto Repetido",
                f"Ya existe un producto llamado '{existente}'. Usa otro nombre o edita el que ya existe."
            )
            return
        codigo, error = db.leer_codigo(self.entry_codigo.get())
        if error:
            messagebox.showerror("Código Inválido", error)
            return
        otro = db.codigo_repetido(codigo, excluir_id=self.id_producto_seleccionado)
        if otro:
            messagebox.showerror("Código Repetido", f"El código {codigo} ya pertenece a '{otro}'.")
            return

        if db.categoria_es_nueva(categoria) and not messagebox.askyesno(
            "Categoría Nueva",
            f"La categoría '{categoria}' no existe todavía.\n\n"
            f"Categorías actuales: {', '.join(db.obtener_categorias()) or '(ninguna)'}\n\n"
            "¿Crear esta categoría nueva?"
        ):
            return

        if self.id_producto_seleccionado:
            exito, mensaje = db.actualizar_producto(
                self.id_producto_seleccionado, nombre, categoria, precio, stock, codigo
            )
        else:
            exito, mensaje = db.agregar_producto(nombre, categoria, precio, stock, codigo)

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

        if self.sumar_al_carrito(producto, cantidad):
            self.limpiar_formulario()

    def sumar_al_carrito(self, producto, cantidad):
        """Suma unidades de un producto al carrito si hay stock. Retorna True si se agregaron."""
        en_carrito = self.carrito.get(producto["id"], {}).get("cantidad", 0)
        if en_carrito + cantidad > producto["stock"]:
            messagebox.showerror(
                "Stock Insuficiente",
                f"Solo quedan {formatear_numero(producto['stock'])} unidades de '{producto['nombre']}' "
                f"y ya hay {formatear_numero(en_carrito)} en el carrito."
            )
            return False

        self.carrito[producto["id"]] = {
            "nombre": producto["nombre"], "precio": producto["precio"], "cantidad": en_carrito + cantidad
        }
        self.actualizar_carrito()
        return True

    @manejar_errores_bd
    def escanear_codigo(self):
        """El lector escribe el código y presiona Enter: se suma 1 unidad de ese producto al carrito."""
        codigo = self.entry_escanear.get().strip()
        self.entry_escanear.delete(0, "end")
        if not codigo:
            return

        producto = db.buscar_por_codigo(codigo)
        if producto:
            if self.sumar_al_carrito(producto, 1):
                cantidad = formatear_numero(self.carrito[producto["id"]]["cantidad"])
                # Nombre recortado para que el aviso no empuje el total fuera de la ventana
                nombre = producto["nombre"] if len(producto["nombre"]) <= 22 else producto["nombre"][:21] + "…"
                self.lbl_escaneo.configure(text=f"✓ {nombre} ({cantidad} en el carrito)")
            else:
                self.lbl_escaneo.configure(text="")
            self.entry_escanear.focus_set()
            return

        self.lbl_escaneo.configure(text="")
        if messagebox.askyesno(
            "Código No Registrado",
            f"El código {codigo} no pertenece a ningún producto.\n\n"
            "¿Quieres registrar un producto nuevo con este código?\n\n"
            "(Para ponérselo a un producto que ya existe, selecciónalo en la tabla y "
            "escanéalo en el campo 'Código de barras' del formulario.)"
        ):
            self.limpiar_formulario()
            self.entry_codigo.insert(0, codigo)
            self.entry_nombre.focus_set()
        else:
            self.entry_escanear.focus_set()

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
        if not self.carrito:
            self.lbl_escaneo.configure(text="")

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
            if producto["precio"] != linea["precio"]:
                cambios.append(
                    f"'{producto['nombre']}': precio {formatear_precio(linea['precio'])} → "
                    f"{formatear_precio(producto['precio'])}"
                )
            linea["nombre"], linea["precio"] = producto["nombre"], producto["precio"]
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

        pago = pedir_pago(self, total)
        if pago is None:
            return

        items = [(id_producto, linea["cantidad"]) for id_producto, linea in self.carrito.items()]
        exito, mensaje, id_recibo = db.registrar_venta_carrito(items, pago)

        if exito:
            self.carrito.clear()
            self.actualizar_carrito()
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()
            # El recibo reemplaza al mensaje de "venta realizada": muestra total, pago y cambio
            VentanaRecibo(self, db.obtener_recibo(id_recibo))
        else:
            messagebox.showerror("Error en Venta", mensaje)

    @manejar_errores_bd
    def abrir_ventana_ventas(self):
        VentanaVentas(self, al_anular=self.actualizar_tras_cambio_de_stock)

    @manejar_errores_bd
    def abrir_ventana_entradas(self):
        """Registra la llegada de mercancía para el producto seleccionado y muestra el historial de entradas."""
        producto = db.obtener_producto(self.id_producto_seleccionado) if self.id_producto_seleccionado else None
        VentanaEntradas(self, producto, al_registrar=self.actualizar_tras_cambio_de_stock)

    def actualizar_tras_cambio_de_stock(self):
        """
        Otra ventana cambió el stock (anuló una venta o registró una entrada).
        El formulario tendría el stock anterior, así que se limpia para no
        sobrescribirlo, y la tabla se recarga.
        """
        self.limpiar_formulario()
        self.cargar_productos_en_tabla()

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
        self.entry_codigo.delete(0, "end")
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