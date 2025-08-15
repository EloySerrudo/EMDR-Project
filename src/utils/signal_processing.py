"""
Módulo para procesamiento de señales en tiempo real.
Contiene funciones para filtrar la señal fotopletismográfica (PPG),
y para calcular la frecuencia cardiaca.
"""

import numpy as np
from scipy import signal
from collections import deque

class OnlinePPGFilter:
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


class OfflineEOGFilter:
    """
    Filtro EOG offline optimizado para análisis de sacadas.
    
    Estrategia SIMPLE y EFECTIVA:
    1. DC removal con filtro HP muy suave (0.01 Hz)
    2. Notch 50 Hz para eliminar ruido de red
    3. Filtro FIR con filtfilt (FASE CERO) para preservar temporización exacta
    4. Detección y limpieza de artefactos de parpadeo
    
    CLAVE: filtfilt() procesa hacia adelante y hacia atrás = fase cero
    """
    
    def __init__(self, fs=125, hp_cutoff=0.01, lp_cutoff=35.0, 
                 notch_freq=50, notch_q=30, fir_order=101):
        """
        Inicializar filtro EOG offline.
        
        Args:
            fs: Frecuencia de muestreo (Hz)
            hp_cutoff: Corte HP muy bajo para eliminar deriva DC (0.01 Hz)
            lp_cutoff: Corte LP para ruido de alta frecuencia (35 Hz)
            notch_freq: Solo 50 Hz como pediste
            notch_q: Factor de calidad del notch
            fir_order: Orden del filtro FIR (debe ser par para filtfilt)
        """
        self.fs = fs
        self.hp_cutoff = hp_cutoff
        self.lp_cutoff = lp_cutoff
        self.notch_freq = notch_freq
        self.notch_q = notch_q
        self.fir_order = fir_order if fir_order % 2 == 0 else fir_order + 1
        
        self._design_filters()
        
        print(f"Filtro EOG Offline configurado:")
        print(f"  - DC removal: {self.hp_cutoff} Hz")
        print(f"  - Notch: {self.notch_freq} Hz")
        print(f"  - Low-pass: {self.lp_cutoff} Hz (FIR orden {self.fir_order})")
        print(f"  - FASE CERO garantizada con filtfilt()")
    
    def _design_filters(self):
        """Diseñar filtros offline optimizados."""
        nyq = self.fs * 0.5
        
        # 1. High-pass Butterworth orden 2 (eliminar deriva DC)
        self.b_hp, self.a_hp = signal.butter(2, self.hp_cutoff/nyq, 'highpass')
        
        # 2. Notch 50 Hz únicamente
        self.b_notch, self.a_notch = signal.iirnotch(self.notch_freq/nyq, self.notch_q)
        
        # 3. FIR Low-pass con ventana Kaiser (excelente para EOG)
        # Beta=5 da buen balance entre roll-off y ringing
        self.b_lp = signal.firwin(
            self.fir_order + 1,
            self.lp_cutoff,
            fs=self.fs,
            window=('kaiser', 5)
        )
    
    def filter_signal(self, eog_data):
        """
        Filtrar señal EOG completa con fase cero.
        
        Args:
            eog_data: Array numpy con datos EOG raw
            
        Returns:
            dict: {
                'filtered': array filtrado,
                'dc_removed': señal sin deriva DC,
                'no_powerline': señal sin 50Hz,
                'metadata': información del procesamiento
            }
        """
        if not isinstance(eog_data, np.ndarray):
            eog_data = np.array(eog_data)
        
        print(f"Filtrando señal EOG: {len(eog_data)} muestras ({len(eog_data)/self.fs:.1f}s)")
        
        # PASO 1: Eliminar deriva DC con filtfilt (FASE CERO)
        dc_removed = signal.filtfilt(self.b_hp, self.a_hp, eog_data)
        
        # PASO 2: Eliminar 50 Hz con filtfilt (FASE CERO)
        no_powerline = signal.filtfilt(self.b_notch, self.a_notch, dc_removed)
        
        # PASO 3: Low-pass FIR con filtfilt (FASE CERO)
        filtered_final = signal.filtfilt(self.b_lp, [1.0], no_powerline)
        
        # Detectar y marcar posibles artefactos de parpadeo
        blink_artifacts = self._detect_blink_artifacts(filtered_final)
        
        metadata = {
            'original_length': len(eog_data),
            'duration_sec': len(eog_data) / self.fs,
            'dc_offset_removed': np.mean(eog_data) - np.mean(dc_removed),
            'powerline_reduction_db': self._estimate_powerline_reduction(eog_data, no_powerline),
            'blink_artifacts_detected': len(blink_artifacts),
            'signal_quality': self._assess_signal_quality(filtered_final),
            'processing_steps': ['DC_removal', 'notch_50Hz', 'lowpass_FIR', 'phase_zero']
        }
        
        return {
            'filtered': filtered_final,
            'dc_removed': dc_removed,
            'no_powerline': no_powerline,
            'blink_artifacts': blink_artifacts,
            'metadata': metadata
        }
    
    def _detect_blink_artifacts(self, filtered_signal):
        """
        Detectar artefactos de parpadeo basándose en amplitud y duración.
        
        Args:
            filtered_signal: Señal EOG filtrada
            
        Returns:
            list: Lista de índices donde se detectaron parpadeos
        """
        # Los parpadeos son típicamente:
        # - Amplitud muy alta (>3-5 veces la desviación estándar)
        # - Duración corta (100-400 ms)
        # - Forma característica (pico negativo seguido de positivo)
        
        signal_std = np.std(filtered_signal)
        threshold = 4 * signal_std  # Umbral conservador
        
        # Encontrar picos que excedan el umbral
        peaks_pos, _ = signal.find_peaks(filtered_signal, height=threshold)
        peaks_neg, _ = signal.find_peaks(-filtered_signal, height=threshold)
        
        # Combinar picos positivos y negativos
        all_peaks = np.sort(np.concatenate([peaks_pos, peaks_neg]))
        
        # Filtrar por duración típica de parpadeos (100-400ms)
        min_duration = int(0.1 * self.fs)  # 100ms
        max_duration = int(0.4 * self.fs)  # 400ms
        
        blink_candidates = []
        for peak in all_peaks:
            # Buscar retorno al baseline
            start_idx = max(0, peak - max_duration//2)
            end_idx = min(len(filtered_signal), peak + max_duration//2)
            
            # Verificar si la duración está en rango típico
            if (end_idx - start_idx) >= min_duration:
                blink_candidates.append(peak)# Buscar retorno al baseline
            start_idx = max(0, peak - max_duration//2)
            end_idx = min(len(filtered_signal), peak + max_duration//2)
            
            # Verificar si la duración está en rango típico
            if (end_idx - start_idx) >= min_duration:
                blink_candidates.append(peak)
        
        print(f"Detectados {len(blink_candidates)} posibles artefactos de parpadeo")
        return blink_candidates
    
    def _estimate_powerline_reduction(self, original, filtered):
        """Estimar reducción de ruido de 50Hz en dB."""
        try:
            # FFT de ambas señales
            fft_orig = np.fft.rfft(original)
            fft_filt = np.fft.rfft(filtered)
            freqs = np.fft.rfftfreq(len(original), 1/self.fs)
            
            # Encontrar potencia cerca de 50Hz
            f_idx = np.argmin(np.abs(freqs - 50))
            
            power_orig = np.abs(fft_orig[f_idx])**2
            power_filt = np.abs(fft_filt[f_idx])**2
            
            if power_orig > 0 and power_filt > 0:
                reduction_db = 10 * np.log10(power_orig / power_filt)
                return reduction_db
        except:
            pass
        
        return 0.0
    
    def _assess_signal_quality(self, filtered_signal):
        """Evaluar calidad de la señal filtrada."""
        signal_std = np.std(filtered_signal)
        signal_range = np.ptp(filtered_signal)  # Peak-to-peak
        
        # Métricas simples de calidad
        if signal_std < 10:  # Muy poco ruido
            return 'excellent'
        elif signal_std < 50:
            return 'good'
        elif signal_std < 100:
            return 'acceptable'
        else:
            return 'poor'
    
    def filter_with_artifact_removal(self, eog_data, remove_blinks=True):
        """
        Filtrar con opción de limpieza de artefactos.
        
        Args:
            eog_data: Datos EOG raw
            remove_blinks: Si True, interpoler sobre artefactos detectados
            
        Returns:
            dict: Resultado del filtrado con artefactos limpiados
        """
        # Filtrado normal
        result = self.filter_signal(eog_data)
        
        if remove_blinks and result['blink_artifacts']:
            print(f"Limpiando {len(result['blink_artifacts'])} artefactos...")
            
            cleaned_signal = result['filtered'].copy()
            
            # Interpolar sobre cada artefacto
            for artifact_idx in result['blink_artifacts']:
                # Definir ventana de interpolación
                window_size = int(0.3 * self.fs)  # 300ms
                start_idx = max(0, artifact_idx - window_size//2)
                end_idx = min(len(cleaned_signal), artifact_idx + window_size//2)
                
                # Interpolar linealmente
                if start_idx > 0 and end_idx < len(cleaned_signal):
                    x_interp = np.array([start_idx, end_idx])
                    y_interp = np.array([cleaned_signal[start_idx], cleaned_signal[end_idx]])
                    
                    # Crear interpolación
                    x_fill = np.arange(start_idx, end_idx)
                    y_fill = np.interp(x_fill, x_interp, y_interp)
                    
                    cleaned_signal[start_idx:end_idx] = y_fill
            
            result['cleaned'] = cleaned_signal
            result['metadata']['artifact_removal'] = True
        
        return result
    
    def test_filter_response(self, plot=True):
        """Probar respuesta en frecuencia del filtro completo."""
        try:
            import matplotlib.pyplot as plt
            
            # Diseñar filtro combinado equivalente
            w, h_hp = signal.freqz(self.b_hp, self.a_hp, fs=self.fs, worN=2048)
            _, h_notch = signal.freqz(self.b_notch, self.a_notch, fs=self.fs, worN=2048)
            _, h_lp = signal.freqz(self.b_lp, [1.0], fs=self.fs, worN=2048)
            
            # Respuesta combinada
            h_total = h_hp * h_notch * h_lp
            
            if plot:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
                
                # Magnitud
                ax1.semilogx(w, 20 * np.log10(abs(h_total)), 'b-', linewidth=2)
                ax1.set_title('Respuesta del Filtro EOG Offline (Fase Cero)', fontsize=14)
                ax1.set_xlabel('Frecuencia (Hz)')
                ax1.set_ylabel('Magnitud (dB)')
                ax1.grid(True, alpha=0.3)
                ax1.axvline(self.hp_cutoff, color='r', linestyle='--', alpha=0.7, label=f'HP: {self.hp_cutoff} Hz')
                ax1.axvline(self.lp_cutoff, color='g', linestyle='--', alpha=0.7, label=f'LP: {self.lp_cutoff} Hz')
                ax1.axvline(self.notch_freq, color='orange', linestyle='--', alpha=0.7, label=f'Notch: {self.notch_freq} Hz')
                ax1.legend()
                ax1.set_ylim([-80, 5])
                
                # Fase (será cero con filtfilt)
                ax2.semilogx(w, np.angle(h_total, deg=True), 'r-', linewidth=2)
                ax2.set_xlabel('Frecuencia (Hz)')
                ax2.set_ylabel('Fase (grados)')
                ax2.grid(True, alpha=0.3)
                ax2.set_title('Fase (Se anula con filtfilt - mostrada solo como referencia)')
                
                plt.tight_layout()
                plt.show()
            
            return w, h_total
            
        except ImportError:
            print("matplotlib no disponible")
            return None, None


class OfflinePPGFilter:
    """
    Filtro PPG offline optimizado para análisis de frecuencia cardíaca.
    
    Estrategia específica para PPG:
    1. DC removal suave (0.5 Hz) - Preserva variabilidad HRV
    2. Notch 50 Hz - Elimina interferencia eléctrica
    3. Bandpass 0.5-5.0 Hz - Rango óptimo para señales cardíacas
    4. Filtro de suavizado opcional para reducir ruido
    
    CLAVE: PPG requiere preservar componentes de 0.5-5 Hz (30-300 BPM)
    """
    
    def __init__(self, fs=125, hp_cutoff=0.5, lp_cutoff=5.0, notch_enabled=False,
                 notch_freq=50, notch_q=30, smoothing=True):    # notch_q: Factor de calidad
        """
        Inicializar filtro PPG offline.
        
        Args:
            fs: Frecuencia de muestreo (Hz)
            hp_cutoff: Corte HP para eliminar deriva (0.5 Hz típico)
            lp_cutoff: Corte LP para ruido HF (5 Hz típico)
            notch_freq: Frecuencia notch (50/60 Hz)
            notch_q: Factor de calidad del notch
            smoothing: Aplicar suavizado adicional
        """
        self.fs = fs
        self.hp_cutoff = hp_cutoff
        self.lp_cutoff = lp_cutoff
        self.notch_enabled = notch_enabled
        self.notch_freq = notch_freq
        self.notch_q = notch_q
        self.smoothing = smoothing
        
        # Validar rango de frecuencias cardíacas
        self.min_hr_hz = hp_cutoff      # ~30 BPM
        self.max_hr_hz = lp_cutoff      # ~300 BPM
        
        self._design_filters()
        
        print(f"Filtro PPG Offline configurado:")
        print(f"  - Bandpass: {self.hp_cutoff}-{self.lp_cutoff} Hz")
        print(f"  - Rango BPM: {self.hp_cutoff*60:.0f}-{self.lp_cutoff*60:.0f}")
        print(f"  - Notch: {self.notch_freq} Hz")
        print(f"  - Suavizado: {'ON' if smoothing else 'OFF'}")
        print(f"  - FASE CERO con filtfilt()")
    
    def _design_filters(self):
        """Diseñar filtros específicos para PPG."""
        nyq = self.fs * 0.5
        
        # 1. Bandpass Butterworth para rango cardíaco
        # Orden 4 da buen balance entre roll-off y estabilidad
        low_norm = self.hp_cutoff / nyq
        high_norm = self.lp_cutoff / nyq
        
        self.b_bandpass, self.a_bandpass = signal.butter(
            4, [low_norm, high_norm], btype='bandpass'
        )
        
        # 2. Notch para interferencia eléctrica
        if self.notch_freq < nyq and self.notch_enabled:
            self.b_notch, self.a_notch = signal.iirnotch(
                self.notch_freq/nyq, self.notch_q
            )
            self.notch_enabled = True
        else:
            self.notch_enabled = False
            print(f"Advertencia: Notch {self.notch_freq} Hz deshabilitado")
        
        # 3. Filtro de suavizado opcional (FIR)
        if self.smoothing:
            # FIR corto para reducir ruido sin afectar morfología
            self.smooth_taps = int(0.1 * self.fs)  # 100ms
            if self.smooth_taps % 2 == 0:
                self.smooth_taps += 1  # Asegurar impar
                
            self.b_smooth = signal.firwin(
                self.smooth_taps,
                self.lp_cutoff * 0.8,  # Cutoff ligeramente menor
                fs=self.fs,
                window='hamming'
            )
        
        # 4. Detector de artefactos (opcional)
        self.artifact_threshold_std = 4.0  # Umbral en desviaciones estándar
    
    def filter_signal(self, ppg_data):
        """
        Filtrar señal PPG completa con fase cero.
        
        Args:
            ppg_data: Array numpy con datos PPG raw
            
        Returns:
            dict: Resultado completo del filtrado
        """
        if not isinstance(ppg_data, np.ndarray):
            ppg_data = np.array(ppg_data)
        
        print(f"Filtrando señal PPG: {len(ppg_data)} muestras ({len(ppg_data)/self.fs:.1f}s)")
        
        # PASO 1: Bandpass principal (elimina DC + ruido HF)
        bandpass_filtered = signal.filtfilt(
            self.b_bandpass, self.a_bandpass, ppg_data, method='gust'   # Metodo de Gustafsson
        )
        
        # PASO 2: Notch 50 Hz (si está habilitado)
        if self.notch_enabled:
            notch_filtered = signal.filtfilt(
                self.b_notch, self.a_notch, bandpass_filtered
            )
        else:
            notch_filtered = bandpass_filtered.copy()
        
        # PASO 3: Suavizado opcional
        if self.smoothing:
            final_filtered = signal.filtfilt(
                self.b_smooth, [1.0], notch_filtered
            )
        else:
            final_filtered = notch_filtered.copy()
        
        # PASO 4: Detección de artefactos
        artifacts = self._detect_movement_artifacts(final_filtered)
        
        # PASO 5: Análisis de calidad
        quality_metrics = self._assess_ppg_quality(ppg_data, final_filtered)
        
        return {
            'filtered': final_filtered,
            'bandpass_only': bandpass_filtered,
            'notch_applied': notch_filtered,
            'artifacts': artifacts,
            'quality': quality_metrics,
            'metadata': {
                'original_length': len(ppg_data),
                'duration_sec': len(ppg_data) / self.fs,
                'dc_removed': np.mean(ppg_data) - np.mean(final_filtered),
                'snr_improvement_db': self._calculate_snr_improvement(ppg_data, final_filtered),
                'processing_chain': self._get_processing_chain()
            }
        }
    
    def _detect_movement_artifacts(self, filtered_signal):
        """
        Detectar artefactos de movimiento en señal PPG.
        
        Los artefactos de movimiento típicamente:
        - Tienen amplitud muy alta (>4 std)
        - Duración relativamente larga (>1 segundo)
        - Distorsionan la morfología normal del pulso
        """
        signal_std = np.std(filtered_signal)
        threshold = self.artifact_threshold_std * signal_std
        
        # Encontrar regiones que excedan el umbral
        above_threshold = np.abs(filtered_signal) > threshold
        
        # Agrupar regiones consecutivas
        artifact_regions = []
        in_artifact = False
        start_idx = 0
        
        for i, is_artifact in enumerate(above_threshold):
            if is_artifact and not in_artifact:
                start_idx = i
                in_artifact = True
            elif not is_artifact and in_artifact:
                # Verificar duración mínima (evitar false positives)
                duration_ms = (i - start_idx) / self.fs * 1000
                if duration_ms > 200:  # Mínimo 200ms
                    artifact_regions.append((start_idx, i, duration_ms))
                in_artifact = False
        
        print(f"Detectados {len(artifact_regions)} artefactos de movimiento")
        return artifact_regions
    
    def _assess_ppg_quality(self, original, filtered):
        """Evaluar calidad de la señal PPG."""
        # Métricas básicas
        snr_db = self._calculate_snr_improvement(original, filtered)
        signal_std = np.std(filtered)
        
        # Detectar pulsos para evaluar regularidad
        peaks, _ = signal.find_peaks(
            filtered,
            distance=int(0.4 * self.fs),  # Mínimo 150 BPM
            prominence=np.std(filtered) * 0.3
        )
        
        if len(peaks) > 2:
            rr_intervals = np.diff(peaks) / self.fs
            hr_mean = 60 / np.mean(rr_intervals)
            hr_cv = np.std(rr_intervals) / np.mean(rr_intervals)
            
            # Clasificar calidad
            if 50 <= hr_mean <= 120 and hr_cv < 0.1 and snr_db > 10:
                quality = 'excellent'
            elif 40 <= hr_mean <= 150 and hr_cv < 0.2 and snr_db > 5:
                quality = 'good'
            elif 30 <= hr_mean <= 180 and hr_cv < 0.3 and snr_db > 0:
                quality = 'acceptable'
            else:
                quality = 'poor'
        else:
            quality = 'insufficient_peaks'
        
        return {
            'overall': quality,
            'snr_db': snr_db,
            'peaks_detected': len(peaks),
            'estimated_hr': hr_mean if len(peaks) > 2 else None,
            'hr_variability': hr_cv if len(peaks) > 2 else None
        }
    
    def _calculate_snr_improvement(self, original, filtered):
        """Calcular mejora de SNR en dB."""
        try:
            # Estimar ruido como diferencia
            noise_estimate = original - filtered
            
            signal_power = np.var(filtered)
            noise_power = np.var(noise_estimate)
            
            if noise_power > 0:
                snr_db = 10 * np.log10(signal_power / noise_power)
                return max(0, snr_db)  # No negativo
        except:
            pass
        
        return 0.0
    
    def _get_processing_chain(self):
        """Obtener cadena de procesamiento aplicada."""
        chain = ['bandpass_0.5-5Hz']
        
        if self.notch_enabled:
            chain.append(f'notch_{self.notch_freq}Hz')
        
        if self.smoothing:
            chain.append('smoothing_FIR')
        
        chain.append('phase_zero_filtfilt')
        return chain
    
    def extract_heart_rate(self, filtered_signal, method='peaks'):
        """
        Extraer frecuencia cardíaca de señal PPG filtrada.
        
        Args:
            filtered_signal: Señal PPG ya filtrada
            method: 'peaks' o 'fft'
            
        Returns:
            dict: Resultados de análisis cardíaco
        """
        if method == 'peaks':
            return self._hr_from_peaks(filtered_signal)
        elif method == 'fft':
            return self._hr_from_fft(filtered_signal)
        else:
            # Ambos métodos
            peaks_result = self._hr_from_peaks(filtered_signal)
            fft_result = self._hr_from_fft(filtered_signal)
            
            return {
                'peaks_method': peaks_result,
                'fft_method': fft_result,
                'consensus_hr': self._consensus_hr(peaks_result, fft_result)
            }
    
    def _hr_from_peaks(self, signal_data):
        """Extraer HR usando detección de picos."""
        # Similar al método ya implementado en PPGHeartRateCalculator
        peaks, _ = signal.find_peaks(
            signal_data,
            distance=int(0.4 * self.fs),  # Min 150 BPM
            prominence=np.std(signal_data) * 0.2
        )
        
        if len(peaks) < 3:
            return {'hr_bpm': None, 'confidence': 0.0, 'method': 'peaks'}
        
        rr_intervals = np.diff(peaks) / self.fs
        hr_bpm = 60 / np.mean(rr_intervals)
        hr_std = 60 * np.std(rr_intervals) / (np.mean(rr_intervals)**2)
        
        # Confianza basada en regularidad
        cv = np.std(rr_intervals) / np.mean(rr_intervals)
        confidence = max(0.0, 1.0 - cv * 2)
        
        return {
            'hr_bpm': hr_bpm,
            'hr_std': hr_std,
            'confidence': confidence,
            'peaks_count': len(peaks),
            'method': 'peaks'
        }
    
    def _hr_from_fft(self, signal_data):
        """Extraer HR usando análisis FFT."""
        # Aplicar ventana y calcular FFT
        windowed = signal_data * signal.windows.hann(len(signal_data))
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(signal_data), 1/self.fs)
        
        # Rango de frecuencias cardíacas (0.5-3 Hz = 30-180 BPM)
        mask = (freqs >= 0.5) & (freqs <= 3.0)
        power = np.abs(fft[mask])**2
        
        # Encontrar pico dominante
        peak_idx = np.argmax(power)
        peak_freq = freqs[mask][peak_idx]
        hr_bpm = peak_freq * 60
        
        # Confianza basada en prominencia del pico
        peak_power = power[peak_idx]
        mean_power = np.mean(power)
        snr_linear = peak_power / (mean_power + 1e-10)
        confidence = min(1.0, np.log10(snr_linear + 1) / 2)
        
        return {
            'hr_bpm': hr_bpm,
            'peak_frequency': peak_freq,
            'confidence': confidence,
            'snr_linear': snr_linear,
            'method': 'fft'
        }
    
    def _consensus_hr(self, peaks_result, fft_result):
        """Consenso entre métodos de detección."""
        hr_peaks = peaks_result.get('hr_bpm')
        hr_fft = fft_result.get('hr_bpm')
        
        if hr_peaks is None or hr_fft is None:
            return hr_peaks or hr_fft
        
        # Si están cerca (±10%), promediar
        diff_percent = abs(hr_peaks - hr_fft) / ((hr_peaks + hr_fft) / 2) * 100
        
        if diff_percent < 10:
            return (hr_peaks + hr_fft) / 2
        else:
            # Elegir el más confiable
            conf_peaks = peaks_result.get('confidence', 0)
            conf_fft = fft_result.get('confidence', 0)
            
            return hr_peaks if conf_peaks > conf_fft else hr_fft


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


class BPMOfflineCalculation:
    """
    Calculador offline de evolución de BPM para señales PPG filtradas.
    
    Análisis offline optimizado para sessiones EMDR:
    - Ventana de cálculo: 15 segundos
    - Intervalo de cálculo: 1 segundo
    - Extensión automática para artefactos: 5 segundos
    - Suavizado de serie temporal integrado
    
    Uso típico:
        calculator = BPMOfflineCalculation()
        result = calculator.calculate_bpm_evolution(filtered_ppg, ms_data)
    """
    
    def __init__(self, fs=125):
        """
        Inicializar calculador BPM offline.
        
        Args:
            fs: Frecuencia de muestreo estimada (Hz)
        """
        self.fs = fs
        
        # Parámetros fijos optimizados para análisis offline
        self.initial_window_sec = 15     # Ventana inicial (primeros 60s)
        self.extended_window_sec = 60    # Ventana extendida (después de 60s)
        self.transition_time_sec = 60    # Momento de transición
        self.calculation_interval_sec = 1  # BPM cada segundo
        self.min_window_size_sec = 8     # Ventana mínima válida
        self.artifact_extension_sec = 5   # Extensión por artefactos
        
        print(f"BPM Offline Calculator configurado:")
        print(f"  - Ventana inicial (0-60s): {self.initial_window_sec}s")
        print(f"  - Ventana extendida (>60s): {self.extended_window_sec}s")
        print(f"  - Transición en: {self.transition_time_sec}s")
        print(f"  - Intervalo de cálculo: {self.calculation_interval_sec}s")
        print(f"  - Extensión por artefactos: {self.artifact_extension_sec}s")
        print(f"  - Frecuencia de muestreo: {self.fs} Hz")
    
    def calculate_bpm_evolution(self, filtered_ppg_data, ms_data):
        """
        Calcular evolución de BPM a lo largo de toda la señal filtrada.
        
        Args:
            filtered_ppg_data: Array numpy con señal PPG ya filtrada
            ms_data: Array numpy con timestamps en milisegundos
            
        Returns:
            dict: {
                'times_sec': array con tiempos en segundos,
                'bpm_values': array con valores BPM suavizados,
                'confidence_values': array con valores de confianza,
                'metadata': dict con información del procesamiento
            }
        """
        if not isinstance(filtered_ppg_data, np.ndarray):
            filtered_ppg_data = np.array(filtered_ppg_data)
        
        if not isinstance(ms_data, np.ndarray):
            ms_data = np.array(ms_data)
        
        print(f"Calculando evolución BPM: {len(filtered_ppg_data)} muestras")
        
        # Convertir tiempo a segundos
        time_sec = ms_data / 1000.0
        total_duration = time_sec[-1] - time_sec[0]
        
        # Preparar arrays de resultado
        bpm_times = []
        bpm_values = []
        confidence_values = []
        
        # Empezar después de la ventana inicial mínima
        start_time = time_sec[0] + self.initial_window_sec
        end_time = time_sec[-1]
        current_time = start_time
        
        print(f"Calculando BPM desde {start_time:.1f}s hasta {end_time:.1f}s")
        print(f"Transición de ventana en {self.transition_time_sec}s")
        
        while current_time <= end_time:
            # **VENTANA ADAPTATIVA**: Determinar tamaño de ventana según tiempo transcurrido
            time_from_start = current_time - time_sec[0]
            
            if time_from_start <= self.transition_time_sec:
                # Primeros 60 segundos: ventana de 15s
                current_window_size = self.initial_window_sec
            else:
                # Después de 60 segundos: ventana de 60s
                current_window_size = self.extended_window_sec
            
            # Definir ventana de análisis
            window_start = current_time - current_window_size
            window_end = current_time
            
            # Extraer datos de la ventana
            mask = (time_sec >= window_start) & (time_sec <= window_end)
            window_ppg = filtered_ppg_data[mask]
            window_time = time_sec[mask]
            
            if len(window_ppg) > 0:
                # Calcular BPM para esta ventana
                bpm_result = self._calculate_bpm_for_window(window_ppg, window_time)
                
                if bpm_result['bpm'] is not None:
                    bpm_times.append(current_time)
                    bpm_values.append(bpm_result['bpm'])
                    confidence_values.append(bpm_result['confidence'])
                else:
                    # Extender ventana por artefactos
                    extended_result = self._calculate_with_extended_window(
                        time_sec, filtered_ppg_data, current_time, window_start, window_end
                    )
                    if extended_result['bpm'] is not None:
                        bpm_times.append(current_time)
                        bpm_values.append(extended_result['bpm'])
                        confidence_values.append(extended_result['confidence'])
            
            # Avanzar en el tiempo
            current_time += self.calculation_interval_sec
        
        # Aplicar suavizado a la serie temporal de BPM
        if len(bpm_values) > 5:
            bpm_smoothed = self._smooth_bpm_series(np.array(bpm_values))
        else:
            bpm_smoothed = np.array(bpm_values)
        
        # Preparar resultado
        result = {
            'times_sec': np.array(bpm_times),
            'bpm_values': bpm_smoothed,
            'confidence_values': np.array(confidence_values),
            'metadata': {
                'total_points': len(bpm_times),
                'duration_sec': total_duration,
                'initial_window_sec': self.initial_window_sec,
                'extended_window_sec': self.extended_window_sec,
                'transition_time_sec': self.transition_time_sec,
                'calculation_interval_sec': self.calculation_interval_sec,
                'mean_bpm': np.mean(bpm_smoothed) if len(bpm_smoothed) > 0 else None,
                'std_bpm': np.std(bpm_smoothed) if len(bpm_smoothed) > 0 else None
            }
        }
        
        print(f"✅ BPM evolution calculado: {len(bpm_times)} puntos")
        if result['metadata']['mean_bpm']:
            print(f"  - BPM promedio: {result['metadata']['mean_bpm']:.1f} ± {result['metadata']['std_bpm']:.1f}")
        
        return result
    
    def _calculate_bpm_for_window(self, ppg_window, time_window):
        """Calcular BPM para una ventana específica"""
        try:
            if len(ppg_window) < self.fs * 5:  # Mínimo 5 segundos
                return {'bpm': None, 'confidence': 0.0}
            
            # Detección de picos con parámetros optimizados
            # Distancia mínima entre picos (0.4s = 150 BPM máximo)
            min_distance = int(0.4 * self.fs)
            
            # Prominencia adaptativa
            prominence = np.std(ppg_window) * 0.3
            
            peaks, properties = signal.find_peaks(
                ppg_window,
                distance=min_distance,
                prominence=prominence,
                height=np.mean(ppg_window)
            )
            
            if len(peaks) < 3:
                return {'bpm': None, 'confidence': 0.0}
            
            # Calcular intervalos RR en segundos
            peak_times = time_window[peaks[0]] + (peaks / self.fs)
            rr_intervals = np.diff(peak_times)
            
            # Filtrar intervalos fisiológicos (0.4s a 1.5s = 40-150 BPM)
            valid_rr = rr_intervals[(rr_intervals >= 0.4) & (rr_intervals <= 1.5)]
            
            if len(valid_rr) < 2:
                return {'bpm': None, 'confidence': 0.0}
            
            # Calcular BPM promedio
            mean_rr = np.mean(valid_rr)
            bpm = 60.0 / mean_rr
            
            # Validar rango fisiológico
            if bpm < 40 or bpm > 120:
                return {'bpm': None, 'confidence': 0.0}
            
            # Calcular confianza basada en variabilidad
            cv = np.std(valid_rr) / mean_rr  # Coeficiente de variación
            confidence = max(0.0, min(1.0, 1.0 - cv * 3))  # Normalizar
            
            return {'bpm': bpm, 'confidence': confidence}
            
        except Exception as e:
            return {'bpm': None, 'confidence': 0.0}
    
    def _calculate_with_extended_window(self, full_time, full_ppg, current_time, original_start, original_end):
        """Calcular BPM con ventana extendida para manejar artefactos"""
        try:
            # Extender ventana hacia atrás y adelante
            extended_start = original_start - self.artifact_extension_sec
            extended_end = original_end + self.artifact_extension_sec
            
            # Asegurar límites
            extended_start = max(extended_start, full_time[0])
            extended_end = min(extended_end, full_time[-1])
            
            # Extraer datos extendidos
            mask = (full_time >= extended_start) & (full_time <= extended_end)
            extended_ppg = full_ppg[mask]
            extended_time = full_time[mask]
            
            return self._calculate_bpm_for_window(extended_ppg, extended_time)
            
        except Exception as e:
            return {'bpm': None, 'confidence': 0.0}
    
    def _smooth_bpm_series(self, bpm_values):
        """Aplicar suavizado a la serie temporal de BPM"""
        if len(bpm_values) < 5:
            return bpm_values
        
        # Usar filtro de media móvil con ventana de 5 puntos
        try:
            from scipy.ndimage import uniform_filter1d
            return uniform_filter1d(bpm_values, size=5, mode='nearest')
        except:
            # Fallback: media móvil simple
            smoothed = np.copy(bpm_values)
            for i in range(2, len(bpm_values) - 2):
                smoothed[i] = np.mean(bpm_values[i-2:i+3])
            return smoothed
