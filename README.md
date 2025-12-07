# AnalizadorMetadatos

Herramienta diseñada para el análisis, extracción, limpieza y modificación de metadatos en diversos tipos de archivos.

## Características

La herramienta permite realizar varias operaciones sobre los metadatos de los archivos soportados:

*   **Análisis de Metadatos:** Extrae y muestra información detallada de los metadatos del archivo.
*   **Verificación de Extensión:** Comprueba si la extensión del archivo coincide con su tipo MIME real y sugiere la extensión correcta en caso de discrepancia.
*   **Limpieza de Metadatos (Wipe):** Elimina los metadatos existentes para limpiar el archivo (útil para privacidad).
*   **Aplicación de Metadatos por Defecto:** Aplica un conjunto predefinido de metadatos.
*   **Metadatos Personalizados:** Permite al usuario definir y aplicar campos de metadatos específicos (clave=valor).

### Formatos Soportados
*   **PDF** (`.pdf`)
*   **Microsoft Word** (`.docx`)
*   **Imágenes** (Formatos soportados por Pillow, ej, `.jpg`, `.png`, `.heic`)

## Requisitos

*   Python 3.x
*   Las dependencias listadas en `requirements.txt`:
    *   `puremagic`
    *   `pillow` (y `pillow-heif`)
    *   `piexif`
    *   `PyPDF2`
    *   `python-docx`

## Instalación

1.  Clona este repositorio o descarga el código fuente.
2.  Instala las dependencias necesarias ejecutando:

```bash
pip install -r requirements.txt
```

## Uso

La herramienta se puede ejecutar en dos modos: Interfaz de Línea de Comandos (CLI) y Interfaz Gráfica de Usuario (GUI).

### Ejecución Básica (CLI)

Ejecuta el script principal sin argumentos para iniciar el menú interactivo en la consola:

```bash
python3 analizadorMetadatos.py
```

Sigue las instrucciones en pantalla para seleccionar la operación deseada e introducir la ruta del archivo.

**Menú Principal:**
1.  Analyze file metadata (Analizar metadatos)
2.  Verify file extension consistency (Verificar extensión)
3.  Wipe all metadata (Eliminar metadatos)
4.  Apply default metadata templates (Aplicar plantilla por defecto)
5.  Set custom metadata fields (Establecer metadatos personalizados)
6.  Exit (Salir)

### Ejecución con Interfaz Gráfica (GUI)

Para lanzar la versión con interfaz gráfica, utiliza la bandera `-g` o `--gui`:

```bash
python3 analizadorMetadatos.py --gui
```

## Estructura del Proyecto

*   `analizadorMetadatos.py`: Punto de entrada de la aplicación.
*   `requirements.txt`: Lista de librerías necesarias.
*   `src/`: Código fuente principal.
    *   `main.py`: Lógica principal y flujo de la aplicación.
    *   `core/`: Módulos para operaciones de metadatos (análisis, modificación, detección).
    *   `gui/`: Implementación de la interfaz gráfica.
    *   `security/`: Módulos de análisis de seguridad.
    *   `utils/`: Utilidades generales.

## Notas
*   Al limpiar o modificar metadatos, la herramienta suele generar un nuevo archivo con el sufijo `_clean` o similar para preservar el archivo original.
