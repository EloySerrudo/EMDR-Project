import threading
import struct
import numpy as np
from scipy import signal
from collections import deque
from pulse_monitor import PulseMonitor, SAMPLE_RATE, BUFFER_SIZE, DISPLAY_TIME


class PulseFilter:
    """
    Clase para aplicar filtros a las señales de pulso cardiaco
    """
    def __init__(self, cutoff_freq=30, filter_order=101):
        """
        Inicializa el filtro FIR paso bajas
        
        Args:
            cutoff_freq: Frecuencia de corte en Hz
            filter_order: Orden del filtro (debe ser impar)
        """
        self.cutoff_freq = cutoff_freq
        self.filter_order = filter_order if filter_order % 2 == 1 else filter_order + 1
        self.sample_rate = SAMPLE_RATE
        
        # Diseñar coeficientes del filtro FIR paso bajas
        self.b = self._design_lowpass_filter()
        
        # Buffer para mantener muestras anteriores (necesarias para el filtrado)
        self.buffer = deque(maxlen=self.filter_order)
        for _ in range(self.filter_order):
            self.buffer.append(0)
    
    def _design_lowpass_filter(self):
        """
        Diseña un filtro FIR paso bajas usando el método de la ventana
        
        Returns:
            Coeficientes del filtro FIR
        """
        # Normalizar la frecuencia de corte (entre 0 y 1, donde 1 es Nyquist)
        nyquist = 0.5 * self.sample_rate
        normal_cutoff = self.cutoff_freq / nyquist
        
        # Diseñar filtro FIR paso bajas usando ventana Hamming
        b = signal.firwin(self.filter_order, normal_cutoff, window='hamming')
        return b
    
    def reset(self):
        """Reinicia el buffer del filtro"""
        for i in range(len(self.buffer)):
            self.buffer[i] = 0
    
    def apply(self, value):
        """
        Aplica el filtro a un solo valor
        
        Args:
            value: Valor a filtrar
            
        Returns:
            Valor filtrado
        """
        # Agregar nuevo valor al buffer
        self.buffer.append(value)
        
        # Aplicar el filtro (convolución)
        filtered_value = 0
        for i in range(len(self.b)):
            if i < len(self.buffer):
                filtered_value += self.b[i] * self.buffer[-(i+1)]
        
        return filtered_value
    
    def apply_batch(self, values):
        """
        Aplica el filtro a un array de valores
        
        Args:
            values: Array de valores a filtrar
            
        Returns:
            Array de valores filtrados
        """
        # Asegurarse de que values sea un array numpy
        values = np.array(values)
        
        # Aplicar filtro usando convolución
        filtered_values = signal.filtfilt(self.b, 1.0, values)
        return filtered_values


class FilteredPulseMonitor(PulseMonitor):
    """
    Clase que extiende PulseMonitor para agregar funcionalidades de filtrado
    """
    def __init__(self, port, baudrate, display_time=5, cutoff_freq=30, filter_order=101):
        super().__init__(port, baudrate, display_time)
        
        # Crear el filtro
        self.filter = PulseFilter(cutoff_freq, filter_order)
        
        # Datos filtrados
        self.filtered_values = deque(maxlen=self.display_size)
        
        # Agregar una línea adicional para los datos filtrados
        self.filtered_line, = self.ax.plot([], [], 'r-', lw=1, label='Filtrado')
        
        # Actualizar la leyenda
        self.line.set_label('Original')
        self.ax.legend(loc='upper left')
    
    def start_acquisition(self):
        """Iniciar la adquisición de datos"""
        if self.serial and not self.running:
            # Limpiar buffers anteriores
            self.times.clear()
            self.values.clear()
            self.filtered_values.clear()
            self.filter.reset()
            self.last_timestamp = -5.0
            
            # Continuar con el método original
            super().start_acquisition()
    
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
                            # Convertir bytes a valor entero (uint16)
                            value = struct.unpack('<H', data[i:i+2])[0]
                            
                            # Incrementar el tiempo exactamente según la frecuencia de muestreo
                            self.last_timestamp += sample_interval
                            self.times.append(self.last_timestamp)
                            self.values.append(value)
                            
                            # Aplicar filtro y almacenar el valor filtrado
                            filtered_value = self.filter.apply(value)
                            self.filtered_values.append(filtered_value)

    def update_plot(self, frame):
        """Actualizar la gráfica (llamada por FuncAnimation)"""
        if len(self.times) > 0:
            # Convertir deques a listas para la graficación
            x_data = np.array(self.times)
            y_data = np.array(self.values) -1500
            y_filtered_data = np.array(self.filtered_values)
            
            # Actualizar datos de la gráfica
            self.line.set_data(x_data, y_data)
            self.filtered_line.set_data(x_data, y_filtered_data)
            
            # Obtener el tiempo actual (último punto de datos)
            current_time = x_data[-1]
            
            # Establecer ventana fija de ancho DISPLAY_TIME que se desliza con los datos
            window_start = current_time - DISPLAY_TIME
            window_end = current_time
            self.ax.set_xlim(window_start, window_end)
            
            # Ajustar escala Y automáticamente si es necesario
            all_y = np.concatenate((y_data, y_filtered_data))
            if len(all_y) > 0:
                y_min, y_max = all_y.min(), all_y.max()
                margin = (y_max - y_min) * 0.1  # 10% de margen
                self.ax.set_ylim(y_min - margin, y_max + margin)
        
        return self.line, self.filtered_line

# Código para ejecutar el monitor con filtrado
if __name__ == "__main__":
    import argparse
    from pulse_monitor import DEFAULT_PORT, DEFAULT_BAUDRATE
    
    parser = argparse.ArgumentParser(description='Monitor de Pulso Cardiaco con Filtro FIR Paso Bajas')
    parser.add_argument('-p', '--port', default=DEFAULT_PORT,
                        help=f'Puerto serial (default: {DEFAULT_PORT})')
    parser.add_argument('-b', '--baudrate', type=int, default=DEFAULT_BAUDRATE,
                        help=f'Velocidad en baudios (default: {DEFAULT_BAUDRATE})')
    parser.add_argument('-c', '--cutoff', type=float, default=30.0,
                        help='Frecuencia de corte en Hz (default: 30.0)')
    parser.add_argument('-o', '--order', type=int, default=101,
                        help='Orden del filtro FIR (default: 101)')
    args = parser.parse_args()
    
    monitor = FilteredPulseMonitor(
        port=args.port, 
        baudrate=args.baudrate,
        cutoff_freq=args.cutoff,
        filter_order=args.order
    )
    monitor.run()
