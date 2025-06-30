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
    filtering_completed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, eog_data_uv, sample_rate=125):
        super().__init__()
        self.eog_data_uv = eog_data_uv  # Datos ya en microvoltios
        self.sample_rate = sample_rate
        
    def run(self):
        """Ejecutar filtrado en hilo separado"""
        try:
            # Crear filtro offline
            offline_filter = OfflineEOGFilter(fs=self.sample_rate)
            
            # Simular progreso
            self.progress_updated.emit(25)
            
            # Aplicar filtrado con fase cero (usando datos en µV)
            result = offline_filter.filter_signal(self.eog_data_uv)
            
            self.progress_updated.emit(75)
            
            # Filtrado con limpieza de artefactos
            result_cleaned = offline_filter.filter_with_artifact_removal(
                self.eog_data_uv, remove_blinks=True
            )
            
            self.progress_updated.emit(100)
            
            # Combinar resultados
            final_result = {
                'filtered': result['filtered'],
                'cleaned': result_cleaned.get('cleaned', result['filtered']),
                'metadata': result['metadata'],
                'blink_artifacts': result['blink_artifacts']
            }
            
            self.filtering_completed.emit(final_result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class OfflineAnalysisWindow(QMainWindow):
    """Ventana principal para análisis offline de señales EOG"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Análisis Offline - Señales EOG")
        self.setGeometry(100, 100, 1400, 800)
        
        # Variables de datos
        self.df = None
        self.eog_raw = None          # Datos crudos ADC
        self.eog_raw_uv = None       # Datos crudos en microvoltios
        self.eog_filtered_uv = None  # Datos filtrados en microvoltios
        self.timestamps = None
        self.time_seconds = None
        self.sample_rate = 125  # Hz por defecto
        
        # Variables de visualización
        self.window_duration = 8  # segundos a mostrar
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
        
        # Panel de información
        self.create_info_panel(main_layout)
        
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
        
        # Botón procesar (inicialmente deshabilitado)
        self.process_btn = QPushButton("⚙️ Procesar con Filtro Offline")
        self.process_btn.setStyleSheet(self.get_button_style('#4CAF50'))
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_signal)
        
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
        control_layout.addWidget(self.process_btn)
        control_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(control_frame)
        
    def create_plots_area(self, main_layout):
        """Crear área de gráficas"""
        plots_frame = QFrame()
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(10, 10, 10, 10)
        
        # Configurar PyQtGraph para fondo oscuro
        pg.setConfigOption('background', '#1A1A1A')
        pg.setConfigOption('foreground', '#FFFFFF')
        
        # Gráfica señal cruda (ahora en µV)
        self.plot_raw = pg.PlotWidget(title="Señal EOG Cruda")
        self.plot_raw.setFixedHeight(250)
        self.plot_raw.setLabel('left', 'Amplitud', units='µV', color='#FFFFFF')
        self.plot_raw.setLabel('bottom', 'Tiempo', units='s', color='#FFFFFF')
        self.plot_raw.getAxis('left').setTextPen('#FFFFFF')
        self.plot_raw.getAxis('bottom').setTextPen('#FFFFFF')
        self.plot_raw.setBackground('#1A1A1A')
        self.plot_raw.setYRange(-350, 250)
        
        # Gráfica señal filtrada (también en µV)
        self.plot_filtered = pg.PlotWidget(title="Señal EOG Filtrada (Offline)")
        self.plot_filtered.setFixedHeight(250)
        self.plot_filtered.setLabel('left', 'Amplitud', units='µV', color='#FFFFFF')
        self.plot_filtered.setLabel('bottom', 'Tiempo', units='s', color='#FFFFFF')
        self.plot_filtered.getAxis('left').setTextPen('#FFFFFF')
        self.plot_filtered.getAxis('bottom').setTextPen('#FFFFFF')
        self.plot_filtered.setBackground('#1A1A1A')
        self.plot_filtered.setYRange(-450, 650)
        
        # Sincronizar zoom entre gráficas
        self.plot_filtered.setXLink(self.plot_raw)
        
        plots_layout.addWidget(self.plot_raw)
        plots_layout.addWidget(self.plot_filtered)
        
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
        
    def create_info_panel(self, main_layout):
        """Crear panel de información"""
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        # Panel estadísticas
        stats_group = QGroupBox("Estadísticas de la Señal")
        stats_layout = QGridLayout(stats_group)
        
        self.stats_label = QTextEdit()
        self.stats_label.setMaximumHeight(80)
        self.stats_label.setReadOnly(True)
        self.stats_label.setStyleSheet("""
            QTextEdit {
                background-color: #2A2A2A;
                border: 1px solid #555555;
                color: #FFFFFF;
                font-family: 'Courier New';
                font-size: 10px;
            }
        """)
        
        stats_layout.addWidget(self.stats_label)
        
        # Panel calidad
        quality_group = QGroupBox("Calidad del Filtrado")
        quality_layout = QGridLayout(quality_group)
        
        self.quality_label = QTextEdit()
        self.quality_label.setMaximumHeight(80)
        self.quality_label.setReadOnly(True)
        self.quality_label.setStyleSheet(self.stats_label.styleSheet())
        
        quality_layout.addWidget(self.quality_label)
        
        info_layout.addWidget(stats_group)
        info_layout.addWidget(quality_group)
        
        main_layout.addWidget(info_frame)
        
    def setup_plots(self):
        """Configurar las curvas de las gráficas"""
        # Curva para señal cruda
        self.curve_raw = self.plot_raw.plot(
            pen=pg.mkPen(color='#FF6B6B', width=2),
            name='EOG Raw (µV)'
        )
        
        # Curva para señal filtrada
        self.curve_filtered = self.plot_filtered.plot(
            pen=pg.mkPen(color='#4ECDC4', width=2),
            name='EOG Filtered (µV)'
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
                # Cargar datos
                self.df = pd.read_csv(file_path)
                
                # Verificar columnas requeridas
                required_columns = ['timestamp', 'eog_raw']
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
                    f"✅ {filename} | {samples} muestras | {duration:.1f}s | {self.sample_rate:.1f} Hz | {uv_range}"
                )
                self.file_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                # Habilitar procesamiento
                self.process_btn.setEnabled(True)
                
                # Configurar slider de navegación
                max_time = max(0, duration - self.window_duration)
                self.time_slider.setMaximum(int(max_time))
                self.time_slider.setValue(0)
                
                # Mostrar datos crudos iniciales (en µV)
                self.update_raw_plot()
                self.update_statistics()
                
                print(f"Archivo cargado: {samples} muestras, {duration:.1f}s, {self.sample_rate:.1f} Hz")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al cargar archivo",
                    f"No se pudo cargar el archivo:\n{str(e)}"
                )
                
    def process_signal(self):
        """Procesar señal con filtro offline"""
        if self.eog_raw_uv is None:
            return
            
        try:
            # Mostrar barra de progreso
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.process_btn.setEnabled(False)
            
            # Crear y ejecutar hilo de filtrado (usando datos en µV)
            self.filtering_thread = FilteringThread(self.eog_raw_uv, self.sample_rate)
            self.filtering_thread.progress_updated.connect(self.progress_bar.setValue)
            self.filtering_thread.filtering_completed.connect(self.on_filtering_completed)
            self.filtering_thread.error_occurred.connect(self.on_filtering_error)  # ✅ Corregido
            self.filtering_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar señal:\n{str(e)}")
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            
    def on_filtering_completed(self, result):
        """Callback cuando el filtrado se completa"""
        try:
            self.eog_filtered_uv = result['filtered']  # Ya en µV
            self.filtering_metadata = result['metadata']
            self.blink_artifacts = result['blink_artifacts']
            
            # Ocultar barra de progreso
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            
            # Actualizar gráficas
            self.update_filtered_plot()
            self.update_quality_info()
            
            # Mostrar rango de señal filtrada
            filtered_range = f"{np.min(self.eog_filtered_uv):.1f} - {np.max(self.eog_filtered_uv):.1f} µV"
            
            QMessageBox.information(
                self,
                "Filtrado Completado",
                f"Señal procesada exitosamente!\n\n"
                f"Duración: {self.filtering_metadata['duration_sec']:.1f}s\n"
                f"Calidad: {self.filtering_metadata['signal_quality']}\n"
                f"Artefactos detectados: {self.filtering_metadata['blink_artifacts_detected']}\n"
                f"Rango filtrado: {filtered_range}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error procesando resultado:\n{str(e)}")
            
    def on_filtering_error(self, error_msg):
        """Callback cuando ocurre error en el filtrado"""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Error en Filtrado", error_msg)
        
    def update_window_duration(self, value):
        """Actualizar duración de ventana de visualización"""
        self.window_duration = value
        
        if self.time_seconds is not None:
            # Reconfigurar slider
            max_time = max(0, self.time_seconds[-1] - self.window_duration)
            self.time_slider.setMaximum(int(max_time))
            
            # Actualizar gráficas
            self.update_plots()
            
    def update_time_position(self, value):
        """Actualizar posición temporal"""
        self.current_position = value
        self.update_plots()
        
        if self.time_seconds is not None:
            total_time = self.time_seconds[-1]
            self.position_label.setText(f"Posición: {value:.1f} / {total_time:.1f} s")
            
    def update_raw_plot(self):
        """Actualizar gráfica de señal cruda (en µV)"""
        if self.eog_raw_uv is None or self.time_seconds is None:
            return
            
        # Obtener ventana de datos
        start_time = self.current_position
        end_time = start_time + self.window_duration
        
        mask = (self.time_seconds >= start_time) & (self.time_seconds <= end_time)
        time_window = self.time_seconds[mask]
        data_window = self.eog_raw_uv[mask]  # Usar datos en µV
        
        if len(time_window) > 0:
            self.curve_raw.setData(time_window, data_window)
            self.plot_raw.setXRange(start_time, end_time, padding=0)
            
    def update_filtered_plot(self):
        """Actualizar gráfica de señal filtrada (en µV)"""
        if self.eog_filtered_uv is None or self.time_seconds is None:
            return
            
        # Obtener ventana de datos
        start_time = self.current_position
        end_time = start_time + self.window_duration
        
        mask = (self.time_seconds >= start_time) & (self.time_seconds <= end_time)
        time_window = self.time_seconds[mask]
        data_window = self.eog_filtered_uv[mask]  # Usar datos filtrados en µV
        
        if len(time_window) > 0:
            self.curve_filtered.setData(time_window, data_window)
            self.plot_filtered.setXRange(start_time, end_time, padding=0)
            
            # Marcar artefactos de parpadeo si existen
            if hasattr(self, 'blink_artifacts') and self.blink_artifacts:
                for artifact_idx in self.blink_artifacts:
                    artifact_time = self.time_seconds[artifact_idx]
                    if start_time <= artifact_time <= end_time:
                        # Añadir línea vertical para marcar artefacto
                        line = pg.InfiniteLine(
                            artifact_time, 
                            angle=90, 
                            pen=pg.mkPen(color='#FF9800', width=2, style=Qt.DashLine)
                        )
                        self.plot_filtered.addItem(line)
            
    def update_plots(self):
        """Actualizar ambas gráficas"""
        self.update_raw_plot()
        if self.eog_filtered_uv is not None:
            self.update_filtered_plot()
            
    def update_statistics(self):
        """Actualizar estadísticas de la señal (en µV)"""
        if self.eog_raw_uv is None:
            return
            
        stats = f"""Estadísticas Señal Cruda:
• Muestras: {len(self.eog_raw_uv)}
• Duración: {self.time_seconds[-1]:.2f} segundos
• Freq. Muestreo: {self.sample_rate:.1f} Hz
• Media: {np.mean(self.eog_raw_uv):.2f} µV
• Std: {np.std(self.eog_raw_uv):.2f} µV
• Rango: {np.min(self.eog_raw_uv):.2f} - {np.max(self.eog_raw_uv):.2f} µV
• Factor conversión: {ADC_TO_MICROVOLTS:.6f}"""
        
        self.stats_label.setText(stats)
        
    def update_quality_info(self):
        """Actualizar información de calidad del filtrado"""
        if not hasattr(self, 'filtering_metadata'):
            return
            
        meta = self.filtering_metadata
        
        # Calcular estadísticas adicionales del filtrado
        if self.eog_filtered_uv is not None:
            filtered_std = np.std(self.eog_filtered_uv)
            noise_reduction = (np.std(self.eog_raw_uv) - filtered_std) / np.std(self.eog_raw_uv) * 100
        else:
            noise_reduction = 0
        
        quality_info = f"""Información del Filtrado:
• Calidad: {meta['signal_quality']}
• DC removido: {meta['dc_offset_removed']:.2f} µV
• Reducción 50Hz: {meta['powerline_reduction_db']:.1f} dB
• Reducción ruido: {noise_reduction:.1f}%
• Artefactos: {meta['blink_artifacts_detected']}
• Pasos: {', '.join(meta['processing_steps'])}"""
        
        self.quality_label.setText(quality_info)


# Para pruebas independientes
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = OfflineAnalysisWindow()
    window.show()
    sys.exit(app.exec())
