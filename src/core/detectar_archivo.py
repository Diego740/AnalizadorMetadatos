import magic
import sys
import os
from pathlib import Path
from utils import archivo_existe

# Diccionario global de extensiones a MIME types
EXTENSIONES_MIME = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
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
    '.css': 'text/css',
    '.rtf': 'text/rtf'
}

def detectar_tipo_archivo(ruta_archivo):
    """
    Detecta el tipo de archivo
    
    Args:
        ruta_archivo (str): Ruta completa al archivo a analizar
        
    Returns:
        (list or None): Array con las respuestas del análisis del documento 
                     o None si el archivo no existe
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        Exception: Para otros errores durante el análisis
    """
    if not archivo_existe(ruta_archivo):
        print(f"El archivo '{ruta_archivo}' no existe.")
        return
    
    try:
        # Crea un objeto Magic para obtener la descripción del archivo
        ms = magic.Magic(mime=False)  # mime=False devuelve una descripción legible (por ejemplo, "JPEG image data")
        descripcion = ms.from_file(ruta_archivo)

        # Crea otro objeto Magic para obtener el tipo MIME
        ms_mime = magic.Magic(mime=True)
        mime_type = ms_mime.from_file(ruta_archivo)
        
        res = [f"Archivo: {ruta_archivo}", f"Descripción: {descripcion}", f"Tipo MIME: {mime_type}"]
        '''
        print(f"Archivo: {ruta_archivo}")
        print(f"Descripción: {descripcion}")
        print(f"Tipo MIME: {mime_type}")
        '''

        return(res)
        

    except Exception as e:
        print(f"Error al analizar el archivo: {e}")


def coincidencia_extensiones(ruta_archivo):
    """
    Comprueba si las extensiones del archivo se corresponden con la extesion detectada
    
    Args:
        ruta_archivo (str): Ruta completa al archivo a analizar
        
    Returns:
        bool : Resultado de la comparación entre la extensión teorica y el archivo real
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        Exception: Para otros errores durante el análisis
    """
    try:
         # Obtener información del archivo
        path = Path(ruta_archivo)
        extension = path.suffix.lower()  # Extensión en minúsculas
        
        ms_mime = magic.Magic(mime=True)
        mime_type = ms_mime.from_file(ruta_archivo)
        
        
        # Verificar coincidencia
        mime_esperado = EXTENSIONES_MIME.get(extension, "desconocido")
        
        return mime_esperado == mime_type

    except Exception as e:
        print(f"Error al analizar el archivo: {e}")
        return None



    



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python detectar_tipo_archivo.py <ruta_del_archivo>")
    else:
        
        
        ruta = sys.argv[1]
        if archivo_existe(ruta):
            res = detectar_tipo_archivo(ruta)
            for i in res:
                print(i)

            print(coincidencia_extensiones(ruta))
        else:
            print("Archivo no encontrado")
