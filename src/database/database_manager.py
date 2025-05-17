import sqlite3
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
        cursor.execute("""
            SELECT id, apellido_paterno, apellido_materno, nombre, edad, celular, notas 
            FROM pacientes 
            ORDER BY apellido_paterno, apellido_materno, nombre
        """)
        patients = cursor.fetchall()
        
        return [
            {
                "id": p[0], 
                "apellido_paterno": p[1],
                "apellido_materno": p[2],
                "nombre": p[3],
                "edad": p[4], 
                "celular": p[5],
                "notas": p[6]
            }
            for p in patients
        ]
    
    @staticmethod
    @secure_connection
    def get_patient(patient_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Obtiene un paciente específico por su ID"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, apellido_paterno, apellido_materno, nombre, edad, celular, notas 
            FROM pacientes 
            WHERE id = ?
        """, (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            return None
            
        return {
            "id": patient[0],
            "apellido_paterno": patient[1],
            "apellido_materno": patient[2],
            "nombre": patient[3],
            "edad": patient[4],
            "celular": patient[5],
            "notas": patient[6]
        }
    
    @staticmethod
    @secure_connection
    def add_patient(
        apellido_paterno: str,
        apellido_materno: str,
        nombre: str,
        celular: str,
        edad: Optional[int] = None, 
        notas: str = "", 
        conn=None
    ) -> int:
        """
        Añade un nuevo paciente a la base de datos
        Retorna: ID del paciente creado
        """
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pacientes 
               (apellido_paterno, apellido_materno, nombre, edad, celular, notas) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (apellido_paterno, apellido_materno, nombre, edad, celular, notas)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    @secure_connection
    def update_patient(
        patient_id: int,
        apellido_paterno: Optional[str] = None,
        apellido_materno: Optional[str] = None,
        nombre: Optional[str] = None,
        edad: Optional[int] = None,
        celular: Optional[str] = None, 
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
        apellido_paterno = apellido_paterno if apellido_paterno is not None else current["apellido_paterno"]
        apellido_materno = apellido_materno if apellido_materno is not None else current["apellido_materno"]
        nombre = nombre if nombre is not None else current["nombre"]
        edad = edad if edad is not None else current["edad"]
        celular = celular if celular is not None else current["celular"]
        notas = notas if notas is not None else current["notas"]
        
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE pacientes 
               SET apellido_paterno = ?, apellido_materno = ?, nombre = ?, 
                   edad = ?, celular = ?, notas = ? 
               WHERE id = ?""",
            (apellido_paterno, apellido_materno, nombre, edad, celular, notas, patient_id)
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
        Busca pacientes por nombre, apellidos o notas
        Retorna: Lista de pacientes que coinciden
        """
        cursor = conn.cursor()
        # Usar LIKE para búsqueda parcial case-insensitive
        search_query = f"%{query}%"
        cursor.execute(
            """SELECT id, apellido_paterno, apellido_materno, nombre, edad, celular, notas 
               FROM pacientes 
               WHERE nombre LIKE ? OR apellido_paterno LIKE ? OR 
                     apellido_materno LIKE ? OR notas LIKE ? 
               ORDER BY apellido_paterno, apellido_materno, nombre""",
            (search_query, search_query, search_query, search_query)
        )
        patients = cursor.fetchall()
        
        return [
            {
                "id": p[0],
                "apellido_paterno": p[1],
                "apellido_materno": p[2],
                "nombre": p[3],
                "edad": p[4],
                "celular": p[5],
                "notas": p[6]
            }
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
        datos_bpm: Optional[bytes] = None,  # Nuevo parámetro
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
        datos_bpm = datos_bpm if datos_bpm is not None else current.get("datos_bpm")
        notas = notas if notas is not None else current.get("notas")
        
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sesiones SET datos_eog = ?, datos_ppg = ?, datos_bpm = ?, notas = ? " +
            "WHERE id = ?",
            (datos_eog, datos_ppg, datos_bpm, notas, session_id)
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
    
    # ===== MÉTODOS PARA ADMINISTRADORES =====
    
    @staticmethod
    @secure_connection
    def validate_admin_credentials(user: str, password: str, conn=None) -> bool:
        """
        Valida las credenciales de un administrador usando hash seguro
        Retorna: True si las credenciales son válidas
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM administradores WHERE user = ?", 
            (user,)
        )
        stored = cursor.fetchone()
        
        if not stored:
            return False
        
        # Verificar si la contraseña está en formato hash:salt o es un hash simple
        if ':' in stored[0]:
            # Extraer hash y salt
            stored_hash, salt = stored[0].split(':')
            
            # Calcular hash de la contraseña proporcionada con el mismo salt
            hash_value, _ = DatabaseManager._hash_password(password, salt)
            
            # Comparar los hashes
            return hash_value == stored_hash
        else:
            # Para compatibilidad con contraseñas antiguas (hash simple)
            simple_hash = hashlib.sha256(password.encode()).hexdigest()
            return simple_hash == stored[0]
            
    @staticmethod
    @secure_connection
    def add_admin(user: str, password: str, conn=None) -> bool:
        """
        Añade un nuevo administrador con credenciales seguras
        Retorna: True si el registro fue exitoso
        """
        # Crear hash seguro de la contraseña
        password_hash, salt = DatabaseManager._hash_password(password)

        # Almacenar usuario con hash y salt (almacenados juntos separados por :)
        stored_password = f"{password_hash}:{salt}"
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO administradores (user, password) VALUES (?, ?)",
            (user, stored_password)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return new_id
    
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
    def register_therapist(
        user: str, 
        password: str, 
        apellido_paterno: str,
        apellido_materno: str,
        nombre: str,
        conn=None
    ) -> bool:
        """
        Registra un nuevo terapeuta con credenciales seguras
        Retorna: True si el registro fue exitoso
        """
        # Verificar si el usuario ya existe
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM terapeutas WHERE user = ?", (user,))
        if cursor.fetchone():
            return False
            
        # Crear hash seguro de la contraseña
        password_hash, salt = DatabaseManager._hash_password(password)
        
        # Almacenar usuario con hash y salt (almacenados juntos separados por :)
        stored_password = f"{password_hash}:{salt}"
        
        cursor.execute(
            """INSERT INTO terapeutas 
               (user, password, apellido_paterno, apellido_materno, nombre) 
               VALUES (?, ?, ?, ?, ?)""",
            (user, stored_password, apellido_paterno, apellido_materno, nombre)
        )
        conn.commit()
        return True
    
    @staticmethod
    @secure_connection
    def validate_therapist_credentials(user: str, password: str, conn=None) -> bool:
        """
        Valida las credenciales de un terapeuta usando hash seguro
        Retorna: True si las credenciales son válidas
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM terapeutas WHERE user = ?",
            (user,)
        )
        stored = cursor.fetchone()
        
        if not stored:
            return False
        
        # Verificar si la contraseña está en formato hash:salt o es un hash simple
        if ':' in stored[0]:
            # Extraer hash y salt
            stored_hash, salt = stored[0].split(':')
            
            # Calcular hash de la contraseña proporcionada con el mismo salt
            hash_value, _ = DatabaseManager._hash_password(password, salt)
            
            # Comparar los hashes
            return hash_value == stored_hash
        else:
            # Para compatibilidad con contraseñas antiguas (hash simple)
            simple_hash = hashlib.sha256(password.encode()).hexdigest()
            return simple_hash == stored[0]
    
    @staticmethod
    def get_all_therapists():
        """Obtiene todos los terapeutas de la base de datos"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user, apellido_paterno, apellido_materno, nombre 
                FROM terapeutas 
                ORDER BY apellido_paterno, apellido_materno, nombre
            """)
            
            # Convertir resultados a lista de diccionarios
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
                
            conn.close()
            return results
        except Exception as e:
            print(f"Error obteniendo terapeutas: {e}")
            return []

    @staticmethod
    def add_therapist(user, password_hash, apellido_paterno, apellido_materno, nombre):
        """Añade un nuevo terapeuta con hash simple"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO terapeutas (user, password, apellido_paterno, apellido_materno, nombre)
                VALUES (?, ?, ?, ?, ?)
            """, (user, password_hash, apellido_paterno, apellido_materno, nombre))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return new_id
        except Exception as e:
            print(f"Error añadiendo terapeuta: {e}")
            raise e

    @staticmethod
    def update_therapist(id, user, password_hash, apellido_paterno, apellido_materno, nombre):
        """Actualiza los datos de un terapeuta existente"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Si la contraseña está vacía, no la actualizamos
            if password_hash:
                cursor.execute("""
                    UPDATE terapeutas 
                    SET user = ?, password = ?, apellido_paterno = ?, apellido_materno = ?, nombre = ? 
                    WHERE id = ?
                """, (user, password_hash, apellido_paterno, apellido_materno, nombre, id))
            else:
                cursor.execute("""
                    UPDATE terapeutas 
                    SET user = ?, apellido_paterno = ?, apellido_materno = ?, nombre = ? 
                    WHERE id = ?
                """, (user, apellido_paterno, apellido_materno, nombre, id))
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error actualizando terapeuta: {e}")
            raise e

    @staticmethod
    def delete_therapist(id):
        """Elimina un terapeuta de la base de datos"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM terapeutas WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error eliminando terapeuta: {e}")
            raise e

    @staticmethod
    def get_session_data(session_id: int):
        """
        Recupera los datos fisiológicos de una sesión específica
        """
        try:
            import numpy as np
            import pickle
            import zlib
            
            # Obtener la sesión con todos los datos
            session = DatabaseManager.get_session(session_id, include_data=True)
            if not session:
                return None
                
            result = {"session_info": session}
            
            # Descomprimir EOG si existe
            if session.get("datos_eog"):
                try:
                    eog_decompressed = zlib.decompress(session["datos_eog"])
                    eog_data = pickle.loads(eog_decompressed)
                    result["eog_data"] = eog_data
                except:
                    result["eog_data"] = None
                    
            # Descomprimir PPG si existe  
            if session.get("datos_ppg"):
                try:
                    ppg_decompressed = zlib.decompress(session["datos_ppg"])
                    ppg_data = pickle.loads(ppg_decompressed)
                    result["ppg_data"] = ppg_data
                except:
                    result["ppg_data"] = None
                    
            # Descomprimir BPM si existe
            if session.get("datos_bpm"):
                try:
                    bpm_decompressed = zlib.decompress(session["datos_bpm"])
                    bpm_data = pickle.loads(bpm_decompressed)
                    result["bpm_data"] = bpm_data
                except:
                    result["bpm_data"] = None
                
            return result
            
        except Exception as e:
            print(f"Error al recuperar datos de sesión: {e}")
            return None

# Ejemplo de uso modificado para el nuevo esquema
if __name__ == "__main__":
    # Crear un administrador de prueba
    admin_id = DatabaseManager.add_admin("eloysc", "akqjmhil")
    if admin_id:
        print(f"✅ Administrador creado con ID: {admin_id}")
                
        # Verificar credenciales
        if DatabaseManager.validate_admin_credentials("eloysc", "akqjmhil"):
            print("✅ Credenciales válidas")
        else:
            print("❌ Credenciales inválidas")
    
    # Crear un terapeuta de prueba
    if DatabaseManager.register_therapist(
        "dra.valdivia", "password123", "Valdivia", "Belén", "Margarita"
    ):
        print("✅ Terapeuta registrado exitosamente")
        
        # Verificar credenciales
        if DatabaseManager.validate_therapist_credentials("dra.valdivia", "password123"):
            print("✅ Credenciales válidas")
        else:
            print("❌ Credenciales inválidas")
    
    # Crear un paciente de prueba
    patient_id = DatabaseManager.add_patient(
        apellido_paterno="Pérez",
        apellido_materno="González",
        nombre="Juan",
        celular="78551234",
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