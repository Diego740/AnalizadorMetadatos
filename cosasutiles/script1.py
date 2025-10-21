import magic
import sys
import os
from pathlib import Path

# Diccionario global de extensiones a MIME types
EXTENSIONES_MIME = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.txt': 'text/plain',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.zip': 'application/zip',
    '.rar': 'application/x-rar-compressed',
    '.mp3': 'audio/mpeg',
    '.mp4': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.exe': 'application/x-dosexec',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.xml': 'application/xml',
    '.json': 'application/json',
    '.csv': 'text/csv',
    '.py': 'text/x-python',
    '.js': 'application/javascript',
    '.css': 'text/css'
}

def archivo_existe(ruta_archivo):
    """
    Verifica si el archivo existe y es accesible.
    
    Args:
        ruta_archivo (str): Ruta completa al archivo
        
    Returns:
        bool: True si el archivo existe y es legible, False en caso contrario
    """
    return os.path.isfile(ruta_archivo) and os.access(ruta_archivo, os.R_OK)

def obtener_informacion_basica(ruta_archivo):
    """
    Obtiene información básica del archivo (nombre, extensión, tamaño, etc.)
    
    Args:
        ruta_archivo (str): Ruta completa al archivo
        
    Returns:
        dict: Diccionario con información básica del archivo o None si hay error
    """
    try:
        path = Path(ruta_archivo)
        stats = path.stat()
        
        return {
            'nombre': path.name,
            'extension': path.suffix.lower(),
            'tamaño_bytes': stats.st_size,
            'tamaño_formateado': _formatear_tamaño(stats.st_size),
            'ruta_absoluta': str(path.resolve()),
            'fecha_modificacion': stats.st_mtime
        }
    except Exception as e:
        print(f"Error al obtener información del archivo: {e}")
        return None

def _formatear_tamaño(tamaño_bytes):
    """
    Función interna para formatear el tamaño en bytes a formato legible
    
    Args:
        tamaño_bytes (int): Tamaño en bytes
        
    Returns:
        str: Tamaño formateado (KB, MB, GB)
    """
    for unidad in ['B', 'KB', 'MB', 'GB']:
        if tamaño_bytes < 1024.0:
            return f"{tamaño_bytes:.2f} {unidad}"
        tamaño_bytes /= 1024.0
    return f"{tamaño_bytes:.2f} TB"

def detectar_tipo_archivo(ruta_archivo):
    """
    Detecta el tipo de archivo usando la librería magic
    
    Args:
        ruta_archivo (str): Ruta completa al archivo a analizar
        
    Returns:
        dict or None: Diccionario con información del análisis o None si hay error
    """
    if not archivo_existe(ruta_archivo):
        print(f"Error: El archivo '{ruta_archivo}' no existe o no se puede leer.")
        return None
    
    try:
        # Obtener información básica del archivo
        info_archivo = obtener_informacion_basica(ruta_archivo)
        if not info_archivo:
            return None
        
        # Detección con magic
        ms_desc = magic.Magic(mime=False)
        ms_mime = magic.Magic(mime=True)
        
        descripcion = ms_desc.from_file(ruta_archivo)
        mime_type = ms_mime.from_file(ruta_archivo)
        
        # Verificar coincidencia de extensiones
        coincidencia = verificar_coincidencia_extension(ruta_archivo, mime_type)
        
        resultado = {
            **info_archivo,
            'descripcion_magic': descripcion,
            'mime_type': mime_type,
            'coincidencia_extension': coincidencia['coincide'],
            'mime_esperado': coincidencia['mime_esperado'],
            'extension_sospechosa': not coincidencia['coincide']
        }
        
        return resultado
        
    except Exception as e:
        print(f"Error al analizar el archivo: {e}")
        return None

def verificar_coincidencia_extension(ruta_archivo, mime_type_detectado=None):
    """
    Comprueba si la extensión del archivo coincide con su tipo real detectado
    
    Args:
        ruta_archivo (str): Ruta completa al archivo
        mime_type_detectado (str, optional): MIME type detectado. Si es None, se detecta automáticamente
        
    Returns:
        dict: Resultado de la comparación con detalles
    """
    try:
        path = Path(ruta_archivo)
        extension = path.suffix.lower()
        
        # Si no se proporciona el MIME type, detectarlo
        if mime_type_detectado is None:
            ms_mime = magic.Magic(mime=True)
            mime_type_detectado = ms_mime.from_file(ruta_archivo)
        
        mime_esperado = EXTENSIONES_MIME.get(extension, "desconocido")
        
        return {
            'coincide': mime_esperado == mime_type_detectado,
            'extension': extension,
            'mime_real': mime_type_detectado,
            'mime_esperado': mime_esperado,
            'riesgo': _evaluar_riesgo(extension, mime_type_detectado)
        }
        
    except Exception as e:
        print(f"Error al verificar extensiones: {e}")
        return {'coincide': False, 'error': str(e)}

def _evaluar_riesgo(extension, mime_type):
    """
    Evalúa el nivel de riesgo basado en la extensión y MIME type
    
    Args:
        extension (str): Extensión del archivo
        mime_type (str): MIME type detectado
        
    Returns:
        str: Nivel de riesgo ('bajo', 'medio', 'alto')
    """
    # Extensiones comúnmente usadas para malware
    extensiones_riesgo = ['.exe', '.bat', '.cmd', '.ps1', '.vbs', '.scr', '.pif', '.com']
    
    # MIME types de ejecutables
    mime_types_riesgo = [
        'application/x-dosexec',
        'application/x-msdownload',
        'application/x-msdos-program'
    ]
    
    if extension in extensiones_riesgo or mime_type in mime_types_riesgo:
        return 'alto'
    elif extension in ['.zip', '.rar', '.jar'] and 'executable' in mime_type:
        return 'medio'
    else:
        return 'bajo'

def analizar_multiples_archivos(lista_rutas):
    """
    Analiza múltiples archivos de forma batch
    
    Args:
        lista_rutas (list): Lista de rutas de archivos a analizar
        
    Returns:
        list: Lista de resultados de análisis
    """
    resultados = []
    archivos_con_error = []
    
    for ruta in lista_rutas:
        print(f"Analizando: {ruta}")
        resultado = detectar_tipo_archivo(ruta)
        if resultado:
            resultados.append(resultado)
        else:
            archivos_con_error.append(ruta)
    
    return {
        'resultados': resultados,
        'archivos_con_error': archivos_con_error,
        'total_analizados': len(lista_rutas),
        'exitosos': len(resultados),
        'errores': len(archivos_con_error)
    }

def generar_reporte_analisis(resultado):
    """
    Genera un reporte legible del análisis
    
    Args:
        resultado (dict): Resultado del análisis de detectar_tipo_archivo()
        
    Returns:
        str: Reporte formateado
    """
    if not resultado:
        return "No hay datos de análisis disponibles."
    
    reporte = []
    reporte.append("=" * 60)
    reporte.append(f"ANÁLISIS DE ARCHIVO: {resultado['nombre']}")
    reporte.append("=" * 60)
    reporte.append(f"📁 Ruta: {resultado['ruta_absoluta']}")
    reporte.append(f"📊 Tamaño: {resultado['tamaño_formateado']} ({resultado['tamaño_bytes']} bytes)")
    reporte.append(f"🔍 Extensión: {resultado['extension']}")
    reporte.append(f"📝 Descripción: {resultado['descripcion_magic']}")
    reporte.append(f"🎯 Tipo MIME: {resultado['mime_type']}")
    
    # Información de coincidencia
    if resultado['coincidencia_extension']:
        reporte.append("✅ La extensión coincide con el tipo real del archivo")
    else:
        reporte.append("⚠️  ADVERTENCIA: La extensión NO coincide con el tipo real")
        reporte.append(f"   MIME esperado para {resultado['extension']}: {resultado['mime_esperado']}")
        reporte.append(f"   MIME detectado: {resultado['mime_type']}")
    
    # Información de riesgo
    riesgo_info = verificar_coincidencia_extension(resultado['ruta_absoluta'])
    reporte.append(f"🚨 Nivel de riesgo: {riesgo_info['riesgo'].upper()}")
    
    return "\n".join(reporte)

def es_archivo_ejecutable(resultado_analisis):
    """
    Determina si un archivo es potencialmente ejecutable basado en su análisis
    
    Args:
        resultado_analisis (dict): Resultado de detectar_tipo_archivo()
        
    Returns:
        bool: True si es potencialmente ejecutable
    """
    if not resultado_analisis:
        return False
    
    extensiones_ejecutables = {
        '.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', 
        '.scr', '.pif', '.com', '.app', '.dmg', '.deb', '.rpm'
    }
    
    mime_types_ejecutables = {
        'application/x-dosexec',
        'application/x-msdownload',
        'application/x-msdos-program',
        'application/x-executable',
        'application/x-mach-binary'
    }
    
    extension = resultado_analisis.get('extension', '')
    mime_type = resultado_analisis.get('mime_type', '')
    
    return (extension in extensiones_ejecutables or 
            mime_type in mime_types_ejecutables or
            'executable' in resultado_analisis.get('descripcion_magic', '').lower())

# Función principal para uso standalone
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python detector_archivos.py <ruta_del_archivo> [archivo2 ...]")
        print("Ejemplo: python detector_archivos.py documento.pdf imagen.jpg")
        sys.exit(1)
    
    # Analizar uno o múltiples archivos
    if len(sys.argv) == 2:
        # Un solo archivo
        resultado = detectar_tipo_archivo(sys.argv[1])
        if resultado:
            print(generar_reporte_analisis(resultado))
        else:
            print(f"No se pudo analizar el archivo: {sys.argv[1]}")
    else:
        # Múltiples archivos
        resultados = analizar_multiples_archivos(sys.argv[1:])
        
        print(f"\n📊 RESUMEN DEL ANÁLISIS")
        print(f"Total archivos: {resultados['total_analizados']}")
        print(f"Análisis exitosos: {resultados['exitosos']}")
        print(f"Errores: {resultados['errores']}")
        
        for resultado in resultados['resultados']:
            print("\n" + "-" * 40)
            print(generar_reporte_analisis(resultado))
        
        if resultados['archivos_con_error']:
            print(f"\n❌ Archivos con errores:")
            for archivo in resultados['archivos_con_error']:
                print(f"   - {archivo}")