"""
Ventana para análisis offline de señales PPG guardadas en la base de datos.

Permite cargar sesiones PPG desde la base de datos, aplicar filtrado offline
de alta calidad y visualizar tanto la señal cruda como la filtrada de forma
interactiva con navegación temporal.
"""

import sys
import os
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QMessageBox, QSlider, QSpinBox, QComboBox,
    QFrame, QGroupBox, QGridLayout, QProgressBar, QTextEdit,
    QApplication, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import pyqtgraph as pg

# Añadir el directorio src al path para las importaciones
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Importar clases necesarias
from utils.signal_processing import OfflinePPGFilter
from database.database_manager import DatabaseManager


class PPGFilteringThread(QThread):
    """Hilo para procesar filtrado PPG offline sin bloquear la UI"""
    
    progress_updated = Signal(int)
    filtering_completed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, ppg_data, fs=125):
        super().__init__()
        self.ppg_data = ppg_data
        self.fs = fs
        
    def run(self):
        """Ejecutar filtrado en hilo separado"""
        try:
            # Emitir progreso inicial
            self.progress_updated.emit(10)
            
            # Crear filtro PPG con configuración optimizada
            ppg_filter = OfflinePPGFilter(
                fs=self.fs,
                hp_cutoff=0.5,      # Eliminar deriva DC
                lp_cutoff=5.0,      # Rango cardíaco óptimo
                notch_freq=50,      # Eliminar ruido de red
                notch_q=30,         # Factor de calidad
                smoothing=True      # Suavizado adicional
            )
            
            self.progress_updated.emit(30)
            
            # Aplicar filtrado
            filter_result = ppg_filter.filter_signal(self.ppg_data)
            
            self.progress_updated.emit(80)
            
            # Verificar resultado
            if filter_result is None:
                self.error_occurred.emit("Error en el filtrado: resultado nulo")
                return
                
            self.progress_updated.emit(100)
            
            # Emitir resultado
            self.filtering_completed.emit(filter_result)
            
        except Exception as e:
            self.error_occurred.emit(f"Error durante el filtrado: {str(e)}")


class OfflinePPGAnalysisWindow(QMainWindow):
    """
    Ventana principal para análisis offline de señales PPG desde base de datos.
    
    Características:
    - Carga sesiones desde base de datos
    - Visualización dual: señal cruda y filtrada
    - Navegación temporal con slider
    - Controles de zoom y ventana
    - Panel para métricas futuras
    - Exportación de datos
    """
    
    def __init__(self):
        super().__init__()
        
        # Variables de estado
        self.current_session_id = None
        self.ppg_data_raw = None
        self.ppg_data_filtered = None
        self.ms_data = None
        self.filter_result = None
        self.sessions_list = []
        
        # Variables de navegación
        self.window_size_seconds = 10.0  # Ventana de visualización
        self.current_position = 0.0      # Posición actual en segundos
        self.zoom_factor = 1.0           # Factor de zoom
        
        # Variables de filtrado
        self.filtering_thread = None
        
        # Configurar ventana
        self.setWindowTitle("EMDR Project - Análisis Offline de Señales PPG")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Configurar PyQtGraph
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#323232')
        pg.setConfigOption('foreground', 'w')
        
        # Configurar UI
        self.setup_ui()
        self.apply_styles()
        
        # Cargar sesiones disponibles
        self.load_available_sessions()
        
        print("✅ Ventana de análisis PPG offline inicializada")
    
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # === PANEL DE CONTROL SUPERIOR ===
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # === ÁREA PRINCIPAL CON SPLITTER ===
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: Gráficas
        charts_widget = self.create_charts_panel()
        splitter.addWidget(charts_widget)
        
        # Panel derecho: Métricas y controles
        metrics_widget = self.create_metrics_panel()
        splitter.addWidget(metrics_widget)
        
        # Configurar proporciones del splitter (70% gráficas, 30% métricas)
        splitter.setSizes([1000, 400])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        
        main_layout.addWidget(splitter, 1)
        
        # === PANEL DE NAVEGACIÓN INFERIOR ===
        navigation_panel = self.create_navigation_panel()
        main_layout.addWidget(navigation_panel)
        
        # === BARRA DE ESTADO ===
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
    
    def create_control_panel(self):
        """Crear panel de control superior"""
        control_frame = QFrame()
        control_frame.setObjectName("controlPanel")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title_label = QLabel("Análisis Offline de Señales PPG")
        title_label.setObjectName("titleLabel")
        
        # Selector de sesión
        session_label = QLabel("Sesión:")
        session_label.setObjectName("controlLabel")
        
        self.session_combo = QComboBox()
        self.session_combo.setObjectName("sessionCombo")
        self.session_combo.setMinimumWidth(300)
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        
        # Botón de carga
        self.load_button = QPushButton("Cargar Sesión")
        self.load_button.setObjectName("loadButton")
        self.load_button.clicked.connect(self.load_selected_session)
        self.load_button.setEnabled(False)
        
        # Botón de exportar
        self.export_button = QPushButton("Exportar Datos")
        self.export_button.setObjectName("exportButton")
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setEnabled(False)
        
        # Layout
        control_layout.addWidget(title_label)
        control_layout.addStretch()
        control_layout.addWidget(session_label)
        control_layout.addWidget(self.session_combo)
        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.export_button)
        
        return control_frame
    
    def create_charts_panel(self):
        """Crear panel de gráficas"""
        charts_frame = QFrame()
        charts_frame.setObjectName("chartsPanel")
        charts_layout = QVBoxLayout(charts_frame)
        charts_layout.setContentsMargins(5, 5, 5, 5)
        
        # === GRÁFICA SEÑAL CRUDA ===
        raw_group = QGroupBox("Señal PPG Cruda")
        raw_group.setObjectName("chartGroup")
        raw_layout = QVBoxLayout(raw_group)
        
        self.raw_plot = pg.PlotWidget()
        self.raw_plot.setObjectName("rawPlot")
        self.raw_plot.setMinimumHeight(250)
        self.raw_plot.setLabel('left', 'Amplitud', color='white', size='11pt')
        self.raw_plot.setLabel('bottom', 'Tiempo (ms)', color='white', size='11pt')
        self.raw_plot.setTitle('Señal PPG Sin Filtrar', color='#FFFFFF', size='12pt')
        self.raw_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Configurar ejes
        self.raw_plot.getAxis('left').setPen(color='white', width=1)
        self.raw_plot.getAxis('bottom').setPen(color='white', width=1)
        self.raw_plot.getAxis('left').setTextPen(color='white')
        self.raw_plot.getAxis('bottom').setTextPen(color='white')
        
        raw_layout.addWidget(self.raw_plot)
        charts_layout.addWidget(raw_group)
        
        # === GRÁFICA SEÑAL FILTRADA ===
        filtered_group = QGroupBox("Señal PPG Filtrada")
        filtered_group.setObjectName("chartGroup")
        filtered_layout = QVBoxLayout(filtered_group)
        
        self.filtered_plot = pg.PlotWidget()
        self.filtered_plot.setObjectName("filteredPlot")
        self.filtered_plot.setMinimumHeight(250)
        self.filtered_plot.setLabel('left', 'Amplitud', color='white', size='11pt')
        self.filtered_plot.setLabel('bottom', 'Tiempo (ms)', color='white', size='11pt')
        self.filtered_plot.setTitle('Señal PPG Filtrada', color='#00A99D', size='12pt')
        self.filtered_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Configurar ejes
        self.filtered_plot.getAxis('left').setPen(color='white', width=1)
        self.filtered_plot.getAxis('bottom').setPen(color='white', width=1)
        self.filtered_plot.getAxis('left').setTextPen(color='white')
        self.filtered_plot.getAxis('bottom').setTextPen(color='white')
        
        filtered_layout.addWidget(self.filtered_plot)
        charts_layout.addWidget(filtered_group)
        
        return charts_frame
    
    def create_metrics_panel(self):
        """Crear panel de métricas (vacío para futuras implementaciones)"""
        metrics_frame = QFrame()
        metrics_frame.setObjectName("metricsPanel")
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(10, 10, 10, 10)
        
        # === INFORMACIÓN DE SESIÓN ===
        session_group = QGroupBox("Información de Sesión")
        session_group.setObjectName("metricsGroup")
        session_layout = QVBoxLayout(session_group)
        
        self.session_info_label = QLabel("Ninguna sesión seleccionada")
        self.session_info_label.setObjectName("infoLabel")
        self.session_info_label.setWordWrap(True)
        session_layout.addWidget(self.session_info_label)
        
        metrics_layout.addWidget(session_group)
        
        # === ESTADO DEL FILTRADO ===
        filter_group = QGroupBox("Estado del Filtrado")
        filter_group.setObjectName("metricsGroup")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_status_label = QLabel("Sin filtrar")
        self.filter_status_label.setObjectName("infoLabel")
        self.filter_status_label.setWordWrap(True)
        filter_layout.addWidget(self.filter_status_label)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        filter_layout.addWidget(self.progress_bar)
        
        metrics_layout.addWidget(filter_group)
        
        # === MÉTRICAS FUTURAS ===
        future_group = QGroupBox("Métricas de Análisis")
        future_group.setObjectName("metricsGroup")
        future_layout = QVBoxLayout(future_group)
        
        placeholder_label = QLabel("Panel reservado para métricas futuras:\n\n• Análisis de frecuencia cardíaca\n• Detección de artefactos\n• Métricas de calidad de señal\n• Estadísticas temporales")
        placeholder_label.setObjectName("placeholderLabel")
        placeholder_label.setWordWrap(True)
        future_layout.addWidget(placeholder_label)
        
        metrics_layout.addWidget(future_group)
        
        metrics_layout.addStretch()
        
        return metrics_frame
    
    def create_navigation_panel(self):
        """Crear panel de navegación temporal"""
        nav_frame = QFrame()
        nav_frame.setObjectName("navigationPanel")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 10, 15, 10)
        
        # === CONTROLES DE VENTANA ===
        window_layout = QHBoxLayout()
        
        # Control de duración de ventana
        window_label = QLabel("Ventana de visualización:")
        window_label.setObjectName("navLabel")
        
        self.window_spinbox = QSpinBox()
        self.window_spinbox.setObjectName("navSpinBox")
        self.window_spinbox.setRange(2, 60)
        self.window_spinbox.setValue(int(self.window_size_seconds))
        self.window_spinbox.setSuffix(" segundos")
        self.window_spinbox.valueChanged.connect(self.update_window_duration)
        
        # Control de zoom
        zoom_label = QLabel("Zoom:")
        zoom_label.setObjectName("navLabel")
        
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setObjectName("navSpinBox")
        self.zoom_spinbox.setRange(25, 400)
        self.zoom_spinbox.setValue(int(self.zoom_factor * 100))
        self.zoom_spinbox.setSuffix(" %")
        self.zoom_spinbox.valueChanged.connect(self.update_zoom_factor)
        
        window_layout.addWidget(window_label)
        window_layout.addWidget(self.window_spinbox)
        window_layout.addStretch()
        window_layout.addWidget(zoom_label)
        window_layout.addWidget(self.zoom_spinbox)
        
        nav_layout.addLayout(window_layout)
        
        # === SLIDER DE NAVEGACIÓN TEMPORAL ===
        slider_layout = QHBoxLayout()
        
        # Etiqueta de inicio
        self.start_label = QLabel("0.0s")
        self.start_label.setObjectName("navLabel")
        
        # Slider principal
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setObjectName("timeSlider")
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self.update_time_position)
        self.time_slider.setEnabled(False)
        
        # Etiqueta de fin
        self.end_label = QLabel("0.0s")
        self.end_label.setObjectName("navLabel")
        
        # Etiqueta de posición actual
        self.position_label = QLabel("Posición: 0.0s")
        self.position_label.setObjectName("positionLabel")
        
        slider_layout.addWidget(self.start_label)
        slider_layout.addWidget(self.time_slider, 1)
        slider_layout.addWidget(self.end_label)
        slider_layout.addWidget(self.position_label)
        
        nav_layout.addLayout(slider_layout)
        
        return nav_frame
    
    def create_status_panel(self):
        """Crear panel de estado inferior"""
        status_frame = QFrame()
        status_frame.setObjectName("statusPanel")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("Listo - Seleccione una sesión para comenzar")
        self.status_label.setObjectName("statusLabel")
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        return status_frame
    
    def load_available_sessions(self):
        """Cargar sesiones disponibles desde la base de datos"""
        try:
            # Obtener todas las sesiones que tengan datos PPG
            all_sessions = [DatabaseManager.get_session(session_id=14, signal_data=False)]
            
            if not all_sessions:
                self.session_combo.addItem("No hay sesiones con datos PPG disponibles")
                self.update_status("No se encontraron sesiones con datos PPG")
                return
            
            self.sessions_list = all_sessions
            
            # Llenar el combo box
            self.session_combo.clear()
            self.session_combo.addItem("Seleccione una sesión...")
            
            for session in all_sessions:
                # Obtener información del paciente
                patient_data = DatabaseManager.get_patient(session['id_paciente'])
                patient_name = "Paciente desconocido"
                if patient_data:
                    patient_name = f"{patient_data['nombre']} {patient_data['apellido_paterno']}"
                
                # Formatear fecha
                fecha = session.get('fecha', 'Sin fecha')
                if fecha != 'Sin fecha':
                    try:
                        fecha_parte, hora_parte = fecha.split(' ')
                        year, month, day = fecha_parte.split('-')
                        fecha_formateada = f"{day}/{month}/{year}"
                        hora = hora_parte.split(':')[0] + ':' + hora_parte.split(':')[1]
                        fecha_display = f"{fecha_formateada} {hora}"
                    except:
                        fecha_display = fecha
                else:
                    fecha_display = "Sin fecha"
                
                display_text = f"Sesión {session['id']} - {patient_name} ({fecha_display})"
                self.session_combo.addItem(display_text)
            
            self.update_status(f"Cargadas {len(all_sessions)} sesiones con datos PPG")
            
        except Exception as e:
            error_msg = f"Error cargando sesiones: {str(e)}"
            self.update_status(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def on_session_changed(self):
        """Manejar cambio de sesión seleccionada"""
        current_index = self.session_combo.currentIndex()
        if current_index > 0 and current_index <= len(self.sessions_list):
            self.load_button.setEnabled(True)
            selected_session = self.sessions_list[current_index - 1]
            self.current_session_id = selected_session['id']
            
            # Actualizar información de sesión
            self.update_session_info(selected_session)
        else:
            self.load_button.setEnabled(False)
            self.current_session_id = None
            self.session_info_label.setText("Ninguna sesión seleccionada")
    
    def update_session_info(self, session):
        """Actualizar información de la sesión seleccionada"""
        try:
            patient_data = DatabaseManager.get_patient(session['id_paciente'])
            patient_name = "Paciente desconocido"
            if patient_data:
                patient_name = f"{patient_data['nombre']} {patient_data['apellido_paterno']} {patient_data['apellido_materno']}"
            
            fecha = session.get('fecha', 'Sin fecha')
            objetivo = session.get('objetivo', 'Sin objetivo definido')
            comentarios = session.get('comentarios', 'Sin comentarios')
            
            info_text = f"<b>Paciente:</b> {patient_name}<br>"
            info_text += f"<b>Fecha:</b> {fecha}<br>"
            info_text += f"<b>Objetivo:</b> {objetivo}<br>"
            info_text += f"<b>Comentarios:</b> {comentarios}"
            
            self.session_info_label.setText(info_text)
            
        except Exception as e:
            self.session_info_label.setText(f"Error cargando información: {str(e)}")
    
    def load_selected_session(self):
        """Cargar y procesar la sesión seleccionada"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Advertencia", "No hay sesión seleccionada")
            return
        
        try:
            # Cargar datos de la sesión
            self.update_status("Cargando datos de la sesión...")
            
            session_data = DatabaseManager.get_session(self.current_session_id, signal_data=True)
            
            if not session_data:
                QMessageBox.critical(self, "Error", "No se pudieron cargar los datos de la sesión")
                return
            
            # Extraer datos PPG y tiempo
            self.ppg_data_raw = session_data.get('datos_ppg')
            self.ms_data = session_data.get('datos_ms')
            
            if self.ppg_data_raw is None or self.ms_data is None:
                QMessageBox.warning(
                    self, 
                    "Sin datos PPG", 
                    "La sesión seleccionada no contiene datos de señal PPG.\n\nLas gráficas permanecerán vacías."
                )
                self.clear_plots()
                self.update_status("Sesión cargada - Sin datos PPG")
                return
            
            # Convertir a arrays numpy
            if not isinstance(self.ppg_data_raw, np.ndarray):
                self.ppg_data_raw = np.array(self.ppg_data_raw)
            
            if not isinstance(self.ms_data, np.ndarray):
                self.ms_data = np.array(self.ms_data)
            
            # Validar datos
            if len(self.ppg_data_raw) != len(self.ms_data):
                QMessageBox.critical(
                    self, 
                    "Error de datos", 
                    f"Inconsistencia en los datos:\nPPG: {len(self.ppg_data_raw)} muestras\nTiempo: {len(self.ms_data)} muestras"
                )
                return
            
            if len(self.ppg_data_raw) < 500:  # Mínimo ~4 segundos a 125 Hz
                QMessageBox.warning(
                    self, 
                    "Datos insuficientes", 
                    f"La sesión contiene solo {len(self.ppg_data_raw)} muestras.\nSe requieren al menos 500 muestras para un filtrado efectivo."
                )
            
            # Mostrar señal cruda inmediatamente
            self.plot_raw_signal()
            
            # Configurar navegación
            self.setup_navigation()
            
            # Iniciar filtrado en hilo separado
            self.start_filtering()
            
            self.update_status(f"Datos cargados: {len(self.ppg_data_raw)} muestras - Iniciando filtrado...")
            
        except Exception as e:
            error_msg = f"Error cargando sesión: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self.update_status(error_msg)
    
    def start_filtering(self):
        """Iniciar proceso de filtrado en hilo separado"""
        if self.ppg_data_raw is None:
            return
        
        # Estimar frecuencia de muestreo
        if len(self.ms_data) > 1:
            time_span_sec = (max(self.ms_data) - min(self.ms_data)) / 1000.0
            estimated_fs = len(self.ms_data) / time_span_sec
        else:
            estimated_fs = 125  # Valor por defecto
        
        # Mostrar barra de progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.filter_status_label.setText("Filtrando señal PPG...")
        
        # Crear y configurar hilo de filtrado
        self.filtering_thread = PPGFilteringThread(self.ppg_data_raw, estimated_fs)
        self.filtering_thread.progress_updated.connect(self.update_filter_progress)
        self.filtering_thread.filtering_completed.connect(self.on_filtering_completed)
        self.filtering_thread.error_occurred.connect(self.on_filtering_error)
        
        # Iniciar filtrado
        self.filtering_thread.start()
    
    def update_filter_progress(self, progress):
        """Actualizar progreso del filtrado"""
        self.progress_bar.setValue(progress)
    
    def on_filtering_completed(self, filter_result):
        """Manejar finalización del filtrado"""
        self.filter_result = filter_result
        self.ppg_data_filtered = filter_result['filtered']
        
        # Ocultar barra de progreso
        self.progress_bar.setVisible(False)
        
        # Actualizar estado
        quality = filter_result['quality']['overall']
        self.filter_status_label.setText(f"Filtrado completado\nCalidad: {quality}")
        
        # Mostrar señal filtrada
        self.plot_filtered_signal()
        
        # Habilitar exportación
        self.export_button.setEnabled(True)
        
        self.update_status(f"Filtrado completado - Calidad: {quality}")
        
        print(f"✅ Filtrado PPG completado - Calidad: {quality}")
    
    def on_filtering_error(self, error_message):
        """Manejar error en el filtrado"""
        self.progress_bar.setVisible(False)
        self.filter_status_label.setText(f"Error en filtrado:\n{error_message}")
        
        QMessageBox.critical(self, "Error de Filtrado", f"Error durante el filtrado:\n\n{error_message}")
        self.update_status(f"Error de filtrado: {error_message}")
    
    def plot_raw_signal(self):
        """Graficar señal PPG cruda"""
        if self.ppg_data_raw is None or self.ms_data is None:
            return
        
        try:
            self.raw_plot.clear()
            
            # Calcular ventana de visualización
            start_time_ms, end_time_ms = self.get_current_time_window()
            
            # Filtrar datos en la ventana
            mask = (self.ms_data >= start_time_ms) & (self.ms_data <= end_time_ms)
            windowed_ms = self.ms_data[mask]
            windowed_ppg = self.ppg_data_raw[mask]
            
            if len(windowed_ms) > 0:
                # Aplicar zoom vertical
                if self.zoom_factor != 1.0:
                    mean_val = np.mean(windowed_ppg)
                    windowed_ppg = mean_val + (windowed_ppg - mean_val) * self.zoom_factor
                
                # Graficar con color azul
                pen = pg.mkPen(color='#4A90E2', width=1.5)
                self.raw_plot.plot(windowed_ms, windowed_ppg, pen=pen)
                
                # Configurar límites
                self.raw_plot.setXRange(start_time_ms, end_time_ms, padding=0)
                
                # Actualizar título
                duration_s = (end_time_ms - start_time_ms) / 1000.0
                title = f'Señal PPG Cruda - Ventana: {self.current_position:.1f}s a {self.current_position + duration_s:.1f}s'
                self.raw_plot.setTitle(title, color='#FFFFFF', size='12pt')
            
        except Exception as e:
            print(f"Error graficando señal cruda: {e}")
    
    def plot_filtered_signal(self):
        """Graficar señal PPG filtrada"""
        if self.ppg_data_filtered is None or self.ms_data is None:
            return
        
        try:
            self.filtered_plot.clear()
            
            # Calcular ventana de visualización
            start_time_ms, end_time_ms = self.get_current_time_window()
            
            # Filtrar datos en la ventana
            mask = (self.ms_data >= start_time_ms) & (self.ms_data <= end_time_ms)
            windowed_ms = self.ms_data[mask]
            windowed_ppg = self.ppg_data_filtered[mask]
            
            if len(windowed_ms) > 0:
                # Aplicar zoom vertical
                if self.zoom_factor != 1.0:
                    mean_val = np.mean(windowed_ppg)
                    windowed_ppg = mean_val + (windowed_ppg - mean_val) * self.zoom_factor
                
                # Graficar con color verde esmeralda
                pen = pg.mkPen(color='#00A99D', width=2)
                self.filtered_plot.plot(windowed_ms, windowed_ppg, pen=pen)
                
                # Configurar límites
                self.filtered_plot.setXRange(start_time_ms, end_time_ms, padding=0)
                
                # Actualizar título con información de calidad
                duration_s = (end_time_ms - start_time_ms) / 1000.0
                quality = self.filter_result['quality']['overall'] if self.filter_result else "unknown"
                title = f'Señal PPG Filtrada (Calidad: {quality}) - Ventana: {self.current_position:.1f}s a {self.current_position + duration_s:.1f}s'
                self.filtered_plot.setTitle(title, color='#00A99D', size='12pt')
            
        except Exception as e:
            print(f"Error graficando señal filtrada: {e}")
    
    def get_current_time_window(self):
        """Calcular ventana de tiempo actual"""
        if self.ms_data is None or len(self.ms_data) == 0:
            return 0, 1000
        
        total_time_ms = max(self.ms_data) - min(self.ms_data)
        start_time_ms = min(self.ms_data) + (self.current_position * 1000)
        end_time_ms = start_time_ms + (self.window_size_seconds * 1000)
        
        # Asegurar que no exceda los límites
        end_time_ms = min(end_time_ms, max(self.ms_data))
        
        return start_time_ms, end_time_ms
    
    def setup_navigation(self):
        """Configurar controles de navegación"""
        if self.ms_data is None or len(self.ms_data) == 0:
            return
        
        # Calcular duración total
        total_time_ms = max(self.ms_data) - min(self.ms_data)
        total_time_seconds = total_time_ms / 1000.0
        
        # Configurar slider
        if total_time_seconds > self.window_size_seconds:
            max_position = total_time_seconds - self.window_size_seconds
            self.time_slider.setMaximum(int(max_position * 10))  # Resolución de 0.1s
            self.time_slider.setEnabled(True)
        else:
            self.time_slider.setMaximum(0)
            self.time_slider.setEnabled(False)
        
        # Actualizar etiquetas
        self.start_label.setText("0.0s")
        self.end_label.setText(f"{total_time_seconds:.1f}s")
        
        # Resetear posición
        self.current_position = 0.0
        self.time_slider.setValue(0)
        self.update_position_label()
    
    def update_window_duration(self, value):
        """Actualizar duración de ventana de visualización"""
        self.window_size_seconds = float(value)
        self.setup_navigation()
        self.update_plots()
    
    def update_zoom_factor(self, value):
        """Actualizar factor de zoom"""
        self.zoom_factor = value / 100.0
        self.update_plots()
    
    def update_time_position(self, value):
        """Actualizar posición temporal desde el slider"""
        if self.ms_data is None or len(self.ms_data) == 0:
            return
        
        self.current_position = value / 10.0  # Convertir de resolución alta
        self.update_position_label()
        self.update_plots()
    
    def update_position_label(self):
        """Actualizar etiqueta de posición"""
        if self.ms_data is not None and len(self.ms_data) > 0:
            total_time_ms = max(self.ms_data) - min(self.ms_data)
            total_time_seconds = total_time_ms / 1000.0
            self.position_label.setText(f"Posición: {self.current_position:.1f}s / {total_time_seconds:.1f}s")
        else:
            self.position_label.setText("Posición: 0.0s / 0.0s")
    
    def update_plots(self):
        """Actualizar ambas gráficas"""
        self.plot_raw_signal()
        if self.ppg_data_filtered is not None:
            self.plot_filtered_signal()
    
    def clear_plots(self):
        """Limpiar ambas gráficas"""
        self.raw_plot.clear()
        self.filtered_plot.clear()
        
        self.raw_plot.setTitle('Señal PPG Sin Filtrar - Sin datos', color='#AAAAAA', size='12pt')
        self.filtered_plot.setTitle('Señal PPG Filtrada - Sin datos', color='#AAAAAA', size='12pt')
    
    def export_data(self):
        """Exportar datos procesados"""
        if self.ppg_data_raw is None:
            QMessageBox.warning(self, "Advertencia", "No hay datos para exportar")
            return
        
        try:
            from PySide6.QtWidgets import QFileDialog
            
            # Seleccionar archivo de destino
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar Datos PPG",
                f"sesion_{self.current_session_id}_ppg_analysis.csv",
                "Archivos CSV (*.csv);;Todos los archivos (*)"
            )
            
            if not file_path:
                return
            
            # Preparar datos para exportación
            export_data = {
                'tiempo_ms': self.ms_data,
                'ppg_cruda': self.ppg_data_raw
            }
            
            if self.ppg_data_filtered is not None:
                export_data['ppg_filtrada'] = self.ppg_data_filtered
            
            # Exportar a CSV
            import pandas as pd
            df = pd.DataFrame(export_data)
            df.to_csv(file_path, index=False)
            
            QMessageBox.information(
                self, 
                "Exportación exitosa", 
                f"Datos exportados exitosamente a:\n{file_path}\n\nColumnas exportadas: {list(export_data.keys())}"
            )
            
            self.update_status(f"Datos exportados a: {file_path}")
            
        except Exception as e:
            error_msg = f"Error durante la exportación: {str(e)}"
            QMessageBox.critical(self, "Error de Exportación", error_msg)
            self.update_status(error_msg)
    
    def update_status(self, message):
        """Actualizar mensaje de estado"""
        self.status_label.setText(message)
        print(f"Estado: {message}")
    
    def apply_styles(self):
        """Aplicar estilos CSS a la ventana"""
        self.setStyleSheet("""
            /* Ventana principal */
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Panel de control */
            QFrame#controlPanel {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 8px;
                margin: 2px;
            }
            
            /* Título */
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #00A99D;
                padding: 5px;
            }
            
            /* Etiquetas de control */
            QLabel#controlLabel {
                font-size: 13px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 5px;
            }
            
            /* ComboBox */
            QComboBox#sessionCombo {
                background-color: #3A3A3A;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: #FFFFFF;
                min-height: 20px;
            }
            
            QComboBox#sessionCombo:focus {
                border: 2px solid #00A99D;
            }
            
            QComboBox#sessionCombo::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox#sessionCombo::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #FFFFFF;
                margin-right: 5px;
            }
            
            QComboBox#sessionCombo QAbstractItemView {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                selection-background-color: #00A99D;
                color: #FFFFFF;
            }
            
            /* Botones */
            QPushButton#loadButton, QPushButton#exportButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #00A99D;
                min-width: 100px;
            }
            
            QPushButton#loadButton:hover, QPushButton#exportButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            
            QPushButton#loadButton:pressed, QPushButton#exportButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
            
            QPushButton#loadButton:disabled, QPushButton#exportButton:disabled {
                background-color: #555555;
                border: 2px solid #555555;
                color: #AAAAAA;
            }
            
            /* Panel de gráficas */
            QFrame#chartsPanel {
                background-color: transparent;
                border: none;
            }
            
            /* Grupos de gráficas */
            QGroupBox#chartGroup {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: transparent;
                color: white;
            }
            
            QGroupBox#chartGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
            
            /* Plots */
            PlotWidget#rawPlot, PlotWidget#filteredPlot {
                background-color: #2A2A2A;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            
            /* Panel de métricas */
            QFrame#metricsPanel {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 8px;
                margin: 2px;
            }
            
            /* Grupos de métricas */
            QGroupBox#metricsGroup {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #666666;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: transparent;
                color: white;
            }
            
            QGroupBox#metricsGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #CCCCCC;
            }
            
            /* Etiquetas de información */
            QLabel#infoLabel {
                font-size: 12px;
                color: #FFFFFF;
                padding: 5px;
                background-color: transparent;
            }
            
            /* Etiqueta placeholder */
            QLabel#placeholderLabel {
                font-size: 11px;
                color: #AAAAAA;
                font-style: italic;
                padding: 10px;
                background-color: transparent;
            }
            
            /* Barra de progreso */
            QProgressBar#progressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                background-color: #3A3A3A;
                text-align: center;
                font-weight: bold;
                color: #FFFFFF;
            }
            
            QProgressBar#progressBar::chunk {
                background-color: #00A99D;
                border-radius: 3px;
            }
            
            /* Panel de navegación */
            QFrame#navigationPanel {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 8px;
                margin: 2px;
            }
            
            /* Etiquetas de navegación */
            QLabel#navLabel {
                font-size: 12px;
                color: #FFFFFF;
                font-weight: bold;
                padding: 2px;
            }
            
            /* SpinBoxes de navegación */
            QSpinBox#navSpinBox {
                background-color: #3A3A3A;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
                color: #FFFFFF;
                font-size: 12px;
                min-width: 80px;
            }
            
            QSpinBox#navSpinBox:focus {
                border: 2px solid #00A99D;
            }
            
            /* Slider temporal */
            QSlider#timeSlider::groove:horizontal {
                background: #3A3A3A;
                height: 10px;
                border-radius: 5px;
                border: 1px solid #555555;
            }
            
            QSlider#timeSlider::handle:horizontal {
                background: #00A99D;
                border: 2px solid #00A99D;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            
            QSlider#timeSlider::handle:horizontal:hover {
                background: #00C2B3;
                border: 2px solid #00C2B3;
            }
            
            QSlider#timeSlider::handle:horizontal:pressed {
                background: #008C82;
                border: 2px solid #008C82;
            }
            
            QSlider#timeSlider::handle:horizontal:disabled {
                background: #555555;
                border: 2px solid #555555;
            }
            
            /* Etiqueta de posición */
            QLabel#positionLabel {
                font-size: 12px;
                color: #00A99D;
                font-weight: bold;
                padding: 5px;
                min-width: 120px;
            }
            
            /* Panel de estado */
            QFrame#statusPanel {
                background-color: #2A2A2A;
                border-top: 1px solid #555555;
            }
            
            /* Etiqueta de estado */
            QLabel#statusLabel {
                font-size: 12px;
                color: #CCCCCC;
                padding: 5px;
            }
        """)
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        # Detener hilo de filtrado si está ejecutándose
        if self.filtering_thread and self.filtering_thread.isRunning():
            self.filtering_thread.terminate()
            self.filtering_thread.wait()
        
        event.accept()
        print("🔴 Ventana de análisis PPG cerrada")


# Agregar método a DatabaseManager para obtener sesiones con PPG
def get_all_sessions_with_ppg():
    """Obtener todas las sesiones que tengan datos PPG no nulos"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, id_paciente, fecha, objetivo, comentarios
            FROM sesiones 
            WHERE datos_ppg IS NOT NULL
            ORDER BY fecha DESC
        """)
        
        sessions = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": s[0],
                "id_paciente": s[1],
                "fecha": s[2],
                "objetivo": s[3],
                "comentarios": s[4]
            }
            for s in sessions
        ]
        
    except Exception as e:
        print(f"Error obteniendo sesiones con PPG: {e}")
        return []

# Agregar método al DatabaseManager
# DatabaseManager.get_all_sessions_with_ppg = staticmethod(get_all_sessions_with_ppg)


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Configurar aplicación
    app.setApplicationName("EMDR PPG Analysis")
    app.setApplicationVersion("1.0")
    
    # Crear y mostrar ventana
    window = OfflinePPGAnalysisWindow()
    window.show()
    
    print("🚀 Aplicación de análisis PPG offline iniciada")
    
    # Ejecutar aplicación
    sys.exit(app.exec())
