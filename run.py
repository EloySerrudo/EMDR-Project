"""
Script principal para ejecutar la aplicación EMDR Project.
Este archivo debe ejecutarse desde la raíz del proyecto.

Uso:
    python run.py

El script configura automáticamente el path de Python para que todos los 
módulos del proyecto sean accesibles correctamente.
"""
import sys
import os

# Agregar el directorio src al path de Python
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Importar y ejecutar la aplicación
from main import main

if __name__ == "__main__":
    main()
