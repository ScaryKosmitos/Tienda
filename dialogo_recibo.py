"""
Diálogo que muestra el recibo de una venta y permite abrirlo en el navegador
para imprimirlo o guardarlo como PDF.
"""
import webbrowser
from pathlib import Path

import flet as ft

import recibo as rec
from componentes import mostrar_mensaje


def mostrar_recibo(page, recibo):
    """'recibo' es lo que retorna db.obtener_recibo()."""

    def abrir_en_navegador(_):
        try:
            ruta = rec.guardar_html(recibo)
        except OSError as error:
            mostrar_mensaje(page, "No se pudo guardar", f"No se pudo crear el recibo:\n{error}", error=True)
            return
        if not webbrowser.open(Path(ruta).as_uri()):
            mostrar_mensaje(
                page, "Recibo Guardado", f"No se pudo abrir el navegador. El recibo quedó guardado en:\n{ruta}"
            )

    # Papel blanco y letra de ancho fijo, para que se parezca al recibo impreso
    # y las columnas queden alineadas en modo claro y oscuro
    papel = ft.Container(
        bgcolor=ft.Colors.WHITE,
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        content=ft.Text(
            rec.texto_recibo(recibo), font_family="monospace", size=14, color=ft.Colors.BLACK, selectable=True,
        ),
    )

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(f"Recibo N° {rec.numero_recibo(recibo['id'])}"),
        content=ft.Column([papel], tight=True, scroll=ft.ScrollMode.AUTO),
        actions=[
            ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog()),
            ft.FilledButton("Imprimir o guardar PDF", icon=ft.Icons.PRINT_OUTLINED, on_click=abrir_en_navegador),
        ],
    ))
