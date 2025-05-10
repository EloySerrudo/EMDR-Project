import sqlite3
import os

# Usar ruta relativa para mayor portabilidad
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Consultar todas las tablas en la base de datos
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("==== ESTRUCTURA DE LA BASE DE DATOS ====\n")

# Para cada tabla, obtener y mostrar su estructura
for table in tables:
    table_name = table[0]
    print(f"\n📋 TABLA: {table_name}")
    print("-" * 50)
    
    # Obtener información sobre las columnas de la tabla
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    # Mostrar encabezados de columnas
    print(f"{'ID':3} | {'NOMBRE':<15} | {'TIPO':<10} | {'NOT NULL':<8} | {'DEFAULT':<15} | {'PK'}")
    print("-" * 70)
    
    # Mostrar cada columna con sus propiedades
    for col in columns:
        col_id = col[0]
        col_name = col[1]
        col_type = col[2]
        not_null = "Sí" if col[3] == 1 else "No"
        default_val = col[4] if col[4] is not None else "NULL"
        primary_key = "Sí" if col[5] == 1 else "No"
        
        print(f"{col_id:<3} | {col_name:<15} | {col_type:<10} | {not_null:<8} | {default_val:<15} | {primary_key}")
    
    # Obtener información sobre restricciones de clave foránea
    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
    foreign_keys = cursor.fetchall()
    
    if foreign_keys:
        print("\n🔗 CLAVES FORÁNEAS:")
        print(f"{'COLUMNA':<15} | {'TABLA REFERENCIADA':<20} | {'COLUMNA REFERENCIADA':<20}")
        print("-" * 60)
        for fk in foreign_keys:
            from_col = fk[3]
            to_table = fk[2]
            to_col = fk[4]
            print(f"{from_col:<15} | {to_table:<20} | {to_col:<20}")

print("\n==== FIN DEL REPORTE ====")
conn.close()