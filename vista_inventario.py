"""
Pantalla principal: resumen, tabla de productos, formulario de producto
(en un diálogo) y carrito de venta con lector de códigos de barras.
"""
from datetime import date

import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_MARCA, COLOR_PELIGRO, ERRORES_BD, STOCK_BAJO, avisar, con_desplazamiento, crear_tabla, encabezado,
    etiqueta, manejar_errores_bd, mostrar_error_bd, mostrar_mensaje, panel, preguntar, tarjeta_resumen, texto_vacio,
)
from dialogo_pago import pedir_pago
from dialogo_recibo import mostrar_recibo
from formato import clave_orden, formatear_numero, formatear_precio, leer_entero, leer_precio

# Clave para ordenar cada columna de la tabla (en el mismo orden que las columnas)
CLAVES_ORDEN = [
    lambda p: clave_orden(p["nombre"]),
    lambda p: clave_orden(p["categoria"]),
    lambda p: p["precio"],
    lambda p: p["stock"],
    lambda p: p["codigo_barras"] or "",
]


class VistaInventario:
    def __init__(self, page, abrir_entrada):
        """'abrir_entrada(id_producto)' lleva a la pantalla de entradas con ese producto elegido."""
        self.page = page
        self.abrir_entrada = abrir_entrada
        # Carrito: id_producto -> {"nombre", "precio", "cantidad"}
        self.carrito = {}
        # Columna por la que se ordena la tabla (None = orden de la base de datos)
        self.columna_ordenada = None
        self.orden_ascendente = True

        tarjeta_productos, self.valor_productos = tarjeta_resumen(
            ft.Icons.INVENTORY_2_OUTLINED, "Productos", ft.Colors.INDIGO)
        tarjeta_bajo, self.valor_bajo = tarjeta_resumen(
            ft.Icons.WARNING_AMBER_ROUNDED, "Con stock bajo", ft.Colors.RED)
        tarjeta_inventario, self.valor_inventario = tarjeta_resumen(
            ft.Icons.LAYERS_OUTLINED, "Valor del inventario", ft.Colors.TEAL)
        tarjeta_hoy, self.valor_hoy = tarjeta_resumen(
            ft.Icons.PAYMENTS_OUTLINED, "Ventas de hoy", ft.Colors.GREEN)

        self.control = ft.Column(
            spacing=20,
            expand=True,
            controls=[
                encabezado(
                    "Inventario", "Gestiona tus productos y vende desde el carrito",
                    ft.FilledButton(
                        "Nuevo producto", icon=ft.Icons.ADD, height=44,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                        on_click=lambda _: self.abrir_formulario(),
                    ),
                ),
                ft.Row([tarjeta_productos, tarjeta_bajo, tarjeta_inventario, tarjeta_hoy], spacing=12),
                ft.Row(
                    [self.crear_panel_productos(), self.crear_panel_carrito()],
                    expand=True, spacing=16, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
        )

    # --- CONSTRUCCIÓN ---

    def crear_panel_productos(self):
        self.campo_buscar = ft.TextField(
            hint_text="Buscar por nombre o código…", prefix_icon=ft.Icons.SEARCH,
            filled=True, dense=True, expand=True, on_change=lambda _: self.cargar_productos(),
        )
        self.menu_categoria = ft.Dropdown(
            value="Todas", width=190, dense=True, filled=True, leading_icon=ft.Icons.CATEGORY_OUTLINED,
            options=[ft.DropdownOption("Todas")], on_select=lambda _: self.cargar_productos(),
        )
        self.check_stock_bajo = ft.Checkbox(label="Solo stock bajo", on_change=lambda _: self.cargar_productos())

        self.tabla = crear_tabla(
            [("Producto", False), ("Categoría", False), ("Precio", True), ("Stock", True), ("Código", False),
             ("", False)],
            show_checkbox_column=False,
        )
        # Clic en un encabezado: la primera vez ordena de menor a mayor; otro clic invierte el orden
        for columna in self.tabla.columns[:-1]:
            columna.on_sort = self.ordenar_por_columna

        self.sin_productos = texto_vacio(ft.Icons.SEARCH_OFF, "No hay productos que coincidan")
        return panel(
            ft.Column(
                spacing=16,
                controls=[
                    ft.Row([self.campo_buscar, self.menu_categoria, self.check_stock_bajo], spacing=12),
                    ft.Stack([con_desplazamiento(self.tabla), self.sin_productos], expand=True),
                ],
            ),
            expand=True,
        )

    def crear_panel_carrito(self):
        # Venta con lector de códigos de barras: cada escaneo suma 1 unidad al carrito
        self.campo_escanear = ft.TextField(
            hint_text="Escanear código de barras", prefix_icon=ft.Icons.QR_CODE_SCANNER,
            filled=True, autofocus=True, on_submit=self.escanear_codigo,
        )
        self.texto_escaneo = ft.Text("", size=13, color=COLOR_EXITO, visible=False)
        self.lista_carrito = ft.ListView(spacing=8, expand=True)
        self.carrito_vacio = texto_vacio(ft.Icons.SHOPPING_CART_OUTLINED, "Escanea o agrega productos\ndesde la tabla")
        self.texto_total = ft.Text("$0", size=30, weight=ft.FontWeight.BOLD)
        self.texto_unidades = ft.Text("", color=ft.Colors.ON_SURFACE_VARIANT)
        self.boton_cobrar = ft.FilledButton(
            "Cobrar venta", icon=ft.Icons.POINT_OF_SALE, height=52, expand=True,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14), bgcolor=COLOR_EXITO, color=ft.Colors.WHITE,
                text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
            ),
            on_click=self.cobrar_carrito,
        )
        return panel(
            ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Carrito", size=20, weight=ft.FontWeight.BOLD),
                            ft.TextButton("Vaciar", icon=ft.Icons.DELETE_SWEEP_OUTLINED, on_click=self.vaciar_carrito),
                        ],
                    ),
                    self.campo_escanear,
                    self.texto_escaneo,
                    ft.Stack([self.lista_carrito, self.carrito_vacio], expand=True),
                    ft.Divider(height=1),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=[ft.Column([ft.Text("Total"), self.texto_unidades], spacing=0), self.texto_total],
                    ),
                    ft.Row([self.boton_cobrar]),
                ],
            ),
            width=380,
        )

    # --- CARGA DE DATOS ---

    @manejar_errores_bd
    def mostrar(self):
        """Se llama cada vez que se entra a esta pantalla: recarga todo lo que otra pantalla pudo cambiar."""
        self.cargar_productos()
        self.refrescar_carrito()

    @manejar_errores_bd
    def cargar_productos(self):
        """Recarga la tabla respetando la búsqueda, la categoría, el filtro de stock bajo y el orden."""
        self.actualizar_menu_categorias()
        categoria = self.menu_categoria.value
        productos = db.buscar_productos(
            texto=self.campo_buscar.value.strip(),
            categoria=None if categoria == "Todas" else categoria,
            stock_menor_a=STOCK_BAJO if self.check_stock_bajo.value else None,
        )
        self.actualizar_resumen()

        if self.columna_ordenada is not None:
            productos = sorted(productos, key=CLAVES_ORDEN[self.columna_ordenada], reverse=not self.orden_ascendente)

        self.tabla.rows = [self.fila_producto(p) for p in productos]
        self.sin_productos.visible = not productos
        self.page.update()

    def fila_producto(self, p):
        bajo = p["stock"] < STOCK_BAJO
        return ft.DataRow(
            # Clic en la fila: abrir el producto para editarlo
            on_select_change=lambda _, id_p=p["id"]: self.abrir_formulario(id_p),
            cells=[
                ft.DataCell(ft.Text(p["nombre"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(p["categoria"], color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.DataCell(ft.Text(formatear_precio(p["precio"]))),
                ft.DataCell(etiqueta(formatear_numero(p["stock"]), COLOR_PELIGRO if bajo else COLOR_EXITO)),
                ft.DataCell(ft.Text(p["codigo_barras"] or "—", color=ft.Colors.ON_SURFACE_VARIANT, size=13)),
                ft.DataCell(ft.Row(
                    spacing=0,
                    controls=[
                        ft.IconButton(
                            ft.Icons.ADD_SHOPPING_CART, tooltip="Agregar 1 al carrito", icon_color=COLOR_MARCA,
                            on_click=lambda _, id_p=p["id"]: self.agregar_desde_tabla(id_p),
                        ),
                        ft.IconButton(
                            ft.Icons.MOVE_TO_INBOX_OUTLINED, tooltip="Registrar entrada de mercancía",
                            on_click=lambda _, id_p=p["id"]: self.abrir_entrada(id_p),
                        ),
                        ft.IconButton(
                            ft.Icons.EDIT_OUTLINED, tooltip="Editar",
                            on_click=lambda _, id_p=p["id"]: self.abrir_formulario(id_p),
                        ),
                    ],
                )),
            ],
        )

    def actualizar_menu_categorias(self):
        """Mantiene el menú de categorías al día con los productos existentes."""
        categorias = ["Todas"] + db.obtener_categorias()
        self.menu_categoria.options = [ft.DropdownOption(c) for c in categorias]
        if self.menu_categoria.value not in categorias:
            self.menu_categoria.value = "Todas"

    def actualizar_resumen(self):
        """Números de las tarjetas: se calculan con todos los productos, sin los filtros de la tabla."""
        productos = db.buscar_productos()
        hoy = date.today().strftime("%Y-%m-%d")
        ventas_hoy = sum(v["total"] for v in db.obtener_ventas(hoy, hoy) if not v["anulada"])
        self.valor_productos.value = formatear_numero(len(productos))
        self.valor_bajo.value = formatear_numero(sum(1 for p in productos if p["stock"] < STOCK_BAJO))
        self.valor_inventario.value = formatear_precio(sum(p["precio"] * p["stock"] for p in productos))
        self.valor_hoy.value = formatear_precio(ventas_hoy)

    def ordenar_por_columna(self, e):
        indice = e.column_index
        if indice == self.columna_ordenada:
            self.orden_ascendente = not self.orden_ascendente
        else:
            self.columna_ordenada = indice
            self.orden_ascendente = True
        # Muestra la flecha en el encabezado ordenado
        self.tabla.sort_column_index = indice
        self.tabla.sort_ascending = self.orden_ascendente
        self.cargar_productos()

    # --- FORMULARIO DE PRODUCTO ---

    @manejar_errores_bd
    def abrir_formulario(self, id_producto=None, codigo=""):
        """Diálogo para crear un producto (id_producto=None) o editar uno existente.
        'codigo' prellena el código de barras al registrar un producto escaneado."""
        producto = None
        if id_producto is not None:
            producto = db.obtener_producto(id_producto)
            if not producto:
                mostrar_mensaje(self.page, "Producto no encontrado", "El producto ya no existe.", error=True)
                self.cargar_productos()
                return

        def campo(etiqueta_campo, valor, icono, **opciones):
            return ft.TextField(label=etiqueta_campo, value=valor, prefix_icon=icono, **opciones)

        # El código no guarda con Enter: el lector escribe el código y "presiona" Enter,
        # y eso guardaría el producto antes de terminar de llenar el formulario
        campo_nombre = campo("Nombre del producto", producto["nombre"] if producto else "", ft.Icons.LABEL_OUTLINE,
                             autofocus=True)
        campo_codigo = campo("Código de barras (opcional)",
                             (producto["codigo_barras"] or "") if producto else codigo, ft.Icons.QR_CODE)
        campo_categoria = campo("Categoría (ej: Lácteos)", producto["categoria"] if producto else "",
                                ft.Icons.CATEGORY_OUTLINED)
        campo_precio = campo("Precio ($)", formatear_numero(producto["precio"]) if producto else "",
                             ft.Icons.ATTACH_MONEY, expand=True)
        campo_stock = campo("Stock (unidades)", formatear_numero(producto["stock"]) if producto else "",
                            ft.Icons.LAYERS_OUTLINED, expand=True)
        campos = [campo_nombre, campo_codigo, campo_categoria, campo_precio, campo_stock]

        def marcar_error(campo_con_error, mensaje):
            campo_con_error.error_text = mensaje
            self.page.update()

        async def guardar(_e):
            try:
                await validar_y_guardar()
            except ERRORES_BD as error:
                mostrar_error_bd(self.page, error)

        # Enter guarda desde cualquier campo menos el del código
        for c in (campo_nombre, campo_categoria, campo_precio, campo_stock):
            c.on_submit = guardar

        async def validar_y_guardar():
            for c in campos:
                c.error_text = None
            nombre = campo_nombre.value.strip()
            categoria = campo_categoria.value.strip()

            vacios = [c for c in (campo_nombre, campo_categoria, campo_precio, campo_stock) if not c.value.strip()]
            if vacios:
                for c in vacios:
                    c.error_text = "Campo obligatorio"
                self.page.update()
                return
            try:
                precio = leer_precio(campo_precio.value.strip())
            except ValueError:
                return marcar_error(campo_precio, "Debe ser un número (ej: 1500, 1.500 o 1.500,50)")
            try:
                stock = leer_entero(campo_stock.value.strip())
            except ValueError:
                return marcar_error(campo_stock, "Debe ser un número entero")

            error = db.validar_producto(precio, stock)
            if error:
                mostrar_mensaje(self.page, "Dato Inválido", error, error=True)
                return
            existente = db.nombre_repetido(nombre, excluir_id=id_producto)
            if existente:
                return marcar_error(campo_nombre, f"Ya existe un producto llamado '{existente}'")
            codigo_leido, error = db.leer_codigo(campo_codigo.value)
            if error:
                return marcar_error(campo_codigo, error)
            otro = db.codigo_repetido(codigo_leido, excluir_id=id_producto)
            if otro:
                return marcar_error(campo_codigo, f"Este código ya pertenece a '{otro}'")

            if db.categoria_es_nueva(categoria) and not await preguntar(
                self.page, "Categoría Nueva",
                f"La categoría '{categoria}' no existe todavía.\n\n"
                f"Categorías actuales: {', '.join(db.obtener_categorias()) or '(ninguna)'}\n\n"
                "¿Crear esta categoría nueva?",
                si="Crear categoría",
            ):
                return

            if id_producto is not None:
                exito, mensaje = db.actualizar_producto(id_producto, nombre, categoria, precio, stock, codigo_leido)
            else:
                exito, mensaje = db.agregar_producto(nombre, categoria, precio, stock, codigo_leido)
            if not exito:
                mostrar_mensaje(self.page, "Dato Inválido", mensaje, error=True)
                return

            self.page.pop_dialog()
            avisar(self.page, mensaje)
            self.cargar_productos()
            self.refrescar_carrito()

        async def eliminar(_e):
            try:
                await confirmar_y_eliminar()
            except ERRORES_BD as error:
                mostrar_error_bd(self.page, error)

        async def confirmar_y_eliminar():
            if not await preguntar(
                self.page, "Eliminar producto", f"¿Estás seguro de eliminar '{producto['nombre']}'?",
                si="Eliminar", peligro=True,
            ):
                return
            exito, mensaje = db.eliminar_producto(id_producto)
            if not exito:
                mostrar_mensaje(self.page, "No se pudo eliminar", mensaje, error=True)
                return
            self.page.pop_dialog()
            avisar(self.page, f"Se eliminó '{producto['nombre']}'")
            self.cargar_productos()
            cambios = self.refrescar_carrito()
            if cambios:
                mostrar_mensaje(self.page, "Carrito Actualizado", "\n".join(cambios))

        acciones = [
            ft.TextButton("Cancelar", on_click=lambda _: self.page.pop_dialog()),
            ft.FilledButton("Guardar", icon=ft.Icons.SAVE_OUTLINED, on_click=guardar),
        ]
        if producto:
            acciones.insert(0, ft.TextButton(
                "Eliminar", icon=ft.Icons.DELETE_OUTLINE, style=ft.ButtonStyle(color=COLOR_PELIGRO),
                on_click=eliminar,
            ))

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Editar producto" if producto else "Nuevo producto"),
            content=ft.Column(
                tight=True, spacing=14, width=460,
                controls=[campo_nombre, campo_codigo, campo_categoria, ft.Row([campo_precio, campo_stock])],
            ),
            actions=acciones,
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    # --- CARRITO ---

    @manejar_errores_bd
    def agregar_desde_tabla(self, id_producto):
        producto = db.obtener_producto(id_producto)
        if not producto:
            mostrar_mensaje(self.page, "Error", "El producto ya no existe.", error=True)
            self.cargar_productos()
            return
        if self.sumar_al_carrito(producto, 1):
            self.mostrar_escaneo(producto)

    def sumar_al_carrito(self, producto, cantidad):
        """Suma unidades de un producto al carrito si hay stock. Retorna True si se agregaron."""
        en_carrito = self.carrito.get(producto["id"], {}).get("cantidad", 0)
        return self.poner_cantidad(producto, en_carrito + cantidad)

    def poner_cantidad(self, producto, cantidad):
        """Deja 'cantidad' unidades del producto en el carrito si hay stock. Retorna True si se pudo."""
        if cantidad > producto["stock"]:
            en_carrito = self.carrito.get(producto["id"], {}).get("cantidad", 0)
            mostrar_mensaje(
                self.page, "Stock Insuficiente",
                f"Solo quedan {formatear_numero(producto['stock'])} unidades de '{producto['nombre']}' "
                f"y ya hay {formatear_numero(en_carrito)} en el carrito.",
                error=True,
            )
            return False
        self.carrito[producto["id"]] = {"nombre": producto["nombre"], "precio": producto["precio"], "cantidad": cantidad}
        self.actualizar_carrito()
        return True

    @manejar_errores_bd
    def cambiar_cantidad(self, id_producto, nueva):
        """Botones + y − y el campo de cantidad de cada línea del carrito."""
        if nueva <= 0:
            self.carrito.pop(id_producto, None)
            self.actualizar_carrito()
            return
        producto = db.obtener_producto(id_producto)
        if not producto:
            self.refrescar_carrito()
            return
        if not self.poner_cantidad(producto, nueva):
            # Vuelve a mostrar la cantidad que había, no la que se escribió
            self.actualizar_carrito()

    def escribir_cantidad(self, id_producto, campo):
        try:
            nueva = leer_entero(campo.value.strip())
            if nueva < 0:
                raise ValueError
        except ValueError:
            avisar(self.page, "La cantidad debe ser un número entero positivo.", error=True)
            self.actualizar_carrito()
            return
        if nueva != self.carrito.get(id_producto, {}).get("cantidad"):
            self.cambiar_cantidad(id_producto, nueva)

    def mostrar_escaneo(self, producto):
        cantidad = formatear_numero(self.carrito[producto["id"]]["cantidad"])
        self.texto_escaneo.value = f"✓ {producto['nombre']} ({cantidad} en el carrito)"
        self.texto_escaneo.visible = True
        self.page.update()

    @manejar_errores_bd
    async def escanear_codigo(self, _e):
        """El lector escribe el código y presiona Enter: se suma 1 unidad de ese producto al carrito."""
        codigo = self.campo_escanear.value.strip()
        self.campo_escanear.value = ""
        self.page.update()
        if not codigo:
            return

        producto = db.buscar_por_codigo(codigo)
        if producto:
            if self.sumar_al_carrito(producto, 1):
                self.mostrar_escaneo(producto)
            await self.campo_escanear.focus()
            return

        self.texto_escaneo.visible = False
        if await preguntar(
            self.page, "Código No Registrado",
            f"El código {codigo} no pertenece a ningún producto.\n\n"
            "¿Quieres registrar un producto nuevo con este código?\n\n"
            "(Para ponérselo a un producto que ya existe, ábrelo con el lápiz de la tabla "
            "y escanéalo en el campo 'Código de barras'.)",
            si="Registrar producto",
        ):
            self.abrir_formulario(codigo=codigo)
        else:
            await self.campo_escanear.focus()

    def linea_carrito(self, id_producto, linea):
        campo_cantidad = ft.TextField(
            value=formatear_numero(linea["cantidad"]), width=58, dense=True, text_align=ft.TextAlign.CENTER,
            content_padding=ft.Padding.symmetric(horizontal=4, vertical=8),
        )
        campo_cantidad.on_submit = lambda _: self.escribir_cantidad(id_producto, campo_cantidad)
        campo_cantidad.on_blur = lambda _: self.escribir_cantidad(id_producto, campo_cantidad)
        return ft.Container(
            padding=ft.Padding.only(left=12, right=4, top=6, bottom=6),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Row(
                spacing=2,
                controls=[
                    ft.Column(
                        spacing=0, expand=True,
                        controls=[
                            ft.Text(linea["nombre"], weight=ft.FontWeight.W_500, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(
                                f"{formatear_precio(linea['precio'])} c/u · "
                                f"{formatear_precio(linea['precio'] * linea['cantidad'])}",
                                size=12, color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                    ),
                    ft.IconButton(ft.Icons.REMOVE, icon_size=18, tooltip="Quitar 1",
                                  on_click=lambda _: self.cambiar_cantidad(id_producto, linea["cantidad"] - 1)),
                    campo_cantidad,
                    ft.IconButton(ft.Icons.ADD, icon_size=18, tooltip="Agregar 1",
                                  on_click=lambda _: self.cambiar_cantidad(id_producto, linea["cantidad"] + 1)),
                    ft.IconButton(ft.Icons.CLOSE, icon_size=18, tooltip="Quitar del carrito",
                                  on_click=lambda _: self.cambiar_cantidad(id_producto, 0)),
                ],
            ),
        )

    def actualizar_carrito(self):
        self.lista_carrito.controls = [self.linea_carrito(i, linea) for i, linea in self.carrito.items()]
        total = sum(linea["cantidad"] * linea["precio"] for linea in self.carrito.values())
        unidades = sum(linea["cantidad"] for linea in self.carrito.values())
        self.texto_total.value = formatear_precio(total)
        self.texto_unidades.value = f"{formatear_numero(unidades)} unidad{'es' if unidades != 1 else ''}"
        self.carrito_vacio.visible = not self.carrito
        self.boton_cobrar.disabled = not self.carrito
        if not self.carrito:
            self.texto_escaneo.visible = False
        self.page.update()

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

    async def vaciar_carrito(self, _e):
        if self.carrito and await preguntar(self.page, "Vaciar carrito", "¿Quitar todos los productos del carrito?",
                                            si="Vaciar", peligro=True):
            self.carrito.clear()
            self.actualizar_carrito()
        await self.campo_escanear.focus()

    @manejar_errores_bd
    async def cobrar_carrito(self, _e):
        if not self.carrito:
            return

        cambios = self.refrescar_carrito()
        total = sum(linea["cantidad"] * linea["precio"] for linea in self.carrito.values())
        if cambios:
            if not self.carrito:
                mostrar_mensaje(self.page, "Carrito Actualizado", "\n".join(cambios))
                return
            if not await preguntar(
                self.page, "Carrito Actualizado",
                "Algunos productos cambiaron desde que se agregaron:\n\n" + "\n".join(cambios)
                + f"\n\nNuevo total: {formatear_precio(total)}\n¿Cobrar la venta?",
                si="Cobrar",
            ):
                return

        pago = await pedir_pago(self.page, total)
        if pago is None:
            await self.campo_escanear.focus()
            return

        items = [(id_producto, linea["cantidad"]) for id_producto, linea in self.carrito.items()]
        exito, mensaje, id_recibo = db.registrar_venta_carrito(items, pago)
        if not exito:
            mostrar_mensaje(self.page, "Error en Venta", mensaje, error=True)
            return

        self.carrito.clear()
        self.actualizar_carrito()
        self.cargar_productos()
        # El recibo reemplaza al mensaje de "venta realizada": muestra total, pago y cambio
        mostrar_recibo(self.page, db.obtener_recibo(id_recibo))
