import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import threading
import time
import argparse
from collections import deque

# Configuración por defecto
DEFAULT_PORT = 'COM4'  # Cambiar según el puerto que use tu ESP32
DEFAULT_BAUDRATE = 115200
BUFFER_SIZE = 512  # Máximo número de muestras a leer de una vez
SAMPLE_RATE = 250  # Hz (coincide con SAMPLE_RATE del ESP32 = 250Hz)
DISPLAY_TIME = 5   # Segundos de datos a mostrar en la gráfica

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 13        # Tamaño en bytes de cada paquete (12 original + 1 para device_id)

# Diccionario de esclavos: {ID: (nombre, requerido_para_captura)}
KNOWN_SLAVES = {
    1: ("Sensor de pulso", True),  # ID 1: Sensor de pulso (requerido para captura)
    # Aquí se pueden añadir más esclavos en el futuro
    # 2: ("Sensor de temperatura", False),  # Ejemplo: ID 2 para un sensor que no es obligatorio
    # 3: ("Sensor de luz", False),          # Ejemplo: ID 3 para otro sensor opcional
}

class PulseMonitor:
    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE, display_time=DISPLAY_TIME):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.reading_thread = None
        
        # Para almacenar los datos
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE

        # Inicializar deques con valores cero
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size

        self.times = deque(initial_times, maxlen=self.display_size)
        self.values = deque(initial_values, maxlen=self.display_size)
        
        # Estadísticas
        self.samples_received = 0
        self.packets_received = 0
        self.invalid_packets = 0
        self.duplicate_packets = 0
        self.last_samples_count = 0
        self.samples_per_second = 0
        self.last_rate_update = time.time()
        self.last_packet_id = -1  # Inicializar con -1 para asegurar que procesemos el primer paquete
        
        # Configuración de la gráfica - un solo eje ahora
        self.fig, self.ax1 = plt.subplots(1, 1, figsize=(10, 6))
        self.signal_line, = self.ax1.plot([], [], 'b-', lw=1.5, label='Señal cruda')
        
        # Texto para mostrar estadísticas
        self.stats_text = self.ax1.text(0.02, 0.95, '', transform=self.ax1.transAxes,
                                      verticalalignment='top', bbox=dict(boxstyle='round', 
                                                                      facecolor='wheat', alpha=0.7))
        
        # Configurar ejes y títulos
        self.ax1.set_xlabel('Tiempo (s)')
        self.ax1.set_ylabel('Amplitud')
        self.ax1.set_title('Monitor de Señal Cruda ADS1115')
        self.ax1.set_ylim(-30000, 30000)
        self.ax1.set_xlim(-display_time, 0)
        self.ax1.grid(True)
        
        plt.tight_layout()
        
        # Para mostrar dispositivos conectados
        self.slave_count = 0
        self.connection_thread = None
        
        # Diccionario para mantener estado de conexión por ID
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        
        # Flag para indicar si tenemos los dispositivos requeridos conectados
        self.required_devices_connected = False
        
    def connect(self):
        """Conectar al puerto serial"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Conectado a {self.port} a {self.baudrate} baudios")
            # Asegurarse de que no hay datos pendientes
            self.serial.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"Error al conectar al puerto {self.port}: {e}")
            return False
    
    def start_acquisition(self):
        """Iniciar la adquisición de datos"""
        if self.serial and not self.running:
            # Enviar comando al ESP32 para iniciar la captura
            self.serial.write(b'S')
            
            # Iniciar captura
            self.running = True
            
            # Reiniciar estadísticas
            self.samples_received = 0
            self.packets_received = 0
            self.invalid_packets = 0
            self.last_samples_count = 0
            self.last_rate_update = time.time()
            
            # Iniciar hilo de lectura
            self.reading_thread = threading.Thread(target=self._read_data)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            print("Adquisición iniciada")
            
            # Limpiar deques y reiniciar con ceros
            self.times.clear()
            self.values.clear()
            initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
            initial_values = [0] * self.display_size
            self.times.extend(initial_times)
            self.values.extend(initial_values)

    def stop_acquisition(self):
        """Detener la adquisición de datos"""
        if self.serial and self.running:
            # Enviar comando al ESP32 para detener la captura
            self.serial.write(b'P')
            
            # Detener captura
            self.running = False
            if self.reading_thread:
                self.reading_thread.join(timeout=1.0)
            print(f"Adquisición detenida. Total paquetes recibidos: {self.packets_received}")

    def _find_packet_start(self, buffer):
        """Busca el inicio de un paquete en el buffer"""
        if len(buffer) < 2:
            return -1
            
        for i in range(len(buffer) - 1):
            # Buscar la secuencia de bytes del header (Little Endian: 0x55, 0xAA)
            if buffer[i] == (PACKET_HEADER & 0xFF) and buffer[i + 1] == (PACKET_HEADER >> 8) & 0xFF:
                return i
                
        return -1

    def check_slave_connections(self):
        """Envía comando para verificar conexiones de esclavos"""
        if not self.serial:
            print("No hay conexión serial establecida")
            return
            
        print("Verificando dispositivos conectados...")
        self.serial.write(b'C')  # Enviar comando para verificar conexiones
        
        # Resetear estado de conexión
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        
        # Leer respuesta en un hilo separado para no bloquear la interfaz
        if self.connection_thread is None or not self.connection_thread.is_alive():
            self.connection_thread = threading.Thread(target=self._read_connection_data)
            self.connection_thread.daemon = True
            self.connection_thread.start()
    
    def _read_connection_data(self):
        """Lee datos de conexión en un hilo separado"""
        # Limpiar buffer antes de leer
        message_buffer = bytearray()
        timeout = time.time() + 2.0  # 2 segundos de timeout
        
        # Limpiar buffer serial
        self.serial.reset_input_buffer()
        
        while time.time() < timeout:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    message_buffer.extend(data)
                    
                    # Verificar si tenemos suficientes bytes para procesar
                    if len(message_buffer) >= 3:  # Al menos necesitamos '!', 'C' y slave_count
                        marker = chr(message_buffer[0])
                        command = chr(message_buffer[1])
                        
                        if marker == '!' and command == 'C':
                            slave_count = message_buffer[2]
                            # Verificar si tenemos todos los bytes necesarios
                            if len(message_buffer) >= 3 + (slave_count * 2):
                                self.slave_count = slave_count
                                
                                # Procesar la información de conexión
                                for i in range(slave_count):
                                    device_id = message_buffer[3 + (i * 2)]
                                    status = message_buffer[4 + (i * 2)] == 1
                                    
                                    if device_id in self.slave_status:
                                        self.slave_status[device_id] = status
                                
                                # Mostrar información y salir
                                self._print_connection_status()
                                break
                    
                time.sleep(0.05)
            except Exception as e:
                print(f"Error al leer datos de conexión: {e}")
                break
    
    def _print_connection_status(self):
        """Muestra en la terminal el estado de los esclavos conectados"""
        print("\n--- Estado de conexión de esclavos ---")
        
        # Verificamos todos los esclavos conocidos
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            connected = self.slave_status.get(slave_id, False)
            status = "CONECTADO" if connected else "DESCONECTADO"
            req_text = "(Requerido)" if required else "(Opcional)"
            print(f"Esclavo ID:{slave_id} - {name} {req_text}: {status}")
        
        print("-------------------------------------\n")
        
        # Verificar si tenemos los dispositivos requeridos
        self.required_devices_connected = all(
            self.slave_status.get(slave_id, False) 
            for slave_id, (_, required) in KNOWN_SLAVES.items() 
            if required
        )
        
        if self.required_devices_connected:
            print("Todos los dispositivos requeridos están conectados.\n")
        else:
            print("ADVERTENCIA: Uno o más dispositivos requeridos no están conectados.")
            print("La adquisición de datos está deshabilitada hasta que todos los dispositivos requeridos estén conectados.\n")

    def _read_data(self):
        """Función que se ejecuta en un hilo separado para leer datos binarios"""
        data_buffer = bytearray()
        
        while self.running:
            try:
                # Leer datos disponibles
                available = self.serial.in_waiting
                
                if available > 0:
                    # Leer los datos disponibles
                    new_data = self.serial.read(min(available, BUFFER_SIZE * PACKET_SIZE))
                    data_buffer.extend(new_data)
                    
                    # Procesar mientras tengamos suficientes datos para un paquete completo
                    while len(data_buffer) >= PACKET_SIZE:
                        # Buscar el inicio de un paquete
                        packet_start = self._find_packet_start(data_buffer)
                        
                        if packet_start < 0:
                            # No se encontró un header válido, conservar solo el último byte
                            if len(data_buffer) > 1:
                                data_buffer = data_buffer[-1:]
                            break
                            
                        # Si el paquete no empieza al inicio del buffer, descartar los bytes anteriores
                        if packet_start > 0:
                            data_buffer = data_buffer[packet_start:]
                            
                        # Verificar si tenemos un paquete completo
                        if len(data_buffer) < PACKET_SIZE:
                            break
                            
                        # Extraer datos del paquete
                        try:
                            # Header (2 bytes)
                            header = struct.unpack('<H', data_buffer[0:2])[0]
                            
                            if header == PACKET_HEADER:
                                # ID (4 bytes)
                                packet_id = struct.unpack('<I', data_buffer[2:6])[0]
                                
                                # Verificar si el paquete es duplicado
                                if packet_id <= self.last_packet_id:
                                    self.duplicate_packets += 1
                                    # Quitar el paquete procesado del buffer y continuar
                                    data_buffer = data_buffer[PACKET_SIZE:]
                                    continue
                                
                                # Actualizar el último ID procesado
                                self.last_packet_id = packet_id
                                
                                # Timestamp (4 bytes)
                                timestamp_ms = struct.unpack('<I', data_buffer[6:10])[0]
                                timestamp_s = timestamp_ms / 1000.0  # Convertir a segundos
                                
                                # Valor (2 bytes)
                                value = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # Device ID (1 byte)
                                device_id = data_buffer[12]
                                
                                # Añadir a las colas
                                self.times.append(timestamp_s)
                                self.values.append(value)
                                
                                # Actualizar contadores
                                self.samples_received += 1
                                self.packets_received += 1
                                
                                # Actualizar estadísticas con el device_id si es necesario
                                # Ejemplo: podrías mantener estadísticas por dispositivo
                            else:
                                # Header inválido, descartar byte inicial y continuar
                                self.invalid_packets += 1
                                data_buffer = data_buffer[1:]
                                continue
                                
                            # Quitar el paquete procesado del buffer
                            data_buffer = data_buffer[PACKET_SIZE:]
                        except Exception as e:
                            print(f"Error al procesar paquete: {e}")
                            # En caso de error, descartar el byte inicial y continuar
                            data_buffer = data_buffer[1:]
                
                # Actualizar estadísticas cada segundo
                current_time = time.time()
                if current_time - self.last_rate_update >= 1.0:
                    elapsed = current_time - self.last_rate_update
                    new_samples = self.samples_received - self.last_samples_count
                    self.samples_per_second = int(new_samples / elapsed)
                    
                    self.last_samples_count = self.samples_received
                    self.last_rate_update = current_time
                
                # Pequeña pausa para no saturar la CPU
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error al leer datos: {e}")
                time.sleep(0.1)  # Pausa más larga en caso de error
    
    def update_plot(self, frame):
        """Actualizar la gráfica (llamada por FuncAnimation)"""
        if not self.times or len(self.times) < 2:
            return self.signal_line,
        
        # Convertir deques a arrays para graficación
        x_data = np.array(self.times)
        y_data = np.array(self.values)
        
        # Actualizar datos de la gráfica
        self.signal_line.set_data(x_data, y_data)
        
        # Establecer ventana deslizante
        if len(x_data) > 0:
            current_time = x_data[-1]
            self.ax1.set_xlim(current_time - DISPLAY_TIME, current_time)
        
        # Actualizar texto de estadísticas
        stats_str = (f"Paquetes: {self.packets_received} | "
                     f"Muestras/s: {self.samples_per_second} | "
                     f"Inválidos: {self.invalid_packets} | "
                     f"Duplicados: {self.duplicate_packets}")
        self.stats_text.set_text(stats_str)
                
        return self.signal_line, self.stats_text
    
    def run(self):
        """Iniciar el monitor"""
        if not self.connect():
            return
        
        # Configurar la animación
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=40, blit=True)
        
        # Configurar eventos de teclado
        def on_key(event):
            if event.key == ' ':  # Espacio para iniciar/detener
                if self.running:
                    self.stop_acquisition()
                elif self.required_devices_connected:
                    # Iniciar, solo si los dispositivos requeridos están conectados
                    self.start_acquisition()
                else:
                    print("\nNo se puede iniciar la adquisición: dispositivos requeridos no conectados.")
                    print("Use la tecla 'C' para verificar conexiones.\n")
            elif event.key == 'c':  # C para verificar conexiones
                if not self.running:  # Solo verificar si no está capturando
                    self.check_slave_connections()
            elif event.key == 'q':  # Q para salir
                plt.close()
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Actualizar instrucciones para reflejar el requisito de conexión
        plt.figtext(0.5, 0.01, 
                   "Controles: Espacio = Iniciar/Detener (requiere dispositivos conectados), " +
                   "C = Verificar Conexiones (solo cuando está detenido), Q = Salir", 
                   ha="center", fontsize=10)
        
        # Mostrar la gráfica
        plt.tight_layout()
        plt.show()
        
        # Limpiar al salir
        self.stop_acquisition()
        if self.serial:
            print(f"Puerto {self.port} cerrado")
            self.serial.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor de Señal Cruda')
    parser.add_argument('-p', '--port', default=DEFAULT_PORT,
                        help=f'Puerto serial (default: {DEFAULT_PORT})')
    parser.add_argument('-b', '--baudrate', type=int, default=DEFAULT_BAUDRATE,
                        help=f'Velocidad en baudios (default: {DEFAULT_BAUDRATE})')
    args = parser.parse_args()
    
    monitor = PulseMonitor(port=args.port, baudrate=args.baudrate)
    monitor.run()
