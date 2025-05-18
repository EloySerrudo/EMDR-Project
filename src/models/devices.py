from serial import Serial
from serial.tools.list_ports import comports
from time import sleep
import pygame
from array import array
from src.models.device_config import DEVICE_CONFIG

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
    def do_sound(cls, left):
        if left:
            cls._channel_left.play(cls._beep, cls._sound_duration)
        else:
            cls._channel_right.play(cls._beep, cls._sound_duration)

    @classmethod
    def set_tone(cls, frequency, duration, volume):
        cls._beep = Note(frequency)
        cls._sound_duration = duration
        cls._channel_left.set_volume(1 * volume, 0)
        cls._channel_right.set_volume(0, 1 * volume)