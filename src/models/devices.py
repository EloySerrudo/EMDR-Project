from serial import Serial
from serial.tools.list_ports import comports
from time import sleep
import pygame
from array import array
from src.models.device_config import DEVICE_CONFIG
from pathlib import Path

# Diccionario de esclavos: {ID: (nombre, requerido_para_captura)}
KNOWN_SLAVES = {
    1: ("Sensor", True),   # ID 1: Sensor de pulso (requerido para captura de señales)
    2: ("Lightbar", False),         # Ejemplo: ID 2 para un sensor que no es obligatorio
    3: ("Buzzer", False)            # Ejemplo: ID 3 para otro sensor opcional
    # Aquí se pueden añadir más esclavos en el futuro
}

class Note(pygame.mixer.Sound):
    def __init__(self, frequency, volume=.33):
        self.frequency = frequency
        super().__init__(buffer=self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        period = int(round(pygame.mixer.get_init()[0] / self.frequency))
        samples = array("h", [0] * period)
        amplitude = 2 ** (abs(pygame.mixer.get_init()[1]) - 1) - 1
        for time in range(period):
            if time < period / 2:
                samples[time] = amplitude
            else:
                samples[time] = -amplitude
        return samples

class Devices():
    led_num = 58
    _buzzer_duration = 100
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    _channel_left = pygame.mixer.Channel(0)
    _channel_left.set_volume(1, 0)
    _channel_right = pygame.mixer.Channel(1)
    _channel_right.set_volume(0, 1)
    
    # Variables para manejo de sonidos WAV
    _current_left_sound = None
    _current_right_sound = None
    _current_volume = 0.5
    
    # Mantener compatibilidad con el sistema anterior
    _beep = Note(440)
    _sound_duration = 50
    _master_controller = (None, None)
    # Lista para almacenar dispositivos encontrados
    _found_devices = []

    @classmethod
    def probe(cls):
        """Detecta y conecta dispositivos, incluyendo controlador maestro y sus esclavos"""
        # Cerrar cualquier conexión existente
        _, ser = cls._master_controller
        if ser:
            ser.close()
        cls._master_controller = (None, None)
        
        cls._found_devices = []
        
        # Buscar puerto serial del controlador maestro
        for p in comports():
            for d in DEVICE_CONFIG.values():
                if (p.vid, p.pid) == (d['vid'], d['pid']):
                    ser = None
                    try:
                        ser = Serial(p.device, baudrate=d['baud'], timeout=1.0)
                        sleep(2)  # Dar tiempo para inicialización
                        
                        # Enviar comando de identificación
                        ser.write(bytes([ord('I'), 0, 0, 0, 0]))
                        ser.flush()
                        id_str = ser.read_until().strip()
                        # Verificar si es el controlador maestro
                        if b'EMDR Master Controller' in id_str:
                            cls._found_devices.append("Master Controller")
                            cls._master_controller = (d, ser)  # Usamos esta conexión para comunicarnos con todo
                            
                            # Solicitar verificación de dispositivos conectados
                            ser.write(bytes([ord('A'), 0, 0, 0, 0]))  # Comando 'A' para verificar conexiones
                            ser.flush()
                            sleep(2)  # Esperar respuesta
                            
                            # Leer respuesta del protocolo de verificación de conexión
                            if ser.in_waiting > 0:
                                # Protocolo definido: !C[device_id1][status1][device_id2][status2]...
                                if ser.read(1) == b'!' and ser.read(1) == b'C':
                                    for _ in range(len(KNOWN_SLAVES)):
                                        if ser.in_waiting >= 2:
                                            device_id = ord(ser.read(1))
                                            status = ord(ser.read(1))
                                            device, _ = KNOWN_SLAVES.get(device_id, None)
                                            if status == 1:
                                                cls._found_devices.append(device)
                        else:
                            print(f"Unknown device: {id_str}")
                            ser.close()
                           
                    except Exception as e:
                        print(f"Error probing device on {p.device}: {e}")
                        if ser:
                            ser.close()
        
        return cls._found_devices

    @classmethod
    def master_plugged_in(cls):
        return "Master Controller" in cls._found_devices

    @classmethod
    def sensor_plugged_in(cls):
        return "Sensor" in cls._found_devices

    @classmethod
    def lightbar_plugged_in(cls):
        return "Lightbar" in cls._found_devices

    @classmethod
    def buzzer_plugged_in(cls):
        return "Buzzer" in cls._found_devices

    @classmethod
    def write(cls, devser, cmd):
        (dev, ser) = devser
        if dev and ser:
            ser.write(cmd)
            ser.flush()

    @classmethod
    def get_master_connection(cls):
        return cls._master_controller[1]

    @classmethod
    def start_sensor(cls):
        # Enviar 5 bytes: comando 's' + ID + 3 bytes a cero
        cls.write(cls._master_controller, bytes([ord('s'), 1, 0, 0, 0]))

    @classmethod
    def stop_sensor(cls):
        # Enviar 5 bytes: comando 'p' + ID + 3 bytes a cero
        cls.write(cls._master_controller, bytes([ord('p'), 1, 0, 0, 0]))

    @classmethod
    def set_led(cls, num):
        if num >= 0:
            # Enviar 5 bytes: comando 'l' + ID + posición del LED + 2 bytes a cero
            cls.write(cls._master_controller, bytes([ord('l'), 2, int(num), 0, 0]))
        else:
            # Enviar 5 bytes: comando 't' + ID + 3 bytes a cero
            cls.write(cls._master_controller, bytes([ord('t'), 2, 0, 0, 0]))

    @classmethod
    def set_color(cls, col):
        r = (col >> 16) & 0xFF
        g = (col >> 8) & 0xFF
        b = col & 0xFF
        # Enviar 5 bytes: comando 'c' + ID + r + g + b
        cls.write(cls._master_controller, bytes([ord('c'), 2, r, g, b]))
    
    @classmethod
    def switch_to_next_strip(cls):
        # Enviar 5 bytes: comando 'n' + ID + 3 bytes a cero
        cls.write(cls._master_controller, bytes([ord('n'), 2, 0, 0, 0]))

    @classmethod
    def set_buzzer_duration(cls, duration):
        cls._buzzer_duration = duration

    @classmethod
    def do_buzzer(cls, left):
        cls.write(cls._master_controller, bytes([ord('l' if left else 'r'), 3, cls._buzzer_duration, 0, 0]))

    @classmethod
    def load_wav_sounds(cls, left_file_path, right_file_path):
        """Carga los archivos WAV para estimulación bilateral"""
        try:
            # Verificar que los archivos existen
            left_path = Path(left_file_path)
            right_path = Path(right_file_path)
            
            if not left_path.exists():
                print(f"Advertencia: No se encontró archivo izquierdo: {left_path}")
                return False
                
            if not right_path.exists():
                print(f"Advertencia: No se encontró archivo derecho: {right_path}")
                return False
            
            # Cargar los sonidos WAV
            cls._current_left_sound = pygame.mixer.Sound(str(left_path))
            cls._current_right_sound = pygame.mixer.Sound(str(right_path))
            
            # Aplicar volumen actual
            cls._current_left_sound.set_volume(cls._current_volume)
            cls._current_right_sound.set_volume(cls._current_volume)
            
            print(f"Sonidos WAV cargados exitosamente:")
            print(f"  Izquierdo: {left_path.name}")
            print(f"  Derecho: {right_path.name}")
            
            return True
            
        except Exception as e:
            print(f"Error cargando archivos WAV: {e}")
            cls._current_left_sound = None
            cls._current_right_sound = None
            return False

    @classmethod
    def do_sound(cls, left):
        """Reproduce sonido en el canal especificado"""
        if cls._current_left_sound and cls._current_right_sound:
            # Usar archivos WAV si están disponibles
            if left:
                cls._channel_left.stop()  # Detener sonido anterior
                cls._channel_left.play(cls._current_left_sound)
            else:
                cls._channel_right.stop()  # Detener sonido anterior
                cls._channel_right.play(cls._current_right_sound)
        else:
            # Fallback al sistema anterior con Note
            if left:
                cls._channel_left.play(cls._beep, cls._sound_duration)
            else:
                cls._channel_right.play(cls._beep, cls._sound_duration)

    @classmethod
    def set_tone(cls, tone_data, volume):
        """Establece el tono usando archivos WAV o frecuencia tradicional"""
        cls._current_volume = volume
        
        # Determinar si es un tono WAV (tupla de 4 elementos) o tradicional (tupla de 3)
        if len(tone_data) == 4:
            # Formato WAV: (nombre, descripción, archivo_izq, archivo_der)
            name, description, left_file, right_file = tone_data
            
            print(f"Configurando tono WAV: {name}")
            success = cls.load_wav_sounds(left_file, right_file)
            
            if not success:
                print("Fallback a tono generado")
                # Si falla, usar tono por defecto
                cls._beep = Note(440)
                cls._sound_duration = 50
                cls._current_left_sound = None
                cls._current_right_sound = None
        else:
            # Formato tradicional: (nombre, frecuencia, duración)
            name, frequency, duration = tone_data
            print(f"Configurando tono generado: {name} ({frequency}Hz, {duration}ms)")
            
            cls._beep = Note(frequency)
            cls._sound_duration = duration
            cls._current_left_sound = None
            cls._current_right_sound = None
        
        # Actualizar volumen de canales
        cls._channel_left.set_volume(cls._current_volume, 0)
        cls._channel_right.set_volume(0, cls._current_volume)

    @classmethod 
    def stop_all_sounds(cls):
        """Detiene todos los sonidos de audio"""
        cls._channel_left.stop()
        cls._channel_right.stop()