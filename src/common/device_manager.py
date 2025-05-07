import time
from threading import Lock, Thread
from PySide6.QtCore import QObject, Signal
import sys
import os

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar la clase Devices existente y constantes
from src.models.devices import Devices, KNOWN_SLAVES


class DeviceManager(QObject):
    """
    Gestor centralizado para todas las comunicaciones con los dispositivos EMDR.
    Proporciona señales para notificar cambios en el estado de los dispositivos
    y métodos para controlar todas las funciones de hardware.
    """

    # Señales para notificar cambios en el estado de dispositivos
    device_status_changed = Signal(dict, bool)  # Lista de dispositivos, todos requeridos conectados
    sensor_data_received = Signal(dict)  # Datos del sensor cuando estén disponibles
    
    def __init__(self):
        super().__init__()
        self._lock = Lock()  # Lock para operaciones concurrentes
        self._scanning = False
        self._monitoring_thread = None
        self._monitoring_active = False
        
        # Estado de conexión de dispositivos
        self._device_status = {}
        self._required_devices_connected = False
        
        # NO inicializar con un escaneo inicial - será bajo demanda solamente
        
    def scan_devices(self):
        """
        Escanea los dispositivos conectados y actualiza su estado.
        Regresa la lista de dispositivos encontrados.
        """
        with self._lock:
            if self._scanning:
                return None  # Ya hay un escaneo en progreso
                
            self._scanning = True
        
        # Realizar el escaneo en un hilo separado para no bloquear la interfaz
        scan_thread = Thread(target=self._scan_thread_function)
        scan_thread.daemon = True
        scan_thread.start()
        
        return self._device_status
        
    def _scan_thread_function(self):
        """Función ejecutada en un hilo separado para el escaneo de dispositivos"""
        try:
            # Utilizar el método probe de Devices para buscar dispositivos
            found_devices = Devices.probe()
            
            # Actualizar el estado de dispositivos
            self._device_status = {}
            for device_name in found_devices:
                self._device_status[device_name] = True
                
            # Verificar si todos los dispositivos requeridos están conectados
            self._check_required_devices()
            
            # Emitir señal con los resultados
            self.device_status_changed.emit(self._device_status, self._required_devices_connected)
            
        except Exception as e:
            print(f"Error durante el escaneo de dispositivos: {e}")
        finally:
            with self._lock:
                self._scanning = False
    
    def _check_required_devices(self):
        """Verifica si todos los dispositivos requeridos están conectados"""
        # Verificar primero el controlador maestro
        if "Master Controller" not in self._device_status:
            self._required_devices_connected = False
            return
            
        # Verificar dispositivos esclavos requeridos
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            if required and name not in self._device_status:
                self._required_devices_connected = False
                return
                
        # Si llegamos aquí, todos los dispositivos requeridos están conectados
        self._required_devices_connected = True
    
    def get_device_status(self):
        """Retorna el estado actual de los dispositivos"""
        return self._device_status, self._required_devices_connected
    
    def get_required_devices_connected(self):
        """Retorna si todos los dispositivos requeridos están conectados"""
        return self._required_devices_connected
    
    def start_monitoring_sensors(self):
        """Inicia el monitoreo de datos del sensor"""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        Devices.start_sensor()
        
        # Iniciar hilo de monitoreo
        self._monitoring_thread = Thread(target=self._monitor_sensor_data)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
    
    def stop_monitoring_sensors(self):
        """Detiene el monitoreo de datos del sensor"""
        if not self._monitoring_active:
            return
            
        self._monitoring_active = False
        Devices.stop_sensor()
        
        # Esperar a que termine el hilo
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=1.0)
            self._monitoring_thread = None
    
    def _monitor_sensor_data(self):
        """Función ejecutada en un hilo separado para monitorear datos del sensor"""
        ser = Devices.get_master_connection()
        if not ser:
            self._monitoring_active = False
            return
            
        while self._monitoring_active:
            try:
                if ser.in_waiting > 0:
                    # Protocolo simple: !D[tipo][data1][data2]...
                    if ser.read(1) == b'!' and ser.read(1) == b'D':
                        sensor_type = ord(ser.read(1))
                        # Ejemplo: leer 4 bytes para un sensor de tipo 1
                        if sensor_type == 1 and ser.in_waiting >= 4:
                            data1 = int.from_bytes(ser.read(2), byteorder='little', signed=True)
                            data2 = int.from_bytes(ser.read(2), byteorder='little', signed=True)
                            # Emitir señal con los datos recibidos
                            self.sensor_data_received.emit({
                                'eog': data1,
                                'ppg': data2
                            })
                else:
                    time.sleep(0.01)  # Pequeña pausa para no saturar la CPU
            except Exception as e:
                print(f"Error al leer datos del sensor: {e}")
                time.sleep(0.1)  # Pausa para evitar bucles rápidos en caso de error
    
    # Métodos para controlar la barra de luz (Light Tube)
    def set_led_position(self, position):
        """Establece la posición del LED activo en la barra de luz"""
        Devices.set_led(position)
        
    def set_led_color(self, color_data):
        """Establece el color de los LEDs en la barra de luz"""
        if isinstance(color_data, tuple) and len(color_data) == 4:
            (_, r, g, b) = color_data
            color = r * 256 * 256 + g * 256 + b
            Devices.set_color(color)
        
    def set_light_test(self, active):
        """Activa o desactiva el modo de prueba de luz"""
        Devices.set_led(-1 if active else 0)  # -1 es el código para test en Devices
    
    # Métodos para controlar los pulsadores (Buzzer)
    def set_buzzer_duration(self, duration):
        """Establece la duración de la vibración del buzzer"""
        Devices.set_buzzer_duration(duration // 10)
        
    def do_buzzer(self, left):
        """Activa el buzzer en el lado izquierdo o derecho"""
        Devices.do_buzzer(left)
    
    # Métodos para controlar los auriculares (Headphone)
    def set_tone(self, tone_data, volume):
        """Establece el tono y volumen para los auriculares"""
        if isinstance(tone_data, tuple) and len(tone_data) == 3:
            (_, frequency, duration) = tone_data
            Devices.set_tone(frequency, duration, volume / 100)
        
    def do_sound(self, left):
        """Reproduce un sonido en el auricular izquierdo o derecho"""
        Devices.do_sound(left)
    
    def get_master_connection(self):
        """Obtiene la conexión al controlador maestro"""
        return Devices.get_master_connection()
    
    def is_device_connected(self, device_name):
        """Verifica si un dispositivo específico está conectado"""
        return device_name in self._device_status
    
    def is_master_connected(self):
        """Verifica si el controlador maestro está conectado"""
        return "Master Controller" in self._device_status
    
    def is_lightbar_connected(self):
        """Verifica si la barra de luz está conectada"""
        return "Lightbar" in self._device_status
    
    def is_buzzer_connected(self):
        """Verifica si el buzzer está conectado"""
        return "Buzzer" in self._device_status
    
    def is_headphone_connected(self):
        """Verifica si los auriculares están conectados (siempre disponible con pygame)"""
        return True
    
    # Método para limpiar recursos antes de cerrar
    def cleanup(self):
        """Limpia todos los recursos y conexiones"""
        self.stop_monitoring_sensors()
        # Apagar todos los LEDs
        Devices.set_led(0)
        # No es necesario cerrar las conexiones ya que Devices.probe() lo hace