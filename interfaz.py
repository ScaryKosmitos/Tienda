"""
Ventana principal: barra lateral de navegación y las tres pantallas
(inventario y venta, historial de ventas y entradas de mercancía).
"""
import flet as ft

import base_datos as db
import respaldar
from componentes import COLOR_MARCA, avisar, mostrar_mensaje, preguntar
from vista_entradas import VistaEntradas
from vista_inventario import VistaInventario
from vista_ventas import VistaVentas

INVENTARIO, VENTAS, ENTRADAS = range(3)


class Aplicacion:
    def __init__(self, page):
        self.page = page
        page.title = "Tienda"
        page.theme = ft.Theme(color_scheme_seed=COLOR_MARCA)
        page.dark_theme = ft.Theme(color_scheme_seed=COLOR_MARCA)
        page.theme_mode = ft.ThemeMode.SYSTEM
        # Calendario y textos del sistema en español
        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("es", "CO")], current_locale=ft.Locale("es", "CO"),
        )
        page.padding = 0
        page.window.width = 1320
        page.window.height = 820
        page.window.min_width = 1100
        page.window.min_height = 680
        # Se pregunta antes de cerrar si hay un carrito sin cobrar
        page.window.prevent_close = True
        page.window.on_event = self.al_evento_ventana

        self.inventario = VistaInventario(page, abrir_entrada=self.abrir_entrada)
        self.ventas = VistaVentas(page)
        self.entradas = VistaEntradas(page)
        self.vistas = [self.inventario, self.ventas, self.entradas]

        self.navegacion = ft.NavigationRail(
            selected_index=INVENTARIO,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=96,
            group_alignment=-0.85,
            leading=ft.Container(
                padding=ft.Padding.only(top=16, bottom=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.STOREFRONT, color=ft.Colors.WHITE, size=26),
                            bgcolor=COLOR_MARCA, border_radius=14, padding=10,
                        ),
                        ft.Text("Tienda", weight=ft.FontWeight.BOLD),
                    ],
                ),
            ),
            trailing=ft.Container(
                padding=ft.Padding.only(top=24),
                content=ft.IconButton(ft.Icons.DARK_MODE_OUTLINED, tooltip="Cambiar entre modo claro y oscuro",
                                      on_click=self.cambiar_tema),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.POINT_OF_SALE_OUTLINED, selected_icon=ft.Icons.POINT_OF_SALE, label="Inventario"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG, label="Ventas"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.MOVE_TO_INBOX_OUTLINED, selected_icon=ft.Icons.MOVE_TO_INBOX, label="Entradas"),
            ],
            on_change=lambda e: self.ir_a(e.control.selected_index),
        )
        self.contenido = ft.Container(expand=True, padding=24)

        page.add(ft.Row(
            [self.navegacion, ft.VerticalDivider(width=1), self.contenido], expand=True, spacing=0,
        ))
        self.ir_a(INVENTARIO)

    def ir_a(self, indice, **opciones):
        """Muestra una pantalla y recarga sus datos, por si otra pantalla los cambió."""
        self.navegacion.selected_index = indice
        vista = self.vistas[indice]
        self.contenido.content = vista.control
        self.page.update()
        vista.mostrar(**opciones)

    def abrir_entrada(self, id_producto):
        self.ir_a(ENTRADAS, id_producto=id_producto)

    def cambiar_tema(self, _e):
        if self.page.theme_mode == ft.ThemeMode.SYSTEM:
            oscuro = self.page.platform_brightness == ft.Brightness.DARK
        else:
            oscuro = self.page.theme_mode == ft.ThemeMode.DARK
        self.page.theme_mode = ft.ThemeMode.LIGHT if oscuro else ft.ThemeMode.DARK
        self.page.update()

    async def al_evento_ventana(self, e):
        if e.type != ft.WindowEventType.CLOSE:
            return
        carrito = self.inventario.carrito
        if carrito and not await preguntar(
            self.page, "Carrito Pendiente",
            f"Hay {len(carrito)} producto(s) en el carrito sin cobrar.\n¿Cerrar de todas formas?",
            si="Cerrar", peligro=True,
        ):
            return
        await self.page.window.destroy()


def main(page: ft.Page):
    try:
        db.inicializar_db()
    except Exception as error:
        page.title = "Tienda"
        page.add(ft.Text("No se pudo iniciar la tienda."))
        mostrar_mensaje(page, "Error al iniciar", f"No se pudo inicializar la base de datos:\n{error}", error=True)
        return

    Aplicacion(page)

    # Un fallo del respaldo no debe impedir usar la tienda: solo se avisa
    try:
        respaldar.respaldo_automatico()
    except Exception as error:
        avisar(page, f"No se pudo crear el respaldo de hoy: {error}", error=True)


def iniciar_app():
    ft.run(main)
