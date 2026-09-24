"""
Exporta los datos de la tienda a un archivo de Excel (.xlsx) con cuatro hojas:
Ventas (del período elegido), Más vendidos (del mismo período), Inventario y
Fiado (estado actual). Los números se guardan como números, para que en Excel se
puedan sumar, filtrar u ordenar.
"""
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import base_datos as db
from formato import describir_periodo
from recibo import numero_recibo

ESTILO_TITULO = Font(size=14, bold=True)
ESTILO_ENCABEZADO = Font(bold=True, color="FFFFFF")
FONDO_ENCABEZADO = PatternFill("solid", fgColor="1F538D")
ESTILO_TOTAL = Font(bold=True)
ESTILO_ANULADA = Font(color="888888", italic=True)
ESTILO_STOCK_BAJO = Font(color="D32F2F", bold=True)
CENTRADO = Alignment(horizontal="center")
A_LA_DERECHA = Alignment(horizontal="right")

FORMATO_UNIDADES = "#,##0"
FORMATO_FECHA = "yyyy-mm-dd hh:mm"
FORMATO_PORCENTAJE = "0.0%"


def _formato_pesos(valor):
    """Sin decimales si el valor es entero ($1.500), con dos si no ($1.500,50)."""
    return '"$"#,##0' if float(valor).is_integer() else '"$"#,##0.00'


def _escribir(hoja, fila, columna, valor):
    """
    Escribe un dato en una celda. Un texto que empieza con '=' (ej: un producto
    llamado '=Promo 2x1') se guarda como texto: si no, Excel lo tomaría como
    fórmula y diría que el archivo está dañado.
    """
    celda = hoja.cell(row=fila, column=columna, value=valor)
    if isinstance(valor, str) and valor.startswith("="):
        celda.data_type = "s"
    return celda


def _preparar_hoja(hoja, titulo, encabezados):
    """Escribe el título en la fila 1 y los encabezados en la fila 3. Retorna la fila donde empiezan los datos."""
    hoja["A1"] = titulo
    hoja["A1"].font = ESTILO_TITULO
    for columna, texto in enumerate(encabezados, start=1):
        celda = hoja.cell(row=3, column=columna, value=texto)
        celda.font = ESTILO_ENCABEZADO
        celda.fill = FONDO_ENCABEZADO
        celda.alignment = CENTRADO
    # Los encabezados quedan siempre visibles al bajar por la hoja
    hoja.freeze_panes = "A4"
    return 4


def _terminar_hoja(hoja, ultima_fila_datos, cantidad_columnas, anchos, columnas_centradas=()):
    """Agrega los filtros de Excel a los encabezados, ajusta el ancho de las columnas
    y centra las columnas indicadas (ID, puesto, estado)."""
    for columna in columnas_centradas:
        for fila in range(4, ultima_fila_datos + 1):
            hoja.cell(row=fila, column=columna).alignment = CENTRADO
    if ultima_fila_datos >= 4:
        hoja.auto_filter.ref = f"A3:{get_column_letter(cantidad_columnas)}{ultima_fila_datos}"
    for columna, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(columna)].width = ancho


def _fila_total(hoja, fila, columna_valor, texto, valor):
    """Fila de total en negrita. El texto va alineado a la derecha en la celda anterior
    al valor, así se extiende hacia las celdas vacías de la izquierda sin cortarse."""
    etiqueta = hoja.cell(row=fila, column=columna_valor - 1, value=texto)
    etiqueta.font = ESTILO_TOTAL
    etiqueta.alignment = A_LA_DERECHA
    celda = hoja.cell(row=fila, column=columna_valor, value=valor)
    celda.font = ESTILO_TOTAL
    celda.number_format = _formato_pesos(valor)


def _ancho(textos, minimo=10, maximo=45):
    """Ancho de columna aproximado según el texto más largo."""
    return max(minimo, min(maximo, max((len(str(t)) for t in textos), default=0) + 3))


def _hoja_ventas(hoja, desde, hasta, generado):
    ventas = db.obtener_ventas(desde, hasta)
    encabezados = ("ID Venta", "Recibo", "Fecha y Hora", "Producto", "Cantidad", "Total", "Estado", "Fiado a")
    fila = _preparar_hoja(
        hoja, f"Ventas: {describir_periodo(desde, hasta)} (generado {generado})", encabezados
    )

    total_vendido = total_fiado = 0.0
    # obtener_ventas las da de la más reciente a la más antigua; en Excel se
    # leen mejor en orden cronológico
    for venta in reversed(ventas):
        anulada, total = venta["anulada"], venta["total"]
        valores = (
            venta["id"], numero_recibo(venta["recibo_id"]) if venta["recibo_id"] else "—",
            datetime.strptime(venta["fecha"], "%Y-%m-%d %H:%M:%S"), venta["nombre_producto"],
            venta["cantidad"], total, "Anulada" if anulada else ("Fiado" if venta["cliente"] else "OK"),
            venta["cliente"] or "",
        )
        for columna, valor in enumerate(valores, start=1):
            celda = _escribir(hoja, fila, columna, valor)
            if anulada:
                celda.font = ESTILO_ANULADA
        hoja.cell(row=fila, column=3).number_format = FORMATO_FECHA
        hoja.cell(row=fila, column=5).number_format = FORMATO_UNIDADES
        hoja.cell(row=fila, column=6).number_format = _formato_pesos(total)
        if not anulada:
            total_vendido += total
            if venta["cliente"]:
                total_fiado += total
        fila += 1

    _terminar_hoja(hoja, fila - 1, len(encabezados), (
        10, 10, 18, _ancho([v["nombre_producto"] for v in ventas] + ["Producto"]), 11, 14, 10,
        _ancho([v["cliente"] or "" for v in ventas] + ["Fiado a"]),
    ), columnas_centradas=(1, 2, 7))

    _fila_total(hoja, fila + 1, 6, "Total vendido (sin anuladas)", total_vendido)
    if total_fiado:
        _fila_total(hoja, fila + 2, 6, "De eso, fiado", total_fiado)
    return len(ventas)


def _hoja_mas_vendidos(hoja, desde, hasta, generado):
    ranking = db.obtener_mas_vendidos(desde, hasta)
    encabezados = ("#", "Producto", "Unidades Vendidas", "Total", "% de lo Vendido")
    fila = _preparar_hoja(
        hoja, f"Más vendidos: {describir_periodo(desde, hasta)} (generado {generado})", encabezados
    )

    total_general = sum(total for _, _, total in ranking)
    for puesto, (nombre, unidades, total) in enumerate(ranking, start=1):
        porcentaje = total / total_general if total_general else 0
        for columna, valor in enumerate((puesto, nombre, unidades, total, porcentaje), start=1):
            _escribir(hoja, fila, columna, valor)
        hoja.cell(row=fila, column=3).number_format = FORMATO_UNIDADES
        hoja.cell(row=fila, column=4).number_format = _formato_pesos(total)
        hoja.cell(row=fila, column=5).number_format = FORMATO_PORCENTAJE
        fila += 1

    _terminar_hoja(hoja, fila - 1, len(encabezados), (
        6, _ancho([r[0] for r in ranking] + ["Producto"]), 19, 14, 17
    ), columnas_centradas=(1,))


def _hoja_inventario(hoja, generado, stock_bajo):
    productos = db.buscar_productos()
    encabezados = ("ID", "Código", "Nombre", "Categoría", "Precio", "Stock", "Valor en Stock")
    fila = _preparar_hoja(hoja, f"Inventario (generado {generado})", encabezados)

    valor_total = 0.0
    for p in productos:
        precio, stock = p["precio"], p["stock"]
        valor = precio * stock
        valor_total += valor
        # El código va como texto, para que Excel no le quite los ceros iniciales
        datos = (p["id"], p["codigo_barras"] or "", p["nombre"], p["categoria"], precio, stock, valor)
        for columna, dato in enumerate(datos, start=1):
            _escribir(hoja, fila, columna, dato)
        hoja.cell(row=fila, column=2).number_format = "@"
        hoja.cell(row=fila, column=5).number_format = _formato_pesos(precio)
        hoja.cell(row=fila, column=6).number_format = FORMATO_UNIDADES
        hoja.cell(row=fila, column=7).number_format = _formato_pesos(valor)
        if stock < stock_bajo:
            hoja.cell(row=fila, column=6).font = ESTILO_STOCK_BAJO
        fila += 1

    _terminar_hoja(hoja, fila - 1, len(encabezados), (
        7, 16, _ancho([p["nombre"] for p in productos] + ["Nombre"]),
        _ancho([p["categoria"] for p in productos] + ["Categoría"]), 13, 10, 17
    ), columnas_centradas=(1, 2))

    _fila_total(hoja, fila + 1, 7, "Valor total del inventario", valor_total)
    return len(productos)


def _hoja_fiado(hoja, generado):
    clientes = db.obtener_clientes()
    encabezados = ("Cliente", "Debe", "Último Movimiento")
    fila = _preparar_hoja(hoja, f"Fiado (generado {generado})", encabezados)

    total_fiado = 0.0
    for cliente in clientes:
        debe = cliente["debe"]
        _escribir(hoja, fila, 1, cliente["nombre"])
        hoja.cell(row=fila, column=2, value=debe).number_format = _formato_pesos(debe)
        if debe > 0:
            hoja.cell(row=fila, column=2).font = ESTILO_STOCK_BAJO
            total_fiado += debe
        ultimo = cliente["ultimo"]
        celda = hoja.cell(row=fila, column=3, value=datetime.strptime(ultimo, "%Y-%m-%d %H:%M:%S") if ultimo else "—")
        celda.number_format = FORMATO_FECHA
        fila += 1

    _terminar_hoja(hoja, fila - 1, len(encabezados), (
        _ancho([c["nombre"] for c in clientes] + ["Cliente"]), 14, 19,
    ), columnas_centradas=(3,))
    _fila_total(hoja, fila + 1, 2, "Total que deben", total_fiado)


def exportar_excel(ruta, desde=None, hasta=None, stock_bajo=5):
    """
    Crea el archivo .xlsx en 'ruta'. 'desde' y 'hasta' son fechas 'AAAA-MM-DD'
    opcionales para las hojas de ventas. Los productos con menos de
    'stock_bajo' unidades se marcan en rojo en el inventario.
    Retorna (cantidad_de_ventas, cantidad_de_productos).
    """
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")
    libro = Workbook()

    hoja_ventas = libro.active
    hoja_ventas.title = "Ventas"
    cantidad_ventas = _hoja_ventas(hoja_ventas, desde, hasta, generado)
    _hoja_mas_vendidos(libro.create_sheet("Más vendidos"), desde, hasta, generado)
    cantidad_productos = _hoja_inventario(libro.create_sheet("Inventario"), generado, stock_bajo)
    _hoja_fiado(libro.create_sheet("Fiado"), generado)

    libro.save(ruta)
    return cantidad_ventas, cantidad_productos
