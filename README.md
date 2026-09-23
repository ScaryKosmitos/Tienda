# Sistema de Inventario y Punto de Venta

Aplicación de escritorio para administrar una tienda pequeña: registrar productos,
vender con carrito, controlar el stock y consultar reportes de ventas.
Está hecha en Python con una interfaz gráfica en [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
y guarda los datos en una base de datos SQLite (un solo archivo, sin necesidad de instalar un servidor).

## Funciones

**Inventario**
- Registrar, editar y eliminar productos (nombre, categoría, precio, stock y código de barras opcional).
- No permite productos repetidos ("Jabon" y "Jabón" cuentan como el mismo) ni códigos de barras repetidos.
- Búsqueda por nombre sin importar tildes ni mayúsculas ("jabon" encuentra "Jabón") o por código de barras.
- Filtros por categoría y por stock bajo; los productos con menos de 5 unidades se marcan en rojo.
- Ordenar la tabla haciendo clic en los encabezados (▲ de menor a mayor, ▼ de mayor a menor), en
  orden alfabético español (las tildes no alteran el orden y la ñ va después de la n).
- Entradas de mercancía y registro de todos los movimientos de stock (stock inicial, entradas y ajustes manuales).

**Ventas**
- Venta híbrida: escaneando con un lector de códigos de barras (cada escaneo suma 1 unidad al
  carrito) o a mano, seleccionando el producto y escribiendo la cantidad (para los que no tienen código).
- Carrito con varios productos por venta. La venta es "todo o nada": si un producto no tiene
  stock suficiente, no se registra ninguno.
- Cálculo del cambio al cobrar, según con cuánto paga el cliente.
- Recibo de cada venta, con número, productos, total, dinero recibido y cambio. Se puede abrir
  en el navegador para imprimirlo o guardarlo como PDF, y volver a verlo desde el historial.
- Anulación de ventas: las unidades vuelven al stock y la venta queda marcada como anulada (no se borra).

**Reportes**
- Historial de ventas con filtros de fecha (hoy, esta semana, este mes o un rango).
- Ranking de productos más vendidos del período, con el porcentaje de lo vendido.
- Exportación a Excel (.xlsx) con tres hojas: ventas, más vendidos e inventario con su valor en stock.

**Seguridad de los datos**
- Respaldo automático de la base de datos una vez al día, al abrir la aplicación.
- Precios y cantidades en formato colombiano: `$1.500`, `$1.500,50`, `1.000 unidades`.
- Validaciones para evitar datos incorrectos (precios en 0 o mayores a $100.000.000, stock negativo
  o mayor a 1.000.000).

## Requisitos

- Python 3 con Tkinter (desarrollado y probado con Python 3.14 y Tk 8.6).
- Las librerías de `requirements.txt`:
  - `customtkinter`: la interfaz gráfica.
  - `openpyxl`: la exportación a Excel. Es opcional; sin ella la aplicación funciona igual,
    solo que el botón de exportar avisa que falta.

Para vender escaneando sirve cualquier lector de códigos de barras USB que funcione como teclado
(los "plug and play" o "USB HID"): no necesita drivers. Sin lector, el código se puede escribir a mano.

En Windows, Tkinter viene incluido con el instalador de Python. En Linux a veces hay que
instalarlo aparte (por ejemplo, el paquete `tk` en Arch/CachyOS o `python3-tk` en Ubuntu/Debian).

## Instalación

1. Descargar o clonar el proyecto y entrar en la carpeta:

   ```bash
   git clone <url-del-repositorio>
   cd Tienda
   ```

2. Crear un entorno virtual e instalar las librerías:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Uso

Con el entorno virtual activado:

```bash
python main.py
```

La primera vez se crea automáticamente la base de datos `inventario.db`, vacía, junto a los archivos del programa.

### Guía rápida

| Para... | Hacer... |
|---|---|
| Agregar un producto | Llenar el formulario de la izquierda y pulsar **Guardar Producto**. |
| Editar un producto | Hacer clic en él en la tabla, cambiar los datos y pulsar **Actualizar Producto**. |
| Vender escaneando | Con el cursor en **📷 Escanear código de barras** (junto al carrito), escanear cada producto y luego pulsar **💵 Cobrar Venta**. |
| Vender a mano | Seleccionar el producto, escribir la cantidad, pulsar **Agregar al Carrito** y luego **💵 Cobrar Venta**. |
| Asignar un código de barras | Seleccionar el producto, escanear en el campo **Código de barras** del formulario y pulsar **Actualizar Producto**. Si se escanea al vender un código que no existe, el programa ofrece registrar el producto. |
| Registrar mercancía que llegó | Seleccionar el producto y pulsar **📥 Entrada de Mercancía**. |
| Imprimir o guardar un recibo | En el recibo que aparece al cobrar, pulsar **🖨 Abrir para imprimir o guardar** y luego Ctrl+P en el navegador. |
| Ver un recibo anterior | En **📋 Historial de Ventas**, seleccionar la venta y pulsar **🧾 Ver Recibo**. |
| Ver ventas, ranking o exportar | Pulsar **📋 Historial de Ventas**, elegir el período y usar las pestañas o **📊 Exportar a Excel**. |

La tecla **Enter** sirve como atajo para guardar el formulario, agregar al carrito y confirmar el cobro.

## Estructura del proyecto

```
Tienda/
├── main.py              Punto de entrada: prepara la base de datos, hace el respaldo del día y abre la ventana
│
├── interfaz.py          Ventana principal: formulario, tabla de productos y carrito
├── ventana_pago.py      Ventana de cobro con el cálculo del cambio
├── ventana_recibo.py    Ventana que muestra el recibo de una venta
├── ventana_ventas.py    Historial de ventas, más vendidos, anulaciones y exportación
├── ventana_entradas.py  Entradas de mercancía y movimientos de stock
├── componentes.py       Piezas compartidas por las ventanas (tablas, avisos de error)
│
├── base_datos.py        Acceso a SQLite: productos, ventas, anulaciones, movimientos de stock y reportes
├── formato.py           Lectura y presentación de precios y cantidades en formato colombiano
├── recibo.py            Armado del recibo (texto y página para imprimir)
├── exportar.py          Generación del reporte de Excel
├── respaldar.py         Copias de seguridad de la base de datos
└── requirements.txt     Librerías necesarias
```

El código está separado en dos capas:

- **Interfaz** (`interfaz.py` y los archivos `ventana_*.py`): lo que se ve en pantalla.
- **Datos** (`base_datos.py`, `formato.py`, `recibo.py`, `exportar.py` y `respaldar.py`): guardar, leer y presentar la información.

Las dependencias van en un solo sentido: la interfaz usa la capa de datos, nunca al revés.
Por eso la lógica de datos puede usarse o probarse sin abrir ninguna ventana.

### Base de datos

`inventario.db` tiene cuatro tablas:

- **productos**: id, nombre, categoría, precio, stock y código de barras (opcional, sin repetir).
- **recibos**: uno por venta, con la fecha, el total y el dinero que entregó el cliente.
- **ventas**: una línea por producto vendido, con cantidad, total, fecha, si fue anulada y el recibo
  al que pertenece. Guarda también el nombre del producto, para que el historial se entienda aunque
  luego cambie.
- **entradas**: movimientos de stock (stock inicial, entradas de mercancía y ajustes manuales).

Un producto que ya tiene ventas no se puede eliminar, para no dejar el historial incompleto.

## Personalizar el recibo

El nombre de la tienda y el mensaje del final del recibo están al principio de `recibo.py`:

```python
NOMBRE_TIENDA = "Mi Tienda"
MENSAJE_FINAL = "¡Gracias por su compra!"
```

Cada recibo que se abre en el navegador queda guardado en la carpeta `recibos/`.

## Respaldos

Cada día, al abrir la aplicación por primera vez, se guarda una copia de la base de datos en la
carpeta `respaldos/`. Se conservan las 30 más recientes y las más antiguas se borran solas.

También se puede crear un respaldo a mano, por ejemplo en una memoria USB:

```bash
python respaldar.py                  # en la carpeta respaldos/
python respaldar.py /ruta/a/la/usb   # en otra carpeta
```

Para restaurar un respaldo: cerrar la aplicación, reemplazar `inventario.db` por la copia
elegida (renombrándola a `inventario.db`) y volver a abrirla.

La base de datos, los respaldos y los recibos no se suben a git (están en `.gitignore`), porque
contienen los datos reales de la tienda.
