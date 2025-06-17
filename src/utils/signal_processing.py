"""
Módulo para procesamiento de señales en tiempo real.
Contiene funciones para filtrar la señal fotopletismográfica (PPG),
y para calcular la frecuencia cardiaca.
"""

import numpy as np
from scipy import signal
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


class OnlineEOGFilter:
    """Clase para implementar filtros para EOG tiempo real."""
    def __init__(self, fs=125, lowcut=0.05, highcut=30.0):
        self.fs = fs    # Frecuencia de muestreo
        nyq = self.fs*0.5    # Frecuencia de Nyquist
        self.lowcut = lowcut
        self.highcut = highcut

        # 1. High-pass 0.05 Hz, 1er orden
        # Objetivo: Descentra cada ventana y evita saturar el codec gráfico
        # Por qué: retiras parpadeos de baseline sin tocar la componente de posición ocular (< 0.1 Hz).
        self.b_hp, self.a_hp = signal.butter(1, self.lowcut/nyq, 'highpass')
        self.z_hp = signal.lfilter_zi(self.b_hp, self.a_hp)

        # 2. Notch 50 Hz
        # Objetivo: Matar interferencia residual sin subir el orden del FIR principal
        # Por qué: Solo un bi-quad; 0.3 ms de cómputo en un ESP32, atenuación > 35 dB y fase plana en < 30 Hz.
        f0 = 50  # Frecuencia de la interferencia de la red eléctrica
        Q = 30   # Factor de calidad del notch
        self.b_notch, self.a_notch = signal.iirnotch(f0/(nyq), Q)
        self.z_notch = signal.lfilter_zi(self.b_notch, self.a_notch)

        # 3. Low-pass FIR 30 Hz
        # Objetivo: Dejar banda útil 0 – 30 Hz con fase lineal
        # Por qué: FIR lineal-fase evita distorsionar las sacadas; al ser 100 taps y 125 Hz, 
        # el retardo ≈ 0.4 s: aceptable para “ver” lo que pasa en clínica (no para control 
        # en bucle cerrado).
        self.b_lp = signal.firwin(numtaps=101, cutoff=self.highcut, fs=self.fs, window='hamming')
        self.zi_lp = np.zeros(len(self.b_lp)-1)

    def reset(self):
        """Reiniciar el filtro."""
        self.z_hp = signal.lfilter_zi(self.b_hp, self.a_hp)
        self.z_notch = signal.lfilter_zi(self.b_notch, self.a_notch)
        self.zi_lp.fill(0)

    def __call__(self, x):
        # high-pass
        y, self.z_hp = signal.lfilter(self.b_hp, self.a_hp, [x], zi=self.z_hp)
        # notch
        y, self.z_notch = signal.lfilter(self.b_notch, self.a_notch, y, zi=self.z_notch)
        # FIR low-pass
        y, self.zi_lp = signal.lfilter(self.b_lp, [1.0], y, zi=self.zi_lp)
        return y[0]


class PulseDetector:
    """Clase para detectar pulsos cardíacos a partir de señales PPG filtradas"""
    
    def __init__(self, sample_rate, buffer_size=125, threshold_factor=0.6):
        """
        Inicializa el detector de pulsos.
        
        Args:
            sample_rate: Frecuencia de muestreo en Hz
            buffer_size: Tamaño del buffer para análisis (recomendado ~1s de datos)
            threshold_factor: Factor para calcular el umbral adaptativo
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.threshold_factor = threshold_factor
        
        # Buffer para análisis de pulso
        self.signal_buffer = deque(maxlen=buffer_size)
        
        # Estado del pulso
        self.prev_pulse_state = 0  # 0 = sin pulso, 1 = pulso
        self.pulse_detected = False
        self.last_pulse_time = 0
        self.pulse_periods = deque(maxlen=10)  # Últimas 10 mediciones de periodo
        
        # Valores adaptables
        self.threshold = 0
        # Aumentar el período refractario a 500ms (adecuado para detectar un solo pico por ciclo)
        self.minimum_delay_samples = int(0.5 * sample_rate)  # 500 ms mínimo entre pulsos
        self.samples_since_last_pulse = self.minimum_delay_samples
        
        # Nuevos parámetros para detección de pico dominante
        self.peak_values = deque(maxlen=5)  # Almacenar los últimos valores pico
        self.in_potential_pulse = False
        self.current_pulse_height = 0
        self.current_pulse_count = 0
        self.last_peak_time = 0
    
    def add_sample(self, filtered_value, timestamp):
        """
        Añade una nueva muestra y analiza si hay un pulso.
        
        Args:
            filtered_value: Valor de la señal filtrada
            timestamp: Tiempo asociado a la muestra
            
        Returns:
            bool: True si se detectó un pulso, False en caso contrario
            int: Estado del pulso (0 = sin pulso, 1 = pulso)
        """
        self.signal_buffer.append(filtered_value)
        self.samples_since_last_pulse += 1
        
        # Necesitamos suficientes muestras para calcular el umbral
        if len(self.signal_buffer) < self.buffer_size // 2:
            return False, 0
        
        # Calcular umbral adaptativo basado en valores recientes
        recent_signal = list(self.signal_buffer)[-self.buffer_size//2:]
        signal_min = min(recent_signal)
        signal_max = max(recent_signal)
        signal_range = signal_max - signal_min
        
        # Ajustar umbral
        self.threshold = signal_min + signal_range * self.threshold_factor
        
        # Detectar estado de pulso (subida por encima del umbral)
        pulse_state = 1 if filtered_value > self.threshold else 0
        pulse_detected = False
        
        # Algoritmo mejorado para detectar picos dominantes
        if pulse_state == 1:
            # Estamos por encima del umbral
            if not self.in_potential_pulse:
                # Comenzando un nuevo pulso potencial
                self.in_potential_pulse = True
                self.current_pulse_height = filtered_value
                self.current_pulse_count = 0
            else:
                # Actualizamos la altura si encontramos un valor mayor (buscando pico)
                if filtered_value > self.current_pulse_height:
                    self.current_pulse_height = filtered_value
        else:
            # Estamos por debajo del umbral
            if self.in_potential_pulse:
                # Terminó un pulso potencial, verificamos si es válido
                time_since_last_peak = timestamp - self.last_peak_time
                
                # Solo consideramos un pulso completo si:
                # 1. Ha pasado suficiente tiempo desde el último pico principal
                # 2. El pulso es lo suficientemente alto (al menos 70% del promedio de picos anteriores)
                avg_peak = np.mean(self.peak_values) if self.peak_values else self.current_pulse_height
                peak_threshold = avg_peak * 0.7
                
                if (time_since_last_peak > 0.4 and  # Mínimo 400ms entre picos principales
                    self.samples_since_last_pulse >= self.minimum_delay_samples and 
                    self.current_pulse_height > peak_threshold):
                    
                    # Es un pico dominante (principal)
                    pulse_detected = True
                    self.peak_values.append(self.current_pulse_height)
                    
                    # Calcular periodo entre pulsos
                    if self.last_pulse_time > 0:
                        period = timestamp - self.last_pulse_time
                        if 0.3 < period < 2.0:  # 30-200 BPM es fisiológicamente razonable
                            self.pulse_periods.append(period)
                    
                    self.last_pulse_time = timestamp
                    self.last_peak_time = timestamp
                    self.samples_since_last_pulse = 0
                
                # Reset para el siguiente pulso
                self.in_potential_pulse = False
                self.current_pulse_count = 0
        
        self.prev_pulse_state = pulse_state
        self.pulse_detected = pulse_detected
        
        return pulse_detected, pulse_state
    
    def get_heart_rate(self):
        """
        Calcula la frecuencia cardíaca basada en los periodos de pulso medidos.
        
        Returns:
            float: Frecuencia cardíaca en BPM, o 0 si no hay suficientes datos
        """
        if not self.pulse_periods or len(self.pulse_periods) < 2:
            return 0
        
        # Calcular frecuencia cardíaca promedio
        avg_period = sum(self.pulse_periods) / len(self.pulse_periods)
        if avg_period <= 0:
            return 0
            
        # Convertir periodo (segundos) a BPM
        heart_rate = 60 / avg_period
        
        # Limitar valores razonables (40-200 BPM)
        return max(40, min(200, heart_rate))
    
    def reset(self):
        """Reinicia el detector de pulsos a su estado inicial"""
        self.last_beat_time = 0
        self.bpm = 0
        self.beat_detected = False
        self.ibi = 0  # Intervalo entre latidos (Inter-Beat Interval)
        self.beats = []  # Lista para almacenar los últimos tiempos de latido
        self.pulse_state = 0  # Estado del pulso (0 = esperando, 1 = detectado)
        
        # Reiniciar variables para la detección 
        self.threshold = 0
        self.peak = 0
        self.trough = 0
        self.average_peak = 0
        self.average_trough = 0
        
        # Si tienes filtros internos, también reinícialos
        if hasattr(self, '_filter'):
            self._filter.reset()
