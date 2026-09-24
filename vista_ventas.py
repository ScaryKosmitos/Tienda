"""
Pantalla del historial de ventas, con dos pestañas que comparten los filtros
de fecha: el historial (donde se ven los recibos y se anulan ventas) y el
ranking de productos más vendidos. También exporta el período a Excel.
"""
import os
from datetime import date, datetime, timedelta

import flet as ft

import base_datos as db
from componentes import (
    COLOR_EXITO, COLOR_PELIGRO, ERRORES_BD, STOCK_BAJO, avisar, con_desplazamiento, crear_tabla, encabezado,
    etiqueta, icono_px, manejar_errores_bd, mostrar_mensaje, panel, preguntar, px, texto_vacio,
)
from dialogo_clave import pedir_clave
from dialogo_recibo import mostrar_recibo
from formato import describir_periodo, formatear_numero, formatear_precio
from recibo import numero_recibo


class VistaVentas:
    def __init__(self, page):
        self.page = page
        # Período que se está mostrando; es el que se exporta a Excel
        self.desde = None
        self.hasta = None
        # Líneas de venta marcadas para anular
        self.seleccion = set()

        self.selector_archivo = ft.FilePicker()
        page.services.append(self.selector_archivo)

        self.boton_anular = ft.OutlinedButton(
            "Anular seleccionadas", icon=ft.Icons.UNDO, disabled=True,
            style=ft.ButtonStyle(color=COLOR_PELIGRO), on_click=self.anular_seleccionadas,
        )

        self.control = ft.Column(
            spacing=20,
            expand=True,
            controls=[
                encabezado(
                    "Ventas", "Historial de ventas, recibos y productos más vendidos",
                    ft.FilledButton(
                        "Exportar a Excel", icon=ft.Icons.TABLE_VIEW_OUTLINED, height=px(44),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), bgcolor=COLOR_EXITO,
                                             color=ft.Colors.WHITE),
                        on_click=self.exportar_a_excel,
                    ),
                ),
                self.crear_filtros(),
                panel(
                    ft.Tabs(
                        length=2,
                        selected_index=0,
                        expand=True,
                        content=ft.Column(
                            expand=True,
                            controls=[
                                ft.TabBar(tabs=[
                                    ft.Tab(label="Historial", icon=icono_px(ft.Icons.RECEIPT_LONG_OUTLINED, 24)),
                                    ft.Tab(label="Más vendidos", icon=icono_px(ft.Icons.EMOJI_EVENTS_OUTLINED, 24)),
                                ]),
                                ft.TabBarView(
                                    expand=True,
                                    controls=[self.crear_pestana_ventas(), self.crear_pestana_ranking()],
                                ),
                            ],
                        ),
                    ),
                    expand=True,
                ),
            ],
        )

    # --- CONSTRUCCIÓN ---

    def campo_fecha(self, etiqueta_campo):
        campo = ft.TextField(
            label=etiqueta_campo, hint_text="AAAA-MM-DD", width=px(170), dense=True, filled=True,
            on_submit=lambda _: self.cargar(),
        )

        def elegir_fecha(_):
            def al_elegir(e):
                if e.control.value:
                    campo.value = e.control.value.strftime("%Y-%m-%d")
                    self.cargar()

            try:
                actual = datetime.strptime(campo.value.strip(), "%Y-%m-%d")
            except ValueError:
                actual = datetime.now()
            self.page.show_dialog(ft.DatePicker(
                value=actual, first_date=datetime(2020, 1, 1), last_date=datetime(2100, 12, 31),
                on_change=al_elegir,
            ))

        campo.suffix_icon = ft.IconButton(ft.Icons.CALENDAR_MONTH_OUTLINED, icon_size=px(20), tooltip="Elegir en el calendario",
                                     on_click=elegir_fecha)
        return campo

    def crear_filtros(self):
        self.campo_desde = self.campo_fecha("Desde")
        self.campo_hasta = self.campo_fecha("Hasta")

        # Las fechas se calculan al hacer clic (hoy = el día de la venta), no al
        # abrir la tienda: así siguen bien aunque quede abierta de un día para otro
        botones_rapidos = (
            ("Hoy", lambda hoy: hoy),
            ("Esta semana", lambda hoy: hoy - timedelta(days=hoy.weekday())),
            ("Este mes", lambda hoy: hoy.replace(day=1)),
            ("Todo", None),
        )
        return ft.Row(
            spacing=10,
            wrap=True,
            controls=[
                self.campo_desde,
                self.campo_hasta,
                ft.FilledButton("Filtrar", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=lambda _: self.cargar()),
                ft.VerticalDivider(width=12),
                *[
                    ft.OutlinedButton(texto, on_click=lambda _, i=inicio: self.poner_periodo(i))
                    for texto, inicio in botones_rapidos
                ],
            ],
        )

    def crear_pestana_ventas(self):
        self.tabla_ventas = crear_tabla(
            [("Recibo", False), ("Producto", False), ("Cant.", True), ("Total", True), ("Fecha y hora", False),
             ("Estado", False), ("", False)],
            show_checkbox_column=True,
        )
        self.sin_ventas = texto_vacio(ft.Icons.RECEIPT_LONG_OUTLINED, "No hay ventas en este período")
        self.texto_total = ft.Text("", size=px(17), weight=ft.FontWeight.BOLD, color=COLOR_EXITO)
        return ft.Column(
            expand=True,
            controls=[
                ft.Stack([con_desplazamiento(self.tabla_ventas), self.sin_ventas], expand=True),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[self.texto_total, self.boton_anular],
                ),
            ],
        )

    def crear_pestana_ranking(self):
        self.tabla_ranking = crear_tabla(
            [("#", True), ("Producto", False), ("Unidades vendidas", True), ("Total", True),
             ("% de lo vendido", True)],
        )
        self.sin_ranking = texto_vacio(ft.Icons.EMOJI_EVENTS_OUTLINED, "No hay ventas en este período")
        self.texto_ranking = ft.Text("", size=px(15), weight=ft.FontWeight.BOLD)
        return ft.Column(
            expand=True,
            controls=[ft.Stack([con_desplazamiento(self.tabla_ranking), self.sin_ranking], expand=True),
                      self.texto_ranking],
        )

    # --- FILTROS Y CARGA DE DATOS ---

    def mostrar(self):
        """Se llama cada vez que se entra a esta pantalla."""
        self.cargar()

    def poner_periodo(self, inicio):
        """'inicio(hoy)' da la primera fecha del período, que termina hoy; None = todo el historial."""
        if inicio is None:
            self.poner_fechas(None, None)
        else:
            hoy = date.today()
            self.poner_fechas(inicio(hoy), hoy)

    def poner_fechas(self, desde, hasta):
        self.campo_desde.value = desde.strftime("%Y-%m-%d") if desde else ""
        self.campo_hasta.value = hasta.strftime("%Y-%m-%d") if hasta else ""
        self.cargar()

    def leer_fechas(self):
        """
        Lee y valida las fechas de los filtros. Retorna (desde, hasta) como
        'AAAA-MM-DD' o None si el campo está vacío; si hay un error, lo marca
        en el campo y retorna None.
        """
        fechas = []
        for campo in (self.campo_desde, self.campo_hasta):
            campo.error_text = None
            texto = campo.value.strip()
            if not texto:
                fechas.append(None)
                continue
            try:
                # Se reescribe con ceros (2026-9-1 -> 2026-09-01), porque la
                # base de datos compara las fechas como texto
                fecha = datetime.strptime(texto, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                campo.error_text = "Usa el formato AAAA-MM-DD"
                self.page.update()
                return None
            campo.value = fecha
            fechas.append(fecha)

        desde, hasta = fechas
        if desde and hasta and desde > hasta:
            self.campo_desde.error_text = "Es posterior a 'Hasta'"
            self.page.update()
            return None
        return desde, hasta

    @manejar_errores_bd
    def cargar(self):
        """Recarga las dos pestañas con el período de los filtros."""
        fechas = self.leer_fechas()
        if fechas is None:
            return
        desde, hasta = fechas
        ventas = db.obtener_ventas(desde, hasta)
        ranking = db.obtener_mas_vendidos(desde, hasta)

        self.desde, self.hasta = desde, hasta
        periodo = describir_periodo(desde, hasta)
        self.seleccion.clear()
        self.mostrar_ventas(ventas, periodo)
        self.mostrar_ranking(ranking, periodo)
        self.page.update()

    def mostrar_ventas(self, ventas, periodo):
        dinero_total = sum(v["total"] for v in ventas if not v["anulada"])
        lineas_validas = sum(1 for v in ventas if not v["anulada"])
        self.tabla_ventas.rows = [self.fila_venta(v) for v in ventas]
        self.sin_ventas.visible = not ventas
        self.texto_total.value = (
            f"Total recaudado ({periodo}): {formatear_precio(dinero_total)}  ·  {lineas_validas} líneas de venta"
        )
        self.actualizar_boton_anular()

    def fila_venta(self, venta):
        anulada = bool(venta["anulada"])
        gris = ft.Colors.OUTLINE if anulada else None
        fila = ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(numero_recibo(venta["recibo_id"]) if venta["recibo_id"] else "—", color=gris)),
                ft.DataCell(ft.Text(venta["nombre_producto"], weight=ft.FontWeight.W_500, color=gris)),
                ft.DataCell(ft.Text(formatear_numero(venta["cantidad"]), color=gris)),
                ft.DataCell(ft.Text(formatear_precio(venta["total"]), color=gris)),
                ft.DataCell(ft.Text(venta["fecha"], color=gris or ft.Colors.ON_SURFACE_VARIANT, size=px(13))),
                ft.DataCell(etiqueta("Anulada", ft.Colors.OUTLINE) if anulada else etiqueta("OK", COLOR_EXITO)),
                ft.DataCell(ft.IconButton(
                    ft.Icons.RECEIPT_OUTLINED, tooltip="Ver recibo",
                    on_click=lambda _, r=venta["recibo_id"]: self.ver_recibo(r),
                )),
            ],
        )
        # Las ventas anuladas no se pueden volver a anular, así que no se pueden marcar
        if not anulada:
            def al_marcar(e, id_venta=venta["id"]):
                if e.data in (True, "true"):
                    self.seleccion.add(id_venta)
                else:
                    self.seleccion.discard(id_venta)
                fila.selected = id_venta in self.seleccion
                self.actualizar_boton_anular()
                self.page.update()
            fila.on_select_change = al_marcar
        return fila

    def actualizar_boton_anular(self):
        cantidad = len(self.seleccion)
        self.boton_anular.disabled = not cantidad
        self.boton_anular.content = f"Anular seleccionadas ({cantidad})" if cantidad else "Anular seleccionadas"

    def mostrar_ranking(self, ranking, periodo):
        total_ranking = sum(fila["total"] for fila in ranking)
        filas = []
        for puesto, fila in enumerate(ranking, start=1):
            porcentaje = f"{fila['total'] / total_ranking * 100:.1f} %".replace(".", ",") if total_ranking else "—"
            medalla = {1: ft.Colors.AMBER, 2: ft.Colors.BLUE_GREY_300, 3: ft.Colors.BROWN_300}.get(puesto)
            filas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Icon(ft.Icons.EMOJI_EVENTS, color=medalla, size=px(20)) if medalla else ft.Text(str(puesto))),
                ft.DataCell(ft.Text(fila["nombre"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(formatear_numero(fila["unidades"]))),
                ft.DataCell(ft.Text(formatear_precio(fila["total"]))),
                ft.DataCell(ft.Text(porcentaje)),
            ]))
        self.tabla_ranking.rows = filas
        self.sin_ranking.visible = not ranking

        if ranking:
            primero = ranking[0]
            self.texto_ranking.value = (
                f"{len(ranking)} producto(s) vendidos ({periodo})  ·  "
                f"Más vendido: {primero['nombre']} ({formatear_numero(primero['unidades'])} unidades)"
            )
        else:
            self.texto_ranking.value = ""

    # --- ACCIONES ---

    @manejar_errores_bd
    def ver_recibo(self, id_recibo):
        if not id_recibo:
            mostrar_mensaje(
                self.page, "Sin Recibo",
                "Esta venta se registró antes de que existieran los recibos, así que no tiene uno.",
            )
            return
        mostrar_recibo(self.page, db.obtener_recibo(id_recibo))

    @manejar_errores_bd
    async def anular_seleccionadas(self, _e):
        if not self.seleccion:
            return
        if not await preguntar(
            self.page, "Anular ventas",
            f"¿Anular {len(self.seleccion)} línea(s) de venta? Las unidades volverán al stock.",
            si="Anular", peligro=True,
        ) or not await pedir_clave(self.page, "Anular ventas necesita la clave."):
            return

        exito, mensaje = db.anular_ventas(sorted(self.seleccion))
        if exito:
            avisar(self.page, mensaje)
            self.cargar()
        else:
            mostrar_mensaje(self.page, "No se pudo anular", mensaje, error=True)

    async def exportar_a_excel(self, _e):
        try:
            # Se importa aquí para que la tienda funcione aunque falte openpyxl
            import exportar
        except ImportError:
            mostrar_mensaje(
                self.page, "Falta una Librería",
                "Para exportar a Excel hay que instalar 'openpyxl'. En Windows, vuelve a ejecutar "
                "instalar_windows.bat; en Linux: .venv/bin/pip install openpyxl",
                error=True,
            )
            return

        desde, hasta = self.desde, self.hasta
        if desde or hasta:
            nombre_sugerido = f"Reporte_Tienda_{desde or 'inicio'}_a_{hasta or date.today()}.xlsx"
        else:
            nombre_sugerido = f"Reporte_Tienda_completo_{date.today()}.xlsx"
        ruta = await self.selector_archivo.save_file(
            dialog_title="Guardar reporte de Excel",
            file_name=nombre_sugerido,
            initial_directory=os.path.expanduser("~"),
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx"],
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".xlsx"):
            ruta += ".xlsx"

        try:
            cantidad_ventas, cantidad_productos = exportar.exportar_excel(ruta, desde, hasta, STOCK_BAJO)
        except PermissionError:
            mostrar_mensaje(
                self.page, "No se pudo guardar",
                "No se pudo escribir el archivo. Si lo tienes abierto en Excel o LibreOffice, "
                "ciérralo e inténtalo de nuevo.",
                error=True,
            )
            return
        except ERRORES_BD as error:
            mostrar_mensaje(self.page, "No se pudo exportar", f"Ocurrió un problema:\n{error}", error=True)
            return

        mostrar_mensaje(
            self.page, "Reporte Exportado",
            f"Se guardó el reporte ({describir_periodo(desde, hasta)}):\n{ruta}\n\n"
            f"Hojas: Ventas ({cantidad_ventas} líneas), Más vendidos e Inventario ({cantidad_productos} productos).",
        )
