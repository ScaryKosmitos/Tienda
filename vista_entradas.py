"""
Pantalla de entradas de mercancía: suma unidades al stock de un producto y
muestra el historial de movimientos de stock.
"""
import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_PELIGRO, FILAS_POR_TANDA, PieMostrarMas, avisar, con_desplazamiento, crear_tabla, encabezado,
    etiqueta, icono_px, manejar_errores_bd, mostrar_mensaje, panel, px, texto_vacio,
)
from formato import clave_orden, formatear_cambio, formatear_numero, leer_entero


class VistaEntradas:
    def __init__(self, page):
        self.page = page
        self.id_producto = None
        # Productos del menú, (id, nombre): si no cambiaron, el menú no se vuelve a
        # armar (con miles de productos, armarlo tarda)
        self.productos_menu = None
        # La tabla muestra los movimientos por tandas: el id del último mostrado y cuántos hay
        self.ultimo_movimiento = None
        self.total_movimientos = 0

        self.menu_producto = ft.Dropdown(
            label="Producto", leading_icon=icono_px(ft.Icons.INVENTORY_2_OUTLINED), width=px(380), filled=True,
            editable=True, enable_filter=True, menu_height=px(360), on_select=self.al_elegir_producto,
        )
        self.texto_stock = ft.Text("Elige el producto que llegó", color=ft.Colors.ON_SURFACE_VARIANT)
        self.campo_cantidad = ft.TextField(
            label="Unidades recibidas", prefix_icon=icono_px(ft.Icons.ADD_BOX_OUTLINED), width=px(200), filled=True,
            disabled=True, on_submit=self.registrar,
        )
        self.boton_registrar = ft.FilledButton(
            "Registrar entrada", icon=ft.Icons.MOVE_TO_INBOX, height=px(48), disabled=True, on_click=self.registrar,
        )

        self.tabla = crear_tabla(
            [("Producto", False), ("Unidades", True), ("Fecha y hora", False), ("Motivo", False)],
        )
        self.sin_movimientos = texto_vacio(ft.Icons.MOVE_TO_INBOX_OUTLINED, "Todavía no hay movimientos de stock")
        self.pie_tabla = PieMostrarMas(self.mostrar_mas_movimientos)

        self.control = ft.Column(
            spacing=20,
            expand=True,
            controls=[
                encabezado("Entradas", "Registra la mercancía que llega y revisa los movimientos de stock"),
                panel(ft.Column(
                    spacing=12,
                    controls=[
                        ft.Text("Nueva entrada", size=px(18), weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [self.menu_producto, self.campo_cantidad, self.boton_registrar],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.START, wrap=True,
                        ),
                        self.texto_stock,
                    ],
                )),
                panel(
                    ft.Column(
                        expand=True,
                        controls=[
                            ft.Text("Movimientos de stock (entradas, stock inicial, ajustes manuales y anulaciones)",
                                    size=px(18), weight=ft.FontWeight.BOLD),
                            ft.Stack([con_desplazamiento(self.tabla), self.sin_movimientos], expand=True),
                            self.pie_tabla.control,
                        ],
                    ),
                    expand=True,
                ),
            ],
        )

    @manejar_errores_bd
    def mostrar(self, id_producto=None):
        """Se llama cada vez que se entra a esta pantalla; 'id_producto' deja ese producto ya elegido."""
        productos = sorted(
            ((p["id"], p["nombre"]) for p in db.buscar_productos()), key=lambda p: clave_orden(p[1])
        )
        if productos != self.productos_menu:
            self.productos_menu = productos
            self.menu_producto.options = [ft.DropdownOption(key=str(i), text=nombre) for i, nombre in productos]
        if id_producto is not None:
            self.id_producto = id_producto
        if self.id_producto is not None and not any(i == self.id_producto for i, _ in productos):
            self.id_producto = None
        self.menu_producto.value = str(self.id_producto) if self.id_producto is not None else None
        self.mostrar_producto()
        self.cargar_movimientos()
        self.page.update()

    @manejar_errores_bd
    def al_elegir_producto(self, e):
        # Solo cambia el producto elegido: no hace falta recargar el menú ni la tabla
        self.id_producto = int(e.control.value) if e.control.value else None
        self.mostrar_producto()
        self.page.update()
        if self.id_producto is not None:
            self.page.run_task(self.campo_cantidad.focus)

    def mostrar_producto(self):
        producto = db.obtener_producto(self.id_producto) if self.id_producto is not None else None
        hay_producto = producto is not None
        self.campo_cantidad.disabled = not hay_producto
        self.boton_registrar.disabled = not hay_producto
        if hay_producto:
            self.texto_stock.value = f"Stock actual de {producto['nombre']}: {formatear_numero(producto['stock'])}"
        else:
            self.texto_stock.value = "Elige el producto que llegó"

    def cargar_movimientos(self):
        movimientos = db.obtener_entradas(limite=FILAS_POR_TANDA)
        self.total_movimientos = (
            db.contar_entradas() if len(movimientos) == FILAS_POR_TANDA else len(movimientos)
        )
        self.tabla.rows = [self.fila_movimiento(m) for m in movimientos]
        self.ultimo_movimiento = movimientos[-1]["id"] if movimientos else None
        self.sin_movimientos.visible = not movimientos
        self.actualizar_pie_tabla()

    @manejar_errores_bd
    def mostrar_mas_movimientos(self):
        """Agrega los siguientes movimientos sin rehacer las filas que ya están."""
        movimientos = db.obtener_entradas(limite=FILAS_POR_TANDA, antes_de_id=self.ultimo_movimiento)
        self.tabla.rows.extend(self.fila_movimiento(m) for m in movimientos)
        if movimientos:
            self.ultimo_movimiento = movimientos[-1]["id"]
        else:
            self.total_movimientos = len(self.tabla.rows)
        self.actualizar_pie_tabla()
        self.page.update()

    def actualizar_pie_tabla(self):
        self.pie_tabla.actualizar(len(self.tabla.rows), self.total_movimientos, "movimientos")

    @staticmethod
    def fila_movimiento(movimiento):
        _id, nombre, cantidad, fecha, motivo = movimiento
        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(nombre, weight=ft.FontWeight.W_500)),
            ft.DataCell(etiqueta(formatear_cambio(cantidad), COLOR_EXITO if cantidad > 0 else COLOR_PELIGRO)),
            ft.DataCell(ft.Text(fecha, color=ft.Colors.ON_SURFACE_VARIANT, size=px(13))),
            ft.DataCell(ft.Text(motivo)),
        ])

    @manejar_errores_bd
    def registrar(self, _e):
        self.campo_cantidad.error_text = None
        try:
            cantidad = leer_entero(self.campo_cantidad.value.strip())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            self.campo_cantidad.error_text = "Debe ser un entero positivo"
            self.page.update()
            return

        exito, mensaje = db.registrar_entrada(self.id_producto, cantidad)
        if not exito:
            mostrar_mensaje(self.page, "Error", mensaje, error=True)
            return
        self.campo_cantidad.value = ""
        self.mostrar()
        avisar(self.page, mensaje)
