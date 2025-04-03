import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import threading
import time
import argparse
from collections import deque
import pandas as pd  # Añadir pandas para guardado de datos
import os
from datetime import datetime
from signal_processing import RealTimeFilter, HeartRateCalculator  # Importar nuestras clases de procesamiento

# Configuración por defecto
DEFAULT_PORT = 'COM4'  # Cambiar según el puerto que use tu ESP32
DEFAULT_BAUDRATE = 115200
BUFFER_SIZE = 512  # Máximo número de muestras a leer de una vez
SAMPLE_RATE = 125  # Hz (tasa efectiva: 250 SPS ÷ 2 canales)
DISPLAY_TIME = 5   # Segundos de datos a mostrar en la gráfica

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 15        # Tamaño en bytes de cada paquete (actualizado para incluir ambos canales)

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
        self.values_0 = deque(initial_values, maxlen=self.display_size)  # Canal A0 (EOG)
        self.values_1 = deque(initial_values, maxlen=self.display_size)  # Canal A1 (PPG)
        
        # Para almacenar señales filtradas
        self.filtered_values_0 = deque(initial_values, maxlen=self.display_size)  # EOG filtrado
        self.filtered_values_1 = deque(initial_values, maxlen=self.display_size)  # PPG filtrado
        
        # Para almacenar datos sin límite
        self.idx = []
        self.tiempos = []
        self.valores_0 = []
        self.valores_1 = []
        self.valores_filtrados_0 = []
        self.valores_filtrados_1 = []
        self.heart_rates = []
        
        # Filtros en tiempo real
        self.eog_filter = RealTimeFilter(
            filter_type='lowpass', fs=SAMPLE_RATE, highcut=10.0, order=4
        )
        self.ppg_filter = RealTimeFilter(
            filter_type='bandpass', fs=SAMPLE_RATE, lowcut=0.5, highcut=5.0, order=4
        )
        
        # Calculador de frecuencia cardiaca
        self.hr_calculator = HeartRateCalculator(fs=SAMPLE_RATE, window_size=5)
        self.current_heart_rate = 0
        
        # Estadísticas
        self.samples_received = 0
        self.packets_received = 0
        self.invalid_packets = 0
        self.duplicate_packets = 0
        self.last_samples_count = 0
        self.samples_per_second = 0
        self.last_rate_update = time.time()
        self.last_packet_id = -1  # Inicializar con -1 para asegurar que procesemos el primer paquete
        
        # Configuración de la gráfica - tres ejes separados que comparten el eje X
        self.fig, (self.ax0, self.ax1, self.ax2) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
        
        # Eliminar espacio vertical entre los subplots
        self.fig.subplots_adjust(hspace=0)
        
        # Líneas para cada canal en su propio eje
        self.signal_line_0, = self.ax0.plot([], [], '0.8', lw=1.0, label='EOG (raw)')
        self.filtered_line_0, = self.ax0.plot([], [], 'g-', lw=1.5, label='EOG (filtrado)')
        
        self.signal_line_1, = self.ax1.plot([], [], '0.8', lw=1.0, label='Pulso (raw)')
        self.filtered_line_1, = self.ax1.plot([], [], 'm-', lw=1.5, label='Pulso (filtrado)')
        
        # Gráfico para la frecuencia cardiaca
        self.hr_times = deque(initial_times, maxlen=self.display_size)
        self.hr_values = deque(initial_values, maxlen=self.display_size)
        self.hr_line, = self.ax2.plot([], [], 'k-', lw=2.0, label='Frecuencia Cardiaca')
        
        # Configurar ejes y títulos
        self.ax0.set_title('Monitor de Señales Fisiológicas')
        self.ax0.set_ylabel('EOG (mV)')
        self.ax0.grid(True)
        self.ax0.legend(loc='upper right')
        
        self.ax1.set_ylabel('PPG (mV)')
        self.ax1.grid(True)
        self.ax1.legend(loc='upper right')
        
        self.ax2.set_xlabel('Tiempo (s)')
        self.ax2.set_ylabel('BPM')
        self.ax2.grid(True)
        self.ax2.set_ylim(40, 180)  # Rango típico de frecuencia cardiaca
        self.ax2.legend(loc='upper right')
        
        # Establecer límites de los ejes
        self.ax0.set_ylim(-30000, 30000)
        self.ax1.set_ylim(-15000, 20000)
        self.ax0.set_xlim(-display_time, 0)
        
        # Texto para mostrar estadísticas y frecuencia cardiaca
        self.stats_text = self.ax0.text(0.02, 0.95, '', transform=self.ax0.transAxes,
                                      verticalalignment='top', bbox=dict(boxstyle='round', 
                                                                      facecolor='wheat', alpha=0.7))
        self.hr_text = self.ax2.text(0.02, 0.95, 'BPM: --', transform=self.ax2.transAxes,
                                    verticalalignment='top', bbox=dict(boxstyle='round',
                                                                      facecolor='wheat', alpha=0.7))
        
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
            
            # Reiniciar estadísticas y filtros
            self.samples_received = 0
            self.packets_received = 0
            self.invalid_packets = 0
            self.last_samples_count = 0
            self.last_rate_update = time.time()
            
            # Reiniciar filtros y calculador de frecuencia cardiaca
            self.eog_filter.reset()
            self.ppg_filter.reset()
            self.hr_calculator.reset()
            self.current_heart_rate = 0
            
            # Iniciar hilo de lectura
            self.reading_thread = threading.Thread(target=self._read_data)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            print("Adquisición iniciada")
            
            # Limpiar deques y reiniciar con ceros
            self.times.clear()
            self.values_0.clear()
            self.values_1.clear()
            initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
            initial_values = [0] * self.display_size
            self.times.extend(initial_times)
            self.values_0.extend(initial_values)
            self.values_1.extend(initial_values)

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
                                
                                # Valor del canal A0 (2 bytes)
                                value_0 = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # Valor del canal A1 (2 bytes)
                                value_1 = struct.unpack('<h', data_buffer[12:14])[0]
                                
                                # Device ID (1 byte)
                                device_id = data_buffer[14]
                                
                                # Filtrar señales en tiempo real
                                filtered_value_0 = value_0 # self.eog_filter.filter(value_0) #<---EDITADO. USAREMOS DESPUÉS EL FILTRADO PARA EOG
                                filtered_value_1 = self.ppg_filter.filter(value_1)
                                
                                # Calcular frecuencia cardiaca con la señal PPG filtrada
                                hr = self.hr_calculator.update(filtered_value_1)
                                if hr > 0:
                                    self.current_heart_rate = hr
                                    self.hr_times.append(timestamp_s)
                                    self.hr_values.append(hr)
                                    self.heart_rates.append(hr)
                                
                                # Añadir a las colas
                                self.times.append(timestamp_s)
                                self.values_0.append(value_0)
                                self.values_1.append(value_1)
                                self.filtered_values_0.append(filtered_value_0)
                                self.filtered_values_1.append(filtered_value_1)
                                
                                self.idx.append(packet_id)
                                self.tiempos.append(timestamp_ms)
                                self.valores_0.append(value_0)
                                self.valores_1.append(value_1)
                                self.valores_filtrados_0.append(filtered_value_0)
                                self.valores_filtrados_1.append(filtered_value_1)
                                
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
            return self.signal_line_0, self.filtered_line_0, self.signal_line_1, self.filtered_line_1, self.hr_line, self.stats_text, self.hr_text
        
        # Convertir deques a arrays para graficación
        x_data = np.array(self.times)
        y_data_0 = np.array(self.values_0)
        y_data_1 = np.array(self.values_1)
        y_filtered_0 = np.array(self.filtered_values_0)
        y_filtered_1 = np.array(self.filtered_values_1)
        
        # Actualizar datos de las gráficas
        self.signal_line_0.set_data(x_data, y_data_0)
        self.filtered_line_0.set_data(x_data, y_filtered_0)
        self.signal_line_1.set_data(x_data, y_data_1)
        self.filtered_line_1.set_data(x_data, y_filtered_1)
        
        # Actualizar gráfico de frecuencia cardiaca
        if len(self.hr_times) > 1:
            x_hr = np.array(self.hr_times)
            y_hr = np.array(self.hr_values)
            self.hr_line.set_data(x_hr, y_hr)
        
        # Establecer ventana deslizante
        if len(x_data) > 0:
            current_time = x_data[-1]
            self.ax0.set_xlim(current_time - DISPLAY_TIME, current_time)
        
        # Actualizar texto de estadísticas
        stats_str = (f"Paquetes: {self.packets_received} | "
                     f"Muestras/s: {self.samples_per_second} | "
                     f"Inválidos: {self.invalid_packets} | "
                     f"Duplicados: {self.duplicate_packets}")
        self.stats_text.set_text(stats_str)
        
        # Actualizar texto de frecuencia cardiaca
        self.hr_text.set_text(f"BPM: {self.current_heart_rate:.1f}")
                
        return self.signal_line_0, self.filtered_line_0, self.signal_line_1, self.filtered_line_1, self.hr_line, self.stats_text, self.hr_text
    
    def save_data_to_csv(self):
        """Guarda los datos recolectados en un archivo CSV"""
        try:
            if len(self.idx) == 0:
                print("No hay datos para guardar")
                return
                
            # Crear un DataFrame con los datos
            data = {
                'ID': self.idx,
                'Timestamp_ms': self.tiempos,
                'EOG_raw': self.valores_0,
                'EOG_filtrado': self.valores_filtrados_0,
                'PPG_raw': self.valores_1,
                'PPG_filtrado': self.valores_filtrados_1,
                'Heart_Rate': self.heart_rates if self.heart_rates else [0] * len(self.idx)
            }
            df = pd.DataFrame(data)
            
            # Crear carpeta de datos si no existe
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Generar nombre de archivo con fecha y hora
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"pulse_data_{timestamp}.csv")
            
            # Guardar datos
            df.to_csv(filename, index=False)
            print(f"\nDatos guardados en: {filename}")
            print(f"Total de muestras guardadas: {len(self.idx)}")
            
        except Exception as e:
            print(f"Error al guardar datos: {e}")
    
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
                # Guardar datos antes de cerrar
                if len(self.idx) > 0:
                    print("\nGuardando datos antes de salir...")
                    self.save_data_to_csv()
                plt.close()
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Actualizar instrucciones para reflejar el requisito de conexión y el guardado de datos
        plt.figtext(0.5, 0.01, 
                   "Controles: Espacio = Iniciar/Detener, " +
                   "C = Verificar Conexiones, Q = Guardar y Salir", 
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