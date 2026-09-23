"""
Lectura y presentación de precios en formato colombiano: punto para los
miles y coma para los decimales (ej: $1.500 o $1.500,50).
"""
import re

# 1.500 / 20.000 / 1.250.000  -> punto como separador de miles
_MILES_CON_PUNTO = re.compile(r"\d{1,3}(\.\d{3})+(,\d{1,2})?")
# 1,500 / 20,000              -> coma como separador de miles
_MILES_CON_COMA = re.compile(r"\d{1,3}(,\d{3})+(\.\d{1,2})?")
# 1500 / 1500.5 / 1500,50     -> sin miles, decimales opcionales
_SIN_MILES = re.compile(r"\d+([.,]\d{1,2})?")
# 1500 / 1.500 / -3           -> cantidades enteras (stock, unidades)
_ENTERO = re.compile(r"-?(\d{1,3}(\.\d{3})+|\d+)")


def leer_precio(texto):
    """
    Convierte lo que escribe el usuario en un número. Acepta '$', espacios y
    separadores de miles, para que '1.500' sea mil quinientos y no 1,5.
    Lanza ValueError si el formato es dudoso (ej: '1.5000').
    """
    limpio = texto.replace("$", "").replace(" ", "").strip()

    if _MILES_CON_PUNTO.fullmatch(limpio):
        return float(limpio.replace(".", "").replace(",", "."))
    if _MILES_CON_COMA.fullmatch(limpio):
        return float(limpio.replace(",", ""))
    if _SIN_MILES.fullmatch(limpio):
        return float(limpio.replace(",", "."))
    raise ValueError(f"Precio no válido: {texto!r}")


def leer_entero(texto):
    """
    Convierte una cantidad escrita por el usuario en un entero. Acepta punto
    de miles ('1.500' -> 1500). Lanza ValueError si no es un entero válido.
    """
    limpio = texto.replace(" ", "").strip()
    if not _ENTERO.fullmatch(limpio):
        raise ValueError(f"Cantidad no válida: {texto!r}")
    return int(limpio.replace(".", ""))


def formatear_numero(valor):
    """1500 -> '1.500'; 1500.5 -> '1.500,50' (sin decimales si es entero)."""
    if float(valor).is_integer():
        texto = f"{int(valor):,}"
    else:
        texto = f"{valor:,.2f}"
    # Intercambiar separadores del formato inglés al colombiano
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatear_cambio(valor):
    """Cantidad con signo, para movimientos de stock: 1500 -> '+1.500'; -3 -> '-3'."""
    return ("+" if valor > 0 else "") + formatear_numero(valor)


def formatear_precio(valor):
    """1500 -> '$1.500'."""
    return f"${formatear_numero(valor)}"


def describir_periodo(desde, hasta):
    """Texto de un rango de fechas: '2026-09-01 a 2026-09-23', 'el inicio a 2026-09-23' o 'todo el historial'."""
    if desde or hasta:
        return f"{desde or 'el inicio'} a {hasta or 'hoy'}"
    return "todo el historial"
