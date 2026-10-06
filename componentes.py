"""
Piezas de interfaz que comparten todas las pantallas: colores, avisos,
preguntas de confirmación y el manejo de errores de la base de datos.
"""
import asyncio
import inspect
import sqlite3
from functools import wraps

import flet as ft

from formato import formatear_numero

# Los productos con menos unidades que esto se marcan en rojo
STOCK_BAJO = 5

# Errores que se muestran como "Error de Base de Datos" (archivo bloqueado, permisos, etc.)
ERRORES_BD = (sqlite3.Error, OSError)

COLOR_MARCA = ft.Colors.INDIGO
COLOR_EXITO = ft.Colors.GREEN_700
COLOR_PELIGRO = ft.Colors.RED

# Estilo glassmorfismo: un fondo de colores degradados con manchas de luz, y
# encima recuadros de "vidrio esmerilado": translúcidos, con el fondo borroso
# detrás y un borde fino claro. Colores de cada modo: los tres del degradado,
# las tres manchas, el vidrio, su borde, los campos de texto, las ventanas y
# los menús (un vidrio más tupido, porque Flet no puede desenfocar lo que
# queda detrás de ellos), el velo que cubre la tienda al abrir una ventana y
# la sombra
_VIDRIO = {
    False: dict(
        degradado=("#C9D6FF", "#E2C6F5", "#FBD3E9"), manchas=("#7F9CFF", "#F48FC0", "#6EDDD0"),
        vidrio=ft.Colors.with_opacity(0.35, "#FFFFFF"), borde=ft.Colors.with_opacity(0.65, "#FFFFFF"),
        campo=ft.Colors.with_opacity(0.45, "#FFFFFF"), ventana=ft.Colors.with_opacity(0.78, "#F7F5FF"),
        menu=ft.Colors.with_opacity(0.86, "#F7F5FF"), velo=ft.Colors.with_opacity(0.45, "#C9C2F0"),
        sombra=ft.Colors.with_opacity(0.18, "#1F2A5C"),
    ),
    True: dict(
        degradado=("#0F1028", "#1B1240", "#2A0F3A"), manchas=("#6366F1", "#D946EF", "#22D3EE"),
        vidrio=ft.Colors.with_opacity(0.07, "#FFFFFF"), borde=ft.Colors.with_opacity(0.20, "#FFFFFF"),
        campo=ft.Colors.with_opacity(0.10, "#FFFFFF"), ventana=ft.Colors.with_opacity(0.80, "#2A2350"),
        menu=ft.Colors.with_opacity(0.88, "#241E42"), velo=ft.Colors.with_opacity(0.60, "#0B0A1E"),
        sombra=ft.Colors.with_opacity(0.35, "#000000"),
    ),
}


# --- TAMAÑO DE LETRA ---

# Opciones del menú "Tamaño de letra": nombre y cuánto se agranda todo
TAMANOS = [("Normal", 1.0), ("Grande", 1.25), ("Muy grande", 1.5), ("Enorme", 1.75)]

_escala = 1.0

# Tamaños de letra estándar de Material Design (los que usan botones, campos,
# tablas y diálogos cuando no se les pone un tamaño)
_TAMANOS_TEMA = {
    "display_large": 57, "display_medium": 45, "display_small": 36,
    "headline_large": 32, "headline_medium": 28, "headline_small": 24,
    "title_large": 22, "title_medium": 16, "title_small": 14,
    "body_large": 16, "body_medium": 14, "body_small": 12,
    "label_large": 14, "label_medium": 12, "label_small": 11,
}


def escala():
    return _escala


def poner_escala(valor):
    """Cambia el tamaño de todo. Las pantallas se deben volver a construir para que se note."""
    global _escala
    _escala = valor


def px(tamano):
    """Tamaño (de letra, ícono o ancho) ajustado al tamaño de letra elegido."""
    return round(tamano * _escala)


def icono_px(nombre, tamano=20):
    """Ícono ajustado al tamaño de letra, para campos, menús y la barra lateral (que no usan el del tema)."""
    return ft.Icon(nombre, size=px(tamano))


def crear_tema(oscuro):
    """Tema de vidrio (claro u oscuro) con las letras e íconos del tamaño elegido."""
    c = _VIDRIO[oscuro]
    # Los íconos de los botones miden 18 en Material Design
    forma = ft.RoundedRectangleBorder(radius=14)
    estilo_botones = ft.ButtonStyle(icon_size=px(18), shape=forma)
    # Los botones sin color son de vidrio, como los recuadros
    estilo_vidrio = ft.ButtonStyle(
        icon_size=px(18), shape=forma, bgcolor=c["vidrio"], side=ft.BorderSide(1, c["borde"]),
    )
    # Ventanas, menús y calendario: vidrio con borde claro
    def forma_vidrio(radio):
        return ft.RoundedRectangleBorder(radius=radio, side=ft.BorderSide(1, c["borde"]))
    # Flet no mezcla estos estilos con los de Material: los reemplaza enteros, así
    # que sin un color los textos quedaban sin color propio y algunos seguían en
    # blanco al pasar de modo oscuro a claro. ON_SURFACE es el color normal del
    # texto y Flet lo calcula aparte para el tema claro y para el oscuro
    #
    # Los recuadros se arman una sola vez y deben cambiar al pasar de modo claro a
    # oscuro, así que toman sus colores del tema: SURFACE_CONTAINER_LOWEST es el
    # vidrio, OUTLINE_VARIANT su borde (y las líneas de las tablas), SHADOW la
    # sombra, SURFACE_CONTAINER_HIGHEST los campos y cuadros internos, y los
    # "fixed" (que Material casi no usa) el degradado y las manchas del fondo
    return ft.Theme(
        color_scheme_seed=COLOR_MARCA,
        color_scheme=ft.ColorScheme(
            surface=c["menu"], surface_container_low=c["menu"], surface_container=c["menu"],
            surface_container_high=c["menu"], surface_container_lowest=c["vidrio"],
            surface_container_highest=c["campo"], outline_variant=c["borde"], shadow=c["sombra"],
            primary_fixed=c["degradado"][0], secondary_fixed=c["degradado"][1], tertiary_fixed=c["degradado"][2],
            primary_fixed_dim=c["manchas"][0], secondary_fixed_dim=c["manchas"][1],
            tertiary_fixed_dim=c["manchas"][2],
        ),
        scaffold_bgcolor=c["degradado"][0],
        text_theme=ft.TextTheme(**{
            nombre: ft.TextStyle(size=px(t), color=ft.Colors.ON_SURFACE) for nombre, t in _TAMANOS_TEMA.items()
        }),
        icon_theme=ft.IconTheme(size=px(24)),
        filled_button_theme=ft.FilledButtonTheme(style=ft.ButtonStyle(
            icon_size=px(18), shape=forma, elevation=3, shadow_color=c["sombra"],
        )),
        outlined_button_theme=ft.OutlinedButtonTheme(style=estilo_vidrio),
        text_button_theme=ft.TextButtonTheme(style=estilo_botones),
        dialog_theme=ft.DialogTheme(bgcolor=c["ventana"], barrier_color=c["velo"], shape=forma_vidrio(24),
                                    elevation=0),
        date_picker_theme=ft.DatePickerTheme(bgcolor=c["ventana"], shape=forma_vidrio(24), elevation=0),
        dropdown_theme=ft.DropdownTheme(menu_style=ft.MenuStyle(
            bgcolor=c["menu"], shape=forma_vidrio(16), side=ft.BorderSide(1, c["borde"]), shadow_color=c["sombra"],
        )),
        popup_menu_theme=ft.PopupMenuTheme(color=c["menu"], shape=forma_vidrio(16), shadow_color=c["sombra"]),
        snackbar_theme=ft.SnackBarTheme(
            bgcolor=c["menu"], shape=forma_vidrio(14),
            content_text_style=ft.TextStyle(size=px(14), color=ft.Colors.ON_SURFACE),
        ),
        divider_theme=ft.DividerTheme(color=c["borde"], thickness=1),
        navigation_rail_theme=ft.NavigationRailTheme(bgcolor=ft.Colors.TRANSPARENT, indicator_color=c["campo"]),
    )


# Opciones de todos los ft.TextField y ft.Dropdown: el campo es un vidrio más
# claro, sin borde, y se marca con el color de la tienda al escribir en él
CAMPO_HUNDIDO = dict(
    filled=True, fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=14,
    border_color=ft.Colors.TRANSPARENT, focused_border_color=COLOR_MARCA,
)


def vidrio(radio=22):
    """Opciones de ft.Container para un recuadro de vidrio esmerilado."""
    return dict(
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST, border_radius=radio, blur=ft.Blur(24, 24),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        shadow=ft.BoxShadow(blur_radius=30, offset=ft.Offset(0, 10), color=ft.Colors.SHADOW),
    )


def fondo_de_color():
    """El degradado con manchas de luz que se ve detrás del vidrio. Va al fondo de un ft.Stack."""
    def mancha(color, tamano, **posicion):
        return ft.Container(
            width=tamano, height=tamano, shape=ft.BoxShape.CIRCLE, **posicion,
            gradient=ft.RadialGradient(colors=[ft.Colors.with_opacity(0.75, color),
                                               ft.Colors.with_opacity(0.0, color)]),
        )

    return ft.Stack(
        left=0, top=0, right=0, bottom=0,
        controls=[
            ft.Container(
                left=0, top=0, right=0, bottom=0,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[ft.Colors.PRIMARY_FIXED, ft.Colors.SECONDARY_FIXED, ft.Colors.TERTIARY_FIXED],
                ),
            ),
            mancha(ft.Colors.PRIMARY_FIXED_DIM, 760, left=-180, top=-220),
            mancha(ft.Colors.SECONDARY_FIXED_DIM, 680, right=-160, top=120),
            mancha(ft.Colors.TERTIARY_FIXED_DIM, 620, left=360, bottom=-260),
        ],
    )


# --- AVISOS Y PREGUNTAS ---

def hay_dialogo_abierto(page):
    """True si hay una ventana (diálogo) abierta; los avisos cortos de abajo no cuentan."""
    # Flet no ofrece esto de forma pública: se revisa su lista interna de diálogos
    dialogos = getattr(getattr(page, "_dialogs", None), "controls", [])
    return any(d.open and not isinstance(d, ft.SnackBar) for d in dialogos)


def avisar(page, mensaje, error=False):
    """Aviso corto en la parte de abajo que se quita solo."""
    page.show_dialog(ft.SnackBar(
        ft.Text(mensaje, color=ft.Colors.WHITE if error else None),
        bgcolor=ft.Colors.RED_700 if error else None,
        behavior=ft.SnackBarBehavior.FLOATING,
        width=px(520),
    ))


def mostrar_mensaje(page, titulo, mensaje, error=False):
    """Mensaje que se cierra con un botón, para cosas que el usuario debe leer."""
    page.show_dialog(ft.AlertDialog(
        icon=ft.Icon(
            ft.Icons.ERROR_OUTLINE if error else ft.Icons.INFO_OUTLINE,
            color=COLOR_PELIGRO if error else COLOR_MARCA,
        ),
        title=ft.Text(titulo),
        content=ft.Text(mensaje, width=px(420)),
        actions=[ft.FilledButton("Entendido", on_click=lambda _: page.pop_dialog())],
    ))


async def preguntar(page, titulo, mensaje, si="Sí", no="Cancelar", peligro=False):
    """Pregunta de sí o no. Espera la respuesta y retorna True o False."""
    respuesta = asyncio.get_running_loop().create_future()

    def responder(valor):
        if not respuesta.done():
            respuesta.set_result(valor)
            page.pop_dialog()

    estilo = ft.ButtonStyle(bgcolor=COLOR_PELIGRO, color=ft.Colors.WHITE) if peligro else None
    page.show_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text(titulo),
        content=ft.Text(mensaje, width=px(420)),
        actions=[
            ft.TextButton(no, on_click=lambda _: responder(False)),
            ft.FilledButton(si, style=estilo, on_click=lambda _: responder(True)),
        ],
        on_dismiss=lambda _: respuesta.done() or respuesta.set_result(False),
    ))
    return await respuesta


def mostrar_error_bd(page, error):
    """Aviso claro cuando falla el acceso a la base de datos."""
    mostrar_mensaje(
        page, "Error de Base de Datos", f"Ocurrió un problema al acceder a la base de datos:\n{error}", error=True
    )


def manejar_errores_bd(func):
    """Evita que un error inesperado de la base de datos deje la pantalla a
    medias sin explicación: muestra un aviso claro en su lugar. Sirve para
    métodos normales y para métodos async de las vistas (que tienen self.page)."""
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def envoltorio_async(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except ERRORES_BD as error:
                mostrar_error_bd(self.page, error)
        return envoltorio_async

    @wraps(func)
    def envoltorio(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ERRORES_BD as error:
            mostrar_error_bd(self.page, error)
    return envoltorio


# --- PIEZAS VISUALES ---

def panel(contenido, **opciones):
    """Recuadro de vidrio esmerilado."""
    return ft.Container(
        content=contenido, padding=opciones.pop("padding", 20), **vidrio(), **opciones,
    )


def encabezado(titulo, subtitulo, *acciones):
    """Título grande de cada pantalla, con botones opcionales a la derecha."""
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=0,
                controls=[
                    ft.Text(titulo, size=px(28), weight=ft.FontWeight.BOLD),
                    ft.Text(subtitulo, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
            ft.Row(list(acciones), spacing=8),
        ],
    )


def tarjeta_resumen(icono, titulo, color):
    """Tarjeta con un ícono y un número. Retorna (tarjeta, texto_del_valor) para poder actualizarla."""
    # Con letra grande puede no caber todo: el texto termina en "…" en vez de cortarse
    valor = ft.Text("—", size=px(22), weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    tarjeta = panel(
        ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    content=ft.Icon(icono, color=color, size=px(24)),
                    bgcolor=ft.Colors.with_opacity(0.15, color), border_radius=14, padding=10,
                ),
                ft.Column(
                    [ft.Text(titulo, size=px(13), color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1,
                             overflow=ft.TextOverflow.ELLIPSIS), valor],
                    spacing=0, expand=True,
                ),
            ],
        ),
        padding=16, expand=True,
    )
    return tarjeta, valor


def etiqueta(texto, color):
    """Pastilla de color suave con texto (ej: el stock o el estado de una venta)."""
    return ft.Container(
        content=ft.Text(texto, size=px(13), weight=ft.FontWeight.W_600, color=color),
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
    )


def crear_tabla(columnas, **opciones):
    """
    Tabla con el estilo de la aplicación. 'columnas' es una lista de
    (título, es_numerica). Las filas se asignan después en tabla.rows.
    """
    return ft.DataTable(
        heading_row_height=px(44),
        data_row_min_height=px(46),
        data_row_max_height=px(46),
        column_spacing=24,
        horizontal_lines=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        heading_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT, size=px(13)),
        columns=[ft.DataColumn(ft.Text(titulo), numeric=numerica) for titulo, numerica in columnas],
        **opciones,
    )


def con_desplazamiento(tabla):
    """Envuelve una tabla para que se pueda desplazar si tiene muchas filas."""
    return ft.Column([ft.Row([tabla], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, expand=True)


# Las tablas largas muestran esta cantidad de filas y un botón para ver más. Cada
# fila le cuesta a la pantalla: con cientos de filas de una vez, la tienda tarda
# segundos en mostrarlas
FILAS_POR_TANDA = 100


class PieMostrarMas:
    """
    Aviso "Se muestran X de Y" con el botón "Mostrar más", para debajo de una
    tabla larga. 'al_pulsar' agrega la siguiente tanda de filas a la tabla.
    """

    def __init__(self, al_pulsar):
        self.texto = ft.Text("", size=px(13), color=ft.Colors.ON_SURFACE_VARIANT)
        self.boton = ft.TextButton(f"Mostrar {FILAS_POR_TANDA} más", icon=ft.Icons.EXPAND_MORE,
                                   on_click=lambda _: al_pulsar())
        self.control = ft.Row([self.texto, self.boton], spacing=8, wrap=True, visible=False,
                              vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def actualizar(self, mostradas, total, que="filas", nota=""):
        """Muestra el pie solo si quedan filas sin mostrar."""
        self.control.visible = total > mostradas
        self.texto.value = f"Se muestran {formatear_numero(mostradas)} de {formatear_numero(total)} {que}.{nota}"


def texto_vacio(icono, mensaje):
    """
    Ícono grande y texto gris para cuando una lista o tabla no tiene nada. Va
    dentro de un ft.Stack, encima de la lista: left/top/right/bottom en 0 le
    hacen ocupar todo el recuadro, para quedar centrado (si no, queda del
    tamaño del texto y pegado a la izquierda).
    """
    return ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        left=0, top=0, right=0, bottom=0,
        controls=[
            ft.Icon(icono, size=px(48), color=ft.Colors.OUTLINE),
            ft.Text(mensaje, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
        ],
    )
