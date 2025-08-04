import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
# import seaborn as sns
from datetime import datetime

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.database.database_manager import DatabaseManager
from src.sensor.sensor_monitor import SAMPLE_RATE


class SignalAnalyzer:
    def __init__(self, db_path='../database/database.db'):
        self.db_path = db_path
        self.data = None
        
    def load_all_sessions(self):
        """Cargar todos los datos de sesiones"""
        # Obtener todos los pacientes para luego obtener sus sesiones
        patients = DatabaseManager.get_all_patients()
        if not patients:
            print("No hay pacientes en la base de datos")
            return False
            
        session_data = {
            'session_ids': [],
            'patient_ids': [],
            'fechas': [],
            'datos_eog': [],
            'datos_ppg': [],
            'datos_bpm': [],
            'notas': []
        }
        
        # Recopilar datos de todas las sesiones
        for patient in patients:
            sessions = DatabaseManager.get_sessions_for_patient(patient['id'])
            for session in sessions:
                # Obtener datos completos de la sesión
                full_session_data = DatabaseManager.get_session(session_id=session['id'], signal_data=True)
                if full_session_data:
                    session_data['session_ids'].append(session['id'])
                    session_data['patient_ids'].append(patient['id'])
                    session_data['fechas'].append(session['fecha'])
                    session_data['notas'].append(session['notas'])
                    session_data['datos_eog'].append(full_session_data.get('datos_eog'))
                    session_data['datos_ppg'].append(full_session_data.get('datos_ppg'))
                    session_data['datos_bpm'].append(full_session_data.get('datos_bpm'))
        
        self.data = session_data
        return len(session_data['session_ids']) > 0
    
    def plot_session_signals(self, session_index=0, save_path=None):
        """
        Graficar las señales de una sesión específica
        
        Args:
            session_index (int): Índice de la sesión (0 = más reciente)
            save_path (str): Ruta para guardar la figura
        """
        if not self.data:
            print("No hay datos cargados. Ejecuta load_all_sessions() primero")
            return
            
        if session_index >= len(self.data['session_ids']):
            print(f"Índice fuera de rango. Máximo: {len(self.data['session_ids'])-1}")
            return
        
        # Obtener datos de la sesión
        eog_data = self.data['datos_eog'][session_index]
        ppg_data = self.data['datos_ppg'][session_index]
        bpm_data = self.data['datos_bpm'][session_index]
        fecha = self.data['fechas'][session_index]
        patient_id = self.data['patient_ids'][session_index]
        
        # Crear figura con subplots
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        fig.suptitle(f'Señales Fisiológicas - Paciente {patient_id} - {fecha}', fontsize=16)
        
        # Plot EOG
        if eog_data is not None:
            eog_array = np.array(eog_data)
            time_eog = np.linspace(0, len(eog_array)/SAMPLE_RATE, len(eog_array))
            axes[0].plot(time_eog, eog_array, 'b-', linewidth=0.8)
            axes[0].set_title('Señal EOG (Electrooculograma)')
            axes[0].set_ylabel('Amplitud (µV)')
            axes[0].grid(True, alpha=0.3)
        else:
            axes[0].text(0.5, 0.5, 'No hay datos EOG', ha='center', va='center', transform=axes[0].transAxes)
        
        # Plot PPG
        if ppg_data is not None:
            ppg_array = np.array(ppg_data)
            time_ppg = np.linspace(0, len(ppg_array)/SAMPLE_RATE, len(ppg_array))
            axes[1].plot(time_ppg, ppg_array, 'r-', linewidth=0.8)
            axes[1].set_title('Señal PPG (Fotopletismografía)')
            axes[1].set_ylabel('Amplitud')
            axes[1].grid(True, alpha=0.3)
        else:
            axes[1].text(0.5, 0.5, 'No hay datos PPG', ha='center', va='center', transform=axes[1].transAxes)
        
        # Plot BPM
        if bpm_data is not None:
            bpm_array = np.array(bpm_data)
            time_bpm = np.linspace(0, len(bpm_array)/SAMPLE_RATE, len(bpm_array))  # BPM capturado a SAMPLE_RATE Hz
            axes[2].plot(time_bpm, bpm_array, 'g-', linewidth=1.5)
            axes[2].set_title('Frecuencia Cardíaca (BPM)')
            axes[2].set_ylabel('BPM')
            axes[2].set_xlabel('Tiempo (s)')
            axes[2].grid(True, alpha=0.3)
        else:
            axes[2].text(0.5, 0.5, 'No hay datos BPM', ha='center', va='center', transform=axes[2].transAxes)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Figura guardada en: {save_path}")
        
        plt.show()
    
    def analyze_session_statistics(self, session_index=0):
        """
        Análisis estadístico de una sesión
        """
        if not self.data:
            print("No hay datos cargados")
            return
            
        eog_data = self.data['datos_eog'][session_index]
        ppg_data = self.data['datos_ppg'][session_index]
        bpm_data = self.data['datos_bpm'][session_index]
        
        print(f"=== Análisis Sesión {self.data['session_ids'][session_index]} ===")
        print(f"Paciente: {self.data['patient_ids'][session_index]}")
        print(f"Fecha: {self.data['fechas'][session_index]}")
        
        # Estadísticas EOG
        if eog_data is not None:
            eog_array = np.array(eog_data)
            print(f"\nEOG:")
            print(f"  Duración: {len(eog_array)/SAMPLE_RATE:.2f} segundos")
            print(f"  Media: {np.mean(eog_array):.2f} µV")
            print(f"  Desviación estándar: {np.std(eog_array):.2f} µV")
            print(f"  Rango: {np.min(eog_array):.2f} - {np.max(eog_array):.2f} µV")
        
        # Estadísticas PPG
        if ppg_data is not None:
            ppg_array = np.array(ppg_data)
            print(f"\nPPG:")
            print(f"  Duración: {len(ppg_array)/SAMPLE_RATE:.2f} segundos")
            print(f"  Media: {np.mean(ppg_array):.2f}")
            print(f"  Desviación estándar: {np.std(ppg_array):.2f}")
            print(f"  Rango: {np.min(ppg_array):.2f} - {np.max(ppg_array):.2f}")
        
        # Estadísticas BPM
        if bpm_data is not None:
            bpm_array = np.array(bpm_data)
            print(f"\nBPM:")
            print(f"  Duración: {len(bpm_array)} mediciones")
            print(f"  BPM promedio: {np.mean(bpm_array):.1f}")
            print(f"  BPM mínimo: {np.min(bpm_array):.1f}")
            print(f"  BPM máximo: {np.max(bpm_array):.1f}")
            print(f"  Variabilidad (std): {np.std(bpm_array):.1f}")
    
    def compare_sessions(self, patient_id=None, save_path=None):
        """
        Comparar múltiples sesiones de un paciente
        """
        if not self.data:
            print("No hay datos cargados")
            return
        
        # Filtrar por paciente si se especifica
        if patient_id:
            indices = [i for i, pid in enumerate(self.data['patient_ids']) if pid == patient_id]
            title = f'Comparación de Sesiones - Paciente {patient_id}'
        else:
            indices = list(range(len(self.data['session_ids'])))
            title = 'Comparación de Todas las Sesiones'
        
        if len(indices) < 2:
            print("Se necesitan al menos 2 sesiones para comparar")
            return
        
        # Extraer datos BPM para comparación
        bpm_sessions = []
        session_labels = []
        
        for i in indices:
            if self.data['datos_bpm'][i] is not None:
                bpm_sessions.append(np.array(self.data['datos_bpm'][i]))
                session_labels.append(f"Sesión {self.data['session_ids'][i]}")
        
        if not bpm_sessions:
            print("No hay datos BPM para comparar")
            return
        
        # Crear gráfico de comparación
        plt.figure(figsize=(12, 8))
        
        # Boxplot de BPM
        plt.subplot(2, 1, 1)
        plt.boxplot(bpm_sessions, labels=session_labels)
        plt.title('Distribución de BPM por Sesión')
        plt.ylabel('BPM')
        plt.xticks(rotation=45)
        
        # Tendencia temporal
        plt.subplot(2, 1, 2)
        for i, bpm_data in enumerate(bpm_sessions):
            plt.plot(bpm_data, label=session_labels[i], alpha=0.7)
        
        plt.title('Evolución Temporal de BPM')
        plt.xlabel('Tiempo (mediciones)')
        plt.ylabel('BPM')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=16)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparación guardada en: {save_path}")
        
        plt.show()

# Ejemplo de uso
if __name__ == "__main__":
    # Crear analizador
    analyzer = SignalAnalyzer()
    
    # Cargar datos
    if analyzer.load_all_sessions():
        print("Datos cargados exitosamente")
        
        # Analizar primera sesión
        analyzer.analyze_session_statistics(3)
        
        # Graficar señales de la primera sesión
        analyzer.plot_session_signals(3)#, save_path='session_analysis.png')
        
        # Comparar sesiones (si hay múltiples)
        # analyzer.compare_sessions(save_path='sessions_comparison.png')
    else:
        print("Error cargando datos")