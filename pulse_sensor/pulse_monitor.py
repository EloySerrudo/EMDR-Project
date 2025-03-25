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
PACKET_SIZE = 12        # Tamaño en bytes de cada paquete

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
                                
                                # Añadir a las colas
                                self.times.append(timestamp_s)
                                self.values.append(value)
                                
                                # Actualizar contadores
                                self.samples_received += 1
                                self.packets_received += 1
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
                else:
                    self.start_acquisition()
            elif event.key == 'q':  # Q para salir
                plt.close()
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Agregar instrucciones en la figura
        plt.figtext(0.5, 0.01, 
                   "Controles: Espacio = Iniciar/Detener, Q = Salir", 
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
