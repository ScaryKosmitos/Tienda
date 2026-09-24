"""
Diálogos del fiado: elegir (o crear) el cliente al fiar una venta, escribir
el nombre de un cliente y registrar un abono.
"""
import asyncio

import flet as ft

import base_datos as db
from componentes import COLOR_EXITO, COLOR_PELIGRO, ERRORES_BD, icono_px, mostrar_error_bd, px
from formato import formatear_numero, formatear_precio, leer_precio, sin_tildes


def texto_deuda(debe):
    """'Debe $15.000', 'Al día' o 'A favor $2.000', con su color."""
    if debe > 0:
        return f"Debe {formatear_precio(debe)}", COLOR_PELIGRO
    if debe < 0:
        return f"A favor {formatear_precio(-debe)}", COLOR_EXITO
    return "Al día", COLOR_EXITO


async def elegir_cliente(page, titulo):
    """
    Lista de clientes con buscador. Si el nombre escrito no existe, ofrece
    crearlo. Retorna el id del cliente elegido, o None si se cancela.
    """
    resultado = asyncio.get_running_loop().create_future()

    def terminar(id_cliente):
        if not resultado.done():
            resultado.set_result(id_cliente)
            page.pop_dialog()

    lista = ft.ListView(spacing=4, height=px(300))
    boton_nuevo = ft.FilledButton(icon=ft.Icons.PERSON_ADD_ALT, visible=False)
    sin_clientes = ft.Text("Todavía no hay clientes: escribe el nombre para crear uno.",
                           color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

    def filtrar(_=None):
        texto = campo.value.strip()
        try:
            clientes = db.obtener_clientes(texto)
        except ERRORES_BD as error:
            mostrar_error_bd(page, error)
            return
        lista.controls = []
        for cliente in clientes:
            deuda, color = texto_deuda(cliente["debe"])
            lista.controls.append(ft.ListTile(
                leading=icono_px(ft.Icons.PERSON_OUTLINE, 24),
                title=ft.Text(cliente["nombre"], weight=ft.FontWeight.W_500),
                trailing=ft.Text(deuda, color=color, size=px(14), weight=ft.FontWeight.BOLD),
                on_click=lambda _, i=cliente["id"]: terminar(i),
            ))
        # Si lo escrito no es exactamente un cliente que ya existe, se ofrece crearlo
        existe = any(sin_tildes(c["nombre"]) == sin_tildes(" ".join(texto.split())) for c in clientes)
        boton_nuevo.visible = bool(texto) and not existe
        boton_nuevo.content = f"Nuevo cliente: {' '.join(texto.split())}"
        sin_clientes.visible = not clientes and not texto
        page.update()

    def crear(_=None):
        try:
            exito, mensaje, id_cliente = db.agregar_cliente(campo.value)
        except ERRORES_BD as error:
            mostrar_error_bd(page, error)
            return
        if exito:
            terminar(id_cliente)
        else:
            campo.error_text = mensaje
            page.update()

    def al_escribir(_):
        campo.error_text = None
        filtrar()

    def al_enter(_):
        """Enter elige al único cliente de la lista, o crea el cliente nuevo."""
        if boton_nuevo.visible:
            crear()
        elif len(lista.controls) == 1:
            lista.controls[0].on_click(None)

    campo = ft.TextField(
        label="Buscar o escribir el nombre del cliente", prefix_icon=icono_px(ft.Icons.SEARCH),
        autofocus=True, on_change=al_escribir, on_submit=al_enter,
    )
    boton_nuevo.on_click = crear

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(titulo),
        content=ft.Column(
            [campo, boton_nuevo, sin_clientes, lista],
            tight=True, spacing=12, width=px(460), horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        actions=[ft.TextButton("Cancelar", on_click=lambda _: terminar(None))],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(None),
    ))
    filtrar()
    return await resultado


async def pedir_texto(page, titulo, etiqueta, guardar, valor=""):
    """
    Pide un texto (ej: el nombre de un cliente). 'guardar(texto)' lo guarda y
    retorna un mensaje de error, o None si salió bien. Retorna True si se guardó.
    """
    resultado = asyncio.get_running_loop().create_future()

    def terminar(valor_final):
        if not resultado.done():
            resultado.set_result(valor_final)
            page.pop_dialog()

    def aceptar(_=None):
        try:
            error = guardar(campo.value)
        except ERRORES_BD as error_bd:
            mostrar_error_bd(page, error_bd)
            return
        if error:
            campo.error_text = error
            page.update()
        else:
            terminar(True)

    campo = ft.TextField(label=etiqueta, value=valor, autofocus=True, on_submit=aceptar,
                         prefix_icon=icono_px(ft.Icons.PERSON_OUTLINE))
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(titulo),
        content=ft.Column([campo], tight=True, width=px(420)),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(False)),
            ft.FilledButton("Guardar", icon=ft.Icons.SAVE_OUTLINED, on_click=aceptar),
        ],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(False),
    ))
    return await resultado


async def pedir_abono(page, cliente):
    """Pide cuánto abona el cliente. Retorna el monto, o None si se cancela."""
    resultado = asyncio.get_running_loop().create_future()
    debe = cliente["debe"]

    def terminar(monto):
        if not resultado.done():
            resultado.set_result(monto)
            page.pop_dialog()

    texto_queda = ft.Text("", size=px(18), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    def leer_monto():
        try:
            return leer_precio(campo.value.strip())
        except ValueError:
            return None

    def actualizar(_=None):
        campo.error_text = None
        monto = leer_monto()
        if monto is None or monto <= 0:
            texto_queda.value, texto_queda.color = "", None
        elif round(monto, 2) > debe:
            texto_queda.value, texto_queda.color = f"Solo debe {formatear_precio(debe)}", COLOR_PELIGRO
        elif round(debe - monto, 2) <= 0:
            texto_queda.value, texto_queda.color = "Queda al día", COLOR_EXITO
        else:
            texto_queda.value, texto_queda.color = f"Queda debiendo {formatear_precio(debe - monto)}", None
        page.update()

    def aceptar(_=None):
        monto = leer_monto()
        if monto is None or monto <= 0:
            campo.error_text = "Escribe cuánto abona (ej: 10000 o 10.000)."
        elif round(monto, 2) > debe:
            campo.error_text = f"Solo debe {formatear_precio(debe)}."
        else:
            terminar(monto)
            return
        page.update()

    def paga_todo(_):
        campo.value = formatear_numero(debe)
        aceptar()

    campo = ft.TextField(
        label="Abona ($)", prefix_icon=icono_px(ft.Icons.PAYMENTS_OUTLINED), text_size=px(20),
        text_align=ft.TextAlign.CENTER, autofocus=True, on_change=actualizar, on_submit=aceptar,
    )
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(f"Abono de {cliente['nombre']}"),
        content=ft.Column(
            tight=True, spacing=14, width=px(420), horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("Debe", color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ft.Text(formatear_precio(debe), size=px(34), weight=ft.FontWeight.BOLD, color=COLOR_PELIGRO,
                        text_align=ft.TextAlign.CENTER),
                campo,
                texto_queda,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(None)),
            ft.OutlinedButton("Paga todo", on_click=paga_todo),
            ft.FilledButton("Registrar abono", icon=ft.Icons.SAVINGS_OUTLINED,
                            style=ft.ButtonStyle(bgcolor=COLOR_EXITO, color=ft.Colors.WHITE), on_click=aceptar),
        ],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(None),
    ))
    return await resultado
