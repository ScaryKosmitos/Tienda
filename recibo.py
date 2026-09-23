"""
Arma el recibo de una venta: como texto (para mostrarlo en pantalla) y como
página HTML (para abrirla en el navegador, imprimirla o guardarla como PDF).
"""
import html
import os
import textwrap

import base_datos as db
from formato import formatear_numero, formatear_precio

# Encabezado y pie del recibo: cámbialos aquí para personalizarlo
NOMBRE_TIENDA = "Mi Tienda"
MENSAJE_FINAL = "¡Gracias por su compra!"

# Ancho del recibo en caracteres (parecido al de una impresora de recibos)
ANCHO = 40


def numero_recibo(id_recibo):
    """7 -> '000007'."""
    return f"{id_recibo:06d}"


def _fila(izquierda, derecha):
    """Texto a la izquierda y a la derecha, separados por espacios hasta completar el ancho."""
    espacios = max(1, ANCHO - len(izquierda) - len(derecha))
    return izquierda + " " * espacios + derecha


def texto_recibo(recibo):
    """Recibo como texto de ancho fijo. 'recibo' es lo que retorna db.obtener_recibo()."""
    separador = "-" * ANCHO
    lineas = [
        NOMBRE_TIENDA.upper().center(ANCHO),
        f"Recibo N° {numero_recibo(recibo['id'])}".center(ANCHO),
        recibo["fecha"][:16].center(ANCHO),
        separador,
    ]

    devuelto = 0.0
    for linea in recibo["lineas"]:
        nombre = linea["nombre_producto"] + (" (ANULADO)" if linea["anulada"] else "")
        lineas.extend(textwrap.wrap(nombre, ANCHO))
        precio_unitario = linea["total"] / linea["cantidad"]
        detalle = f"  {formatear_numero(linea['cantidad'])} x {formatear_precio(precio_unitario)}"
        lineas.append(_fila(detalle, formatear_precio(linea["total"])))
        if linea["anulada"]:
            devuelto += linea["total"]

    lineas += [
        separador,
        _fila("TOTAL", formatear_precio(recibo["total"])),
        _fila("Recibido", formatear_precio(recibo["pago"])),
        _fila("Cambio", formatear_precio(recibo["pago"] - recibo["total"])),
    ]
    if devuelto:
        lineas.append(_fila("Devuelto por anulación", formatear_precio(devuelto)))
    lineas += [separador, "", MENSAJE_FINAL.center(ANCHO)]
    return "\n".join(lineas)


def carpeta_recibos():
    """Carpeta 'recibos' junto a inventario.db."""
    return os.path.join(os.path.dirname(db._ruta_db()), "recibos")


def guardar_html(recibo):
    """
    Guarda el recibo como página HTML en la carpeta 'recibos' y retorna la ruta.
    Al abrirla en el navegador se puede imprimir o guardar como PDF (Ctrl+P).
    """
    numero = numero_recibo(recibo["id"])
    pagina = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Recibo {numero} - {html.escape(NOMBRE_TIENDA)}</title>
<style>
  body {{ background: #eeeeee; margin: 0; padding: 24px; font-family: sans-serif; }}
  .recibo {{
    background: #ffffff; color: #000000; width: fit-content; margin: 0 auto; padding: 16px 20px;
    box-shadow: 0 1px 6px rgba(0, 0, 0, 0.25);
  }}
  pre {{ font-family: "DejaVu Sans Mono", "Consolas", monospace; font-size: 14px; margin: 0; }}
  .ayuda {{ text-align: center; color: #555555; font-size: 14px; margin-top: 16px; }}
  @media print {{
    body {{ background: none; padding: 0; }}
    .recibo {{ box-shadow: none; margin: 0; }}
    .ayuda {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="recibo"><pre>{html.escape(texto_recibo(recibo))}</pre></div>
<p class="ayuda">Pulsa Ctrl+P para imprimir el recibo o guardarlo como PDF.</p>
</body>
</html>
"""
    carpeta = carpeta_recibos()
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"recibo_{numero}.html")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(pagina)
    return ruta
