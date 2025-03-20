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
DEFAULT_PORT = 'COM6'  # Cambiar según el puerto que use tu ESP32. En la laptop es COM6, en la PC es COM4
DEFAULT_BAUDRATE = 115200
BUFFER_SIZE = 512  # Máximo número de muestras a leer de una vez, para control de flujo de datos
SAMPLE_RATE = 250  # Hz (actualizado para coincidir con SAMPLE_RATE del Arduino = 250Hz)
DISPLAY_TIME = 5  # Segundos de datos a mostrar en la gráfica

class PulseMonitor:
    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE, display_time=DISPLAY_TIME):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.reading_thread = None
        
        # Para almacenar los datos
        self.display_size = display_time * SAMPLE_RATE
        sample_interval = 1.0 / SAMPLE_RATE

        # Inicializar deques con valores cero
        initial_times = [-display_time + i * sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size

        self.times = deque(initial_times, maxlen=self.display_size)
        self.values = deque(initial_values, maxlen=self.display_size)
        self.start_time = None
        self.last_timestamp = -sample_interval  # Inicializar para que la primera muestra sea exactamente en 0        
        
        # Configuración de la gráfica
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.line, = self.ax.plot([], [], lw=1)
        
        # Configurar ejes y títulos
        self.ax.set_xlabel('Tiempo (s)')
        self.ax.set_ylabel('Valor ADS1115')
        self.ax.set_title('Monitor de Pulso Cardiaco en Tiempo Real (ADS1115)')
        # Ajuste de límites para el ADS1115 en modo diferencial con GAIN_ONE
        self.ax.set_ylim(-20000, 20000)  # Ajustado para el rango del ADS1115
        self.ax.set_xlim(-display_time, 0)
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
            # self.times.clear()
            # self.values.clear()
            # self.last_timestamp = -sample_interval
            
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
        read_event = threading.Event()
        while self.running and not read_event.wait(timeout=0.001):
            # Pequeña pausa para no saturar la CPU
            available = self.serial.in_waiting
            if available >= 2:  # Al menos un valor de 16 bits (2 bytes)
                # Determinar cuántas muestras completas podemos leer
                samples_to_read = min(available // 2, BUFFER_SIZE)
                
                if samples_to_read > 0:
                    # Leer muestras completas
                    data = self.serial.read(samples_to_read * 2)
                    
                    # Leer y procesar los datos en un solo ciclo
                    for i in range(0, len(data), 2):
                        if i + 1 < len(data):
                            # Convertir bytes a valor entero (int16_t porque los datos son diferenciales)
                            value = struct.unpack('<h', data[i:i+2])[0]
                            
                            # Incrementar el tiempo exactamente según la frecuencia de muestreo
                            self.last_timestamp += sample_interval
                            self.times.append(self.last_timestamp)
                            self.values.append(value)

    def update_plot(self, frame):
        """Actualizar la gráfica (llamada por FuncAnimation)"""
        if len(self.times) > 0:
            # Convertir deques a listas para la graficación
            x_data = np.array(self.times)
            y_data = np.array(self.values)
            
            # Actualizar datos de la gráfica
            self.line.set_data(x_data, y_data)
            
            # Obtener el tiempo actual (último punto de datos)
            current_time = x_data[-1]
            
            # Establecer ventana fija de ancho DISPLAY_TIME que se desliza con los datos
            window_start = current_time - DISPLAY_TIME
            window_end = current_time
            self.ax.set_xlim(window_start, window_end)
                    
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
            print(f"Puerto {self.port} cerrado")
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
