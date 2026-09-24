"""
Ventana principal: barra lateral de navegación y las cinco pantallas
(inventario y venta, historial de ventas, fiado, caja y entradas de mercancía).
"""
import asyncio
import os

import flet as ft

import base_datos as db
import configuracion
import respaldar
from componentes import (
    COLOR_MARCA, TAMANOS, avisar, crear_tema, escala, hay_dialogo_abierto, icono_px, mostrar_mensaje, poner_escala,
    preguntar, px,
)
from dialogo_clave import abrir_ajustes_clave
from dialogo_respaldo import abrir_ajustes_respaldo
from vista_caja import VistaCaja
from vista_entradas import VistaEntradas
from vista_fiado import VistaFiado
from vista_inventario import VistaInventario
from vista_ventas import VistaVentas

INVENTARIO, VENTAS, FIADO, CAJA, ENTRADAS = range(5)

# Cada cuánto se revisa si falta el respaldo del día (por si la tienda queda abierta varios días)
SEGUNDOS_ENTRE_RESPALDOS = 60 * 60


class Aplicacion:
    def __init__(self, page):
        self.page = page
        page.title = "Tienda"
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
        # Abre ocupando toda la pantalla: hay más espacio, sobre todo con letra grande
        page.window.maximized = True
        # Ícono de la ventana y de la barra de tareas (solo tiene efecto en Windows)
        page.window.icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.ico")
        # Se pregunta antes de cerrar si hay un carrito sin cobrar
        page.window.prevent_close = True
        page.window.on_event = self.al_evento_ventana
        # Ctrl + y Ctrl - cambian el tamaño de letra
        page.on_keyboard_event = self.al_presionar_tecla

        # El tamaño de letra elegido la última vez
        guardada = configuracion.leer().get("escala", 1.0)
        poner_escala(guardada if any(guardada == valor for _, valor in TAMANOS) else 1.0)

        # Selector de carpetas del respaldo en la nube. Se crea una sola vez (no en
        # construir()), para no agregar uno nuevo cada vez que cambia el tamaño de letra
        self.selector_carpeta = ft.FilePicker()
        page.services.append(self.selector_carpeta)

        self.construir()
        self.ir_a(INVENTARIO)

    def construir(self):
        """Arma el tema, las pantallas y la barra lateral con el tamaño de letra actual."""
        page = self.page
        page.theme = crear_tema()
        page.dark_theme = crear_tema()

        self.inventario = VistaInventario(page, abrir_entrada=self.abrir_entrada)
        self.ventas = VistaVentas(page)
        self.fiado = VistaFiado(page)
        self.caja = VistaCaja(page)
        self.entradas = VistaEntradas(page)
        # En el mismo orden que INVENTARIO, VENTAS, FIADO, CAJA, ENTRADAS
        self.vistas = [self.inventario, self.ventas, self.fiado, self.caja, self.entradas]

        self.navegacion = ft.NavigationRail(
            selected_index=INVENTARIO,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=px(96),
            group_alignment=-0.85,
            leading=ft.Container(
                padding=ft.Padding.only(top=16, bottom=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.STOREFRONT, color=ft.Colors.WHITE, size=px(26)),
                            bgcolor=COLOR_MARCA, border_radius=14, padding=10,
                        ),
                        ft.Text("Tienda", weight=ft.FontWeight.BOLD),
                    ],
                ),
            ),
            trailing=ft.Container(
                padding=ft.Padding.only(top=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.crear_menu_tamano(),
                        ft.IconButton(ft.Icons.CLOUD_UPLOAD_OUTLINED, tooltip="Respaldo en la nube (Google Drive)",
                                      on_click=lambda _: self.page.run_task(
                                          abrir_ajustes_respaldo, self.page, self.selector_carpeta)),
                        ft.IconButton(ft.Icons.LOCK_OUTLINE, tooltip="Clave para acciones delicadas",
                                      on_click=lambda _: self.page.run_task(abrir_ajustes_clave, self.page)),
                        ft.IconButton(ft.Icons.DARK_MODE_OUTLINED, tooltip="Cambiar entre modo claro y oscuro",
                                      on_click=self.cambiar_tema),
                    ],
                ),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=icono_px(ft.Icons.POINT_OF_SALE_OUTLINED, 24), selected_icon=icono_px(ft.Icons.POINT_OF_SALE, 24),
                    label="Inventario"),
                ft.NavigationRailDestination(
                    icon=icono_px(ft.Icons.RECEIPT_LONG_OUTLINED, 24), selected_icon=icono_px(ft.Icons.RECEIPT_LONG, 24),
                    label="Ventas"),
                ft.NavigationRailDestination(
                    icon=icono_px(ft.Icons.MENU_BOOK_OUTLINED, 24), selected_icon=icono_px(ft.Icons.MENU_BOOK, 24),
                    label="Fiado"),
                ft.NavigationRailDestination(
                    icon=icono_px(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, 24),
                    selected_icon=icono_px(ft.Icons.ACCOUNT_BALANCE_WALLET, 24),
                    label="Caja"),
                ft.NavigationRailDestination(
                    icon=icono_px(ft.Icons.MOVE_TO_INBOX_OUTLINED, 24), selected_icon=icono_px(ft.Icons.MOVE_TO_INBOX, 24),
                    label="Entradas"),
            ],
            on_change=lambda e: self.ir_a(e.control.selected_index),
        )
        self.contenido = ft.Container(expand=True, padding=24)

        page.controls.clear()
        page.add(ft.Row(
            [self.navegacion, ft.VerticalDivider(width=1), self.contenido], expand=True, spacing=0,
        ))

    def crear_menu_tamano(self):
        """Botón "Aa" con las opciones de tamaño de letra; la elegida lleva una marca."""
        return ft.PopupMenuButton(
            icon=ft.Icons.FORMAT_SIZE,
            tooltip="Tamaño de letra (Ctrl + y Ctrl −)",
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(f"{nombre} ({round(valor * 100)} %)"),
                    checked=valor == escala(),
                    on_click=lambda _, v=valor: self.cambiar_tamano(v),
                )
                for nombre, valor in TAMANOS
            ],
        )

    def cambiar_tamano(self, valor):
        """Vuelve a armar todas las pantallas con el nuevo tamaño, conservando el carrito."""
        if valor == escala():
            return
        # Rearmar las pantallas con una ventana abierta (ej: el cobro) la dejaría
        # trabajando sobre las pantallas viejas: el carrito quedaría desfasado
        if hay_dialogo_abierto(self.page):
            avisar(self.page, "Cierra la ventana abierta para cambiar el tamaño de letra.")
            return
        poner_escala(valor)
        try:
            configuracion.guardar(escala=valor)
        except OSError:
            # Si no se puede guardar, el tamaño igual cambia; solo no se recordará
            pass

        indice = self.navegacion.selected_index
        carrito = self.inventario.carrito
        # Cada vez que se arma la pantalla de ventas agrega su selector de archivos
        self.page.services.remove(self.ventas.selector_archivo)
        self.construir()
        self.inventario.carrito = carrito
        self.ir_a(indice)
        nombre = next(n for n, v in TAMANOS if v == valor)
        avisar(self.page, f"Tamaño de letra: {nombre}")

    def al_presionar_tecla(self, e):
        if not e.ctrl:
            return
        valores = [valor for _, valor in TAMANOS]
        posicion = valores.index(escala())
        if e.key in ("=", "+", "Numpad Add"):
            self.cambiar_tamano(valores[min(posicion + 1, len(valores) - 1)])
        elif e.key in ("-", "Numpad Subtract"):
            self.cambiar_tamano(valores[max(posicion - 1, 0)])
        elif e.key in ("0", "Numpad 0"):
            self.cambiar_tamano(1.0)

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
    page.run_task(respaldar_cada_dia, page)


async def respaldar_cada_dia(page):
    """
    Hace el respaldo del día al abrir la tienda y lo copia a la nube. Si queda
    abierta, vuelve a revisar cada hora: así hace el del día siguiente y
    reintenta la copia si Google Drive no estaba disponible. Un fallo del
    respaldo no debe impedir usar la tienda: solo se avisa.
    """
    # Si la nube sigue fallando igual, se avisa una sola vez y no cada hora
    error_nube_avisado = None
    while True:
        try:
            await asyncio.to_thread(respaldar.respaldo_automatico)
        except Exception as error:
            avisar(page, f"No se pudo crear el respaldo de hoy: {error}", error=True)
        try:
            await asyncio.to_thread(respaldar.copiar_a_nube)
            error_nube_avisado = None
        except Exception as error:
            if str(error) != error_nube_avisado:
                avisar(page, f"No se pudo copiar el respaldo a la nube: {error}", error=True)
                error_nube_avisado = str(error)
        await asyncio.sleep(SEGUNDOS_ENTRE_RESPALDOS)


def iniciar_app():
    ft.run(main)
