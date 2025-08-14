import sqlite3
from datetime import datetime, date
import hashlib
import secrets
from typing import List, Dict, Tuple, Optional, Union, Any

# Importar la conexión base
from database.db_connection import get_connection

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
    Proporciona métodos para gestionar pacientes, sesiones, terapeutas y diagnósticos
    """

    # ===== MÉTODOS AUXILIARES =====
    @staticmethod
    def calculate_age(birth_date_str):
        """
        Calcula la edad en años a partir de la fecha de nacimiento
        Args:
            birth_date_str: Fecha de nacimiento en formato string (YYYY-MM-DD)
        Returns:
            int: Edad en años
        """
        try:
            # Si birth_date_str es None o vacío
            if not birth_date_str:
                return 0
            
            # Convertir string a objeto date
            if isinstance(birth_date_str, str):
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            elif isinstance(birth_date_str, date):
                birth_date = birth_date_str
            else:
                return 0
            
            # Fecha actual
            today = date.today()
            
            # Calcular edad
            age = today.year - birth_date.year
            
            # Ajustar si aún no ha pasado el cumpleaños este año
            if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                age -= 1
                
            return max(0, age)  # Asegurar que no sea negativo
            
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error calculando edad para fecha {birth_date_str}: {e}")
            return 0

    # ===== MÉTODOS PARA PACIENTES =====
    @staticmethod
    @secure_connection
    def get_all_patients(conn=None) -> List[Dict[str, Any]]:
        """
        Obtiene todos los pacientes de la base de datos orderados por apellidos paterno, materno y nombre
        """
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, fecha_registro, comentarios 
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
                "fecha_nacimiento": p[4], 
                "edad": DatabaseManager.calculate_age(p[4]),  # Calcular edad
                "celular": p[5],
                "fecha_registro": p[6],
                "comentarios": p[7]
            }
            for p in patients
        ]
    
    @staticmethod
    @secure_connection
    def get_patient(patient_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Obtiene un paciente específico por su ID"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, fecha_registro, comentarios 
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
            "fecha_nacimiento": patient[4],
            "edad": DatabaseManager.calculate_age(patient[4]),  # Calcular edad
            "celular": patient[5],
            "fecha_registro": patient[6],
            "comentarios": patient[7]
        }
    
    @staticmethod
    @secure_connection
    def add_patient(
        apellido_paterno: str,
        apellido_materno: str,
        nombre: str,
        fecha_nacimiento: str,
        celular: str,
        fecha_registro: str,
        comentarios: str = "",
        conn=None
    ) -> int:
        """
        Añade un nuevo paciente a la base de datos
        Args:
            apellido_paterno: Apellido paterno del paciente
            apellido_materno: Apellido materno del paciente
            nombre: Nombre(s) del paciente
            fecha_nacimiento: Fecha de nacimiento en formato YYYY-MM-DD
            celular: Número de celular del paciente
            fecha_registro: Fecha de registro en formato YYYY-MM-DD HH:MM:SS
            comentarios: Comentarios adicionales (opcional)
        Returns:
            int: ID del paciente creado
        """
        print("fecha =",fecha_registro)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pacientes 
               (apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, fecha_registro, comentarios) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, fecha_registro, comentarios)
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
        fecha_nacimiento: Optional[str] = None,
        celular: Optional[str] = None, 
        comentarios: Optional[str] = None,
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
        fecha_nacimiento = fecha_nacimiento if fecha_nacimiento is not None else current["fecha_nacimiento"]
        celular = celular if celular is not None else current["celular"]
        comentarios = comentarios if comentarios is not None else current["comentarios"]
        
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE pacientes 
               SET apellido_paterno = ?, apellido_materno = ?, nombre = ?, 
                   fecha_nacimiento = ?, celular = ?, comentarios = ? 
               WHERE id = ?""",
            (apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, comentarios, patient_id)
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
        Busca pacientes por nombre, apellidos o comentarios
        Retorna: Lista de pacientes que coinciden
        """
        cursor = conn.cursor()
        # Usar LIKE para búsqueda parcial case-insensitive
        search_query = f"%{query}%"
        cursor.execute(
            """SELECT id, apellido_paterno, apellido_materno, nombre, fecha_nacimiento, celular, fecha_registro, comentarios 
               FROM pacientes 
               WHERE nombre LIKE ? OR apellido_paterno LIKE ? OR 
                     apellido_materno LIKE ? OR comentarios LIKE ? 
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
                "fecha_nacimiento": p[4],
                "celular": p[5],
                "fecha_registro": p[6],
                "comentarios": p[7]
            }
            for p in patients
        ]
    
    # ===== MÉTODOS PARA DIAGNÓSTICOS =====
    
    @staticmethod
    @secure_connection
    def get_diagnoses_for_patient(patient_id: int, include_resolved: bool = False, conn=None) -> List[Dict[str, Any]]:
        """
        Obtiene todos los diagnósticos de un paciente específico
        include_resolved: Si es True, incluye diagnósticos resueltos
        """
        cursor = conn.cursor()
        
        if include_resolved:
            cursor.execute("""
                SELECT d.id, d.codigo_diagnostico, d.nombre_diagnostico, d.fecha_diagnostico, 
                       d.fecha_resolucion, d.estado, d.id_terapeuta, d.comentarios,
                       t.apellido_paterno, t.apellido_materno, t.nombre as terapeuta_nombre
                FROM diagnosticos d
                LEFT JOIN terapeutas t ON d.id_terapeuta = t.id
                WHERE d.id_paciente = ?
                ORDER BY d.fecha_diagnostico DESC
            """, (patient_id,))
        else:
            cursor.execute("""
                SELECT d.id, d.codigo_diagnostico, d.nombre_diagnostico, d.fecha_diagnostico, 
                       d.fecha_resolucion, d.estado, d.id_terapeuta, d.comentarios,
                       t.apellido_paterno, t.apellido_materno, t.nombre as terapeuta_nombre
                FROM diagnosticos d
                LEFT JOIN terapeutas t ON d.id_terapeuta = t.id
                WHERE d.id_paciente = ? AND d.estado = 'activo'
                ORDER BY d.fecha_diagnostico DESC
            """, (patient_id,))
        
        diagnoses = cursor.fetchall()
        
        return [
            {
                "id": d[0],
                "codigo_diagnostico": d[1],
                "nombre_diagnostico": d[2],
                "fecha_diagnostico": d[3],
                "fecha_resolucion": d[4],
                "estado": d[5],
                "id_terapeuta": d[6],
                "comentarios": d[7],
                "terapeuta_nombre_completo": f"{d[8]} {d[9]} {d[10]}" if d[8] else "No asignado"
            }
            for d in diagnoses
        ]
    
    @staticmethod
    @secure_connection
    def get_diagnosis(diagnosis_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Obtiene un diagnóstico específico por su ID"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.id_paciente, d.codigo_diagnostico, d.nombre_diagnostico, 
                   d.fecha_diagnostico, d.fecha_resolucion, d.estado, d.id_terapeuta, d.comentarios,
                   p.apellido_paterno, p.apellido_materno, p.nombre as paciente_nombre,
                   t.apellido_paterno as terapeuta_ap, t.apellido_materno as terapeuta_am, 
                   t.nombre as terapeuta_nombre
            FROM diagnosticos d
            LEFT JOIN pacientes p ON d.id_paciente = p.id
            LEFT JOIN terapeutas t ON d.id_terapeuta = t.id
            WHERE d.id = ?
        """, (diagnosis_id,))
        
        diagnosis = cursor.fetchone()
        
        if not diagnosis:
            return None
            
        return {
            "id": diagnosis[0],
            "id_paciente": diagnosis[1],
            "codigo_diagnostico": diagnosis[2],
            "nombre_diagnostico": diagnosis[3],
            "fecha_diagnostico": diagnosis[4],
            "fecha_resolucion": diagnosis[5],
            "estado": diagnosis[6],
            "id_terapeuta": diagnosis[7],
            "comentarios": diagnosis[8],
            "paciente_nombre_completo": f"{diagnosis[9]} {diagnosis[10]} {diagnosis[11]}" if diagnosis[9] else "",
            "terapeuta_nombre_completo": f"{diagnosis[12]} {diagnosis[13]} {diagnosis[14]}" if diagnosis[12] else "No asignado"
        }
    
    @staticmethod
    @secure_connection
    def add_diagnosis(
        id_paciente: int,
        codigo_diagnostico: str,
        nombre_diagnostico: str,
        fecha_diagnostico: Optional[str] = None,
        id_terapeuta: Optional[int] = None,
        comentarios: str = "",
        conn=None
    ) -> int:
        """
        Añade un nuevo diagnóstico para un paciente
        Retorna: ID del diagnóstico creado
        """
        # Verificar que el paciente existe
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM pacientes WHERE id = ?", (id_paciente,))
        if not cursor.fetchone():
            raise ValueError(f"El paciente con ID {id_paciente} no existe")
        
        # Verificar que el terapeuta existe (si se proporciona)
        if id_terapeuta:
            cursor.execute("SELECT id FROM terapeutas WHERE id = ?", (id_terapeuta,))
            if not cursor.fetchone():
                raise ValueError(f"El terapeuta con ID {id_terapeuta} no existe")
        
        # Si no se proporciona fecha, usar la actual
        if not fecha_diagnostico:
            fecha_diagnostico = date.today().strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO diagnosticos 
            (id_paciente, codigo_diagnostico, nombre_diagnostico, fecha_diagnostico, id_terapeuta, comentarios)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_paciente, codigo_diagnostico, nombre_diagnostico, fecha_diagnostico, id_terapeuta, comentarios))
        
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    @secure_connection
    def update_diagnosis(
        diagnosis_id: int,
        codigo_diagnostico: Optional[str] = None,
        nombre_diagnostico: Optional[str] = None,
        fecha_diagnostico: Optional[str] = None,
        fecha_resolucion: Optional[str] = None,
        estado: Optional[str] = None,
        id_terapeuta: Optional[int] = None,
        comentarios: Optional[str] = None,
        conn=None
    ) -> bool:
        """
        Actualiza un diagnóstico existente
        Retorna: True si la actualización fue exitosa
        """
        # Obtener diagnóstico actual
        current = DatabaseManager.get_diagnosis(diagnosis_id)
        if not current:
            return False
        
        # Usar valores actuales para campos no proporcionados
        codigo_diagnostico = codigo_diagnostico if codigo_diagnostico is not None else current["codigo_diagnostico"]
        nombre_diagnostico = nombre_diagnostico if nombre_diagnostico is not None else current["nombre_diagnostico"]
        fecha_diagnostico = fecha_diagnostico if fecha_diagnostico is not None else current["fecha_diagnostico"]
        fecha_resolucion = fecha_resolucion if fecha_resolucion is not None else current["fecha_resolucion"]
        estado = estado if estado is not None else current["estado"]
        id_terapeuta = id_terapeuta if id_terapeuta is not None else current["id_terapeuta"]
        comentarios = comentarios if comentarios is not None else current["comentarios"]
        
        # Verificar que el terapeuta existe (si se proporciona)
        if id_terapeuta:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM terapeutas WHERE id = ?", (id_terapeuta,))
            if not cursor.fetchone():
                raise ValueError(f"El terapeuta con ID {id_terapeuta} no existe")
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE diagnosticos 
            SET codigo_diagnostico = ?, nombre_diagnostico = ?, fecha_diagnostico = ?,
                fecha_resolucion = ?, estado = ?, id_terapeuta = ?, comentarios = ?
            WHERE id = ?
        """, (codigo_diagnostico, nombre_diagnostico, fecha_diagnostico, fecha_resolucion, 
              estado, id_terapeuta, comentarios, diagnosis_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    @secure_connection
    def resolve_diagnosis(
        diagnosis_id: int,
        fecha_resolucion: Optional[str] = None,
        estado: str = "resuelto",
        conn=None
    ) -> bool:
        """
        Marca un diagnóstico como resuelto
        Retorna: True si la operación fue exitosa
        """
        if not fecha_resolucion:
            fecha_resolucion = date.today().strftime("%Y-%m-%d")
        
        return DatabaseManager.update_diagnosis(
            diagnosis_id=diagnosis_id,
            fecha_resolucion=fecha_resolucion,
            estado=estado
        )
    
    @staticmethod
    @secure_connection
    def delete_diagnosis(diagnosis_id: int, conn=None) -> bool:
        """
        Elimina un diagnóstico de la base de datos
        Retorna: True si la eliminación fue exitosa
        """
        cursor = conn.cursor()
        cursor.execute("DELETE FROM diagnosticos WHERE id = ?", (diagnosis_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    @secure_connection
    def search_diagnoses(query: str, conn=None) -> List[Dict[str, Any]]:
        """
        Busca diagnósticos por código, nombre o comentarios
        Retorna: Lista de diagnósticos que coinciden
        """
        cursor = conn.cursor()
        search_query = f"%{query}%"
        
        cursor.execute("""
            SELECT d.id, d.id_paciente, d.codigo_diagnostico, d.nombre_diagnostico, 
                   d.fecha_diagnostico, d.fecha_resolucion, d.estado, d.comentarios,
                   p.apellido_paterno, p.apellido_materno, p.nombre as paciente_nombre
            FROM diagnosticos d
            LEFT JOIN pacientes p ON d.id_paciente = p.id
            WHERE d.codigo_diagnostico LIKE ? OR d.nombre_diagnostico LIKE ? OR d.comentarios LIKE ?
            ORDER BY d.fecha_diagnostico DESC
        """, (search_query, search_query, search_query))
        
        diagnoses = cursor.fetchall()
        
        return [
            {
                "id": d[0],
                "id_paciente": d[1],
                "codigo_diagnostico": d[2],
                "nombre_diagnostico": d[3],
                "fecha_diagnostico": d[4],
                "fecha_resolucion": d[5],
                "estado": d[6],
                "comentarios": d[7],
                "paciente_nombre_completo": f"{d[8]} {d[9]} {d[10]}" if d[8] else ""
            }
            for d in diagnoses
        ]
    
    @staticmethod
    @secure_connection
    def get_active_diagnoses_count(conn=None) -> int:
        """Obtiene el número total de diagnósticos activos en el sistema"""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM diagnosticos WHERE estado = 'activo'")
        return cursor.fetchone()[0]
    
    # ===== MÉTODOS PARA SESIONES =====
    
    @staticmethod
    @secure_connection
    def get_sessions_for_patient(patient_id: int, conn=None) -> List[Dict[str, Any]]:
        """Obtiene todas las sesiones de un paciente específico"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, fecha, objetivo, comentarios FROM sesiones " +
            "WHERE id_paciente = ? ORDER BY fecha DESC",
            (patient_id,)
        )
        sessions = cursor.fetchall()
        
        return [
            {
                "id": s[0],
                "fecha": s[1],
                "objetivo": s[2],
                "comentarios": s[3]
                # No incluimos datos de sensores pues son BLOBs que pueden ser grandes
            }
            for s in sessions
        ]
    
    @staticmethod
    @secure_connection
    def get_session(session_id: int, signal_data: bool = False, conn=None) -> Optional[Dict[str, Any]]:
        """
        Obtiene una sesión específica
        signal_data: Si es True, incluye los datos de EOG, PPG y milisegundos (puede ser pesado)
        """
        cursor = conn.cursor()
        
        if signal_data:
            cursor.execute(
                "SELECT id, id_paciente, fecha, objetivo, sud_inicial, sud_interm, sud_final, voc, " +
                "datos_ms, datos_eog, datos_ppg, datos_bpm, comentarios " +
                "FROM sesiones WHERE id = ?",
                (session_id,)
            )
            session = cursor.fetchone()
            
            if not session:
                return None
            
            signal_data = DatabaseManager.decompress_signal_data(datos_ms=session[8],
                                                                 datos_eog=session[9],
                                                                 datos_ppg=session[10],
                                                                 datos_bpm=session[11]
                                                                )
            
            # Retornar la sesión con los datos de señales
            return {
                "id": session[0],
                "id_paciente": session[1],
                "fecha": session[2],
                "objetivo": session[3],
                "sud_inicial": session[4],
                "sud_interm": session[5],
                "sud_final": session[6],
                "voc": session[7],
                "datos_ms": signal_data['ms_data_decompressed'],
                "datos_eog": signal_data['eog_data_decompressed'],
                "datos_ppg": signal_data['ppg_data_decompressed'],
                "datos_bpm": signal_data['bpm_data_decompressed'],
                "comentarios": session[12]
            }
        else:
            cursor.execute(
                "SELECT id, id_paciente, fecha, objetivo, sud_inicial, sud_interm, sud_final, voc, comentarios " +
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
                "objetivo": session[3],
                "sud_inicial": session[4],
                "sud_interm": session[5],
                "sud_final": session[6],
                "voc": session[7],
                "comentarios": session[8]
            }
    
    @staticmethod
    @secure_connection
    def add_session(
        id_paciente: int,
        fecha: str = None,
        objetivo: Optional[str] = None,
        sud_inicial: Optional[int] = None,
        sud_intermedio: Optional[int] = None,
        sud_final: Optional[int] = None,
        voc: Optional[int] = None,
        datos_ms: Optional[List[int]] = None,
        datos_eog: Optional[List[int]] = None,
        datos_ppg: Optional[List[int]] = None,
        datos_bpm: Optional[List[int]] = None,
        comentarios: Optional[str] = None,
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
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Comprimir los datos de señales si se proporcionan
        if not any(d is None for d in [datos_ms, datos_eog, datos_ppg, datos_bpm]):
            datos_ms, datos_eog, datos_ppg, datos_bpm = DatabaseManager.compress_signal_data(
                datos_ms, datos_eog, datos_ppg, datos_bpm
            )
        
        cursor.execute(
            "INSERT INTO sesiones (id_paciente, fecha, objetivo, sud_inicial, sud_interm, sud_final, \
                                   voc, datos_ms, datos_eog, datos_ppg, datos_bpm, comentarios) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id_paciente, fecha, objetivo, sud_inicial, sud_intermedio, sud_final, 
             voc, datos_ms, datos_eog, datos_ppg, datos_bpm, comentarios)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    @secure_connection
    def update_session_clinical_data(
        session_id: int,
        sud_inicial: Optional[int] = None,
        sud_intermedio: Optional[int] = None,
        sud_final: Optional[int] = None,
        voc: Optional[int] = None,
        conn=None
    ) -> bool:
        """
        Actualiza únicamente los datos clínicos de una sesión (SUD y VOC)
        Retorna: True si la actualización fue exitosa
        """
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sesiones SET sud_inicial = ?, sud_interm = ?, sud_final = ?, voc = ? " +
            "WHERE id = ?",
            (sud_inicial, sud_intermedio, sud_final, voc, session_id)
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
    
    @staticmethod
    @secure_connection
    def get_admin_by_username(username: str, conn=None) -> Optional[Dict[str, Any]]:
        """
        Obtiene los datos de un administrador por su username
        Args:
            username: Nombre de usuario del administrador
        Returns:
            Dict con los datos del administrador o None si no existe
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user, password FROM administradores WHERE user = ?",
            (username,)
        )
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'user': row[1],
                'nombre': row[1],  # Usar user como nombre por compatibilidad
                'password': row[2]
            }
        return None

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
                SELECT id, user, apellido_paterno, apellido_materno, nombre, genero 
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
    def get_therapist_by_username(username):
        """Obtiene los datos completos de un terapeuta por su nombre de usuario"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user, apellido_paterno, apellido_materno, nombre, genero
                FROM terapeutas 
                WHERE user = ?
            """, (username,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'user': row[1], 
                    'apellido_paterno': row[2],
                    'apellido_materno': row[3],
                    'nombre': row[4],
                    'genero': row[5]
                }
            
            return None
            
        except Exception as e:
            print(f"Error al obtener datos del terapeuta: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
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
    def decompress_signal_data(**kwargs: Any) -> Optional[Dict[str, Any]]:
        """
        Recupera los datos fisiológicos de una sesión específica
        Args:
            **kwargs: Argumentos con nombres que pueden incluir:
                - datos_ms: bytes | None
                - datos_eog: bytes | None  
                - datos_ppg: bytes | None
                - datos_bpm: bytes | None
        Returns:
            Dict con los datos descomprimidos o None si hay error
        """
        try:
            import pickle
            import zlib
            
            ms_data = kwargs.get("datos_ms")
            eog_data = kwargs.get("datos_eog")
            ppg_data = kwargs.get("datos_ppg")
            bpm_data = kwargs.get("datos_bpm")

            # Descomprimir datos de milisegundos si existe
            if ms_data:
                ms_decompressed = zlib.decompress(ms_data)
                ms_data = pickle.loads(ms_decompressed)
            
            # Descomprimir EOG si existe
            if eog_data:
                eog_decompressed = zlib.decompress(eog_data)
                eog_data = pickle.loads(eog_decompressed)

            # Descomprimir PPG si existe
            if ppg_data:
                ppg_decompressed = zlib.decompress(ppg_data)
                ppg_data = pickle.loads(ppg_decompressed)

            # Descomprimir BPM si existe
            if bpm_data:
                bpm_decompressed = zlib.decompress(bpm_data)
                bpm_data = pickle.loads(bpm_decompressed)

            return {
                "ms_data_decompressed": ms_data,
                "eog_data_decompressed": eog_data,
                "ppg_data_decompressed": ppg_data,
                "bpm_data_decompressed": bpm_data
            }

        except Exception as e:
            print(f"Error al recuperar datos de sesión: {e}")
            return None
    
    @staticmethod
    def compress_signal_data(
        datos_ms: List[int],
        datos_eog: List[int],
        datos_ppg: List[int],
        datos_bpm: List[int]
    ) -> Tuple[bytes, bytes, bytes, bytes]:
        """
        Comprime los datos fisiológicos de una sesión para almacenamiento
        Retorna: Tupla con los datos comprimidos (ms, eog, ppg, bpm)
        """
        import numpy as np
        import zlib
        import pickle

        # Convertir listas a arreglos de numpy
        datos_ms_np = np.array(datos_ms, dtype=np.int32)
        datos_eog_np = np.array(datos_eog, dtype=np.int32)
        datos_ppg_np = np.array(datos_ppg, dtype=np.int32)

        compressed_ms = zlib.compress(pickle.dumps(datos_ms_np))
        compressed_eog = zlib.compress(pickle.dumps(datos_eog_np))
        compressed_ppg = zlib.compress(pickle.dumps(datos_ppg_np))
        compressed_bpm = zlib.compress(pickle.dumps(datos_bpm))
        
        return compressed_ms, compressed_eog, compressed_ppg, compressed_bpm

# Ejemplo de uso modificado para incluir diagnósticos
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
        fecha_nacimiento="1988-05-15",
        celular="78551234",
        comentarios="Paciente con historial de ansiedad"
    )
    
    if patient_id:
        print(f"✅ Paciente creado con ID: {patient_id}")
        
        # Obtener el ID del terapeuta para el diagnóstico
        therapist = DatabaseManager.get_therapist_by_username("dra.valdivia")
        therapist_id = therapist['id'] if therapist else None
        
        # Añadir un diagnóstico para este paciente
        diagnosis_id = DatabaseManager.add_diagnosis(
            id_paciente=patient_id,
            codigo_diagnostico="F41.1",
            nombre_diagnostico="Trastorno de ansiedad generalizada",
            id_terapeuta=therapist_id,
            comentarios="Diagnóstico inicial basado en evaluación clínica"
        )
        
        if diagnosis_id:
            print(f"✅ Diagnóstico creado con ID: {diagnosis_id}")
        
        # Añadir una sesión para este paciente
        session_id = DatabaseManager.add_session(
            id_paciente=patient_id,
            comentarios="Primera sesión de evaluación"
        )
        
        if session_id:
            print(f"✅ Sesión creada con ID: {session_id}")
            
            # Mostrar todos los pacientes
            patients = DatabaseManager.get_all_patients()
            print(f"Pacientes en la base de datos: {len(patients)}")
            
            # Mostrar diagnósticos del paciente
            diagnoses = DatabaseManager.get_diagnoses_for_patient(patient_id)
            print(f"Diagnósticos del paciente: {len(diagnoses)}")
            
            # Mostrar sesiones del paciente
            sessions = DatabaseManager.get_sessions_for_patient(patient_id)
            print(f"Sesiones del paciente: {len(sessions)}")