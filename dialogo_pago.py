"""
Diálogo de cobro: se escribe con cuánto paga el cliente y muestra el cambio.
"""
import asyncio

import flet as ft

from componentes import COLOR_EXITO, COLOR_PELIGRO
from formato import formatear_numero, formatear_precio, leer_precio


def _alcanza(pago, total):
    return round(pago, 2) >= round(total, 2)


async def pedir_pago(page, total):
    """Abre el diálogo de cobro y espera. Retorna el dinero recibido, o None si se cancela."""
    resultado = asyncio.get_running_loop().create_future()

    def terminar(pago):
        if not resultado.done():
            resultado.set_result(pago)
            page.pop_dialog()

    def leer_pago():
        """El monto escrito, o None si está vacío o no es un número."""
        try:
            return leer_precio(campo_pago.value.strip())
        except ValueError:
            return None

    texto_cambio = ft.Text("Cambio: —", size=20, weight=ft.FontWeight.BOLD)

    def actualizar_cambio(_=None):
        campo_pago.error_text = None
        pago = leer_pago()
        if pago is None:
            texto_cambio.value, texto_cambio.color = "Cambio: —", None
        elif not _alcanza(pago, total):
            texto_cambio.value, texto_cambio.color = f"Faltan {formatear_precio(total - pago)}", COLOR_PELIGRO
        else:
            texto_cambio.value, texto_cambio.color = f"Cambio: {formatear_precio(pago - total)}", COLOR_EXITO
        page.update()

    def confirmar(_=None):
        if not campo_pago.value.strip():
            campo_pago.error_text = "Escribe con cuánto paga el cliente."
        elif (pago := leer_pago()) is None:
            campo_pago.error_text = "Debe ser un número (ej: 20000 o 20.000)."
        elif not _alcanza(pago, total):
            campo_pago.error_text = f"Faltan {formatear_precio(total - pago)} para completar el pago."
        else:
            terminar(pago)
            return
        page.update()

    def pago_exacto(_):
        campo_pago.value = formatear_numero(total)
        confirmar()

    campo_pago = ft.TextField(
        label="Paga con ($)", prefix_icon=ft.Icons.PAYMENTS_OUTLINED, text_size=20,
        text_align=ft.TextAlign.CENTER, autofocus=True,
        on_change=actualizar_cambio, on_submit=confirmar,
    )

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Cobrar venta"),
        content=ft.Column(
            tight=True, spacing=14, width=360, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Total a cobrar", color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(formatear_precio(total), size=34, weight=ft.FontWeight.BOLD),
                campo_pago,
                texto_cambio,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(None)),
            ft.OutlinedButton("Pago exacto", on_click=pago_exacto),
            ft.FilledButton(
                "Cobrar", icon=ft.Icons.POINT_OF_SALE,
                style=ft.ButtonStyle(bgcolor=COLOR_EXITO, color=ft.Colors.WHITE), on_click=confirmar,
            ),
        ],
        # Escape o clic afuera cuentan como cancelar
        on_dismiss=lambda _: resultado.done() or resultado.set_result(None),
    ))
    return await resultado
