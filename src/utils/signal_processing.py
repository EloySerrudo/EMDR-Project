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
    """
    Filtro optimizado para señales EOG en tiempo real.
    
    Cadena de procesamiento:
    1. High-pass 0.05 Hz (orden 1) - Elimina deriva DC, conserva posición ocular
    2. Notch configurable 50/60 Hz - Elimina interferencia de red eléctrica  
    3. Low-pass FIR 30 Hz - Banda útil con fase lineal
    
    Retardo total: ~400ms (aceptable para monitoreo clínico)
    """
    
    def __init__(self, fs=125, hp_cutoff=0.05, lp_cutoff=30.0, 
                 notch_freq=50, notch_q=30, fir_taps=101):
        """
        Inicializar filtro EOG compuesto.
        
        Args:
            fs: Frecuencia de muestreo (Hz)
            hp_cutoff: Frecuencia de corte HP (Hz) - conserva posición ocular
            lp_cutoff: Frecuencia de corte LP (Hz) - banda útil EOG
            notch_freq: Frecuencia notch (Hz) - 50 o 60 Hz típicamente
            notch_q: Factor de calidad del notch (mayor = más selectivo)
            fir_taps: Número de taps del FIR (impar recomendado)
        """
        self.fs = fs
        self.hp_cutoff = hp_cutoff
        self.lp_cutoff = lp_cutoff
        self.notch_freq = notch_freq
        self.notch_q = notch_q
        self.fir_taps = fir_taps if fir_taps % 2 == 1 else fir_taps + 1  # Asegurar impar
        
        self._design_filters()
        self.reset()
    
    def _design_filters(self):
        """Diseñar todos los filtros de la cadena."""
        nyq = self.fs * 0.5
        
        # 1. High-pass Butterworth orden 1
        # Conserva componentes de posición ocular (>0.05 Hz)
        self.b_hp, self.a_hp = signal.butter(1, self.hp_cutoff/nyq, 'highpass')
        
        # 2. Filtro notch único
        if self.notch_freq < nyq:  # Solo si está dentro del rango válido
            self.b_notch, self.a_notch = signal.iirnotch(self.notch_freq/nyq, self.notch_q)
            self.notch_enabled = True
        else:
            # Si la frecuencia está fuera de rango, desactivar notch
            self.notch_enabled = False
            print(f"Advertencia: Frecuencia notch {self.notch_freq} Hz fuera de rango válido (< {nyq} Hz)")
        
        # 3. Low-pass FIR con ventana Hamming
        # Fase lineal para preservar forma de sacadas
        self.b_lp = signal.firwin(
            self.fir_taps, 
            self.lp_cutoff, 
            fs=self.fs, 
            window='hamming'
        )
        
        print(f"EOG Filter configurado:")
        print(f"  - HP: {self.hp_cutoff} Hz (orden 1)")
        if self.notch_enabled:
            print(f"  - Notch: {self.notch_freq} Hz (Q={self.notch_q})")
        else:
            print(f"  - Notch: DESACTIVADO")
        print(f"  - LP: {self.lp_cutoff} Hz (FIR {self.fir_taps} taps)")
        print(f"  - Retardo estimado: {(self.fir_taps-1)/(2*self.fs)*1000:.1f} ms")
    
    def reset(self):
        """Reiniciar todos los estados del filtro."""
        # Estado HP
        self.z_hp = signal.lfilter_zi(self.b_hp, self.a_hp)
        
        # Estado Notch (solo si está habilitado)
        if self.notch_enabled:
            self.z_notch = signal.lfilter_zi(self.b_notch, self.a_notch)
        
        # Buffer FIR (implementación eficiente)
        self.fir_buffer = deque(maxlen=len(self.b_lp))
        self.fir_buffer.extend([0.0] * len(self.b_lp))
    
    def filter(self, x):
        """
        Procesar una muestra a través de la cadena de filtros.
        
        Args:
            x: Muestra de entrada (valor único)
            
        Returns:
            float: Muestra filtrada
        """
        # Convertir a float si es necesario
        if not isinstance(x, (int, float)):
            x = float(x)
        
        # 1. High-pass: eliminar deriva DC
        # y, self.z_hp = signal.lfilter(self.b_hp, self.a_hp, [x], zi=self.z_hp)
        
        # 2. Notch filter: eliminar interferencia de red (solo si está habilitado)
        if self.notch_enabled:
            y, self.z_notch = signal.lfilter(self.b_notch, self.a_notch, [x], zi=self.z_notch)
        
        # 3. FIR Low-pass: filtrado final con fase lineal
        self.fir_buffer.append(y[0])
        
        # Convolución eficiente usando producto punto
        filtered_output = sum(
            sample * coeff 
            for sample, coeff in zip(self.fir_buffer, reversed(self.b_lp))
        )
        
        return filtered_output
    
    def get_filter_info(self):
        """Obtener información del filtro para depuración."""
        return {
            'sample_rate': self.fs,
            'hp_cutoff': self.hp_cutoff,
            'lp_cutoff': self.lp_cutoff,
            'notch_frequency': self.notch_freq if self.notch_enabled else None,
            'notch_q': self.notch_q if self.notch_enabled else None,
            'notch_enabled': self.notch_enabled,
            'fir_taps': self.fir_taps,
            'estimated_delay_ms': (self.fir_taps-1)/(2*self.fs)*1000,
            'total_filters': 2 + (1 if self.notch_enabled else 0)  # HP + Notch + LP
        }

    def test_response(self, plot=False):
        """
        Probar respuesta en frecuencia del filtro completo.
        Útil para verificar el diseño.
        """
        try:
            import matplotlib.pyplot as plt
            
            # Crear filtro equivalente para análisis
            w, h_hp = signal.freqz(self.b_hp, self.a_hp, fs=self.fs, worN=1024)
            
            # Combinar con notch si está habilitado
            if self.notch_enabled:
                _, h_notch = signal.freqz(self.b_notch, self.a_notch, fs=self.fs, worN=1024)
                h_hp = h_hp * h_notch
            
            # Combinar con FIR
            _, h_lp = signal.freqz(self.b_lp, [1.0], fs=self.fs, worN=1024)
            h_total = h_hp * h_lp
            
            if plot:
                plt.figure(figsize=(12, 8))
                
                # Magnitud
                plt.subplot(2, 1, 1)
                plt.semilogx(w, 20 * np.log10(abs(h_total)))
                plt.title('Respuesta en Frecuencia - Filtro EOG Completo')
                plt.xlabel('Frecuencia (Hz)')
                plt.ylabel('Magnitud (dB)')
                plt.grid(True, alpha=0.3)
                plt.axvline(self.hp_cutoff, color='r', linestyle='--', alpha=0.7, label=f'HP: {self.hp_cutoff} Hz')
                plt.axvline(self.lp_cutoff, color='b', linestyle='--', alpha=0.7, label=f'LP: {self.lp_cutoff} Hz')
                if self.notch_enabled:
                    plt.axvline(self.notch_freq, color='g', linestyle='--', alpha=0.7, label=f'Notch: {self.notch_freq} Hz')
                plt.legend()
                
                # Fase
                plt.subplot(2, 1, 2)
                plt.semilogx(w, np.unwrap( np.angle(h_total, deg=True)))
                plt.xlabel('Frecuencia (Hz)')
                plt.ylabel('Fase (grados)')
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                plt.show()
            
            return w, h_total
            
        except ImportError:
            print("matplotlib no disponible - no se puede mostrar respuesta")
            return None, None


class PPGHeartRateCalculator:
    """
    Calculador de BPM optimizado para monitoreo EMDR en tiempo real.
    
    Estrategia:
    - Primer cálculo: 8 segundos (permite setup sin prisa)
    - Actualizaciones: cada 2 segundos con ventana deslizante de 10s
    - Detección de artefactos y validación automática
    
    NOTA: Recibe señal PPG ya filtrada, no aplica filtrado adicional.
    """
    
    def __init__(self, sample_rate=125, min_bpm=40, max_bpm=180):
        """
        Inicializar calculador de BPM.
        
        Args:
            sample_rate: Frecuencia de muestreo (Hz)
            min_bpm: BPM mínimo válido  
            max_bpm: BPM máximo válido
        """
        self.fs = sample_rate
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        
        # Configuración de ventanas
        self.initial_window_sec = 8      # Primera medición
        self.update_window_sec = 10      # Ventana deslizante
        self.update_interval_sec = 2     # Actualizar cada 2s
        
        # Buffer para datos filtrados (NO hay buffer raw ni filtro interno)
        self.ppg_buffer = deque(maxlen=20 * sample_rate)  # 20 segundos de datos
        
        # Estado
        self.last_bpm = None
        self.last_update_time = 0
        self.samples_received = 0
        self.confidence_score = 0.0
        
        print(f"PPG BPM Calculator iniciado:")
        print(f"  - Primer cálculo: {self.initial_window_sec}s")
        print(f"  - Actualizaciones: cada {self.update_interval_sec}s (ventana {self.update_window_sec}s)")
        print(f"  - Rango BPM válido: {min_bpm}-{max_bpm}")
        print(f"  - Recibe señal PPG ya filtrada")
    
    def add_sample(self, filtered_ppg_value, timestamp_sec):
        """
        Añadir nueva muestra PPG filtrada y calcular BPM si es necesario.
        
        Args:
            filtered_ppg_value: Valor PPG ya filtrado
            timestamp_sec: Tiempo en segundos
            
        Returns:
            dict: {'bpm': float/None, 'confidence': float, 'updated': bool}
        """
        # Almacenar muestra filtrada directamente
        self.ppg_buffer.append(filtered_ppg_value)
        self.samples_received += 1
        
        # Determinar si calcular BPM
        should_calculate = False
        
        # Primera medición
        if (self.last_bpm is None and 
            self.samples_received >= self.initial_window_sec * self.fs):
            should_calculate = True
            print(f"Primera medición BPM (después de {self.initial_window_sec}s)")
        
        # Actualizaciones periódicas
        elif (self.last_bpm is not None and 
              timestamp_sec - self.last_update_time >= self.update_interval_sec):
            should_calculate = True
        
        if should_calculate:
            result = self._calculate_bpm()
            self.last_update_time = timestamp_sec
            return {
                'bpm': result['bpm'],
                'confidence': result['confidence'],
                'updated': True,
                'quality': result['quality']
            }
        
        return {
            'bpm': self.last_bpm,
            'confidence': self.confidence_score,
            'updated': False,
            'quality': 'pending'
        }
    
    def _calculate_bpm(self):
        """
        Calcular BPM usando ventana óptima de datos filtrados.
        
        Returns:
            dict: Resultado del cálculo con métricas de calidad
        """
        # Usar ventana apropiada
        window_samples = min(
            len(self.ppg_buffer),
            self.update_window_sec * self.fs
        )
        
        if window_samples < 5 * self.fs:  # Mínimo 5 segundos
            return {'bpm': None, 'confidence': 0.0, 'quality': 'insufficient_data'}
        
        # Obtener datos de la ventana (ya filtrados)
        data = np.array(list(self.ppg_buffer)[-window_samples:])
        
        # Método 1: Detección de picos (principal)
        bpm_peaks, confidence_peaks = self._calculate_bpm_peaks(data)
        
        # Método 2: FFT (validación)
        bpm_fft, confidence_fft = self._calculate_bpm_fft(data)
        
        # Fusión inteligente de resultados
        final_bpm, final_confidence, quality = self._fuse_bpm_estimates(
            bpm_peaks, confidence_peaks,
            bpm_fft, confidence_fft
        )
        
        # Actualizar estado
        if final_bpm is not None:
            self.last_bpm = final_bpm
            self.confidence_score = final_confidence
        
        return {
            'bpm': final_bpm,
            'confidence': final_confidence,
            'quality': quality,
            'debug': {
                'peaks_bpm': bpm_peaks,
                'fft_bpm': bpm_fft,
                'window_sec': window_samples / self.fs
            }
        }
    
    def _calculate_bpm_peaks(self, data):
        """Calcular BPM usando detección de picos."""
        try:
            # Normalizar datos
            data_norm = (data - np.mean(data)) / np.std(data)
            
            # Detectar picos con parámetros optimizados para PPG
            # Distancia mínima = 60 BPM máximo
            min_distance = int(self.fs * 60 / self.max_bpm)
            
            # Altura mínima = 0.3 desviaciones estándar
            min_height = 0.3
            
            peaks, properties = signal.find_peaks(
                data_norm,
                height=min_height,
                distance=min_distance,
                prominence=0.2  # Evitar picos falsos
            )
            
            if len(peaks) < 3:  # Necesitamos al menos 3 picos
                return None, 0.0
            
            # Calcular intervalos RR
            rr_intervals = np.diff(peaks) / self.fs  # En segundos
            rr_mean = np.mean(rr_intervals)
            rr_std = np.std(rr_intervals)
            
            # BPM promedio
            bpm = 60.0 / rr_mean
            
            # Métricas de confianza
            cv_rr = rr_std / rr_mean  # Coeficiente de variación
            confidence = max(0.0, 1.0 - cv_rr * 3)  # Penalizar irregularidad
            
            # Validar rango fisiológico
            if self.min_bpm <= bpm <= self.max_bpm:
                return bpm, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            print(f"Error en cálculo por picos: {e}")
            return None, 0.0
    
    def _calculate_bpm_fft(self, data):
        """Calcular BPM usando análisis FFT."""
        try:
            # Ventana y FFT
            windowed = data * signal.windows.hann(len(data))
            fft = np.fft.rfft(windowed)
            freqs = np.fft.rfftfreq(len(data), 1/self.fs)
            
            # Potencia espectral
            power = np.abs(fft) ** 2
            
            # Rango de frecuencias cardiacas
            f_min = self.min_bpm / 60.0
            f_max = self.max_bpm / 60.0
            
            mask = (freqs >= f_min) & (freqs <= f_max)
            if not np.any(mask):
                return None, 0.0
            
            # Encontrar pico dominante
            max_idx = np.argmax(power[mask])
            peak_freq = freqs[mask][max_idx]
            bpm = peak_freq * 60.0
            
            # Confianza basada en la relación señal/ruido
            peak_power = power[mask][max_idx]
            noise_power = np.mean(power[mask])
            snr = peak_power / (noise_power + 1e-10)
            confidence = min(1.0, np.log10(snr + 1) / 2)  # Normalizar
            
            return bpm, confidence
            
        except Exception as e:
            print(f"Error en cálculo FFT: {e}")
            return None, 0.0
    
    def _fuse_bpm_estimates(self, bpm_peaks, conf_peaks, bpm_fft, conf_fft):
        """Fusionar estimaciones de BPM de múltiples métodos."""
        
        # Si solo uno es válido, usar ese
        if bpm_peaks is None and bpm_fft is None:
            return None, 0.0, 'no_valid_estimates'
        elif bpm_peaks is None:
            return bpm_fft, conf_fft, 'fft_only'
        elif bpm_fft is None:
            return bpm_peaks, conf_peaks, 'peaks_only'
        
        # Ambos válidos - verificar concordancia
        diff_percent = abs(bpm_peaks - bpm_fft) / ((bpm_peaks + bpm_fft) / 2) * 100
        
        if diff_percent < 10:  # Concordancia buena (<10% diferencia)
            # Promedio ponderado por confianza
            total_conf = conf_peaks + conf_fft
            if total_conf > 0:
                fused_bpm = (bpm_peaks * conf_peaks + bpm_fft * conf_fft) / total_conf
                fused_conf = (conf_peaks + conf_fft) / 2
                return fused_bpm, fused_conf, 'fused_good'
        
        # Discordancia - elegir el más confiable
        if conf_peaks > conf_fft:
            return bpm_peaks, conf_peaks, 'peaks_preferred'
        else:
            return bpm_fft, conf_fft, 'fft_preferred'
    
    def get_status(self):
        """Obtener estado actual del calculador."""
        return {
            'samples_received': self.samples_received,
            'buffer_size': len(self.ppg_buffer),
            'last_bpm': self.last_bpm,
            'confidence': self.confidence_score,
            'ready_for_first': self.samples_received >= self.initial_window_sec * self.fs,
            'time_coverage_sec': len(self.ppg_buffer) / self.fs
        }
    
    def reset(self):
        """Reiniciar el calculador."""
        self.ppg_buffer.clear()
        self.last_bpm = None
        self.last_update_time = 0
        self.samples_received = 0
        self.confidence_score = 0.0
        print("BPM Calculator reiniciado")
