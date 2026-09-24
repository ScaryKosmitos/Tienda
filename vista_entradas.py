"""
Pantalla de entradas de mercancía: suma unidades al stock de un producto y
muestra el historial de movimientos de stock.
"""
import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_PELIGRO, avisar, con_desplazamiento, crear_tabla, encabezado, etiqueta, icono_px,
    manejar_errores_bd, mostrar_mensaje, panel, px, texto_vacio,
)
from formato import clave_orden, formatear_cambio, formatear_numero, leer_entero

# La tabla muestra como máximo estos movimientos (los más recientes), para que siga ágil
MAX_FILAS = 300


class VistaEntradas:
    def __init__(self, page):
        self.page = page
        self.id_producto = None

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
        self.aviso_limite = ft.Text("", size=px(13), color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

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
                            self.aviso_limite,
                        ],
                    ),
                    expand=True,
                ),
            ],
        )

    @manejar_errores_bd
    def mostrar(self, id_producto=None):
        """Se llama cada vez que se entra a esta pantalla; 'id_producto' deja ese producto ya elegido."""
        productos = sorted(db.buscar_productos(), key=lambda p: clave_orden(p["nombre"]))
        self.menu_producto.options = [ft.DropdownOption(key=str(p["id"]), text=p["nombre"]) for p in productos]
        if id_producto is not None:
            self.id_producto = id_producto
        if self.id_producto is not None and not any(p["id"] == self.id_producto for p in productos):
            self.id_producto = None
        self.menu_producto.value = str(self.id_producto) if self.id_producto is not None else None
        self.mostrar_producto()
        self.cargar_movimientos()
        self.page.update()

    def al_elegir_producto(self, e):
        self.id_producto = int(e.control.value) if e.control.value else None
        self.mostrar(self.id_producto)
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
        movimientos = db.obtener_entradas(limite=MAX_FILAS)
        total = db.contar_entradas() if len(movimientos) == MAX_FILAS else len(movimientos)
        self.aviso_limite.visible = total > len(movimientos)
        self.aviso_limite.value = (
            f"Se muestran los {formatear_numero(len(movimientos))} movimientos más recientes de {formatear_numero(total)}."
        )
        self.tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(nombre, weight=ft.FontWeight.W_500)),
                ft.DataCell(etiqueta(formatear_cambio(cantidad), COLOR_EXITO if cantidad > 0 else COLOR_PELIGRO)),
                ft.DataCell(ft.Text(fecha, color=ft.Colors.ON_SURFACE_VARIANT, size=px(13))),
                ft.DataCell(ft.Text(motivo)),
            ])
            for _id, nombre, cantidad, fecha, motivo in movimientos
        ]
        self.sin_movimientos.visible = not movimientos

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
