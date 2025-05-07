import sqlite3
import os
import datetime
import hashlib
import secrets
from typing import List, Dict, Tuple, Optional, Union, Any

# Importar la conexión base
from src.database.db_connection import get_connection

# Definir el decorador fuera de la clase
def secure_connection(func):
    """Decorador para asegurar conexiones y manejo de excepciones"""
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = get_connection()
            # Habilitar llaves foráneas
            conn.execute("PRAGMA foreign_keys = ON")
            # Añadir la conexión a los argumentos
            result = func(*args, conn=conn, **kwargs)
            return result
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            print(f"Error en la base de datos: {e}")
            return None
        finally:
            if conn:
                conn.close()
    return wrapper

class DatabaseManager:
    """
    Clase manejadora para operaciones seguras con la base de datos EMDR
    Proporciona métodos para gestionar pacientes, sesiones y terapeutas
    """

    # ===== MÉTODOS PARA PACIENTES =====
    @staticmethod
    @secure_connection
    def get_all_patients(conn=None) -> List[Dict[str, Any]]:
        """Obtiene todos los pacientes de la base de datos"""
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, edad, notas FROM pacientes ORDER BY nombre")
        patients = cursor.fetchall()
        
        return [
            {"id": p[0], "nombre": p[1], "edad": p[2], "notas": p[3]}
            for p in patients
        ]
    
    @staticmethod
    @secure_connection
    def get_patient(patient_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Obtiene un paciente específico por su ID"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, edad, notas FROM pacientes WHERE id = ?", 
            (patient_id,)
        )
        patient = cursor.fetchone()
        
        if not patient:
            return None
            
        return {
            "id": patient[0], 
            "nombre": patient[1],
            "edad": patient[2],
            "notas": patient[3]
        }
    
    @staticmethod
    @secure_connection
    def add_patient(nombre: str, edad: Optional[int] = None, notas: str = "", conn=None) -> int:
        """
        Añade un nuevo paciente a la base de datos
        Retorna: ID del paciente creado
        """
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pacientes (nombre, edad, notas) VALUES (?, ?, ?)",
            (nombre, edad, notas)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    @secure_connection
    def update_patient(
        patient_id: int, 
        nombre: Optional[str] = None, 
        edad: Optional[int] = None, 
        notas: Optional[str] = None,
        conn=None
    ) -> bool:
        """
        Actualiza los datos de un paciente existente
        Retorna: True si la actualización fue exitosa
        """
        # Obtener datos actuales para solo actualizar los campos proporcionados
        current = DatabaseManager.get_patient(patient_id)
        if not current:
            return False
            
        # Usar valores actuales para campos no proporcionados
        nombre = nombre if nombre is not None else current["nombre"]
        edad = edad if edad is not None else current["edad"]
        notas = notas if notas is not None else current["notas"]
        
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pacientes SET nombre = ?, edad = ?, notas = ? WHERE id = ?",
            (nombre, edad, notas, patient_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    @secure_connection
    def delete_patient(patient_id: int, conn=None) -> bool:
        """
        Elimina un paciente de la base de datos
        Retorna: True si la eliminación fue exitosa
        """
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pacientes WHERE id = ?", (patient_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    @secure_connection
    def search_patients(query: str, conn=None) -> List[Dict[str, Any]]:
        """
        Busca pacientes por nombre o notas
        Retorna: Lista de pacientes que coinciden
        """
        cursor = conn.cursor()
        # Usar LIKE para búsqueda parcial case-insensitive
        search_query = f"%{query}%"
        cursor.execute(
            "SELECT id, nombre, edad, notas FROM pacientes " +
            "WHERE nombre LIKE ? OR notas LIKE ? " +
            "ORDER BY nombre",
            (search_query, search_query)
        )
        patients = cursor.fetchall()
        
        return [
            {"id": p[0], "nombre": p[1], "edad": p[2], "notas": p[3]}
            for p in patients
        ]
    
    # ===== MÉTODOS PARA SESIONES =====
    
    @staticmethod
    @secure_connection
    def get_sessions_for_patient(patient_id: int, conn=None) -> List[Dict[str, Any]]:
        """Obtiene todas las sesiones de un paciente específico"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, fecha, notas FROM sesiones " +
            "WHERE id_paciente = ? ORDER BY fecha DESC",
            (patient_id,)
        )
        sessions = cursor.fetchall()
        
        return [
            {
                "id": s[0], 
                "fecha": s[1], 
                "notas": s[2],
                # No incluimos datos de sensores pues son BLOBs que pueden ser grandes
            }
            for s in sessions
        ]
    
    @staticmethod
    @secure_connection
    def get_session(session_id: int, include_data: bool = False, conn=None) -> Optional[Dict[str, Any]]:
        """
        Obtiene una sesión específica
        include_data: Si es True, incluye los datos de EOG y PPG (puede ser pesado)
        """
        cursor = conn.cursor()
        
        if include_data:
            cursor.execute(
                "SELECT id, id_paciente, fecha, datos_eog, datos_ppg, notas " +
                "FROM sesiones WHERE id = ?",
                (session_id,)
            )
            session = cursor.fetchone()
            
            if not session:
                return None
                
            return {
                "id": session[0],
                "id_paciente": session[1],
                "fecha": session[2],
                "datos_eog": session[3],
                "datos_ppg": session[4],
                "notas": session[5]
            }
        else:
            cursor.execute(
                "SELECT id, id_paciente, fecha, notas " +
                "FROM sesiones WHERE id = ?",
                (session_id,)
            )
            session = cursor.fetchone()
            
            if not session:
                return None
                
            return {
                "id": session[0],
                "id_paciente": session[1],
                "fecha": session[2],
                "notas": session[3]
            }
    
    @staticmethod
    @secure_connection
    def add_session(
        id_paciente: int, 
        datos_eog: Optional[bytes] = None,
        datos_ppg: Optional[bytes] = None,
        notas: str = "",
        fecha: Optional[str] = None,
        conn=None
    ) -> int:
        """
        Añade una nueva sesión EMDR para un paciente
        Retorna: ID de la sesión creada
        """
        # Verificar que el paciente existe
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM pacientes WHERE id = ?", (id_paciente,))
        patient = cursor.fetchone()
        
        if not patient:
            raise ValueError(f"El paciente con ID {id_paciente} no existe")
        
        # Si no se proporciona fecha, usar la actual
        if not fecha:
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        cursor.execute(
            "INSERT INTO sesiones (id_paciente, fecha, datos_eog, datos_ppg, notas) " +
            "VALUES (?, ?, ?, ?, ?)",
            (id_paciente, fecha, datos_eog, datos_ppg, notas)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    @secure_connection
    def update_session(
        session_id: int,
        datos_eog: Optional[bytes] = None,
        datos_ppg: Optional[bytes] = None,
        notas: Optional[str] = None,
        conn=None
    ) -> bool:
        """
        Actualiza una sesión existente
        Retorna: True si la actualización fue exitosa
        """
        # Obtener sesión actual para actualizar solo los campos proporcionados
        current = DatabaseManager.get_session(session_id, include_data=True)
        if not current:
            return False
            
        # Solo actualizar campos proporcionados
        datos_eog = datos_eog if datos_eog is not None else current.get("datos_eog")
        datos_ppg = datos_ppg if datos_ppg is not None else current.get("datos_ppg")
        notas = notas if notas is not None else current.get("notas")
        
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sesiones SET datos_eog = ?, datos_ppg = ?, notas = ? " +
            "WHERE id = ?",
            (datos_eog, datos_ppg, notas, session_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    @secure_connection
    def delete_session(session_id: int, conn=None) -> bool:
        """
        Elimina una sesión de la base de datos
        Retorna: True si la eliminación fue exitosa
        """
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sesiones WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # ===== MÉTODOS PARA TERAPEUTAS =====
    
    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Crea un hash seguro para la contraseña usando PBKDF2
        Retorna: (hash, salt)
        """
        if not salt:
            salt = secrets.token_hex(16)
        
        # Usar un algoritmo de hash seguro con 100,000 iteraciones
        key = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            iterations=100000
        )
        hash_value = key.hex()
        
        return hash_value, salt
    
    @staticmethod
    @secure_connection
    def register_therapist(usuario: str, password: str, conn=None) -> bool:
        """
        Registra un nuevo terapeuta con credenciales seguras
        Retorna: True si el registro fue exitoso
        """
        # Verificar si el usuario ya existe
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM terapeutas WHERE usuario = ?", (usuario,))
        if cursor.fetchone():
            return False
            
        # Crear hash seguro de la contraseña
        password_hash, salt = DatabaseManager._hash_password(password)
        
        # Almacenar usuario con hash y salt (almacenados juntos separados por :)
        stored_password = f"{password_hash}:{salt}"
        
        cursor.execute(
            "INSERT INTO terapeutas (usuario, password) VALUES (?, ?)",
            (usuario, stored_password)
        )
        conn.commit()
        return True
    
    @staticmethod
    @secure_connection
    def validate_therapist(usuario: str, password: str, conn=None) -> bool:
        """
        Valida las credenciales de un terapeuta
        Retorna: True si las credenciales son válidas
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM terapeutas WHERE usuario = ?",
            (usuario,)
        )
        stored = cursor.fetchone()
        
        if not stored:
            return False
            
        # Extraer hash y salt
        stored_hash, salt = stored[0].split(':')
        
        # Calcular hash de la contraseña proporcionada con el mismo salt
        hash_value, _ = DatabaseManager._hash_password(password, salt)
        
        # Comparar los hashes
        return hash_value == stored_hash

# Ejemplo de uso
if __name__ == "__main__":
    # Crear un terapeuta de prueba
    if DatabaseManager.register_therapist("admin", "password123"):
        print("✅ Terapeuta registrado exitosamente")
        
        # Verificar credenciales
        if DatabaseManager.validate_therapist("admin", "password123"):
            print("✅ Credenciales válidas")
        else:
            print("❌ Credenciales inválidas")
    
    # Crear un paciente de prueba
    patient_id = DatabaseManager.add_patient(
        nombre="Juan Pérez",
        edad=35,
        notas="Paciente con historial de ansiedad"
    )
    
    if patient_id:
        print(f"✅ Paciente creado con ID: {patient_id}")
        
        # Añadir una sesión para este paciente
        session_id = DatabaseManager.add_session(
            id_paciente=patient_id,
            notas="Primera sesión de evaluación"
        )
        
        if session_id:
            print(f"✅ Sesión creada con ID: {session_id}")
            
            # Mostrar todos los pacientes
            patients = DatabaseManager.get_all_patients()
            print(f"Pacientes en la base de datos: {len(patients)}")
            
            # Mostrar sesiones del paciente
            sessions = DatabaseManager.get_sessions_for_patient(patient_id)
            print(f"Sesiones del paciente: {len(sessions)}")