# Sistema de Inventario y Punto de Venta

Aplicación de escritorio para administrar una tienda pequeña: registrar productos,
vender con carrito, controlar el stock y consultar reportes de ventas.
Está hecha en Python con una interfaz gráfica en [Flet](https://flet.dev) (basada en Flutter, con modo claro y oscuro)
y guarda los datos en una base de datos SQLite (un solo archivo, sin necesidad de instalar un servidor).

## Funciones

**Inventario**
- Registrar, editar y eliminar productos (nombre, categoría, precio, stock y código de barras opcional).
- No permite productos repetidos ("Jabon" y "Jabón" cuentan como el mismo) ni códigos de barras repetidos.
- Búsqueda por nombre sin importar tildes ni mayúsculas ("jabon" encuentra "Jabón") o por código de barras.
- Filtros por categoría y por stock bajo; los productos con menos de 5 unidades se marcan en rojo.
- Ordenar la tabla haciendo clic en los encabezados (▲ de menor a mayor, ▼ de mayor a menor), en
  orden alfabético español (las tildes no alteran el orden y la ñ va después de la n).
- Entradas de mercancía y registro de todos los movimientos de stock (stock inicial, entradas, ajustes manuales y anulaciones de ventas).

**Ventas**
- Venta híbrida: escaneando con un lector de códigos de barras (cada escaneo suma 1 unidad al
  carrito) o a mano, seleccionando el producto y escribiendo la cantidad (para los que no tienen código).
- Carrito con varios productos por venta. La venta es "todo o nada": si un producto no tiene
  stock suficiente, no se registra ninguno.
- Cálculo del cambio al cobrar, según con cuánto paga el cliente. Botones de billetes ($1.000 a
  $100.000) que se suman al tocarlos, para no tener que escribir el monto. Si el cambio pasaría de
  $1.000.000 no deja cobrar, porque casi seguro se escaneó un código de barras en el campo del pago.
- Recibo de cada venta, con número, productos, total, dinero recibido y cambio. Se puede abrir
  en el navegador para imprimirlo o guardarlo como PDF, y volver a verlo desde el historial.
- Anulación de ventas: las unidades vuelven al stock y la venta queda marcada como anulada (no se borra).

**Fiado**
- Al cobrar, el botón **Fiar** le fía la venta completa a un cliente: se busca por nombre o se crea
  escribiéndolo. El recibo dice a quién se le fió.
- Pantalla **Fiado**: lo que debe cada cliente, el total fiado y los movimientos de cada uno (fiados,
  abonos y ventas anuladas), con acceso a sus recibos.
- Abonos parciales o **Paga todo**. Un abono registrado por error se anula (pide la clave) y la deuda vuelve a subir.
- Si se anula una venta fiada, se le descuenta al cliente de lo que debe.

**Medios de pago y caja**
- Al cobrar se puede pagar en efectivo o con **Pagó por Nequi**, que antes pregunta si ya se revisó en la
  app de Nequi que llegó la plata (para no caer con comprobantes falsos). Los abonos del fiado también
  se registran en efectivo o por Nequi.
- Pantalla **Caja**: la base con la que empieza el día, las salidas de efectivo (pagos a proveedores,
  gastos, retiros, con su motivo) y el resumen para cerrar la caja: base + ventas y abonos en efectivo
  − salidas = **lo que debería haber en la caja**. Aparte muestra lo que entró por Nequi y lo que se fió.
  Se puede ver cualquier día anterior. Anular una salida registrada por error pide la clave.

**Reportes**
- Historial de ventas con filtros de fecha (hoy, esta semana, este mes o un rango).
- Ranking de productos más vendidos del período, con el porcentaje de lo vendido.
- Exportación a Excel (.xlsx) con cuatro hojas: ventas (con el medio de pago y lo fiado), más vendidos, inventario
  con su valor en stock y fiado (lo que debe cada cliente).

**Comodidad**
- Tamaño de letra ajustable (Normal, Grande, Muy grande y Enorme) desde el botón **Tamaño de letra** (el ícono de las dos T) de la barra lateral
  o con `Ctrl +` / `Ctrl −` (`Ctrl 0` vuelve a Normal). Se recuerda al volver a abrir la aplicación.
- Modo claro y oscuro.

**Clave para acciones delicadas**
- Con el **candado** de la barra lateral se crea una clave de 4 a 8 números. Desde entonces se pide para
  eliminar productos, cambiar el precio o el stock de un producto y anular ventas. Vender, registrar
  entradas y crear productos nuevos no la piden.
- Después de escribirla bien no se vuelve a pedir durante 5 minutos (**Bloquear ahora** la pide de inmediato).
- Se guarda cifrada en `configuracion.json`. **Si se olvida**: cerrar la tienda, abrir `configuracion.json`
  con el Bloc de notas, borrar la parte `"clave": {...}` (o borrar el archivo entero: además de la clave,
  solo se pierde el tamaño de letra elegido) y volver a abrir la tienda.

**Seguridad de los datos**
- Respaldo automático de la base de datos una vez al día: al abrir la aplicación y, si queda abierta
  de un día para otro, también al día siguiente.
- Respaldo en la nube: con el ícono de la **nube** de la barra lateral se elige la carpeta de Google Drive
  y cada respaldo diario se copia allí. Así los datos no se pierden aunque el computador se dañe.
- Precios y cantidades en formato colombiano: `$1.500`, `$1.500,50`, `1.000 unidades`.
- Validaciones para evitar datos incorrectos (precios en 0 o mayores a $100.000.000, stock negativo
  o mayor a 1.000.000).

## Requisitos

- Python 3 (desarrollado y probado con Python 3.14).
- Las librerías de `requirements.txt`:
  - `flet`: la interfaz gráfica. La primera vez que se abre la aplicación descarga su visor de escritorio.
    En Linux, el diálogo para guardar el reporte de Excel usa `zenity` (viene con GNOME).
  - `openpyxl`: la exportación a Excel. Es opcional; sin ella la aplicación funciona igual,
    solo que el botón de exportar avisa que falta.

Para vender escaneando sirve cualquier lector de códigos de barras USB que funcione como teclado
(los "plug and play" o "USB HID"): no necesita drivers. Sin lector, el código se puede escribir a mano.

## Instalación

### En Windows (computador de la tienda)

1. Instalar Python desde [python.org/downloads](https://www.python.org/downloads/). En la primera
   pantalla del instalador, marcar la casilla **"Add python.exe to PATH"**.
2. Copiar la carpeta de la tienda en una ubicación del usuario, por ejemplo `C:\Users\<usuario>\Tienda`
   (no en `Archivos de programa`, porque ahí Windows no deja guardar la base de datos).
   Se puede descargar desde GitHub con **Code → Download ZIP** y descomprimir.
3. Hacer doble clic en **`instalar_windows.bat`**. Prepara todo (necesita internet la primera vez)
   y crea el ícono **Tienda** en el Escritorio y en el menú Inicio.

Desde ahí la tienda se abre con ese ícono. Si alguna vez no abre, el error queda anotado en
`errores.log`, dentro de la carpeta de la tienda.

Para **actualizar** la tienda a la última versión publicada en GitHub: cerrar la tienda y abrir
**Actualizar Tienda** en el menú Inicio (o doble clic en `actualizar_windows.bat`). Antes de cambiar
nada hace un respaldo de la base de datos, y nunca toca los datos: `inventario.db`, `respaldos`,
`recibos`, `configuracion.json` y `errores.log`. Sin internet, se puede actualizar desde un ZIP
(por ejemplo, en una USB) con `py actualizar.py ruta\del\archivo.zip`.

### En Linux (o para desarrollar)

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
| Agregar un producto | Pulsar **Nuevo producto**, llenar el formulario y pulsar **Guardar**. |
| Editar o eliminar un producto | Hacer clic en su fila de la tabla (o en el lápiz), cambiar los datos y pulsar **Guardar**, o **Eliminar**. |
| Vender escaneando | Con el cursor en **Escanear código de barras** (arriba del carrito), escanear cada producto y luego pulsar **Cobrar venta**. |
| Vender a mano | Pulsar el carrito de la fila del producto y ajustar la cantidad con **−** / **+** o escribiéndola en el carrito; luego **Cobrar venta**. |
| Asignar un código de barras | Abrir el producto, escanear en el campo **Código de barras** y pulsar **Guardar**. Si se escanea al vender un código que no existe, el programa ofrece registrar el producto. |
| Registrar mercancía que llegó | Pulsar la bandeja de la fila del producto, o ir a **Entradas** en la barra lateral y elegirlo. |
| Agrandar o achicar la letra | Pulsar el ícono de las dos **T** en la barra lateral y elegir el tamaño, o usar `Ctrl +` y `Ctrl −`. |
| Imprimir o guardar un recibo | En el recibo que aparece al cobrar, pulsar **Imprimir o guardar PDF** y luego Ctrl+P en el navegador. |
| Ver un recibo anterior | En **Ventas** (barra lateral), pulsar el ícono de recibo de la venta. |
| Anular ventas | En **Ventas**, marcar las casillas de las líneas y pulsar **Anular seleccionadas** (pide la clave si hay una). |
| Fiar una venta | Al cobrar, pulsar **Fiar**, elegir el cliente (o escribir su nombre para crearlo) y confirmar. |
| Registrar un abono | Ir a **Fiado**, elegir el cliente y pulsar **Registrar abono** (o **Paga todo** si paga lo que debe). |
| Cobrar por Nequi | Al cobrar, revisar en la app de Nequi que llegó la plata y pulsar **Pagó por Nequi**. |
| Empezar el día | Ir a **Caja** y pulsar **Registrar base** con el efectivo que hay en la caja. |
| Sacar plata de la caja | Ir a **Caja**, pulsar **Registrar salida** y escribir cuánto y para qué. |
| Cerrar la caja | Ir a **Caja**, contar el efectivo y compararlo con **Debería haber en la caja**. |
| Crear, cambiar o quitar la clave | Pulsar el **candado** de la barra lateral. |
| Ver ventas, ranking o exportar | Ir a **Ventas**, elegir el período (o el calendario) y usar las pestañas o **Exportar a Excel**. |

La tecla **Enter** sirve como atajo para guardar el formulario, confirmar el cobro y registrar una entrada.

## Estructura del proyecto

```
Tienda/
├── main.py              Punto de entrada: prepara la base de datos, hace el respaldo del día y abre la ventana
│
├── interfaz.py          Ventana principal: barra lateral, cambio de pantalla y cierre
├── vista_inventario.py  Pantalla principal: resumen, tabla de productos, formulario y carrito
├── vista_ventas.py      Historial de ventas, más vendidos, anulaciones y exportación
├── vista_fiado.py       Fiado: lo que debe cada cliente, sus movimientos y los abonos
├── vista_caja.py        Caja: base del día, salidas de efectivo y resumen para el cierre
├── vista_entradas.py    Entradas de mercancía y movimientos de stock
├── dialogo_pago.py      Diálogo de cobro con botones de billetes y el cálculo del cambio
├── dialogo_clave.py     Diálogos para pedir la clave y para crearla, cambiarla o quitarla
├── dialogo_recibo.py    Diálogo que muestra el recibo de una venta
├── dialogo_cliente.py   Diálogos del fiado: elegir o crear el cliente, cambiar su nombre y registrar abonos
├── dialogo_respaldo.py  Diálogo del respaldo en la nube: elegir la carpeta de Google Drive y respaldar ahora
├── componentes.py       Piezas compartidas por las pantallas (tablas, tarjetas, avisos, preguntas)
│
├── base_datos.py        Acceso a SQLite: productos, ventas, anulaciones, movimientos de stock y reportes
├── formato.py           Lectura y presentación de precios y cantidades en formato colombiano
├── recibo.py            Armado del recibo (texto y página para imprimir)
├── exportar.py          Generación del reporte de Excel
├── respaldar.py         Copias de seguridad de la base de datos y su copia en la nube
├── configuracion.py     Preferencias guardadas (tamaño de letra, clave y carpeta de la nube) en configuracion.json
├── seguridad.py         Clave cifrada para las acciones delicadas
├── instalar.py          Instalador: entorno de Python, librerías y accesos directos de Windows
├── instalar_windows.bat Doble clic para instalar en Windows (ejecuta instalar.py)
├── actualizar.py        Actualizador: descarga la última versión de GitHub sin tocar los datos
├── actualizar_windows.bat Doble clic para actualizar en Windows (ejecuta actualizar.py)
├── tienda.ico           Ícono de la aplicación
└── requirements.txt     Librerías necesarias
```

El código está separado en dos capas:

- **Interfaz** (`interfaz.py`, `componentes.py` y los archivos `vista_*.py` y `dialogo_*.py`): lo que se ve en pantalla.
- **Datos** (`base_datos.py`, `formato.py`, `recibo.py`, `exportar.py` y `respaldar.py`): guardar, leer y presentar la información.

Las dependencias van en un solo sentido: la interfaz usa la capa de datos, nunca al revés.
Por eso la lógica de datos puede usarse o probarse sin abrir ninguna ventana.

### Base de datos

`inventario.db` tiene cuatro tablas:

- **productos**: id, nombre, categoría, precio, stock y código de barras (opcional, sin repetir).
- **recibos**: uno por venta, con la fecha, el total, el dinero que entregó el cliente y, si la venta
  fue fiada, a qué cliente.
- **ventas**: una línea por producto vendido, con cantidad, total, fecha, si fue anulada y el recibo
  al que pertenece. Guarda también el nombre del producto, para que el historial se entienda aunque
  luego cambie.
- **entradas**: movimientos de stock (stock inicial, entradas de mercancía, ajustes manuales y anulaciones de ventas).
- **clientes**: los clientes a los que se les fía (solo el nombre, sin repetir).
- **fiado**: la cuenta de cada cliente. Lo fiado suma y los abonos y las ventas anuladas restan; lo que
  debe es la suma. Los abonos registrados por error se marcan como anulados, no se borran. Cada abono
  guarda si se pagó en efectivo o por Nequi.
- **caja_base**: la base (efectivo al empezar) de cada día.
- **salidas**: el efectivo que se saca de la caja, con su motivo. Las registradas por error se anulan.

Los recibos guardan además el medio de pago (efectivo o Nequi; vacío en las ventas fiadas).

Un producto que ya tiene ventas no se puede eliminar, para no dejar el historial incompleto.

## Personalizar el recibo

El nombre de la tienda y el mensaje del final del recibo están al principio de `recibo.py`:

```python
NOMBRE_TIENDA = "Mi Tienda"
MENSAJE_FINAL = "¡Gracias por su compra!"
```

Cada recibo que se abre en el navegador queda guardado en la carpeta `recibos/`.

## Respaldos

Cada día, al abrir la aplicación por primera vez (o al cambiar de día si queda abierta), se guarda
una copia de la base de datos en la carpeta `respaldos/`. Se conservan las 30 más recientes y las
más antiguas se borran solas.

### Respaldo en Google Drive

Los respaldos de `respaldos/` están en el mismo computador: si se daña o se lo roban, se pierden
con él. Para tener una copia en internet:

1. Instalar [Google Drive para escritorio](https://www.google.com/drive/download/) e iniciar sesión.
   Crea una unidad nueva (normalmente `G:\Mi unidad`) que se sube sola a internet.
2. En la tienda, tocar el ícono de la **nube** de la barra lateral y luego **Usar Google Drive**
   (o **Elegir carpeta** si no la encuentra sola).

Desde entonces, cada respaldo diario se copia a `Mi unidad\Respaldos Tienda` (se conservan los 30
más recientes). Si Google Drive está cerrado, la tienda avisa y lo vuelve a intentar cada hora. En
la misma ventana se ve la fecha del último respaldo que llegó a la nube y está el botón
**Respaldar ahora**. Funciona igual con OneDrive, Dropbox o una memoria USB: basta con elegir su carpeta.

También se puede crear un respaldo a mano, por ejemplo en una memoria USB:

```bash
python respaldar.py                  # en la carpeta respaldos/
python respaldar.py /ruta/a/la/usb   # en otra carpeta
```

Para restaurar un respaldo: cerrar la aplicación, reemplazar `inventario.db` por la copia
elegida (renombrándola a `inventario.db`) y volver a abrirla.

La base de datos, los respaldos y los recibos no se suben a git (están en `.gitignore`), porque
contienen los datos reales de la tienda.
