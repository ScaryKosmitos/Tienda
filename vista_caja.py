"""
Pantalla de caja: la base con la que empieza el día, las salidas de efectivo
y el resumen para el cierre (cuánto efectivo debería haber en la caja y
cuánto entró por Nequi o se fió).
"""
import asyncio
from datetime import date, datetime, timedelta

import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_MARCA, COLOR_PELIGRO, avisar, encabezado, icono_px, manejar_errores_bd, mostrar_mensaje, panel,
    preguntar, px, texto_vacio,
)
from dialogo_clave import pedir_clave
from formato import formatear_numero, formatear_precio, leer_precio

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
COLOR_NEQUI = ft.Colors.PURPLE_700


def describir_dia(dia):
    """date(2026, 9, 24) -> 'Hoy, jueves 24 de septiembre' (o 'Ayer, ...', o con el año si no es este)."""
    texto = f"{DIAS[dia.weekday()]} {dia.day} de {MESES[dia.month - 1]}"
    if dia.year != date.today().year:
        texto += f" de {dia.year}"
    if dia == date.today():
        return f"Hoy, {texto}"
    if dia == date.today() - timedelta(days=1):
        return f"Ayer, {texto}"
    return texto[0].upper() + texto[1:]


async def pedir_monto(page, titulo, etiqueta, valor=None, con_motivo=False):
    """
    Pide un monto (y un motivo, si 'con_motivo'). Retorna el monto, o
    (monto, motivo) si se pidió el motivo, o None si se cancela.
    """
    resultado = asyncio.get_running_loop().create_future()

    def terminar(respuesta):
        if not resultado.done():
            resultado.set_result(respuesta)
            page.pop_dialog()

    def aceptar(_=None):
        campo.error_text = None
        if con_motivo:
            campo_motivo.error_text = None
        try:
            monto = leer_precio(campo.value.strip())
        except ValueError:
            campo.error_text = "Debe ser un número (ej: 50000 o 50.000)."
            page.update()
            return
        error = db.validar_monto_caja(monto)
        if error:
            campo.error_text = error
        elif con_motivo and monto == 0:
            campo.error_text = "El monto debe ser mayor a 0."
        elif con_motivo and not campo_motivo.value.strip():
            campo_motivo.error_text = "Escribe para qué se sacó la plata."
        else:
            terminar((monto, campo_motivo.value) if con_motivo else monto)
            return
        page.update()

    campo = ft.TextField(
        label=etiqueta, value=formatear_numero(valor) if valor is not None else "", autofocus=True,
        prefix_icon=icono_px(ft.Icons.ATTACH_MONEY), text_size=px(20), text_align=ft.TextAlign.CENTER,
        on_submit=aceptar,
    )
    controles = [campo]
    if con_motivo:
        campo_motivo = ft.TextField(label="Motivo", hint_text="Ej: pago al proveedor de gaseosas", on_submit=aceptar,
                                    prefix_icon=icono_px(ft.Icons.NOTES), max_length=100)
        controles.append(campo_motivo)

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(titulo),
        content=ft.Column(controles, tight=True, spacing=14, width=px(420),
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: terminar(None)),
            ft.FilledButton("Guardar", icon=ft.Icons.SAVE_OUTLINED, on_click=aceptar),
        ],
        on_dismiss=lambda _: resultado.done() or resultado.set_result(None),
    ))
    return await resultado


class VistaCaja:
    def __init__(self, page):
        self.page = page
        # Día que se está mostrando
        self.dia = date.today()

        self.texto_dia = ft.Text("", size=px(18), weight=ft.FontWeight.BOLD)
        self.boton_siguiente = ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Día siguiente",
                                             on_click=lambda _: self.cambiar_dia(1))
        selector_dia = ft.Row(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Día anterior", on_click=lambda _: self.cambiar_dia(-1)),
                self.texto_dia,
                self.boton_siguiente,
                ft.IconButton(ft.Icons.CALENDAR_MONTH_OUTLINED, tooltip="Elegir en el calendario",
                              on_click=self.elegir_en_calendario),
                ft.OutlinedButton("Hoy", on_click=lambda _: self.ir_a_dia(date.today())),
            ],
        )

        self.control = ft.Column(
            spacing=20,
            expand=True,
            controls=[
                encabezado("Caja", "Base, salidas y cuánto efectivo debería haber para cerrar la caja"),
                selector_dia,
                ft.Row(
                    [self.crear_panel_resumen(), self.crear_panel_salidas()],
                    expand=True, spacing=16, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
        )

    # --- CONSTRUCCIÓN ---

    def fila(self, texto, valor, signo="", grande=False, color=None):
        """Una línea del resumen: texto a la izquierda y monto a la derecha."""
        tamano = px(26) if grande else None
        peso = ft.FontWeight.BOLD if grande else None
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(texto, size=tamano, weight=peso, expand=True),
                ft.Text(f"{signo} {valor}".strip(), size=tamano, weight=ft.FontWeight.BOLD, color=color),
            ],
        )

    def crear_panel_resumen(self):
        self.resumen = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        return panel(self.resumen, expand=True)

    def crear_panel_salidas(self):
        self.boton_salida = ft.FilledButton(
            "Registrar salida", icon=ft.Icons.OUTBOX_OUTLINED, height=px(48), expand=True,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)), on_click=self.registrar_salida,
        )
        self.lista_salidas = ft.ListView(spacing=6, expand=True)
        self.sin_salidas = texto_vacio(ft.Icons.OUTBOX_OUTLINED, "No hay salidas este día")
        return panel(
            ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Text("Salidas de efectivo", size=px(20), weight=ft.FontWeight.BOLD),
                    ft.Text("Plata que se saca de la caja: pagos a proveedores, gastos, retiros.",
                            color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Row([self.boton_salida]),
                    ft.Stack([self.lista_salidas, self.sin_salidas], expand=True),
                ],
            ),
            width=px(430),
        )

    # --- CARGA DE DATOS ---

    def mostrar(self):
        """Se llama cada vez que se entra a esta pantalla: muestra el día de hoy."""
        self.ir_a_dia(date.today())

    def cambiar_dia(self, dias):
        self.ir_a_dia(self.dia + timedelta(days=dias))

    def ir_a_dia(self, dia):
        # No se puede ir a días futuros: todavía no tienen nada
        self.dia = min(dia, date.today())
        self.cargar()

    def elegir_en_calendario(self, _e):
        def al_elegir(e):
            if e.control.value:
                self.ir_a_dia(e.control.value.date() if isinstance(e.control.value, datetime) else e.control.value)

        self.page.show_dialog(ft.DatePicker(
            value=datetime.combine(self.dia, datetime.min.time()), first_date=datetime(2020, 1, 1),
            last_date=datetime.now(), on_change=al_elegir,
        ))

    @manejar_errores_bd
    def cargar(self):
        fecha = self.dia.isoformat()
        es_hoy = self.dia == date.today()
        self.texto_dia.value = describir_dia(self.dia)
        self.boton_siguiente.disabled = es_hoy
        self.mostrar_resumen(db.resumen_caja(fecha))

        # Las salidas se registran en el momento, así que solo se agregan hoy
        self.boton_salida.visible = es_hoy
        salidas = db.obtener_salidas(fecha)
        self.lista_salidas.controls = [self.linea_salida(s) for s in salidas]
        self.sin_salidas.visible = not salidas
        self.page.update()

    def mostrar_resumen(self, r):
        base = r["base"]
        if base is None:
            texto_base = ft.Text("Sin registrar", color=COLOR_PELIGRO, weight=ft.FontWeight.BOLD)
        else:
            texto_base = ft.Text(formatear_precio(base), weight=ft.FontWeight.BOLD)
        nequi = r["ventas_nequi"] + r["abonos_nequi"]

        self.resumen.controls = [
            ft.Text("Efectivo en la caja", size=px(20), weight=ft.FontWeight.BOLD),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Base (con la que empezó el día)", expand=True),
                    ft.TextButton("Registrar base" if base is None else "Cambiar", icon=ft.Icons.EDIT_OUTLINED,
                                  on_click=self.registrar_base),
                    texto_base,
                ],
            ),
            self.fila("Ventas en efectivo", formatear_precio(r["ventas_efectivo"]), "+"),
            self.fila("Abonos de fiado en efectivo", formatear_precio(r["abonos_efectivo"]), "+"),
            self.fila("Salidas", formatear_precio(r["salidas"]), "−", color=COLOR_PELIGRO if r["salidas"] else None),
            ft.Divider(height=1),
            self.fila("Debería haber en la caja", formatear_precio(r["en_caja"]), grande=True, color=COLOR_EXITO),
            ft.Text(
                "Cuenta el efectivo de la caja: debería dar este número. Si no se registró la base, "
                "no está incluida." if base is None else
                "Cuenta el efectivo de la caja: debería dar este número.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=8),
            ft.Text("Fuera de la caja", size=px(20), weight=ft.FontWeight.BOLD),
            self.fila("Por Nequi (ventas y abonos)", formatear_precio(nequi), color=COLOR_NEQUI if nequi else None),
            self.fila("Fiado (ventas que no se pagaron)", formatear_precio(r["fiado"]),
                      color=ft.Colors.ORANGE_800 if r["fiado"] else None),
            ft.Divider(height=1),
            self.fila("Total vendido del día", formatear_precio(r["total_vendido"]), color=COLOR_MARCA),
        ]

    def linea_salida(self, salida):
        anulada = bool(salida["anulada"])
        acciones = []
        if not anulada:
            acciones.append(ft.IconButton(
                ft.Icons.UNDO, icon_size=px(18), icon_color=COLOR_PELIGRO,
                tooltip="Anular esta salida (si se registró por error)",
                on_click=lambda _, s=salida: self.page.run_task(self.anular_salida, s),
            ))
        return ft.Container(
            padding=ft.Padding.only(left=12, right=4, top=6, bottom=6),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Row(
                spacing=4,
                controls=[
                    ft.Column(
                        spacing=0, expand=True,
                        controls=[
                            ft.Text(salida["motivo"] + (" (anulada)" if anulada else ""), weight=ft.FontWeight.W_500,
                                    color=ft.Colors.OUTLINE if anulada else None),
                            ft.Text(salida["fecha"][11:16], size=px(12), color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                    ),
                    ft.Text(f"−{formatear_precio(salida['monto'])}", weight=ft.FontWeight.BOLD,
                            color=ft.Colors.OUTLINE if anulada else COLOR_PELIGRO),
                    *acciones,
                ],
            ),
        )

    # --- ACCIONES ---

    @manejar_errores_bd
    async def registrar_base(self, _e):
        fecha = self.dia.isoformat()
        monto = await pedir_monto(
            self.page, f"Base del día ({describir_dia(self.dia)})", "Efectivo al empezar el día ($)",
            valor=db.obtener_base(fecha),
        )
        if monto is None:
            return
        exito, mensaje = db.poner_base(fecha, monto)
        if exito:
            avisar(self.page, mensaje)
        else:
            mostrar_mensaje(self.page, "No se pudo guardar", mensaje, error=True)
        self.cargar()

    @manejar_errores_bd
    async def registrar_salida(self, _e):
        respuesta = await pedir_monto(self.page, "Salida de efectivo", "Cuánto se sacó ($)",
                                      con_motivo=True)
        if respuesta is None:
            return
        exito, mensaje = db.registrar_salida(*respuesta)
        if exito:
            avisar(self.page, mensaje)
        else:
            mostrar_mensaje(self.page, "No se pudo registrar", mensaje, error=True)
        self.cargar()

    @manejar_errores_bd
    async def anular_salida(self, salida):
        if not await preguntar(
            self.page, "Anular salida",
            f"¿Anular la salida de {formatear_precio(salida['monto'])} ({salida['motivo']})?",
            si="Anular", peligro=True,
        ) or not await pedir_clave(self.page, "Anular una salida de caja necesita la clave."):
            return
        exito, mensaje = db.anular_salida(salida["id"])
        if exito:
            avisar(self.page, mensaje)
        else:
            mostrar_mensaje(self.page, "No se pudo anular", mensaje, error=True)
        self.cargar()
