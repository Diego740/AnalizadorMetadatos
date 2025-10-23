import os

def archivo_existe(ruta_archivo):
    """Verifica si el archivo existe."""
    return os.path.isfile(ruta_archivo)
