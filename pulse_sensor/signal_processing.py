"""
Módulo para procesamiento de señales en tiempo real.
Contiene funciones para filtrar señales EOG y fotopletismográficas,
y para calcular la frecuencia cardiaca.
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from collections import deque

class RealTimeFilter:
    """Clase para implementar filtros en tiempo real."""
    
    def __init__(self, filter_type='bandpass', fs=125, lowcut=0.5, highcut=5.0, order=4):
        """
        Inicializar filtro.
        
        Args:
            filter_type: Tipo de filtro ('lowpass', 'highpass', 'bandpass')
            fs: Frecuencia de muestreo en Hz
            lowcut: Frecuencia de corte inferior para bandpass/highpass
            highcut: Frecuencia de corte superior para bandpass/lowpass
            order: Orden del filtro
        """
        self.fs = fs
        self.lowcut = lowcut
        self.highcut = highcut
        self.filter_type = filter_type
        self.order = order
        
        # Crear coeficientes del filtro
        self._design_filter()
        
        # Estado del filtro (para filtrado en tiempo real)
        self.zi = signal.lfilter_zi(self.b, self.a)
        self.z = self.zi.copy()
        
    def _design_filter(self):
        """Calcular coeficientes del filtro."""
        nyquist = 0.5 * self.fs
        
        if self.filter_type == 'bandpass':
            low = self.lowcut / nyquist
            high = self.highcut / nyquist
            self.b, self.a = signal.butter(self.order, [low, high], btype='band')
        elif self.filter_type == 'lowpass':
            cutoff = self.highcut / nyquist
            self.b, self.a = signal.butter(self.order, cutoff, btype='low')
        elif self.filter_type == 'highpass':
            cutoff = self.lowcut / nyquist
            self.b, self.a = signal.butter(self.order, cutoff, btype='high')
        else:
            raise ValueError(f"Tipo de filtro desconocido: {self.filter_type}")
            
    def reset(self):
        """Reiniciar el filtro."""
        self.z = self.zi.copy()
        
    def filter(self, data):
        """
        Aplicar filtro a los datos en tiempo real.
        
        Args:
            data: Valor único o array de datos
            
        Returns:
            Datos filtrados y nuevo estado del filtro
        """
        if np.isscalar(data):
            # Un solo valor
            filtered, self.z = signal.lfilter(self.b, self.a, [data], zi=self.z)
            return filtered[0]
        else:
            # Array de valores
            filtered, self.z = signal.lfilter(self.b, self.a, data, zi=self.z)
            return filtered


class HeartRateCalculator:
    """Clase para calcular frecuencia cardiaca en tiempo real."""
    
    def __init__(self, fs=125, window_size=5):
        """
        Inicializar calculador de frecuencia cardiaca.
        
        Args:
            fs: Frecuencia de muestreo en Hz
            window_size: Tamaño de la ventana para calcular HR (segundos)
        """
        self.fs = fs
        self.window_size = window_size
        self.buffer_size = int(window_size * fs)
        
        # Buffer para almacenar valores filtrados
        self.ppg_buffer = deque(maxlen=self.buffer_size)
        
        # Para detección de picos
        self.min_bpm = 40
        self.max_bpm = 180
        self.min_peak_distance = int(fs * 60 / self.max_bpm)  # Mínima distancia entre picos (en muestras)
        self.last_peaks = deque(maxlen=10)  # Guarda los últimos picos detectados
        self.heart_rates = deque(maxlen=5)  # Historial reciente de frecuencias cardíacas
        self.current_hr = 0
        
        # Umbrales adaptativos
        self.threshold = 0
        self.adaptive_influence = 0.125  # Influencia de nuevos datos en el umbral
        
    def reset(self):
        """Reiniciar el calculador."""
        self.ppg_buffer.clear()
        self.last_peaks.clear()
        self.heart_rates.clear()
        self.current_hr = 0
        self.threshold = 0
        
    def update(self, new_value):
        """
        Actualizar con un nuevo valor de señal PPG filtrada.
        
        Args:
            new_value: Nuevo valor de la señal PPG filtrada
            
        Returns:
            Frecuencia cardiaca estimada (0 si aún no hay suficientes datos)
        """
        # Añadir nuevo valor al buffer
        self.ppg_buffer.append(new_value)
        
        # Esperar a que el buffer esté suficientemente lleno
        if len(self.ppg_buffer) < self.buffer_size * 0.5:
            return 0
            
        # Calcular umbral adaptativo si aún no está establecido
        if self.threshold == 0:
            self.threshold = 0.6 * (max(self.ppg_buffer) - min(self.ppg_buffer))
            
        # Actualizar umbral de forma adaptativa
        signal_range = max(self.ppg_buffer) - min(self.ppg_buffer)
        target_threshold = 0.6 * signal_range
        self.threshold = (1 - self.adaptive_influence) * self.threshold + self.adaptive_influence * target_threshold
        
        # Detectar picos en la ventana actual
        data = np.array(self.ppg_buffer)
        peaks, _ = signal.find_peaks(data, height=self.threshold, distance=self.min_peak_distance)
        
        # Si hay suficientes picos, calcular frecuencia cardiaca
        if len(peaks) >= 2:
            # Calcular intervalos entre picos
            intervals = np.diff(peaks) / self.fs  # en segundos
            
            # Calcular BPM basado en intervalos
            bpm_values = 60 / intervals  # 60 segundos / intervalo = BPM
            
            # Filtrar BPM fuera de rango
            valid_bpm = [bpm for bpm in bpm_values if self.min_bpm <= bpm <= self.max_bpm]
            
            if valid_bpm:
                # Calcular BPM promedio
                hr = np.median(valid_bpm)  # Usando mediana para ser más resistente a valores atípicos
                
                # Añadir al historial
                self.heart_rates.append(hr)
                
                # Obtener promedio de las últimas mediciones
                self.current_hr = np.mean(self.heart_rates)
                
        return self.current_hr
        
    def get_heart_rate(self):
        """Obtener la frecuencia cardiaca actual."""
        return self.current_hr


def process_eog_signal(raw_signal, fs=125):
    """
    Procesar señal EOG: aplicar filtro pasa-bajas.
    
    Args:
        raw_signal: Señal EOG sin procesar
        fs: Frecuencia de muestreo
        
    Returns:
        Señal EOG filtrada
    """
    # Crear filtro pasa-bajas para EOG (0-10 Hz)
    eog_filter = RealTimeFilter(filter_type='lowpass', fs=fs, highcut=10.0, order=4)
    
    # Aplicar filtro
    filtered_eog = eog_filter.filter(raw_signal)
    
    return filtered_eog

def process_ppg_signal(raw_signal, fs=125):
    """
    Procesar señal fotopletismográfica: aplicar filtro pasa-banda.
    
    Args:
        raw_signal: Señal PPG sin procesar
        fs: Frecuencia de muestreo
        
    Returns:
        Señal PPG filtrada
    """
    # Crear filtro pasa-banda para PPG (0.5-5 Hz)
    ppg_filter = RealTimeFilter(filter_type='bandpass', fs=fs, lowcut=0.5, highcut=5.0, order=4)
    
    # Aplicar filtro
    filtered_ppg = ppg_filter.filter(raw_signal)
    
    return filtered_ppg


# Ejemplos de uso
if __name__ == "__main__":
    # Generar señal de prueba 
    fs = 125
    t = np.arange(0, 10, 1/fs)
    
    # Simular EOG con ruido
    eog_raw = np.sin(2 * np.pi * 0.5 * t) + 0.2 * np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    
    # Simular PPG con ruido
    ppg_raw = np.sin(2 * np.pi * 1.2 * t) + 0.2 * np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    
    # Filtrar
    eog_filtered = process_eog_signal(eog_raw, fs)
    ppg_filtered = process_ppg_signal(ppg_raw, fs)
    
    # Visualizar resultados
    plt.figure(figsize=(10, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(t, eog_raw)
    plt.title('EOG señal original')
    plt.grid(True)
    
    plt.subplot(2, 2, 2)
    plt.plot(t, eog_filtered)
    plt.title('EOG filtrado')
    plt.grid(True)
    
    plt.subplot(2, 2, 3)
    plt.plot(t, ppg_raw)
    plt.title('PPG señal original')
    plt.grid(True)
    
    plt.subplot(2, 2, 4)
    plt.plot(t, ppg_filtered)
    plt.title('PPG filtrado')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()
