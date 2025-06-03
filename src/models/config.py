from threading import Lock
import pickle
from pathlib import Path
import os

class Config():
    speeds = [
        10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60
    ]
    # Estimulación Visual
    colors = [
        ("Rojo Profundo", 139, 0, 0),
        ("Rojo", 255, 0, 0),
        ("Vela", 255, 69, 0),
        ("Incandescente baja", 255, 107, 0),
        ("Incandescente alta", 255, 140, 0),
        ("Amarillo", 255, 255, 0),
        ("Dorado", 255, 215, 0),
        ("Ámbar", 255, 191, 0),
        ("Azul Cielo", 135, 206, 235),
        ("Azul Acero", 70, 130, 180),
        ("Azul Real", 65, 105, 225),
        ("Azul Profundo", 0, 0, 255),
        ("Azul Púrpura", 106, 90, 205),
        ("Índigo", 75, 0, 205),
        ("Violeta", 138, 43, 226),
        ("Púrpura Profundo", 75, 0, 130)
    ]
    intensities = [
        20, 40, 60, 80, 100
    ]
    # Estimulación Auditiva
    volumes = [
        20, 40, 60, 80, 100
    ]
    
    # Nuevos tonos WAV desde archivos
    @classmethod
    def get_tones_path(cls):
        """Obtiene la ruta del directorio de tonos"""
        current_dir = Path(__file__).parent
        project_root = current_dir.parent
        return project_root / "resources" / "tones"
    
    @classmethod
    def load_wav_tones(cls):
        """Carga los tonos WAV desde el directorio de recursos"""
        tones_path = cls.get_tones_path()
        
        if not tones_path.exists():
            print(f"Advertencia: No se encontró el directorio de tonos: {tones_path}")
            return cls._get_fallback_tones()
        
        # Definir los tonos disponibles con sus archivos correspondientes
        tone_definitions = [
            {
                'name': 'Sonido 1',  # Tono 00 - Audio EMDR 1 (Custom)
                'description': 'Audio personalizado',
                'left_file': 'tone_00_custom_LEFT.wav',
                'right_file': 'tone_00_custom_RIGHT.wav'
            },
            {
                'name': 'Sonido 2',     # Tono 01 - La Natural (440Hz)
                'description': 'Tono puro suave',
                'left_file': 'tone_01_pure_440Hz_LEFT.wav',
                'right_file': 'tone_01_pure_440Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 3',             # Tono 02 - Mi (330Hz)
                'description': 'Tono cálido medio',
                'left_file': 'tone_02_warm_330Hz_LEFT.wav',
                'right_file': 'tone_02_warm_330Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 4',       # Tono 03 - Do Medio (261Hz)
                'description': 'Tono profundo',
                'left_file': 'tone_03_deep_261Hz_LEFT.wav',
                'right_file': 'tone_03_deep_261Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 5',        # Tono 04 - Do Alto (523Hz)
                'description': 'Tono brillante',
                'left_file': 'tone_04_bright_523Hz_LEFT.wav',
                'right_file': 'tone_04_bright_523Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 6',            # Tono 05 - Sol (392Hz)
                'description': 'Tono suave con armónicos',
                'left_file': 'tone_05_soft_392Hz_LEFT.wav',
                'right_file': 'tone_05_soft_392Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 7',             # Tono 06 - Re (293Hz)
                'description': 'Tono meloso',
                'left_file': 'tone_06_mellow_293Hz_LEFT.wav',
                'right_file': 'tone_06_mellow_293Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 8',             # Tono 07 - Fa (349Hz)
                'description': 'Onda triangular suave',
                'left_file': 'tone_07_gentle_349Hz_LEFT.wav',
                'right_file': 'tone_07_gentle_349Hz_RIGHT.wav'
            },
            {
                'name': 'Sonido 9',             # Tono 08 - Si (493Hz)
                'description': 'Onda triangular calmante',
                'left_file': 'tone_08_calm_493Hz_LEFT.wav',
                'right_file': 'tone_08_calm_493Hz_RIGHT.wav'
            }
        ]
        
        # Verificar que los archivos existen y crear la lista de tonos
        available_tones = []
        
        for tone_def in tone_definitions:
            left_path = tones_path / tone_def['left_file']
            right_path = tones_path / tone_def['right_file']
            
            if left_path.exists() and right_path.exists():
                # Agregar como tupla (nombre, descripción, archivo_izq, archivo_der)
                available_tones.append((
                    tone_def['name'],
                    tone_def['description'], 
                    str(left_path),
                    str(right_path)
                ))
            else:
                print(f"Advertencia: Archivos faltantes para {tone_def['name']}")
                print(f"  Izquierdo: {left_path.exists()}")
                print(f"  Derecho: {right_path.exists()}")
        
        if not available_tones:
            print("No se encontraron tonos WAV válidos. Usando tonos por defecto.")
            return cls._get_fallback_tones()
        
        print(f"Encontrados {len(available_tones)} tonos WAV exitosamente")
        return available_tones
    
    @classmethod
    def _get_fallback_tones(cls):
        """Tonos de respaldo si no se encuentran los archivos WAV"""
        return [
            ('Medio/Corto', 'Tono medio duración corta', 440, 50),
            ('Medio/Largo', 'Tono medio duración larga', 440, 100),
            ('Alto/Corto', 'Tono alto duración corta', 880, 100),
            ('Alto/Largo', 'Tono alto duración larga', 880, 200),
            ('Bajo/Corto', 'Tono bajo duración corta', 220, 25),
            ('Bajo/Largo', 'Tono bajo duración larga', 220, 50),
        ]
    
    # Cargar tonos al inicializar la clase
    tones = []
    
    @classmethod
    def initialize_tones(cls):
        """Inicializa los tonos WAV"""
        cls.tones = cls.load_wav_tones()
    
    # Estimulación Táctil
    durations = [
        100, 200, 300
    ]
    
    data = {
        'general.speed': 10,
        'lightbar.on': True,
        'lightbar.intensity': 20,
        'lightbar.color': colors[0],
        'buzzer.on': True,
        'buzzer.duration': 100,
        'headphone.on': True,
        'headphone.volume': 0.5,
        'headphone.tone': None,  # Se establecerá después de cargar los tonos
    }

    @classmethod
    def load(cls):
        try:
            with open('emdr.config', 'rb') as f:
                loaded_data = pickle.load(f)
                cls.data.update(loaded_data)
        except:
            pass
        
        # Asegurar que tenemos un tono válido seleccionado
        if not cls.tones:
            cls.initialize_tones()
        
        if cls.tones and (cls.data.get('headphone.tone') is None or 
                         cls.data.get('headphone.tone') not in cls.tones):
            cls.data['headphone.tone'] = cls.tones[0]

    @classmethod
    def save(cls):
        with open('emdr.config', 'wb') as f:
            pickle.dump(cls.data, f)

# Inicializar tonos al importar el módulo
Config.initialize_tones()