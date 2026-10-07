"""
Diálogo para vender un producto por peso (el pescado): se escribe lo que
marca la gramera o la plata que pide el cliente ("deme 10 mil de trucha"), y
cada campo calcula el otro.
"""
import asyncio

import flet as ft

import base_datos as db
from componentes import CAMPO_HUNDIDO, COLOR_EXITO, COLOR_PELIGRO, icono_px, px
from formato import formatear_cantidad, formatear_kilos, formatear_numero, formatear_precio, leer_gramos, leer_precio

# Botones de peso (en gramos) y de plata: cada toque pone ese valor
PESOS = [("½ libra", 250), ("1 libra", 500), ("1 ½ libra", 750), ("1 kilo", 1000)]
PLATAS = [5_000, 10_000, 20_000, 30_000]


async def pedir_peso(page, producto, gramos=None):
    """
    Pregunta cuánto se lleva de un producto por peso. 'gramos' es lo que ya
    hay en el carrito (para corregirlo). Retorna los gramos, o None si se cancela.
    """
    resultado = asyncio.get_running_loop().create_future()
    precio = producto["precio"]

    def terminar(valor):
        if not resultado.done():
            resultado.set_result(valor)
            page.pop_dialog()

    def leer(campo, lector):
        """Lo escrito en el campo, o None si está vacío o no es un número."""
        try:
            return lector(campo.value.strip())
        except ValueError:
            return None

    def mostrar_resumen(gramos_elegidos):
        campo_peso.error_text = None
        if not gramos_elegidos:
            texto_resumen.value, texto_resumen.color = "—", None
        elif gramos_elegidos > producto["stock"]:
            texto_resumen.value = f"Solo quedan {formatear_cantidad(producto['stock'], True)}"
            texto_resumen.color = COLOR_PELIGRO
        else:
            texto_resumen.value = (f"{formatear_cantidad(gramos_elegidos, True)} = "
                                   f"{formatear_precio(db.total_linea(precio, gramos_elegidos, True))}")
            texto_resumen.color = COLOR_EXITO
        page.update()

    def al_escribir_peso(_=None):
        """Con el peso escrito se calcula la plata."""
        gramos_elegidos = leer(campo_peso, leer_gramos)
        campo_plata.value = (formatear_numero(db.total_linea(precio, gramos_elegidos, True))
                             if gramos_elegidos else "")
        mostrar_resumen(gramos_elegidos)

    def al_escribir_plata(_=None):
        """Con la plata escrita se calcula cuánto pesar."""
        plata = leer(campo_plata, leer_precio)
        gramos_elegidos = round(plata * 1000 / precio) if plata else None
        campo_peso.value = formatear_numero(gramos_elegidos) if gramos_elegidos else ""
        mostrar_resumen(gramos_elegidos)

    def poner_peso(gramos_elegidos):
        campo_peso.value = formatear_numero(gramos_elegidos)
        al_escribir_peso()

    def poner_plata(plata):
        campo_plata.value = formatear_numero(plata)
        al_escribir_plata()

    def confirmar(_=None):
        gramos_elegidos = leer(campo_peso, leer_gramos)
        if not campo_peso.value.strip():
            campo_peso.error_text = "Escribe el peso o la plata."
        elif not gramos_elegidos or gramos_elegidos < 0:
            campo_peso.error_text = "Escribe los gramos (ej: 750) o los kilos con coma (ej: 1,5)."
        elif gramos_elegidos > producto["stock"]:
            campo_peso.error_text = f"Solo quedan {formatear_cantidad(producto['stock'], True)}."
        else:
            terminar(gramos_elegidos)
            return
        page.update()

    campo_peso = ft.TextField(
        **CAMPO_HUNDIDO, label="Peso (gramos)", hint_text="Ej: 750", suffix=ft.Text("g"), expand=True,
        prefix_icon=icono_px(ft.Icons.SCALE_OUTLINED), text_size=px(20), autofocus=True,
        on_change=al_escribir_peso, on_submit=confirmar,
    )
    campo_plata = ft.TextField(
        **CAMPO_HUNDIDO, label="o plata ($)", hint_text="Ej: 10000", expand=True,
        prefix_icon=icono_px(ft.Icons.PAYMENTS_OUTLINED), text_size=px(20),
        on_change=al_escribir_plata, on_submit=confirmar,
    )
    texto_resumen = ft.Text("—", size=px(22), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    estilo = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=12), padding=ft.Padding.symmetric(horizontal=4),
        text_style=ft.TextStyle(size=px(15), weight=ft.FontWeight.BOLD),
    )
    botones_peso = ft.Row(spacing=8, controls=[
        ft.OutlinedButton(nombre, height=px(48), expand=True, style=estilo, on_click=lambda _, g=g: poner_peso(g))
        for nombre, g in PESOS
    ])
    botones_plata = ft.Row(spacing=8, controls=[
        ft.OutlinedButton(formatear_precio(p), height=px(48), expand=True, style=estilo,
                          on_click=lambda _, p=p: poner_plata(p))
        for p in PLATAS
    ])

    if gramos:
        poner_peso(gramos)

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(producto["nombre"]),
        content=ft.Column(
            tight=True, spacing=14, width=px(500), horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(
                    f"{formatear_precio(precio)} el kilo  ·  quedan {formatear_kilos(producto['stock'])}",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text("Escribe lo que marca la gramera, o la plata que pide el cliente:",
                        color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([campo_peso, campo_plata], spacing=10),
                botones_peso,
                botones_plata,
                texto_resumen,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(None)),
            ft.FilledButton(
                "Listo" if gramos else "Agregar al carrito", icon=ft.Icons.ADD_SHOPPING_CART,
                style=ft.ButtonStyle(bgcolor=COLOR_EXITO, color=ft.Colors.WHITE), on_click=confirmar,
            ),
        ],
        # Escape o clic afuera cuentan como cancelar
        on_dismiss=lambda _: resultado.done() or resultado.set_result(None),
    ))
    return await resultado
