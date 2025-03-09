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
BUFFER_SIZE = 512  # Debe coincidir con el BUFFER_SIZE del Arduino
SAMPLE_RATE = 1000  # Hz (debe coincidir con I2S_SAMPLE_RATE del Arduino)
DISPLAY_TIME = 10  # Segundos de datos a mostrar en la gráfica

class PulseMonitor:
    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE, display_time=DISPLAY_TIME):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.reading_thread = None
        
        # Para almacenar los datos
        self.display_size = display_time * SAMPLE_RATE
        self.times = deque(maxlen=self.display_size)
        self.values = deque(maxlen=self.display_size)
        self.start_time = None
        self.last_timestamp = 0
        
        # Configuración de la gráfica
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.line, = self.ax.plot([], [], lw=1)
        
        # Configurar ejes y títulos
        self.ax.set_xlabel('Tiempo (s)')
        self.ax.set_ylabel('Valor ADC')
        self.ax.set_title('Monitor de Pulso Cardiaco en Tiempo Real')
        self.ax.set_ylim(0, 8191)  # ADC de 12 bits (0-4095)
        self.ax.set_xlim(0, display_time)
        self.ax.grid(True)
        
    def connect(self):
        """Conectar al puerto serial"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate)
            print(f"Conectado a {self.port} a {self.baudrate} baudios")
            return True
        except serial.SerialException as e:
            print(f"Error al conectar al puerto {self.port}: {e}")
            return False
    
    def start_acquisition(self):
        """Iniciar la adquisición de datos"""
        if self.serial and not self.running:
            # Limpiar buffers anteriores
            self.times.clear()
            self.values.clear()
            self.last_timestamp = 0
            
            # Enviar comando al ESP32 para iniciar la captura
            self.serial.write(b'S')
            
            # Iniciar captura directamente sin esperar confirmación
            self.running = True
            self.start_time = time.time()
            
            # Iniciar hilo de lectura
            self.reading_thread = threading.Thread(target=self._read_data)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            print("Adquisición iniciada")

    def stop_acquisition(self):
        """Detener la adquisición de datos"""
        if self.serial and self.running:
            # Enviar comando al ESP32 para detener la captura
            self.serial.write(b'P')
            
            # Detener captura directamente sin esperar confirmación
            self.running = False
            if self.reading_thread:
                self.reading_thread.join(timeout=1.0)
            print("Adquisición detenida")

    def _read_data(self):
        """Función que se ejecuta en un hilo separado para leer datos"""
        sample_interval = 1.0 / SAMPLE_RATE  # Intervalo de tiempo entre muestras
        
        while self.running:
            available = self.serial.in_waiting
            if available >= 2:  # Al menos un valor de 16 bits (2 bytes)
                # Determinar cuántas muestras completas podemos leer
                samples_to_read = min(available // 2, BUFFER_SIZE)
                
                if samples_to_read > 0:
                    # Leer muestras completas
                    data = self.serial.read(samples_to_read * 2)
                    
                    # Convertir bytes a valores enteros (uint16)
                    values = []
                    for i in range(0, len(data), 2):
                        if i + 1 < len(data):
                            value = struct.unpack('<H', data[i:i+2])[0]
                            # Ya no necesitamos hacer la operación AND con 0x0FFF 
                            # porque el ESP32 ya envía valores de 12 bits
                            values.append(value)
                    
                    # Agregar valores a las colas con tiempos precisos
                    for value in values:
                        # Incrementar el tiempo exactamente según la frecuencia de muestreo
                        self.last_timestamp += sample_interval
                        self.times.append(self.last_timestamp)
                        self.values.append(value)
            
            # Pequeña pausa para no saturar la CPU
            time.sleep(0.01)
    
    def update_plot(self, frame):
        """Actualizar la gráfica (llamada por FuncAnimation)"""
        if len(self.times) > 0:
            # Convertir deques a listas para la graficación
            x_data = list(self.times)
            y_data = list(self.values)
            
            # Actualizar datos de la gráfica
            self.line.set_data(x_data, y_data)
            
            # Ajustar el eje X para mostrar la ventana de tiempo correcta
            latest_time = x_data[-1]
            earliest_time = max(0, latest_time - DISPLAY_TIME)
            
            # Establecer límites con un pequeño margen para mejor visualización
            self.ax.set_xlim(earliest_time, latest_time)
            
            # Ajustar límites de Y dinámicamente si es necesario
            if len(y_data) > 10:  # Asegurar que haya suficientes datos
                min_val = max(0, min(y_data[-int(self.display_size/2):]) - 100)
                max_val = min(4095, max(y_data[-int(self.display_size/2):]) + 100)
                self.ax.set_ylim(min_val, max_val)
        
        return self.line,
    
    def run(self):
        """Iniciar el monitor"""
        if not self.connect():
            return
        
        # Configurar la animación
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=50, blit=True, save_count=50)
        
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
            self.serial.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor de Pulso Cardiaco')
    parser.add_argument('-p', '--port', default=DEFAULT_PORT,
                        help=f'Puerto serial (default: {DEFAULT_PORT})')
    parser.add_argument('-b', '--baudrate', type=int, default=DEFAULT_BAUDRATE,
                        help=f'Velocidad en baudios (default: {DEFAULT_BAUDRATE})')
    args = parser.parse_args()
    
    monitor = PulseMonitor(port=args.port, baudrate=args.baudrate)
    monitor.run()
