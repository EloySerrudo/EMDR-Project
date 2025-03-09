import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt
import time
import csv
from datetime import datetime

class PulseAnalyzer:
    def __init__(self, sample_rate=1000):
        self.sample_rate = sample_rate
        
    def filter_signal(self, data, lowcut=0.5, highcut=5.0, order=2):
        """Aplica un filtro paso banda al señal de pulso"""
        nyq = 0.5 * self.sample_rate
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        filtered_data = filtfilt(b, a, data)
        return filtered_data
    
    def find_heartbeats(self, data, filtered_data=None, distance=None):
        """Encuentra los latidos en una señal de pulso"""
        if filtered_data is None:
            filtered_data = self.filter_signal(data)
            
        if distance is None:
            # Si no se especifica, usar una distancia que corresponde a ~180 BPM
            distance = int(self.sample_rate * 60 / 180)
        
        # Encontrar picos en la señal filtrada
        peaks, _ = find_peaks(filtered_data, distance=distance, height=0)
        
        return peaks, filtered_data
    
    def calculate_heart_rate(self, peaks, signal_duration):
        """Calcula la frecuencia cardíaca promedio"""
        if len(peaks) < 2:
            return 0
        
        # Calcular intervalos entre picos
        intervals = np.diff(peaks) / self.sample_rate  # en segundos
        
        # Calcular BPM promedio
        avg_interval = np.mean(intervals)
        bpm = 60 / avg_interval
        
        return bpm
    
    def analyze_recording(self, times, values, output_prefix=None):
        """Analiza una grabación completa y genera visualizaciones"""
        data = np.array(values)
        time_array = np.array(times)
        
        # Filtrar señal
        filtered_data = self.filter_signal(data)
        
        # Encontrar picos (latidos)
        peaks, _ = self.find_heartbeats(data, filtered_data)
        
        # Calcular frecuencia cardíaca
        duration = time_array[-1] - time_array[0]
        bpm = self.calculate_heart_rate(peaks, duration)
        
        # Crear visualización
        plt.figure(figsize=(12, 10))
        
        # Señal original
        plt.subplot(3, 1, 1)
        plt.plot(time_array, data, 'b-')
        plt.title('Señal Original')
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Valor ADC')
        plt.grid(True)
        
        # Señal filtrada con picos detectados
        plt.subplot(3, 1, 2)
        plt.plot(time_array, filtered_data, 'g-')
        plt.plot(time_array[peaks], filtered_data[peaks], 'ro')
        plt.title(f'Señal Filtrada con Picos Detectados (BPM: {bpm:.1f})')
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Amplitud')
        plt.grid(True)
        
        # Histograma de intervalos entre latidos
        if len(peaks) >= 2:
            intervals = np.diff(peaks) / self.sample_rate  # en segundos
            plt.subplot(3, 1, 3)
            plt.hist(intervals, bins=20, alpha=0.7)
            plt.axvline(x=np.mean(intervals), color='r', linestyle='--')
            plt.title(f'Distribución de Intervalos entre Latidos (Media: {np.mean(intervals):.3f}s)')
            plt.xlabel('Intervalo (s)')
            plt.ylabel('Frecuencia')
            plt.grid(True)
        
        plt.tight_layout()
        
        # Guardar archivos si se proporciona un prefijo
        if output_prefix:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Guardar gráfico
            plt.savefig(f"{output_prefix}_{timestamp}_analysis.png")
            
            # Guardar datos en CSV
            with open(f"{output_prefix}_{timestamp}_data.csv", 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Time', 'Raw_Value', 'Filtered_Value'])
                for i in range(len(time_array)):
                    writer.writerow([time_array[i], data[i], filtered_data[i]])
            
            # Guardar resultados en un archivo de texto
            with open(f"{output_prefix}_{timestamp}_results.txt", 'w') as f:
                f.write(f"Análisis de Pulso Cardiaco - {timestamp}\n")
                f.write(f"Duración de la grabación: {duration:.2f} segundos\n")
                f.write(f"Número de latidos detectados: {len(peaks)}\n")
                f.write(f"Frecuencia cardíaca promedio: {bpm:.1f} BPM\n")
                
                if len(peaks) >= 2:
                    f.write(f"Intervalo medio entre latidos: {np.mean(intervals):.3f} segundos\n")
                    f.write(f"Intervalo mínimo: {np.min(intervals):.3f} segundos\n")
                    f.write(f"Intervalo máximo: {np.max(intervals):.3f} segundos\n")
                    f.write(f"Desviación estándar: {np.std(intervals):.3f} segundos\n")
        
        return bpm, peaks, filtered_data

if __name__ == "__main__":
    print("Este es un módulo de análisis y debe importarse desde otro script.")
    print("Para una demostración, ejecute pulse_monitor.py primero.")
