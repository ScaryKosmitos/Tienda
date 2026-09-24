"""
Diálogo de cobro: se escribe (o se marca con los botones de billetes) con
cuánto paga el cliente y muestra el cambio. También permite fiar la venta.
"""
import asyncio

import flet as ft

import base_datos as db
from componentes import COLOR_EXITO, COLOR_PELIGRO, ERRORES_BD, icono_px, mostrar_error_bd, preguntar, px
from dialogo_cliente import elegir_cliente
from formato import formatear_numero, formatear_precio, leer_precio

# Botones de billetes (y la moneda de $1.000): cada toque suma al monto recibido
BILLETES = [1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]


async def pedir_pago(page, total):
    """
    Abre el diálogo de cobro y espera. Retorna (dinero_recibido, None) si se
    cobra, (None, id_cliente) si se fía, o None si se cancela.
    """
    resultado = asyncio.get_running_loop().create_future()

    def terminar(cobro):
        if not resultado.done():
            resultado.set_result(cobro)
            page.pop_dialog()

    def leer_pago():
        """El monto escrito, o None si está vacío o no es un número."""
        try:
            return leer_precio(campo_pago.value.strip())
        except ValueError:
            return None

    texto_cambio = ft.Text("Cambio: —", size=px(20), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    def actualizar_cambio(_=None):
        campo_pago.error_text = None
        pago = leer_pago()
        if pago is None:
            texto_cambio.value, texto_cambio.color = "Cambio: —", None
        elif error := db.validar_pago(pago, total):
            texto_cambio.value, texto_cambio.color = error, COLOR_PELIGRO
        else:
            texto_cambio.value, texto_cambio.color = f"Cambio: {formatear_precio(pago - total)}", COLOR_EXITO
        page.update()

    def confirmar(_=None):
        if not campo_pago.value.strip():
            campo_pago.error_text = "Escribe con cuánto paga el cliente."
        elif (pago := leer_pago()) is None:
            campo_pago.error_text = "Debe ser un número (ej: 20000 o 20.000)."
        elif error := db.validar_pago(pago, total):
            campo_pago.error_text = error
        else:
            terminar((pago, None))
            return
        page.update()

    def pago_exacto(_):
        campo_pago.value = formatear_numero(total)
        confirmar()

    def sumar_billete(billete):
        """Suma el billete a lo que ya hay: 20.000 + 5.000 = 25.000. No cobra: eso se confirma con 'Cobrar'."""
        campo_pago.value = formatear_numero((leer_pago() or 0) + billete)
        actualizar_cambio()

    async def fiar(_):
        id_cliente = await elegir_cliente(page, f"¿A quién se le fían {formatear_precio(total)}?")
        if id_cliente is None:
            return
        try:
            cliente = db.obtener_cliente(id_cliente)
        except ERRORES_BD as error:
            mostrar_error_bd(page, error)
            return
        if cliente and await preguntar(
            page, "Fiar venta",
            f"¿Fiar {formatear_precio(total)} a {cliente['nombre']}?\n"
            f"Quedará debiendo {formatear_precio(cliente['debe'] + total)}.",
            si="Fiar",
        ):
            terminar((None, id_cliente))

    def borrar(_):
        campo_pago.value = ""
        actualizar_cambio()

    estilo_billete = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=12),
        text_style=ft.TextStyle(size=px(16), weight=ft.FontWeight.BOLD),
        padding=ft.Padding.symmetric(horizontal=4),
    )
    botones = [
        ft.OutlinedButton(formatear_precio(b), height=px(52), expand=True, style=estilo_billete,
                          on_click=lambda _, b=b: sumar_billete(b))
        for b in BILLETES
    ]
    botones.append(ft.TextButton("Borrar", icon=ft.Icons.BACKSPACE_OUTLINED, height=px(52), expand=True,
                                 style=ft.ButtonStyle(color=COLOR_PELIGRO), on_click=borrar))
    # Cuatro botones por fila
    filas_billetes = [ft.Row(botones[i:i + 4], spacing=8) for i in range(0, len(botones), 4)]

    campo_pago = ft.TextField(
        label="Paga con ($)", prefix_icon=icono_px(ft.Icons.PAYMENTS_OUTLINED), text_size=px(20),
        text_align=ft.TextAlign.CENTER, autofocus=True,
        on_change=actualizar_cambio, on_submit=confirmar,
    )

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Cobrar venta"),
        content=ft.Column(
            tight=True, spacing=14, width=px(460), horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("Total a cobrar", color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ft.Text(formatear_precio(total), size=px(34), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                campo_pago,
                ft.Text("Toca los billetes que te dieron:", color=ft.Colors.ON_SURFACE_VARIANT),
                *filas_billetes,
                texto_cambio,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(None)),
            ft.OutlinedButton("Fiar", icon=ft.Icons.MENU_BOOK_OUTLINED, on_click=fiar),
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
