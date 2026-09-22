import customtkinter as ctk
from tkinter import ttk, messagebox
import base_datos as db

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

         
class AplicacionInventario(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema CRUD y Gestión de Inventario")
        self.geometry("1000x700")
        self.minsize(1500, 800)

        # Variables internas de selección
        self.id_producto_seleccionado = None
        self.precio_producto_seleccionado = 0.0
        self.nombre_producto_seleccionado = ""
        self.orden_ascendente = True

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
            self.frame_formulario, text="🛒 Registrar Venta", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_venta.pack(padx=10, pady=(12, 6))

        self.entry_cant_venta = ctk.CTkEntry(
            self.frame_formulario, placeholder_text="Cantidad a vender", font=ctk.CTkFont(size=14)
        )
        self.entry_cant_venta.pack(fill="x", padx=15, pady=5)

        self.btn_vender = ctk.CTkButton(
            self.frame_formulario, 
            text="Confirmar Venta", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32", 
            hover_color="#1B5E20",
            command=self.procesar_venta
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
        self.cargar_productos_en_tabla()

    def configurar_tabla(self):
        columnas = ("id", "nombre", "categoria", "precio", "stock")
        self.tabla = ttk.Treeview(self.tabla_frame, columns=columnas, show="headings")

        # Ajuste de tamaño de fuente en la tabla
        estilo = ttk.Style()
        estilo.configure("Treeview", font=("TkDefaultFont", 13), rowheight=28)
        estilo.configure("Treeview.Heading", font=("TkDefaultFont", 14, "bold"))

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

    def ordenar_por_columna(self, columna, indice):
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
        self.nombre_producto_seleccionado = valores[1]
        self.precio_producto_seleccionado = float(valores[3])
        
        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, valores[1])

        self.entry_categoria.delete(0, "end")
        self.entry_categoria.insert(0, valores[2])

        self.entry_precio.delete(0, "end")
        self.entry_precio.insert(0, valores[3])

        self.entry_stock.delete(0, "end")
        self.entry_stock.insert(0, valores[4])

        self.btn_guardar.configure(text="Actualizar Producto", fg_color="#2E7D32", hover_color="#1B5E20")

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
            db.actualizar_producto(self.id_producto_seleccionado, nombre, categoria, precio, stock)
            messagebox.showinfo("Éxito", f"Producto '{nombre}' actualizado.")
        else:
            db.agregar_producto(nombre, categoria, precio, stock)
            messagebox.showinfo("Éxito", f"Producto '{nombre}' registrado.")

        self.limpiar_formulario()
        self.cargar_productos_en_tabla()

    def procesar_venta(self):
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

        exito, mensaje = db.registrar_venta(
            self.id_producto_seleccionado, 
            self.nombre_producto_seleccionado, 
            cantidad, 
            self.precio_producto_seleccionado
        )

        if exito:
            messagebox.showinfo("Venta Realizada", mensaje)
            self.entry_cant_venta.delete(0, "end")
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()
        else:
            messagebox.showerror("Error en Venta", mensaje)

    def abrir_ventana_ventas(self):
        ventana_ventas = ctk.CTkToplevel(self)
        ventana_ventas.title("Historial de Ventas")
        ventana_ventas.geometry("750x480")
        ventana_ventas.grab_set()

        lbl_titulo = ctk.CTkLabel(
            ventana_ventas, text="📜 Historial de Transacciones", font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_titulo.pack(pady=10)

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

        ventas = db.obtener_ventas()
        dinero_total = 0.0

        for v in ventas:
            id_venta, prod_id, nombre_prod, cant, total, fecha = v
            dinero_total += total
            tabla_ventas.insert("", "end", values=(id_venta, nombre_prod, cant, f"${total:,.2f}", fecha))

        lbl_total_acumulado = ctk.CTkLabel(
            ventana_ventas, 
            text=f"Total Recaudado: ${dinero_total:,.2f}", 
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#2E7D32"
        )
        lbl_total_acumulado.pack(pady=10)

    def eliminar_producto(self):
        if not self.id_producto_seleccionado:
            messagebox.showwarning("Selección Requerida", "Selecciona un producto de la tabla.")
            return

        if messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar '{self.entry_nombre.get()}'?"):
            db.eliminar_producto(self.id_producto_seleccionado)
            self.limpiar_formulario()
            self.cargar_productos_en_tabla()

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

    def limpiar_formulario(self):
        self.id_producto_seleccionado = None
        self.entry_nombre.delete(0, "end")
        self.entry_categoria.delete(0, "end")
        self.entry_precio.delete(0, "end")
        self.entry_stock.delete(0, "end")
        self.entry_cant_venta.delete(0, "end")
        self.btn_guardar.configure(text="Guardar Producto", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#325882", "#14375e"])


def iniciar_app():
    app = AplicacionInventario()
    app.mainloop()