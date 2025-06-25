import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sqlite3
from scipy import signal, stats
from collections import deque

class SessionAnalyzer:
    """Analizador principal para sesiones EMDR con métricas avanzadas"""
    
    def __init__(self, sample_rate: int = 125):
        self.sample_rate = sample_rate
        
    def load_session_data(self, session_id: int) -> Optional[Dict]:
        """Carga datos de una sesión desde la base de datos"""
        from src.database.database_manager import DatabaseManager
        
        try:
            # Obtener metadatos de la sesión
            session = DatabaseManager.get_session(session_id)
            if not session:
                return None
                
            # Deserializar datos binarios
            session_data = {
                'id': session['id'],
                'patient_id': session['id_paciente'],
                'fecha': session['fecha'],
                'comentarios': session['comentarios'],
                'timestamps': self._deserialize_blob(session['datos_ms']),
                'eog_data': self._deserialize_blob(session['datos_eog']),
                'ppg_data': self._deserialize_blob(session['datos_ppg']),
                'bpm_data': self._deserialize_blob(session['datos_bpm'])
            }
            
            return session_data
            
        except Exception as e:
            print(f"Error cargando sesión {session_id}: {e}")
            return None
    
    def _deserialize_blob(self, blob_data) -> np.ndarray:
        """Deserializa datos BLOB a numpy array"""
        if blob_data is None:
            return np.array([])
        
        # Convertir BLOB a numpy array (ajustar según formato usado)
        # Asumiendo que se guardó como array de float64
        return np.frombuffer(blob_data, dtype=np.float64)
    
    def calculate_comprehensive_metrics(self, session_data: Dict) -> Dict:
        """Calcula métricas comprehensivas de la sesión"""
        
        timestamps = session_data['timestamps']
        eog_data = session_data['eog_data']
        ppg_data = session_data['ppg_data']
        bpm_data = session_data['bpm_data']
        
        # Convertir timestamps a tiempo relativo en segundos
        time_seconds = (timestamps - timestamps[0]) / 1000.0
        
        metrics = {
            'session_info': {
                'duration_minutes': time_seconds[-1] / 60.0,
                'total_samples': len(timestamps),
                'sample_rate_actual': len(timestamps) / time_seconds[-1]
            },
            
            # Métricas de variabilidad cardíaca (HRV)
            'hrv_metrics': self._calculate_hrv_metrics(bpm_data, time_seconds),
            
            # Métricas de respuesta al estrés
            'stress_metrics': self._calculate_stress_metrics(bpm_data, ppg_data, time_seconds),
            
            # Métricas de relajación
            'relaxation_metrics': self._calculate_relaxation_metrics(bpm_data, time_seconds),
            
            # Métricas de movimientos oculares
            'eog_metrics': self._calculate_eog_metrics(eog_data, time_seconds),
            
            # Análisis temporal por segmentos
            'temporal_analysis': self._calculate_temporal_analysis(
                bpm_data, ppg_data, eog_data, time_seconds
            )
        }
        
        return metrics
    
    def _calculate_hrv_metrics(self, bpm_data: np.ndarray, time_seconds: np.ndarray) -> Dict:
        """Calcula métricas de variabilidad del ritmo cardíaco"""
        
        # Filtrar valores de BPM válidos (40-200)
        valid_bpm = bpm_data[(bpm_data >= 40) & (bpm_data <= 200)]
        
        if len(valid_bpm) < 10:
            return {'error': 'Datos insuficientes para HRV'}
        
        # Convertir BPM a intervalos RR (en ms)
        rr_intervals = 60000 / valid_bpm  # ms entre latidos
        
        # Métricas de tiempo
        rmssd = np.sqrt(np.mean(np.diff(rr_intervals) ** 2))  # Root Mean Square of Successive Differences
        sdnn = np.std(rr_intervals)  # Standard Deviation of NN intervals
        
        # Métricas estadísticas
        cv = (np.std(valid_bpm) / np.mean(valid_bpm)) * 100  # Coeficiente de variación
        
        # Análisis de frecuencia (simplificado)
        # Calcular PSD de la señal de BPM
        if len(valid_bpm) > 50:
            freqs, psd = signal.welch(valid_bpm, fs=1.0, nperseg=min(len(valid_bpm)//4, 256))
            
            # Bandas de frecuencia HRV
            lf_band = (freqs >= 0.04) & (freqs <= 0.15)  # Low Frequency
            hf_band = (freqs >= 0.15) & (freqs <= 0.4)   # High Frequency
            
            lf_power = np.trapz(psd[lf_band], freqs[lf_band])
            hf_power = np.trapz(psd[hf_band], freqs[hf_band])
            lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0
        else:
            lf_power = hf_power = lf_hf_ratio = 0
        
        return {
            'mean_bpm': float(np.mean(valid_bpm)),
            'std_bpm': float(np.std(valid_bpm)),
            'min_bpm': float(np.min(valid_bpm)),
            'max_bpm': float(np.max(valid_bpm)),
            'cv_bpm': float(cv),
            'rmssd': float(rmssd),
            'sdnn': float(sdnn),
            'lf_power': float(lf_power),
            'hf_power': float(hf_power),
            'lf_hf_ratio': float(lf_hf_ratio)
        }
    
    def _calculate_stress_metrics(self, bpm_data: np.ndarray, ppg_data: np.ndarray, 
                                 time_seconds: np.ndarray) -> Dict:
        """Calcula métricas de respuesta al estrés"""
        
        # Segmentar la sesión en tercios para análisis temporal
        third = len(bpm_data) // 3
        
        inicio_bpm = bpm_data[:third]
        medio_bpm = bpm_data[third:2*third]
        final_bpm = bpm_data[2*third:]
        
        # Tendencia general del BPM
        if len(bpm_data) > 10:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                time_seconds, bpm_data
            )
        else:
            slope = r_value = 0
        
        # Detección de picos de estrés (aumentos súbitos de BPM)
        stress_peaks = self._detect_stress_peaks(bpm_data, time_seconds)
        
        # Amplitud de variación de PPG (indicador de tono vascular)
        ppg_amplitude = np.max(ppg_data) - np.min(ppg_data) if len(ppg_data) > 0 else 0
        
        return {
            'bpm_trend_slope': float(slope),
            'bpm_trend_correlation': float(r_value),
            'inicio_mean_bpm': float(np.mean(inicio_bpm)) if len(inicio_bpm) > 0 else 0,
            'final_mean_bpm': float(np.mean(final_bpm)) if len(final_bpm) > 0 else 0,
            'bpm_change_percent': float(
                ((np.mean(final_bpm) - np.mean(inicio_bpm)) / np.mean(inicio_bpm)) * 100
            ) if len(inicio_bpm) > 0 and len(final_bpm) > 0 else 0,
            'stress_peaks_count': len(stress_peaks),
            'stress_peaks_times': [float(t) for t in stress_peaks],
            'ppg_amplitude': float(ppg_amplitude)
        }
    
    def _detect_stress_peaks(self, bpm_data: np.ndarray, time_seconds: np.ndarray) -> List[float]:
        """Detecta picos de estrés en la señal de BPM"""
        
        if len(bpm_data) < 10:
            return []
        
        # Suavizar la señal para detectar tendencias
        window_size = min(25, len(bpm_data) // 4)  # Ventana de ~10 segundos a 125Hz
        if window_size < 3:
            return []
            
        smoothed_bpm = signal.savgol_filter(bpm_data, window_size, 3)
        
        # Detectar aumentos súbitos (> 10 BPM en < 30 segundos)
        stress_peaks = []
        threshold = 10  # BPM
        
        for i in range(len(smoothed_bpm) - 1):
            current_time = time_seconds[i]
            
            # Buscar ventana de 30 segundos hacia adelante
            future_idx = np.where(time_seconds <= current_time + 30)[0]
            if len(future_idx) > 0:
                future_max = np.max(smoothed_bpm[i:future_idx[-1]])
                if future_max - smoothed_bpm[i] > threshold:
                    stress_peaks.append(current_time)
        
        return stress_peaks
    
    def _calculate_relaxation_metrics(self, bpm_data: np.ndarray, time_seconds: np.ndarray) -> Dict:
        """Calcula métricas de tendencias de relajación"""
        
        if len(bpm_data) < 20:
            return {'error': 'Datos insuficientes para análisis de relajación'}
        
        # Análisis por ventanas deslizantes de 5 minutos
        window_duration = 300  # 5 minutos en segundos
        window_metrics = []
        
        current_time = 0
        while current_time + window_duration <= time_seconds[-1]:
            # Seleccionar datos en la ventana
            window_mask = (time_seconds >= current_time) & (time_seconds <= current_time + window_duration)
            window_bpm = bpm_data[window_mask]
            
            if len(window_bpm) > 10:
                window_metrics.append({
                    'time_start': current_time,
                    'mean_bpm': np.mean(window_bpm),
                    'std_bpm': np.std(window_bpm),
                    'trend_slope': self._calculate_local_trend(window_bpm)
                })
            
            current_time += 60  # Avanzar 1 minuto
        
        # Identificar períodos de relajación (BPM decreciente y estable)
        relaxation_periods = []
        for i, metrics in enumerate(window_metrics):
            if (metrics['trend_slope'] < -0.5 and  # BPM decreciente
                metrics['std_bpm'] < 5):            # BPM estable
                relaxation_periods.append(metrics['time_start'])
        
        # Calcular métricas globales de relajación
        total_relaxation_time = len(relaxation_periods) * 60  # en segundos
        relaxation_percentage = (total_relaxation_time / time_seconds[-1]) * 100
        
        return {
            'window_analysis': window_metrics,
            'relaxation_periods': relaxation_periods,
            'total_relaxation_time_minutes': float(total_relaxation_time / 60),
            'relaxation_percentage': float(relaxation_percentage),
            'baseline_bpm': float(np.percentile(bpm_data, 10)),  # BPM basal (percentil 10)
            'recovery_rate': self._calculate_recovery_rate(bpm_data, time_seconds)
        }
    
    def _calculate_local_trend(self, data: np.ndarray) -> float:
        """Calcula la tendencia local de una serie de datos"""
        if len(data) < 3:
            return 0.0
        
        x = np.arange(len(data))
        slope, _, _, _, _ = stats.linregress(x, data)
        return float(slope)
    
    def _calculate_recovery_rate(self, bpm_data: np.ndarray, time_seconds: np.ndarray) -> float:
        """Calcula la tasa de recuperación cardiovascular"""
        
        # Buscar el BPM máximo y ver qué tan rápido vuelve al baseline
        max_bpm_idx = np.argmax(bpm_data)
        max_bpm = bpm_data[max_bpm_idx]
        baseline = np.percentile(bpm_data, 25)  # Baseline más conservador
        
        # Buscar cuánto tarda en volver al 80% del camino al baseline
        target_bpm = max_bpm - 0.8 * (max_bpm - baseline)
        
        # Buscar después del pico máximo
        post_peak_data = bpm_data[max_bpm_idx:]
        post_peak_times = time_seconds[max_bpm_idx:]
        
        recovery_idx = np.where(post_peak_data <= target_bpm)[0]
        
        if len(recovery_idx) > 0:
            recovery_time = post_peak_times[recovery_idx[0]] - post_peak_times[0]
            return float(recovery_time)  # tiempo en segundos
        
        return float('inf')  # No se recuperó en la sesión
    
    def _calculate_eog_metrics(self, eog_data: np.ndarray, time_seconds: np.ndarray) -> Dict:
        """Calcula métricas de patrones de movimientos oculares"""
        
        if len(eog_data) < 10:
            return {'error': 'Datos EOG insuficientes'}
        
        # Análisis de actividad ocular
        eog_amplitude = np.max(eog_data) - np.min(eog_data)
        eog_rms = np.sqrt(np.mean(eog_data ** 2))
        
        # Detección de movimientos oculares (cruces por cero)
        zero_crossings = np.where(np.diff(np.signbit(eog_data)))[0]
        movement_rate = len(zero_crossings) / time_seconds[-1]  # movimientos por segundo
        
        # Análisis de frecuencia de movimientos
        if len(eog_data) > 100:
            freqs, psd = signal.welch(eog_data, fs=self.sample_rate, nperseg=min(len(eog_data)//4, 512))
            
            # Banda de frecuencia típica de movimientos oculares (0.1-10 Hz)
            eye_movement_band = (freqs >= 0.1) & (freqs <= 10)
            eye_movement_power = np.trapz(psd[eye_movement_band], freqs[eye_movement_band])
        else:
            eye_movement_power = 0
        
        # Análisis de simetría (indicador de seguimiento bilateral)
        eog_skewness = float(stats.skew(eog_data))
        eog_kurtosis = float(stats.kurtosis(eog_data))
        
        return {
            'amplitude': float(eog_amplitude),
            'rms': float(eog_rms),
            'movement_rate_per_second': float(movement_rate),
            'total_movements': len(zero_crossings),
            'eye_movement_power': float(eye_movement_power),
            'skewness': eog_skewness,
            'kurtosis': eog_kurtosis,
            'bilateral_symmetry_index': float(1.0 / (1.0 + abs(eog_skewness)))  # Más cerca de 1 = más simétrico
        }
    
    def _calculate_temporal_analysis(self, bpm_data: np.ndarray, ppg_data: np.ndarray, 
                                   eog_data: np.ndarray, time_seconds: np.ndarray) -> Dict:
        """Análisis temporal por segmentos de la sesión"""
        
        # Dividir sesión en 6 segmentos de ~8 minutos cada uno
        n_segments = 6
        segment_duration = time_seconds[-1] / n_segments
        
        segment_analysis = []
        
        for i in range(n_segments):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            # Seleccionar datos del segmento
            segment_mask = (time_seconds >= start_time) & (time_seconds <= end_time)
            
            seg_bpm = bpm_data[segment_mask]
            seg_ppg = ppg_data[segment_mask]
            seg_eog = eog_data[segment_mask]
            
            if len(seg_bpm) > 5:
                segment_metrics = {
                    'segment': i + 1,
                    'time_start_minutes': float(start_time / 60),
                    'time_end_minutes': float(end_time / 60),
                    'mean_bpm': float(np.mean(seg_bpm)),
                    'std_bpm': float(np.std(seg_bpm)),
                    'ppg_amplitude': float(np.max(seg_ppg) - np.min(seg_ppg)) if len(seg_ppg) > 0 else 0,
                    'eog_activity': float(np.std(seg_eog)) if len(seg_eog) > 0 else 0
                }
                segment_analysis.append(segment_metrics)
        
        return {
            'segments': segment_analysis,
            'progression_analysis': self._analyze_progression(segment_analysis)
        }
    
    def _analyze_progression(self, segment_analysis: List[Dict]) -> Dict:
        """Analiza la progresión a lo largo de la sesión"""
        
        if len(segment_analysis) < 3:
            return {'error': 'Segmentos insuficientes'}
        
        # Extraer series temporales
        bpm_progression = [seg['mean_bpm'] for seg in segment_analysis]
        stress_progression = [seg['std_bpm'] for seg in segment_analysis]
        
        # Calcular tendencias
        x = np.arange(len(bpm_progression))
        bpm_trend, _, bpm_r, _, _ = stats.linregress(x, bpm_progression)
        stress_trend, _, stress_r, _, _ = stats.linregress(x, stress_progression)
        
        return {
            'bpm_trend_slope': float(bpm_trend),
            'bpm_trend_correlation': float(bpm_r),
            'stress_trend_slope': float(stress_trend),
            'stress_trend_correlation': float(stress_r),
            'initial_vs_final_bpm_change': float(bpm_progression[-1] - bpm_progression[0]),
            'session_stability': float(1.0 / (1.0 + np.std(bpm_progression)))  # Más cerca de 1 = más estable
        }