"""
Ventana para análisis offline de señales EOG guardadas en archivos CSV.

Permite cargar archivos CSV de datos EOG y visualizarlos de forma interactiva
con filtrado offline de alta calidad y navegación temporal.
"""

import sys
import numpy as np
import pandas as pd
import pyqtgraph as pg
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QFileDialog, QMessageBox, QSlider, QSpinBox,
    QFrame, QGroupBox, QGridLayout, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

# Importar el filtro offline
import sys
from pathlib import Path

# Añadir el directorio src al path para las importaciones
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.signal_processing import OfflineEOGFilter

# Constantes de conversión
ADC_TO_MICROVOLTS = 0.0078125 * 4.03225806  # Ganancia de 16 del ADS1115 y 248 del AD620 * 1000 µV


class FilteringThread(QThread):
    """Hilo para procesar filtrado offline sin bloquear la UI"""
    
    progress_updated = Signal(int)
    filtering_completed = Signal(np.ndarray)  # ✅ Cambiar a retornar solo el array
    error_occurred = Signal(str)
    
    def __init__(self, eog_data_uv, sample_rate=125):
        super().__init__()
        self.eog_data_uv = eog_data_uv
        self.sample_rate = sample_rate
        
    def run(self):
        """Ejecutar filtrado en hilo separado"""
        try:
            self.progress_updated.emit(25)
            offline_filter = OfflineEOGFilter(fs=self.sample_rate)
            
            self.progress_updated.emit(50)
            # Aplicar filtrado con fase cero
            result = offline_filter.filter_signal(self.eog_data_uv)
            
            self.progress_updated.emit(100)
            # ✅ CORRECCIÓN: Emitir solo el array filtrado
            self.filtering_completed.emit(result['filtered'])
            
        except Exception as e:
            self.error_occurred.emit(f"Error en el hilo de filtrado: {e}")


class OfflineAnalysisWindow(QMainWindow):
    """Ventana principal para análisis offline de señales EOG"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Análisis Offline - Señales EOG")
        self.setGeometry(100, 100, 1400, 800)
        
        # Variables de datos
        self.df = None
        self.eog_raw = None
        self.eog_raw_uv = None
        self.eog_filtered_uv = None
        self.time_seconds = None
        self.sample_rate = 125
        self.test_name = "Desconocido"
        
        # Variables de visualización
        self.window_duration = 8
        self.current_position = 0  # posición actual en segundos
        
        # Thread para filtrado
        self.filtering_thread = None
        
        self.setup_ui()
        self.setup_plots()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Estilo oscuro
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QWidget {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444444;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border: 2px solid #666666;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                background: #3A3A3A;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4ECDC4;
                border: 2px solid #4ECDC4;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSpinBox {
                background-color: #3A3A3A;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
                color: #FFFFFF;
            }
        """)
        
        # Panel de control superior
        self.create_control_panel(main_layout)
        
        # Área de gráficas
        self.create_plots_area(main_layout)
        
        # Panel de navegación
        self.create_navigation_panel(main_layout)
        
        # ELIMINADO: Panel de información
        # self.create_info_panel(main_layout)
        
    def create_control_panel(self, main_layout):
        """Crear panel de control para cargar archivos"""
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(15, 10, 15, 10)
        
        # Título
        title_label = QLabel("📊 Análisis Offline de Señales EOG")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #4ECDC4; margin-right: 20px;")
        
        # Botón cargar archivo
        self.load_file_btn = QPushButton("📁 Cargar Archivo CSV")
        self.load_file_btn.setStyleSheet(self.get_button_style('#2196F3'))
        self.load_file_btn.clicked.connect(self.load_csv_file)
        
        # Label estado del archivo
        self.file_status_label = QLabel("No hay archivo cargado")
        self.file_status_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        
        # ELIMINADO: Botón de procesar
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                color: #FFFFFF;
                background-color: #2A2A2A;
            }
            QProgressBar::chunk {
                background-color: #4ECDC4;
                border-radius: 3px;
            }
        """)
        
        control_layout.addWidget(title_label)
        control_layout.addStretch()
        control_layout.addWidget(self.load_file_btn)
        control_layout.addWidget(self.file_status_label)
        # ELIMINADO: control_layout.addWidget(self.process_btn)
        control_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(control_frame)
        
    def create_plots_area(self, main_layout):
        """Crear área de gráficas para la señal procesada y la referencia ideal"""
        plots_frame = QFrame()
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(10, 10, 10, 10)
        
        pg.setConfigOption('background', '#1A1A1A')
        pg.setConfigOption('foreground', '#FFFFFF')
        
        # Gráfica superior: Señal EOG procesada
        self.plot_eog = pg.PlotWidget(title="Señal EOG Procesada (Filtrada y Recortada)")
        self.plot_eog.setFixedHeight(300)
        self.plot_eog.setLabel('left', 'Amplitud', units='µV')
        self.plot_eog.setLabel('bottom', 'Tiempo', units='s')
        
        # Gráfica inferior: Señal de referencia ideal
        self.plot_reference = pg.PlotWidget(title="Señal de Referencia Ideal")
        self.plot_reference.setFixedHeight(200)
        self.plot_reference.setLabel('left', 'Ángulo', units='°')
        self.plot_reference.setLabel('bottom', 'Tiempo', units='s')
        
        # Sincronizar zoom y paneo en el eje X
        self.plot_reference.setXLink(self.plot_eog)
        
        plots_layout.addWidget(self.plot_eog)
        plots_layout.addWidget(self.plot_reference)
        
        main_layout.addWidget(plots_frame)
        
    def create_navigation_panel(self, main_layout):
        """Crear panel de navegación temporal"""
        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 10, 15, 10)
        
        # Control de ventana de tiempo
        window_label = QLabel("Ventana:")
        self.window_spinbox = QSpinBox()
        self.window_spinbox.setRange(2, 30)
        self.window_spinbox.setValue(8)
        self.window_spinbox.setSuffix(" segundos")
        self.window_spinbox.valueChanged.connect(self.update_window_duration)
        
        # Slider de navegación
        nav_label = QLabel("Navegación:")
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(0)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self.update_time_position)
        
        # Label posición actual
        self.position_label = QLabel("Posición: 0.0 / 0.0 s")
        self.position_label.setStyleSheet("color: #4ECDC4; font-weight: bold;")
        
        nav_layout.addWidget(window_label)
        nav_layout.addWidget(self.window_spinbox)
        nav_layout.addWidget(QLabel("   "))  # Espaciador
        nav_layout.addWidget(nav_label)
        nav_layout.addWidget(self.time_slider)
        nav_layout.addWidget(self.position_label)
        
        main_layout.addWidget(nav_frame)
        
    # ELIMINADO: create_info_panel
        
    def setup_plots(self):
        """Configurar las curvas de las gráficas"""
        # Curva para la señal EOG procesada
        self.curve_eog = self.plot_eog.plot(
            pen=pg.mkPen(color='#4ECDC4', width=2),
            name='EOG Procesada (µV)'
        )
        
        # Curva para la señal de referencia ideal
        self.curve_reference = self.plot_reference.plot(
            pen=pg.mkPen(color='#FFCA58', width=2, style=Qt.DashLine),
            name='Referencia Ideal (°)'
        )
        
    def get_button_style(self, color):
        """Generar estilo para botones"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid {color};
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: transparent;
                border: 2px solid {color};
                color: {color};
            }}
            QPushButton:pressed {{
                background-color: {color};
                border: 2px solid {color};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                border: 2px solid #666666;
                color: #AAAAAA;
            }}
        """
        
    def load_csv_file(self):
        """Cargar archivo CSV con datos EOG"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo CSV de datos EOG",
            str(Path(__file__).parent.parent / 'data'),
            "CSV files (*.csv)"
        )
        
        if file_path:
            try:
                # Leer el nombre de la prueba de la primera línea
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.test_name = f.readline().strip().replace('#', '').strip()

                # Cargar datos saltando las 2 primeras filas de comentarios
                self.df = pd.read_csv(file_path, skiprows=2)
                
                # Verificar columnas requeridas
                required_columns = ['timestamp', 'eog_raw', 'event']
                missing_columns = [col for col in required_columns if col not in self.df.columns]
                
                if missing_columns:
                    QMessageBox.critical(
                        self,
                        "Error en archivo CSV",
                        f"El archivo no contiene las columnas requeridas:\n{missing_columns}\n\n"
                        f"Columnas disponibles: {list(self.df.columns)}"
                    )
                    return
                
                # Extraer datos
                self.timestamps = self.df['timestamp'].values
                self.eog_raw = self.df['eog_raw'].values
                
                # ✅ CONVERTIR ADC A MICROVOLTIOS
                self.eog_raw_uv = self.eog_raw * ADC_TO_MICROVOLTS
                print(f"Conversión ADC → µV: Factor = {ADC_TO_MICROVOLTS:.6f}")
                print(f"Rango ADC: {np.min(self.eog_raw):.1f} - {np.max(self.eog_raw):.1f}")
                print(f"Rango µV: {np.min(self.eog_raw_uv):.1f} - {np.max(self.eog_raw_uv):.1f} µV")
                
                # Convertir timestamp a segundos relativos
                self.time_seconds = (self.timestamps - self.timestamps[0]) / 1000.0
                
                # Calcular frecuencia de muestreo
                if len(self.time_seconds) > 1:
                    time_diff = np.diff(self.time_seconds)
                    mean_interval = np.mean(time_diff)
                    self.sample_rate = 1.0 / mean_interval
                
                # Actualizar UI
                filename = Path(file_path).name
                duration = self.time_seconds[-1]
                samples = len(self.eog_raw)
                
                # Mostrar rangos en µV en el status
                uv_range = f"{np.min(self.eog_raw_uv):.1f} - {np.max(self.eog_raw_uv):.1f} µV"
                
                self.file_status_label.setText(
                    f"✅ {self.test_name} | {samples} muestras | {duration:.1f}s"
                )
                self.file_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                # Iniciar procesamiento automático
                self.process_signal()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al cargar archivo",
                    f"No se pudo cargar el archivo:\n{str(e)}"
                )
                
    def process_signal(self):
        """Inicia el hilo de filtrado de la señal cargada."""
        if self.eog_raw_uv is None:
            QMessageBox.warning(self, "Advertencia", "No hay datos de EOG para procesar.")
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.load_file_btn.setEnabled(False)
        
        self.filtering_thread = FilteringThread(self.eog_raw_uv, self.sample_rate)
        self.filtering_thread.progress_updated.connect(self.progress_bar.setValue)
        self.filtering_thread.filtering_completed.connect(self.on_filtering_completed)
        self.filtering_thread.error_occurred.connect(self.on_filtering_error)
        self.filtering_thread.start()
            
    def on_filtering_completed(self, filtered_result):
        """Se ejecuta al completar el filtrado. Inicia la segmentación y graficado."""
        # ✅ CORRECCIÓN: extraer el array filtrado del resultado
        if isinstance(filtered_result, dict):
            self.eog_filtered_uv = filtered_result['filtered']
            self.filtering_metadata = filtered_result.get('metadata', {})
        else:
            # Si es un array directo (por compatibilidad)
            self.eog_filtered_uv = filtered_result
            self.filtering_metadata = {}
        
        self.progress_bar.setVisible(False)
        self.load_file_btn.setEnabled(True)

        QMessageBox.information(self, "Procesamiento Completo", "La señal ha sido filtrada. Ahora se segmentará y graficará.")

        self.segment_and_plot_data()

    def segment_and_plot_data(self):
        """Recorta los datos según eventos y genera la gráfica de referencia."""
        try:
            # Verificar que tenemos datos filtrados
            if self.eog_filtered_uv is None:
                raise ValueError("No hay datos filtrados disponibles")
            
            # ✅ CORRECCIÓN: asegurar que sea array numpy
            if not isinstance(self.eog_filtered_uv, np.ndarray):
                self.eog_filtered_uv = np.array(self.eog_filtered_uv)
            
            print(f"Tipo de eog_filtered_uv: {type(self.eog_filtered_uv)}")
            print(f"Shape de eog_filtered_uv: {self.eog_filtered_uv.shape}")
            
            # Identificar protocolo y recortar datos
            events_df = self.df[['timestamp', 'event']].dropna()
            
            start_event, end_event, protocol_type = (None, None, None)

            if not events_df[events_df['event'] == 'STEP_FIXATION_START'].empty:
                start_event = 'STEP_FIXATION_START'
                end_event = 'STEP_FIXATION_END'
                protocol_type = 'Step Fixation'
            elif not events_df[events_df['event'] == 'LINEAR_PURSUIT_START'].empty:
                start_event = 'LINEAR_PURSUIT_START'
                end_event = 'LINEAR_PURSUIT_END'
                protocol_type = 'Linear Pursuit'
            
            if not protocol_type:
                raise ValueError("No se encontraron eventos de inicio/fin de protocolo conocidos.")

            # Obtener los índices correctamente
            start_event_rows = events_df[events_df['event'] == start_event]
            end_event_rows = events_df[events_df['event'] == end_event]
            
            if start_event_rows.empty or end_event_rows.empty:
                raise ValueError(f"No se encontraron eventos completos para {protocol_type}")
            
            # Obtener los índices en el DataFrame original
            start_idx = start_event_rows.index[0]
            end_idx = end_event_rows.index[0]
            
            print(f"Protocolo detectado: {protocol_type}")
            print(f"Índice inicio: {start_idx}, Índice fin: {end_idx}")
            print(f"Longitud original eog_filtered_uv: {len(self.eog_filtered_uv)}")
            print(f"Longitud original DataFrame: {len(self.df)}")
            
            # ✅ CORRECCIÓN: Verificar que los índices sean válidos
            if start_idx >= len(self.eog_filtered_uv) or end_idx >= len(self.eog_filtered_uv):
                raise ValueError(f"Índices fuera de rango: start={start_idx}, end={end_idx}, len={len(self.eog_filtered_uv)}")
            
            # Convertir timestamps a tiempo relativo desde el inicio
            timestamps_segment = self.df['timestamp'].iloc[start_idx:end_idx+1].values
            self.time_seconds = (timestamps_segment - timestamps_segment[0]) / 1000.0
            
            # ✅ CORRECCIÓN: Recortar la señal filtrada usando slice numpy
            self.eog_filtered_uv = self.eog_filtered_uv[start_idx:end_idx+1]
            
            print(f"Datos recortados: {len(self.time_seconds)} muestras, {self.time_seconds[-1]:.1f}s")
            print(f"Nueva longitud eog_filtered_uv: {len(self.eog_filtered_uv)}")
            
            # Recortar los eventos también para la generación de referencia
            events_segment = events_df.iloc[start_idx:end_idx+1].copy()
            
            # Generar señal de referencia
            reference_signal = self.generate_reference_signal(protocol_type, events_segment)

            # Actualizar plots con datos recortados
            self.update_plots(reference_signal)
            
            # Configurar slider de navegación para el nuevo rango
            duration = self.time_seconds[-1] - self.time_seconds[0]
            max_time = max(0, duration - self.window_duration)
            self.time_slider.setMaximum(int(max_time * 10)) # Mayor resolución
            self.time_slider.setValue(0)
            self.current_position = self.time_seconds[0] # Posición inicial
            
            self.plot_eog.setTitle(f"Señal EOG Procesada - {protocol_type}")
            
            print(f"Segmentación completada para {protocol_type}")

        except Exception as e:
            print(f"Error en segmentación: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error de Segmentación", f"No se pudo procesar el protocolo: {e}")

    def generate_reference_signal(self, protocol_type, events_df):
        """Genera la forma de onda ideal (cuadrada o triangular) basada en los eventos."""
        print(f"Generando señal de referencia para: {protocol_type}")
        
        # Crear un array de referencia vacío con la misma longitud que la señal recortada
        reference = np.zeros_like(self.time_seconds, dtype=float)
        
        if protocol_type == 'Step Fixation':
            # Generar onda cuadrada
            # Filtrar solo los eventos de estímulo relevantes
            stim_events = events_df[events_df['event'].str.contains("STIMULUS_ANGLE", na=False)].copy()
            print(f"Eventos de estímulo encontrados: {len(stim_events)}")
            
            if stim_events.empty:
                print("No se encontraron eventos STIMULUS_ANGLE")
                return reference # No hay eventos para procesar

            # Asegurar que los timestamps están ordenados
            stim_events = stim_events.sort_values('timestamp')

            for i in range(len(stim_events)):
                current_event = stim_events.iloc[i]
                
                # Extraer el ángulo del evento
                try:
                    event_parts = current_event['event'].split('_')
                    angle_str = event_parts[-1]  # Última parte después del último _
                    angle = float(angle_str)
                    print(f"Procesando evento: {current_event['event']}, ángulo: {angle}°")
                except (ValueError, IndexError) as e:
                    print(f"Error extrayendo ángulo de {current_event['event']}: {e}")
                    continue # Ignorar eventos mal formados

                # Definir el rango de tiempo para este ángulo
                start_time = (current_event['timestamp'] - events_df['timestamp'].iloc[0]) / 1000.0
                
                if i + 1 < len(stim_events):
                    end_time = (stim_events.iloc[i + 1]['timestamp'] - events_df['timestamp'].iloc[0]) / 1000.0
                else:
                    end_time = self.time_seconds[-1]
                
                # Crear una máscara booleana para aplicar el ángulo
                mask = (self.time_seconds >= start_time) & (self.time_seconds < end_time)
                samples_affected = np.sum(mask)
                print(f"  Tiempo: {start_time:.2f}-{end_time:.2f}s, muestras: {samples_affected}")
                
                reference[mask] = angle
        
        elif protocol_type == 'Linear Pursuit':
            # Generar onda triangular
            edge_events = events_df[events_df['event'].str.contains("PURSUIT_EDGE", na=False)].copy()
            print(f"Eventos de edge encontrados: {len(edge_events)}")
            
            if len(edge_events) < 2: 
                print("Insuficientes eventos PURSUIT_EDGE para generar triangular")
                return reference

            edge_events = edge_events.sort_values('timestamp')

            for i in range(len(edge_events) - 1):
                start_event_row = edge_events.iloc[i]
                end_event_row = edge_events.iloc[i+1]
                
                start_angle = -20.0 if 'LEFT' in start_event_row['event'] else 20.0
                end_angle = -20.0 if 'LEFT' in end_event_row['event'] else 20.0
                
                start_time = (start_event_row['timestamp'] - events_df['timestamp'].iloc[0]) / 1000.0
                end_time = (end_event_row['timestamp'] - events_df['timestamp'].iloc[0]) / 1000.0

                # Asegurarse de que el tiempo no vaya hacia atrás
                if end_time <= start_time: 
                    print(f"Tiempo inválido: {start_time} -> {end_time}")
                    continue

                mask = (self.time_seconds >= start_time) & (self.time_seconds <= end_time)
                time_segment = self.time_seconds[mask]
                
                # Interpolación lineal
                if len(time_segment) > 0:
                    reference[mask] = np.interp(time_segment, [start_time, end_time], [start_angle, end_angle])
                    print(f"  Segmento {i}: {start_angle}° -> {end_angle}°, {len(time_segment)} muestras")

        print(f"Señal de referencia generada: rango {np.min(reference):.1f} - {np.max(reference):.1f}°")
        return reference

    def on_filtering_error(self, error_msg):
        """Callback cuando ocurre error en el filtrado"""
        self.progress_bar.setVisible(False)
        self.load_file_btn.setEnabled(True)
        QMessageBox.critical(self, "Error en Filtrado", error_msg)
        
    def update_window_duration(self, value):
        """Actualizar duración de ventana de visualización"""
        self.window_duration = value
        
        if self.time_seconds is not None:
            # Reconfigurar slider
            duration = self.time_seconds[-1] - self.time_seconds[0]
            max_time = max(0, duration - self.window_duration)
            self.time_slider.setMaximum(int(max_time * 10))
            
            # Actualizar gráficas
            self.update_plots()
            
    def update_time_position(self, value):
        """Actualizar posición temporal desde el slider."""
        if self.time_seconds is None: return
        start_offset = self.time_seconds[0]
        self.current_position = start_offset + (value / 10.0)
        self.update_plots()
        
        total_duration = self.time_seconds[-1] - self.time_seconds[0]
        current_duration = self.current_position - start_offset
        self.position_label.setText(f"Posición: {current_duration:.1f} / {total_duration:.1f} s")
            
    def update_plots(self, reference_signal=None):
        """Actualizar ambas gráficas con los datos actuales."""
        if self.eog_filtered_uv is None or self.time_seconds is None:
            return

        start_time = self.current_position
        end_time = start_time + self.window_duration
        
        mask = (self.time_seconds >= start_time) & (self.time_seconds <= end_time)
        time_window = self.time_seconds[mask]
        
        # Actualizar plot EOG
        eog_window = self.eog_filtered_uv[mask]
        if len(time_window) > 0:
            self.curve_eog.setData(time_window, eog_window)
            self.plot_eog.setXRange(start_time, end_time, padding=0)

        # Actualizar plot de referencia si se proporciona
        if reference_signal is not None:
            self.reference_signal = reference_signal # Guardar para futuros updates
        
        if hasattr(self, 'reference_signal'):
            ref_window = self.reference_signal[mask]
            if len(time_window) > 0:
                self.curve_reference.setData(time_window, ref_window)
                self.plot_reference.setXRange(start_time, end_time, padding=0)


# Para pruebas independientes
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Crear ventana de prueba de Análisis Offline
    window = OfflineAnalysisWindow()
    window.show()
    sys.exit(app.exec())
