"""
Pantalla del fiado: lista de clientes con lo que debe cada uno y, del cliente
elegido, sus movimientos (fiados, abonos y ventas anuladas) y los abonos.
"""
import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_PELIGRO, avisar, con_desplazamiento, crear_tabla, encabezado, icono_px, manejar_errores_bd,
    mostrar_mensaje, panel, preguntar, px, tarjeta_resumen, texto_vacio,
)
from dialogo_clave import pedir_clave
from dialogo_cliente import pedir_abono, pedir_texto, texto_deuda
from dialogo_recibo import mostrar_recibo
from formato import formatear_numero, formatear_precio


class VistaFiado:
    def __init__(self, page):
        self.page = page
        # Cliente que se está mostrando a la derecha (None = ninguno)
        self.id_cliente = None

        tarjeta_total, self.valor_total = tarjeta_resumen(
            ft.Icons.MENU_BOOK_OUTLINED, "Total fiado (lo que deben)", ft.Colors.ORANGE)
        tarjeta_deudores, self.valor_deudores = tarjeta_resumen(
            ft.Icons.PEOPLE_OUTLINE, "Clientes que deben", ft.Colors.INDIGO)

        self.control = ft.Column(
            spacing=20,
            expand=True,
            controls=[
                encabezado(
                    "Fiado", "Lo que deben los clientes y sus abonos",
                    ft.FilledButton(
                        "Nuevo cliente", icon=ft.Icons.PERSON_ADD_ALT, height=px(44),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                        on_click=self.nuevo_cliente,
                    ),
                ),
                ft.Row([tarjeta_total, tarjeta_deudores], spacing=12),
                ft.Row(
                    [self.crear_panel_clientes(), self.crear_panel_detalle()],
                    expand=True, spacing=16, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
        )

    # --- CONSTRUCCIÓN ---

    def crear_panel_clientes(self):
        self.campo_buscar = ft.TextField(
            hint_text="Buscar cliente…", prefix_icon=icono_px(ft.Icons.SEARCH), filled=True, dense=True,
            expand=True, on_change=lambda _: self.cargar_clientes(),
        )
        self.check_deben = ft.Checkbox(label="Solo los que deben", value=True,
                                       on_change=lambda _: self.cargar_clientes())
        self.tabla = crear_tabla([("Cliente", False), ("Debe", True), ("Último movimiento", False)],
                                 show_checkbox_column=False)
        self.sin_clientes = texto_vacio(ft.Icons.PEOPLE_OUTLINE, "No hay clientes que coincidan")
        return panel(
            ft.Column(
                spacing=16,
                controls=[
                    ft.Row([self.campo_buscar, self.check_deben], spacing=12),
                    ft.Stack([con_desplazamiento(self.tabla), self.sin_clientes], expand=True),
                ],
            ),
            expand=True,
        )

    def crear_panel_detalle(self):
        self.texto_nombre = ft.Text("", size=px(22), weight=ft.FontWeight.BOLD, max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS)
        self.texto_deuda = ft.Text("", size=px(30), weight=ft.FontWeight.BOLD)
        self.boton_abono = ft.FilledButton(
            "Registrar abono", icon=ft.Icons.SAVINGS_OUTLINED, height=px(48), expand=True,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14), bgcolor=COLOR_EXITO,
                                 color=ft.Colors.WHITE),
            on_click=self.registrar_abono,
        )
        self.boton_eliminar = ft.TextButton("Eliminar", icon=ft.Icons.DELETE_OUTLINE,
                                            style=ft.ButtonStyle(color=COLOR_PELIGRO), on_click=self.eliminar_cliente)
        self.lista_movimientos = ft.ListView(spacing=6, expand=True)
        self.sin_movimientos = texto_vacio(ft.Icons.HISTORY, "Todavía no tiene movimientos")

        self.detalle = ft.Column(
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                self.texto_nombre,
                self.texto_deuda,
                ft.Row([self.boton_abono]),
                ft.Row(
                    [ft.TextButton("Cambiar nombre", icon=ft.Icons.EDIT_OUTLINED, on_click=self.renombrar_cliente),
                     self.boton_eliminar],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=1),
                ft.Text("Movimientos", weight=ft.FontWeight.BOLD),
                ft.Stack([self.lista_movimientos, self.sin_movimientos], expand=True),
            ],
        )
        self.sin_elegir = texto_vacio(ft.Icons.TOUCH_APP_OUTLINED, "Elige un cliente de la lista\npara ver su cuenta")
        return panel(ft.Stack([self.detalle, self.sin_elegir], expand=True), width=px(430))

    # --- CARGA DE DATOS ---

    @manejar_errores_bd
    def mostrar(self):
        """Se llama cada vez que se entra a esta pantalla."""
        self.cargar_clientes()
        self.mostrar_cliente()

    @manejar_errores_bd
    def cargar_clientes(self):
        """Recarga la tabla de clientes y las tarjetas de resumen."""
        todos = db.obtener_clientes()
        deudores = [c for c in todos if c["debe"] > 0]
        self.valor_total.value = formatear_precio(sum(c["debe"] for c in deudores))
        self.valor_deudores.value = formatear_numero(len(deudores))

        clientes = db.obtener_clientes(self.campo_buscar.value)
        if self.check_deben.value:
            clientes = [c for c in clientes if c["debe"] > 0]
        self.tabla.rows = [self.fila_cliente(c) for c in clientes]
        self.sin_clientes.visible = not clientes
        self.sin_clientes.controls[1].value = (
            "Nadie debe nada" if self.check_deben.value and not self.campo_buscar.value.strip()
            else "No hay clientes que coincidan"
        )
        self.page.update()

    def fila_cliente(self, cliente):
        deuda, color = texto_deuda(cliente["debe"])
        return ft.DataRow(
            selected=cliente["id"] == self.id_cliente,
            on_select_change=lambda _, i=cliente["id"]: self.elegir_cliente(i),
            cells=[
                ft.DataCell(ft.Text(cliente["nombre"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(deuda, color=color, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(cliente["ultimo"][:16] if cliente["ultimo"] else "—",
                                    color=ft.Colors.ON_SURFACE_VARIANT, size=px(13))),
            ],
        )

    def elegir_cliente(self, id_cliente):
        self.id_cliente = id_cliente
        self.cargar_clientes()
        self.mostrar_cliente()

    @manejar_errores_bd
    def mostrar_cliente(self):
        """Muestra a la derecha la cuenta del cliente elegido."""
        cliente = db.obtener_cliente(self.id_cliente) if self.id_cliente is not None else None
        if not cliente:
            self.id_cliente = None
            self.detalle.visible, self.sin_elegir.visible = False, True
            self.page.update()
            return

        self.detalle.visible, self.sin_elegir.visible = True, False
        self.texto_nombre.value = cliente["nombre"]
        self.texto_deuda.value, self.texto_deuda.color = texto_deuda(cliente["debe"])
        self.boton_abono.disabled = cliente["debe"] <= 0

        movimientos = db.obtener_movimientos_fiado(self.id_cliente)
        self.lista_movimientos.controls = [self.linea_movimiento(m) for m in movimientos]
        self.sin_movimientos.visible = not movimientos
        # Solo se puede eliminar un cliente sin movimientos (ej: creado por error)
        self.boton_eliminar.visible = not movimientos
        self.page.update()

    def linea_movimiento(self, movimiento):
        anulado = bool(movimiento["anulado"])
        monto = movimiento["monto"]
        # Lo fiado sube la deuda (rojo); abonos y anulaciones la bajan (verde)
        color = ft.Colors.OUTLINE if anulado else (COLOR_PELIGRO if monto > 0 else COLOR_EXITO)
        signo = "+" if monto > 0 else "−"
        acciones = []
        if movimiento["recibo_id"]:
            acciones.append(ft.IconButton(
                ft.Icons.RECEIPT_OUTLINED, icon_size=px(18), tooltip="Ver recibo",
                on_click=lambda _, r=movimiento["recibo_id"]: self.ver_recibo(r),
            ))
        if movimiento["tipo"] == "Abono" and not anulado:
            acciones.append(ft.IconButton(
                ft.Icons.UNDO, icon_size=px(18), tooltip="Anular este abono (si se registró por error)",
                icon_color=COLOR_PELIGRO, on_click=lambda _, m=movimiento: self.page.run_task(self.anular_abono, m),
            ))
        return ft.Container(
            padding=ft.Padding.only(left=12, right=4, top=6, bottom=6),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Row(
                spacing=4,
                controls=[
                    ft.Column(
                        spacing=0, expand=True,
                        controls=[
                            ft.Text(movimiento["tipo"] + (" (anulado)" if anulado else ""),
                                    weight=ft.FontWeight.W_500, color=ft.Colors.OUTLINE if anulado else None),
                            ft.Text(movimiento["fecha"][:16], size=px(12), color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                    ),
                    ft.Text(f"{signo}{formatear_precio(abs(monto))}", color=color, weight=ft.FontWeight.BOLD),
                    *acciones,
                ],
            ),
        )

    # --- ACCIONES ---

    @manejar_errores_bd
    async def nuevo_cliente(self, _e):
        nuevo = {}

        def guardar(nombre):
            exito, mensaje, id_cliente = db.agregar_cliente(nombre)
            nuevo["id"] = id_cliente
            return None if exito else mensaje

        if await pedir_texto(self.page, "Nuevo cliente", "Nombre del cliente", guardar):
            avisar(self.page, "Cliente agregado")
            self.elegir_cliente(nuevo["id"])

    @manejar_errores_bd
    async def renombrar_cliente(self, _e):
        cliente = db.obtener_cliente(self.id_cliente)
        if not cliente:
            return self.mostrar()

        def guardar(nombre):
            exito, mensaje = db.renombrar_cliente(self.id_cliente, nombre)
            return None if exito else mensaje

        if await pedir_texto(self.page, "Cambiar nombre", "Nombre del cliente", guardar, cliente["nombre"]):
            avisar(self.page, "Nombre cambiado")
            self.mostrar()

    @manejar_errores_bd
    async def eliminar_cliente(self, _e):
        cliente = db.obtener_cliente(self.id_cliente)
        if not cliente or not await preguntar(
            self.page, "Eliminar cliente", f"¿Eliminar a '{cliente['nombre']}'?", si="Eliminar", peligro=True,
        ):
            return
        exito, mensaje = db.eliminar_cliente(self.id_cliente)
        if not exito:
            mostrar_mensaje(self.page, "No se pudo eliminar", mensaje, error=True)
            return
        avisar(self.page, mensaje)
        self.id_cliente = None
        self.mostrar()

    @manejar_errores_bd
    async def registrar_abono(self, _e):
        cliente = db.obtener_cliente(self.id_cliente)
        if not cliente:
            return self.mostrar()
        monto = await pedir_abono(self.page, cliente)
        if monto is None:
            return
        exito, mensaje = db.registrar_abono(self.id_cliente, monto)
        if exito:
            avisar(self.page, mensaje)
        else:
            mostrar_mensaje(self.page, "No se pudo registrar", mensaje, error=True)
        self.mostrar()

    @manejar_errores_bd
    async def anular_abono(self, movimiento):
        if not await preguntar(
            self.page, "Anular abono",
            f"¿Anular el abono de {formatear_precio(-movimiento['monto'])} del {movimiento['fecha'][:16]}? "
            "La deuda volverá a subir.",
            si="Anular", peligro=True,
        ) or not await pedir_clave(self.page, "Anular un abono necesita la clave."):
            return
        exito, mensaje = db.anular_abono(movimiento["id"])
        if exito:
            avisar(self.page, mensaje)
        else:
            mostrar_mensaje(self.page, "No se pudo anular", mensaje, error=True)
        self.mostrar()

    @manejar_errores_bd
    def ver_recibo(self, id_recibo):
        recibo = db.obtener_recibo(id_recibo)
        if recibo:
            mostrar_recibo(self.page, recibo)
