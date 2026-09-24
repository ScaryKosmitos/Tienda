"""
Diálogo del respaldo en la nube: elegir la carpeta de Google Drive (u otra),
ver cuándo fue el último respaldo que llegó allí y respaldar en el momento.
"""
import asyncio
import os

import flet as ft

import respaldar
from componentes import COLOR_EXITO, COLOR_PELIGRO, avisar, icono_px, mostrar_mensaje, preguntar, px


async def abrir_ajustes_respaldo(page, selector_carpeta):
    """'selector_carpeta' es un ft.FilePicker ya agregado a page.services."""
    texto_carpeta = ft.Text(selectable=True)
    texto_ultimo = ft.Text(weight=ft.FontWeight.BOLD)
    sugerencia = ft.Text(color=ft.Colors.ON_SURFACE_VARIANT)
    boton_sugerencia = ft.OutlinedButton("Usar Google Drive", icon=ft.Icons.ADD_TO_DRIVE)
    boton_ahora = ft.FilledButton("Respaldar ahora", icon=ft.Icons.CLOUD_UPLOAD_OUTLINED)
    boton_quitar = ft.TextButton("Dejar de respaldar", style=ft.ButtonStyle(color=COLOR_PELIGRO))
    drive = respaldar.buscar_google_drive()

    def refrescar():
        """Muestra el estado actual: carpeta elegida y último respaldo en la nube."""
        carpeta = respaldar.carpeta_nube()
        if carpeta:
            texto_carpeta.value = f"Carpeta: {os.path.join(carpeta, respaldar.SUBCARPETA_NUBE)}"
            ultimo = respaldar.ultimo_respaldo_nube()
            texto_ultimo.value = f"Último respaldo en la nube: {ultimo}" if ultimo else "Todavía no hay respaldos en la nube"
            texto_ultimo.color = COLOR_EXITO if ultimo else COLOR_PELIGRO
        else:
            texto_carpeta.value = "Todavía no se ha elegido dónde guardar los respaldos."
            texto_ultimo.value = "Los respaldos solo están en este computador"
            texto_ultimo.color = COLOR_PELIGRO
        # Si se encontró Google Drive y no se está usando, se propone con un botón
        mostrar_sugerencia = drive is not None and drive != carpeta
        sugerencia.visible = boton_sugerencia.visible = mostrar_sugerencia
        sugerencia.value = f"Se encontró Google Drive en {drive}" if drive else ""
        boton_ahora.visible = boton_quitar.visible = carpeta is not None
        page.update()

    def guardar_carpeta(carpeta):
        """Guarda la carpeta elegida (None = ninguna). Retorna True si se pudo."""
        try:
            respaldar.poner_carpeta_nube(carpeta)
            return True
        except OSError as error:
            mostrar_mensaje(page, "No se pudo guardar", f"No se pudo guardar en configuracion.json:\n{error}",
                            error=True)
            return False

    async def usar_carpeta(carpeta):
        if respaldar.es_carpeta_de_la_tienda(carpeta):
            mostrar_mensaje(
                page, "Carpeta no válida",
                "Esa carpeta es la de la tienda: si el computador se daña, el respaldo se pierde con él. "
                "Elige la carpeta de Google Drive (Mi unidad) o una USB.", error=True,
            )
            return
        if guardar_carpeta(carpeta):
            await copiar_ahora()

    async def copiar_ahora():
        boton_ahora.disabled = True
        boton_ahora.content = "Respaldando…"
        page.update()
        try:
            await asyncio.to_thread(respaldar.respaldar_ahora)
        except Exception as error:
            mostrar_mensaje(page, "No se pudo respaldar", f"No se pudo copiar el respaldo a la nube:\n{error}",
                            error=True)
        else:
            avisar(page, "Respaldo guardado en la nube")
        finally:
            boton_ahora.disabled = False
            boton_ahora.content = "Respaldar ahora"
            refrescar()

    async def elegir_carpeta(_):
        carpeta = await selector_carpeta.get_directory_path(
            dialog_title="Elige la carpeta de Google Drive (Mi unidad)",
            initial_directory=drive or os.path.expanduser("~"),
        )
        if carpeta:
            await usar_carpeta(carpeta)

    async def quitar(_):
        if await preguntar(
            page, "Dejar de respaldar",
            "Los respaldos quedarán solo en este computador: si se daña o se lo roban, se pierden los datos. "
            "¿Dejar de copiarlos a la nube? (Los que ya están en la nube no se borran.)",
            si="Dejar de respaldar", peligro=True,
        ):
            guardar_carpeta(None)
            refrescar()

    boton_sugerencia.on_click = lambda _: page.run_task(usar_carpeta, drive)
    boton_ahora.on_click = lambda _: page.run_task(copiar_ahora)
    boton_quitar.on_click = quitar

    page.show_dialog(ft.AlertDialog(
        icon=icono_px(ft.Icons.CLOUD_OUTLINED, 32),
        title=ft.Text("Respaldo en la nube"),
        content=ft.Column(
            tight=True, spacing=12, width=px(480),
            controls=[
                ft.Text(
                    "Cada día se copia un respaldo de la tienda a Google Drive, así los datos no se pierden "
                    "aunque el computador se dañe. Se guardan los últimos "
                    f"{respaldar.MAX_RESPALDOS} días."
                ),
                texto_ultimo,
                texto_carpeta,
                sugerencia,
                ft.Row([boton_sugerencia], wrap=True),
            ],
        ),
        actions=[
            boton_quitar,
            ft.OutlinedButton("Elegir carpeta", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=elegir_carpeta),
            boton_ahora,
            ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog()),
        ],
    ))
    refrescar()
