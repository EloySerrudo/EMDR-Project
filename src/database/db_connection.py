import sqlite3
import os
import sys
from pathlib import Path

def get_database_path():
    """Obtiene la ruta correcta de la base de datos según el entorno"""
    
    if getattr(sys, 'frozen', False):
        # Ejecutable empaquetado con PyInstaller
        # Los archivos están en sys._MEIPASS (carpeta temporal)
        base_path = Path(sys._MEIPASS)
        db_path = base_path / 'database' / 'database.db'
        
        # Para base de datos compartida, copiar a una ubicación accesible
        # si no existe ya en el directorio del ejecutable
        exe_dir = Path(sys.executable).parent
        shared_db_path = exe_dir / 'database.db'
        
        # Si no existe la DB compartida, copiarla desde los recursos
        if not shared_db_path.exists() and db_path.exists():
            import shutil
            shutil.copy2(db_path, shared_db_path)
            print(f"✅ Base de datos copiada a: {shared_db_path}")
        
        return str(shared_db_path)
    else:
        # Desarrollo normal
        base_path = Path(__file__).parent
        db_path = base_path / 'database.db'
        return str(db_path)

# Actualizar las variables globales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = get_database_path()

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_schema_path():
    """Obtiene la ruta correcta del schema según el entorno"""
    
    if getattr(sys, 'frozen', False):
        # Ejecutable empaquetado
        base_path = Path(sys._MEIPASS)
        schema_path = base_path / 'database' / 'schema.sql'
    else:
        # Desarrollo normal
        base_path = Path(__file__).parent
        schema_path = base_path / 'schema.sql'
    
    return str(schema_path)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Lee y ejecuta el archivo SQL
    schema_path = get_schema_path()
    
    if not os.path.exists(schema_path):
        print(f"❌ Schema no encontrado en: {schema_path}")
        return False
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("✅ Base de datos inicializada exitosamente.")
        print(f"📁 Ubicación: {DB_PATH}")
        return True
    except sqlite3.Error as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()