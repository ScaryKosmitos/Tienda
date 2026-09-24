"""
Diálogos de la clave: pedirla antes de una acción delicada, y crearla,
cambiarla o quitarla desde el candado de la barra lateral.
"""
import asyncio

import flet as ft

import seguridad
from componentes import avisar, icono_px, mostrar_mensaje, preguntar, px


def _campo_clave(etiqueta, **opciones):
    return ft.TextField(
        label=etiqueta, password=True, can_reveal_password=True, prefix_icon=icono_px(ft.Icons.PIN_OUTLINED),
        input_filter=ft.NumbersOnlyInputFilter(), text_size=px(20), **opciones,
    )


async def pedir_clave(page, motivo):
    """
    Pide la clave antes de una acción delicada (cada vez, aunque se haya
    escrito hace poco). Retorna True si se puede seguir: no hay clave, o se
    escribió bien.
    """
    if not seguridad.tiene_clave():
        return True

    resultado = asyncio.get_running_loop().create_future()

    def terminar(valor):
        if not resultado.done():
            resultado.set_result(valor)
            page.pop_dialog()

    def comprobar(_=None):
        if seguridad.verificar(campo.value):
            terminar(True)
        else:
            campo.error_text = "Clave incorrecta"
            campo.value = ""
            page.update()

    campo = _campo_clave("Clave", autofocus=True, on_submit=comprobar)
    page.show_dialog(ft.AlertDialog(
        modal=True,
        icon=icono_px(ft.Icons.LOCK_OUTLINE, 32),
        title=ft.Text("Se necesita la clave"),
        content=ft.Column([ft.Text(motivo), campo], tight=True, spacing=14, width=px(380),
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(False)),
            ft.FilledButton("Continuar", on_click=comprobar),
        ],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(False),
    ))
    return await resultado


async def _crear_clave(page, titulo):
    """Pide la clave nueva dos veces y la guarda. Retorna True si se guardó."""
    resultado = asyncio.get_running_loop().create_future()

    def terminar(valor):
        if not resultado.done():
            resultado.set_result(valor)
            page.pop_dialog()

    def guardar(_=None):
        nueva.error_text = repetida.error_text = None
        error = seguridad.clave_valida(nueva.value)
        if error:
            nueva.error_text = error
        elif nueva.value != repetida.value:
            repetida.error_text = "Las dos claves no son iguales"
        else:
            seguridad.poner_clave(nueva.value)
            terminar(True)
            return
        page.update()

    nueva = _campo_clave("Clave nueva (4 a 8 números)", autofocus=True)
    repetida = _campo_clave("Repite la clave", on_submit=guardar)
    page.show_dialog(ft.AlertDialog(
        modal=True,
        icon=icono_px(ft.Icons.LOCK_OUTLINE, 32),
        title=ft.Text(titulo),
        content=ft.Column(
            [
                ft.Text("Se pedirá para eliminar productos, cambiar precios o stock y anular ventas."),
                nueva,
                repetida,
            ],
            tight=True, spacing=14, width=px(400), horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(False)),
            ft.FilledButton("Guardar clave", on_click=guardar),
        ],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(False),
    ))
    return await resultado


async def abrir_ajustes_clave(page):
    """Candado de la barra lateral: crear la clave o, con la clave actual, cambiarla o quitarla."""
    try:
        await _ajustes_clave(page)
    except OSError as error:
        mostrar_mensaje(page, "No se pudo guardar", f"No se pudo guardar la clave en configuracion.json:\n{error}",
                        error=True)


async def _ajustes_clave(page):
    if not seguridad.tiene_clave():
        if await _crear_clave(page, "Crear clave"):
            avisar(page, "Clave creada")
        return

    if not await pedir_clave(page, "Escribe la clave actual para cambiarla o quitarla."):
        return

    eleccion = asyncio.get_running_loop().create_future()

    def elegir(valor):
        if not eleccion.done():
            eleccion.set_result(valor)
            page.pop_dialog()

    page.show_dialog(ft.AlertDialog(
        icon=icono_px(ft.Icons.LOCK_OUTLINE, 32),
        title=ft.Text("Clave"),
        content=ft.Text(
            "La clave está activa: se pide cada vez que se elimina un producto, se cambia un precio o "
            "el stock, o se anula una venta, un abono o una salida de caja.",
            width=px(420),
        ),
        actions=[
            ft.TextButton("Quitar clave", on_click=lambda _: elegir("quitar")),
            ft.OutlinedButton("Cambiar clave", on_click=lambda _: elegir("cambiar")),
            ft.FilledButton("Listo", on_click=lambda _: elegir(None)),
        ],
        on_dismiss=lambda _: eleccion.done() or eleccion.set_result(None),
    ))
    opcion = await eleccion

    if opcion == "cambiar":
        if await _crear_clave(page, "Cambiar clave"):
            avisar(page, "Clave cambiada")
    elif opcion == "quitar":
        if await preguntar(page, "Quitar clave", "Cualquiera podrá eliminar productos, cambiar precios y "
                                                 "anular ventas sin clave. ¿Quitarla?", si="Quitar", peligro=True):
            seguridad.quitar_clave()
            avisar(page, "Se quitó la clave")
