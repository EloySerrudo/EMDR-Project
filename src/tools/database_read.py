import sqlite3
import pickle
import numpy as np
import pandas as pd
import zlib  # Añadir zlib para descompresión
from pathlib import Path

def read_session_data(db_path='../database/database.db'):
    """
    Lee los datos de la tabla sesiones y extrae los datos BLOB
    
    Returns:
        dict: Diccionario con los datos extraídos
    """
    # Construir la ruta completa a la base de datos
    current_dir = Path(__file__).parent
    db_full_path = current_dir / db_path
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_full_path)
        
        # Query para obtener los datos de las sesiones
        query = """
        SELECT 
            id,
            id_paciente,
            fecha,
            datos_eog,
            datos_ppg,
            datos_bpm,
            notas
        FROM sesiones
        ORDER BY fecha DESC
        """
        
        # Ejecutar query y obtener resultados
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Procesar los datos
        session_data = {
            'session_ids': [],
            'patient_ids': [],
            'fechas': [],
            'datos_eog': [],
            'datos_ppg': [],
            'datos_bpm': [],  # Corregir nombre de variable
            'notas': []
        }
        
        for row in rows:
            session_id, patient_id, fecha, eog_blob, ppg_blob, bpm_blob, notas = row
            
            session_data['session_ids'].append(session_id)
            session_data['patient_ids'].append(patient_id)
            session_data['fechas'].append(fecha)
            session_data['notas'].append(notas)
            
            # Deserializar los datos BLOB (están comprimidos con zlib y serializados con pickle)
            try:
                # EOG data
                if eog_blob:
                    eog_decompressed = zlib.decompress(eog_blob)
                    eog_data = pickle.loads(eog_decompressed)
                else:
                    eog_data = None
                
                # PPG data
                if ppg_blob:
                    ppg_decompressed = zlib.decompress(ppg_blob)
                    ppg_data = pickle.loads(ppg_decompressed)
                else:
                    ppg_data = None
                
                # BPM data
                if bpm_blob:  # Corregir nombre de variable
                    bpm_decompressed = zlib.decompress(bpm_blob)
                    bpm_data = pickle.loads(bpm_decompressed)
                else:
                    bpm_data = None
                
                session_data['datos_eog'].append(eog_data)
                session_data['datos_ppg'].append(ppg_data)
                session_data['datos_bpm'].append(bpm_data)  # Corregir nombre de variable
                
            except Exception as e:
                print(f"Error deserializando datos de sesión {session_id}: {e}")
                session_data['datos_eog'].append(None)
                session_data['datos_ppg'].append(None)
                session_data['datos_bpm'].append(None)  # Corregir nombre de variable
        
        conn.close()
        
        print(f"Se leyeron {len(rows)} sesiones de la base de datos")
        return session_data
        
    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
        return None
    except Exception as e:
        print(f"Error general: {e}")
        return None

def get_session_by_id(session_id, db_path='../database/database.db'):
    """
    Obtiene los datos de una sesión específica por ID
    
    Args:
        session_id (int): ID de la sesión
        
    Returns:
        dict: Datos de la sesión específica
    """
    current_dir = Path(__file__).parent
    db_full_path = current_dir / db_path
    
    try:
        conn = sqlite3.connect(db_full_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            id,
            id_paciente,
            fecha,
            datos_eog,
            datos_ppg,
            datos_bpm,
            notas
        FROM sesiones 
        WHERE id = ?
        """
        
        cursor.execute(query, (session_id,))
        row = cursor.fetchone()
        
        if row:
            session_id, patient_id, fecha, eog_blob, ppg_blob, bpm_blob, notas = row
            
            # Deserializar datos BLOB con descompresión
            try:
                eog_data = None
                if eog_blob:
                    eog_decompressed = zlib.decompress(eog_blob)
                    eog_data = pickle.loads(eog_decompressed)
                
                ppg_data = None
                if ppg_blob:
                    ppg_decompressed = zlib.decompress(ppg_blob)
                    ppg_data = pickle.loads(ppg_decompressed)
                
                bpm_data = None
                if bpm_blob:  # Corregir nombre de variable
                    bpm_decompressed = zlib.decompress(bpm_blob)
                    bpm_data = pickle.loads(bpm_decompressed)
                
            except Exception as e:
                print(f"Error deserializando datos: {e}")
                eog_data = ppg_data = bpm_data = None
            
            return {
                'session_id': session_id,
                'patient_id': patient_id,
                'fecha': fecha,
                'datos_eog': eog_data,
                'datos_ppg': ppg_data,
                'datos_bpm': bpm_data,  # Corregir nombre de variable
                'notas': notas
            }
        else:
            print(f"No se encontró sesión con ID {session_id}")
            return None
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        return None

# Ejemplo de uso para Jupyter Notebook
if __name__ == "__main__":
    # Leer todos los datos
    data = read_session_data()
    
    if data:
        print("Datos cargados exitosamente:")
        print(f"Número de sesiones: {len(data['session_ids'])}")
        
        # Ejemplo: mostrar información de la primera sesión
        if len(data['session_ids']) > 0:
            print(f"\nPrimera sesión:")
            print(f"ID: {data['session_ids'][0]}")
            print(f"Paciente ID: {data['patient_ids'][0]}")
            print(f"Fecha: {data['fechas'][0]}")
            print(f"EOG data shape: {np.array(data['datos_eog'][0]).shape if data['datos_eog'][0] is not None else 'None'}")
            print(f"PPG data shape: {np.array(data['datos_ppg'][0]).shape if data['datos_ppg'][0] is not None else 'None'}")
            print(f"BPM data shape: {np.array(data['datos_bpm'][0]).shape if data['datos_bpm'][0] is not None else 'None'}")  # Corregir nombre