import sys
import os
import winsound
import numpy as np
import struct
import threading
import time
import pandas as pd
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QSizePolicy, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

import pyqtgraph as pg
import qtawesome as qta

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones del proyecto
from src.models.devices import Devices
from src.utils.signal_processing import OnlineEOGFilter
from src.views.step_fixation import StepFixationThread
from src.views.linear_smooth_pursuit import LinealSmoothPursuitThread

# Configuración de constantes
SAMPLE_RATE = 125  # Hz para EOG (mayor frecuencia que para pulso)
DISPLAY_TIME = 5   # Segundos de datos a mostrar
GRAPH_PADDING = 0.01
BUFFER_SIZE = 512

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55
PACKET_SIZE = 15


class EOGTestWindow(QMainWindow):
    """Ventana especializada para pruebas de señales EOG (ElectroOculoGrafía)"""
    
    # Señal para regresar al dashboard
    return_to_dashboard = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Variables de estado
        self.connected = False # Estado de conexión del dispositivo
        self.acquiring = False # Estado de adquisición de datos
        self.reading_thread = None # Hilo de lectura de datos
        self.is_closing = False
        
        # Variables específicas de EOG
        self.calibration_active = False
        
        # Variables para protocolo Step-Fixation
        self.step_fixation_thread = None
        self.protocol_running = False
        
        # Variables para protocolo Smooth-Pursuit
        self.smooth_pursuit_thread = None
        
        # Datos para visualización
        self.display_size = DISPLAY_TIME * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Inicializar buffers
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        # Buffers para tiempo y EOG (crudo y filtrado)
        self.times = deque(initial_times, maxlen=self.display_size)
        self.eog_raw_values = deque(initial_values, maxlen=self.display_size)
        self.eog_filtered_values = deque(initial_values, maxlen=self.display_size)
        
        # Datos para CSV
        self.csv_data = {
            'index': [],
            'timestamp': [],
            'eog_raw': [],
            'eog_filtered': [],
            'signal_quality': [],
            'event': []
        }
        
        # Procesamiento de señales EOG con filtro especializado
        # OnlineEOGFilter proporciona:
        # - High-pass 0.05 Hz: conserva movimientos oculares lentos
        # - Notch 50 Hz: elimina interferencia eléctrica
        # - Low-pass FIR 30 Hz: banda útil con fase lineal
        # - Retardo total: ~400ms (aceptable para monitoreo clínico)
        self.eog_filter = OnlineEOGFilter(
            fs=SAMPLE_RATE,
            hp_cutoff=0.05,     # Conserva movimientos oculares lentos
            lp_cutoff=30.0,     # Banda útil para EOG
            notch_freq=50,      # Elimina interferencia de 50Hz
            notch_q=30,         # Factor de calidad del notch
            fir_taps=101        # Filtro FIR con fase lineal
        )

        # Variables para el sistema
        self.last_packet_id = -1
        
        # Contador de muestras para tasa
        self.sample_count = 0
        self.last_sample_time = time.time()
        self.current_sample_rate = 0
        
        # Configurar ventana
        self.setup_window()
        
        # Configurar interfaz
        self.setup_ui()
        
        # Timer para actualización de gráficas
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(40)  # 25 FPS (mayor que para pulso)
        
        # Timer para actualización de tasa de muestras
        self.rate_timer = QTimer()
        self.rate_timer.timeout.connect(self.update_sample_rate)
        self.rate_timer.start(1000)  # Cada segundo
    
    def setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle("EMDR Project - Prueba de EOG (ElectroOculoGrafía)")
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'emdr_icon.png')))
        
        # Centrar ventana
        self.center_on_screen()
    
    def center_on_screen(self):
        """Centra la ventana en la pantalla"""
        desktop_rect = QApplication.primaryScreen().availableGeometry()
        center = desktop_rect.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center)
        self.move(frame_geometry.topLeft())
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        
        # === HEADER ===
        self.create_header(main_layout)
        
        # === BARRA DE ESTADO ===
        self.create_status_bar(main_layout)
        
        # === ÁREA DE GRÁFICAS ===
        self.create_plots_area(main_layout)
        
        # === PANEL DE CONTROL ===
        self.create_control_panel(main_layout)
        
        # === ESPACIO FLEXIBLE AL FINAL ===
        main_layout.addStretch()
    
        # Estilo global
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #FFFFFF;
                border-radius: 0px;
            }
        """)
    
    def create_header(self, main_layout):
        """Crear header con título y logo"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                           stop: 0 rgba(120, 255, 180, 0.9),
                                           stop: 0.2 rgba(0, 230, 140, 0.8),
                                           stop: 0.4 rgba(0, 169, 157, 0.85),
                                           stop: 0.6 rgba(0, 140, 130, 0.8),
                                           stop: 0.8 rgba(0, 200, 160, 0.85),
                                           stop: 1 rgba(120, 255, 180, 0.9));
                border-top: 2px solid rgba(200, 255, 220, 0.8);
                border-left: 1px solid rgba(255, 255, 255, 0.6);
                border-right: 1px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.4);
                padding: 0px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 2, 20, 2)
        header_layout.setSpacing(5)
        
        # Logo o icono principal
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(220, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
        else:
            logo_label.setText("EMDR PROJECT")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setFont(QFont('Arial', 20, QFont.Bold))
        
        logo_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # Título de la sección
        title_label = QLabel("PRUEBA DE EOG (ElectroOculoGrafía)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # Botón de regreso
        self.back_btn = QPushButton()
        self.back_btn.setIcon(qta.icon('fa5s.arrow-left', color='white'))
        self.back_btn.setText(" Regresar")
        self.back_btn.setFixedSize(120, 35)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #555555;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 1px solid #777777;
            }
            QPushButton:pressed {
                background-color: #333333;
                border: 1px solid #444444;
            }
        """)
        self.back_btn.clicked.connect(self.go_back_to_dashboard)
        
        # Añadir elementos al header
        header_layout.addWidget(self.back_btn)
        header_layout.addStretch()
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addWidget(header_frame)
    
    def create_status_bar(self, main_layout):
        """Crear barra de estado con información de conexión y datos"""
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-top: 1px solid #444444;
                border-bottom: 1px solid #444444;
                padding: 0px;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 0, 20, 0)
        status_layout.setSpacing(30)
        
        # Estado de conexión
        self.connection_label = QLabel("● Desconectado")
        self.connection_label.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        # Tasa de muestras
        self.sample_rate_label = QLabel("Muestras/s: 0")
        self.sample_rate_label.setStyleSheet("""
            QLabel {
                color: #4ECDC4;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        # Estado de señal
        self.signal_quality_label = QLabel("Calidad de señal: --")
        self.signal_quality_label.setStyleSheet("""
            QLabel {
                color: #FFE66D;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        # Botón conectar/desconectar (centrado)
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.setFixedHeight(30)
        self.connect_btn.setStyleSheet(self.get_button_style('#4CAF50'))
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # Botón iniciar/detener adquisición
        self.acquire_btn = QPushButton("▶️ Iniciar")
        self.acquire_btn.setFixedHeight(30)
        self.acquire_btn.setStyleSheet(self.get_button_style('#2196F3'))
        self.acquire_btn.setEnabled(False)
        self.acquire_btn.clicked.connect(self.toggle_acquisition)
        
        # Botón guardar datos
        self.save_btn = QPushButton("💾 Guardar CSV")
        self.save_btn.setFixedHeight(30)
        self.save_btn.setStyleSheet(self.get_button_style('#FF9800'))
        self.save_btn.clicked.connect(self.save_data)
        
        # Añadir elementos a la barra de estado
        status_layout.addWidget(self.connection_label)
        status_layout.addWidget(self.sample_rate_label)
        status_layout.addWidget(self.signal_quality_label)
        status_layout.addStretch()
        status_layout.addWidget(self.connect_btn)
        status_layout.addWidget(self.acquire_btn)
        status_layout.addWidget(self.save_btn)
        status_layout.addStretch()
        
        main_layout.addWidget(status_frame)
    
    def create_plots_area(self, main_layout):
        """Crear área de gráficas para señales EOG (2 gráficas)"""
        plots_frame = QFrame()
        plots_frame.setFrameShape(QFrame.StyledPanel)
        plots_frame.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(10, 5, 10, 5)
        plots_layout.setSpacing(5)
        
        # Configurar PyQtGraph para tema oscuro
        pg.setConfigOption('background', '#1A1A1A')
        pg.setConfigOption('foreground', '#FFFFFF')
        
        # === GRÁFICA 1: SEÑAL EOG RAW ===
        self.plot_raw = pg.PlotWidget(title="Señal EOG Raw")
        self.plot_raw.setFixedHeight(200)
        self.plot_raw.setLabel('left', 'Amplitud', units='uV', color='#FFFFFF')
        self.plot_raw.setLabel('bottom', 'Tiempo', units='s', color='#FFFFFF')
        self.plot_raw.getAxis('left').setTextPen('#FFFFFF')
        self.plot_raw.getAxis('bottom').setTextPen('#FFFFFF')
        self.plot_raw.setYRange(-350, 250)
        
        # Configurar apariencia de la gráfica raw
        self.plot_raw.setBackground('#1A1A1A')
        self.plot_raw.getPlotItem().getViewBox().setBackgroundColor('#1A1A1A')
        self.plot_raw.getPlotItem().titleLabel.setText("Señal EOG Raw", color='#FFFFFF', size='12pt')
        
        # Línea para señal raw
        self.curve_raw = self.plot_raw.plot(pen=pg.mkPen(color='#FF6B6B', width=2))
        
        # === GRÁFICA 2: SEÑAL EOG FILTRADA ===
        self.plot_filtered = pg.PlotWidget(title="Señal EOG Filtrada")
        self.plot_filtered.setFixedHeight(200)
        self.plot_filtered.setLabel('left', 'Amplitud', units='uV', color='#FFFFFF')
        self.plot_filtered.setLabel('bottom', 'Tiempo', units='s', color='#FFFFFF')
        self.plot_filtered.getAxis('left').setTextPen('#FFFFFF')
        self.plot_filtered.getAxis('bottom').setTextPen('#FFFFFF')
        self.plot_filtered.setYRange(-400, 250)
        
        # Configurar apariencia de la gráfica filtrada
        self.plot_filtered.setBackground('#1A1A1A')
        self.plot_filtered.getPlotItem().getViewBox().setBackgroundColor('#1A1A1A')
        self.plot_filtered.getPlotItem().titleLabel.setText("Señal EOG Filtrada", color='#FFFFFF', size='12pt')
        
        # Línea para señal filtrada
        self.curve_filtered = self.plot_filtered.plot(pen=pg.mkPen(color='#4ECDC4', width=2))
        
        # Añadir gráficas al layout
        plots_layout.addWidget(self.plot_raw)
        plots_layout.addWidget(self.plot_filtered)
        
        main_layout.addWidget(plots_frame)
    
    def create_control_panel(self, main_layout):
        """Crear panel de control principal"""
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 2px solid #444444;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(20, 5, 20, 5)
        control_layout.setSpacing(30)
        
        # === GRUPO: CALIBRACIÓN Y FILTROS ===
        calibration_group = QGroupBox("Filtros y Sistema")
        calibration_group.setStyleSheet("""
            QGroupBox {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #2A2A2A;
            }
        """)
        
        calibration_layout = QGridLayout(calibration_group)
        calibration_layout.setSpacing(8)
        
        # Botón información del filtro
        self.filter_info_btn = QPushButton("ℹ️ Info Filtro")
        self.filter_info_btn.setFixedHeight(35)
        self.filter_info_btn.setStyleSheet(self.get_button_style('#607D8B'))
        self.filter_info_btn.clicked.connect(self.show_filter_info)
        
        # Botón reiniciar filtro
        self.reset_filter_btn = QPushButton("🔄 Reset Filtro")
        self.reset_filter_btn.setFixedHeight(35)
        self.reset_filter_btn.setStyleSheet(self.get_button_style('#795548'))
        self.reset_filter_btn.clicked.connect(self.reset_filter)
        
        # Botón análisis offline
        self.offline_analysis_btn = QPushButton("📊 Análisis Offline")
        self.offline_analysis_btn.setFixedHeight(35)
        self.offline_analysis_btn.setStyleSheet(self.get_button_style('#9C27B0'))
        self.offline_analysis_btn.clicked.connect(self.open_offline_analysis)
        
        calibration_layout.addWidget(self.filter_info_btn, 0, 0)
        calibration_layout.addWidget(self.reset_filter_btn, 0, 1)
        calibration_layout.addWidget(self.offline_analysis_btn, 1, 0, 1, 2)  # Span 2 columns
        
        # === GRUPO: PRUEBAS OCULOMOTORAS ===
        oculomotor_group = QGroupBox("Pruebas Oculomotoras")
        oculomotor_group.setStyleSheet(calibration_group.styleSheet())
        
        oculomotor_layout = QGridLayout(oculomotor_group)
        oculomotor_layout.setSpacing(8)
        
        # Botón movimientos sacádicos
        self.saccadic_test_btn = QPushButton("🎯 Movimientos Sacádicos")
        self.saccadic_test_btn.setFixedHeight(35)
        self.saccadic_test_btn.setStyleSheet(self.get_button_style('#607D8B'))
        self.saccadic_test_btn.clicked.connect(self.start_saccadic_test)
        
        # Botón seguimiento suave senoidal
        self.smooth_pursuit_sin_btn = QPushButton("🌊 Seguimiento Suave Senoidal")
        self.smooth_pursuit_sin_btn.setFixedHeight(35)
        self.smooth_pursuit_sin_btn.setStyleSheet(self.get_button_style('#607D8B'))
        self.smooth_pursuit_sin_btn.clicked.connect(self.start_smooth_pursuit_sinusoidal)
        
        # Botón seguimiento suave lineal
        self.smooth_pursuit_lin_btn = QPushButton("📈 Seguimiento Suave Lineal")
        self.smooth_pursuit_lin_btn.setFixedHeight(35)
        self.smooth_pursuit_lin_btn.setStyleSheet(self.get_button_style('#607D8B'))
        self.smooth_pursuit_lin_btn.clicked.connect(self.start_smooth_pursuit_linear)
        
        oculomotor_layout.addWidget(self.saccadic_test_btn, 0, 0)
        oculomotor_layout.addWidget(self.smooth_pursuit_sin_btn, 0, 1)
        oculomotor_layout.addWidget(self.smooth_pursuit_lin_btn, 1, 0, 1, 2)  # Span 2 columns
        
        # Añadir grupos al layout
        control_layout.addWidget(calibration_group)
        control_layout.addWidget(oculomotor_group)
        control_layout.addStretch()
        
        main_layout.addWidget(control_frame)
    
    def get_button_style(self, base_color):
        """Genera estilo para botones con color base específico"""
        return f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid {base_color};
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: transparent;
                border: 2px solid {base_color};
                color: {base_color};
            }}
            QPushButton:pressed {{
                background-color: {base_color};
                border: 2px solid {base_color};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                border: 2px solid #666666;
                color: #AAAAAA;
            }}
        """
    
    # === MÉTODOS DE CONTROL ===
    
    def toggle_connection(self):
        """Alterna el estado de conexión"""
        if not self.connected:
            self.connect_device()
        else:
            self.disconnect_device()
    
    def connect_device(self):
        """Enviar comando para conectar el dispositivo EOG"""
        Devices.probe()
        print("Conectando el dispositivo EOG...")
        try:
            # Verificar que el controlador maestro esté conectado
            if not Devices.master_plugged_in():
                QMessageBox.critical(
                    self,
                    "Error de Conexión",
                    "No se encontró el controlador maestro.\n"
                    "Verifique que esté conectado al puerto USB.",
                    QMessageBox.Ok
                )
                return
            
            # Verificar que el sensor EOG esté conectado
            if not Devices.sensor_plugged_in():
                QMessageBox.critical(
                    self,
                    "Error de Conexión",
                    "No se encontró el sensor EOG.\n"
                    "Verifique que esté conectado al controlador maestro.",
                    QMessageBox.Ok
                )
                return
            
            self.connected = True
            self.connection_label.setText("● Conectado")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-size: 14px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
            print("EOG conectado")
        
            self.connect_btn.setText("🔌 Desconectar")
            self.connect_btn.setStyleSheet(self.get_button_style('#F44336'))
            self.acquire_btn.setEnabled(True)
            
            # Sonido de confirmación
            winsound.MessageBeep(winsound.MB_OK)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error de Conexión",
                f"No se pudo conectar al dispositivo EOG:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def disconnect_device(self):
        """Desconecta del dispositivo EOG"""
        try:
            if self.acquiring:
                self.stop_acquisition()
            
            self.connected = False
            self.connection_label.setText("● Desconectado")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #FF6B6B;
                    font-size: 14px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
            
            print("EOG desconectado")
        
            self.connect_btn.setText("🔌 Conectar")
            self.connect_btn.setStyleSheet(self.get_button_style('#4CAF50'))
            self.acquire_btn.setEnabled(False)
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error de Desconexión",
                f"Error al desconectar:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def toggle_acquisition(self):
        """Alterna el estado de adquisición de datos"""
        if not self.acquiring:
            self.start_acquisition()
        else:
            self.stop_acquisition()
    
    def start_acquisition(self):
        """Inicia la adquisición de señales EOG"""
        try:
            # Verificar que estamos conectados
            if not self.connected:
                QMessageBox.warning(
                    self,
                    "No Conectado",
                    "Debe conectar el dispositivo primero.",
                    QMessageBox.Ok
                )
                return
            
            # Verificar conexión con el hardware
            if not Devices.master_plugged_in():
                QMessageBox.critical(
                    self,
                    "Error de Hardware",
                    "Se perdió la conexión con el controlador maestro.",
                    QMessageBox.Ok
                )
                self.disconnect_device()
                return
            
            # Reiniciar filtro EOG
            self.eog_filter.reset()
            self.last_packet_id = -1
            
            # Limpiar y resetear los buffers de datos
            self.times.clear()
            self.eog_raw_values.clear()
            self.eog_filtered_values.clear()
        
            # Limpiar datos previos
            self.csv_data = {
                'index': [],
                'timestamp': [],
                'eog_raw': [],
                'eog_filtered': [],
                'signal_quality': [],
                'event': []
            }
            
            # Enviar comando al ESP32 para iniciar captura
            Devices.start_sensor()
            
            # Iniciar la captura de datos
            self.acquiring = True
            self.acquire_btn.setText("⏹️ Detener")
            self.acquire_btn.setStyleSheet(self.get_button_style('#F44336'))
            
            # Iniciar hilo de lectura de datos
            self.reading_thread = threading.Thread(target=self._read_data, daemon=True)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            
            print("Adquisición EOG iniciada")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error de Adquisición",
                f"No se pudo iniciar la adquisición:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def stop_acquisition(self):
        """Detiene la adquisición de señales EOG"""
        try:
            if not self.acquiring:
                return
            
            # Detener protocolo Step-Fixation si está ejecutándose
            if self.protocol_running:
                self.stop_protocol()
                
            # Detener adquisición
            self.acquiring = False
            
            # Enviar comando al ESP32 para detener captura
            if Devices.master_plugged_in():
                Devices.stop_sensor()
            
            # Esperar a que termine el hilo de lectura
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=1.0)
            
            self.acquire_btn.setText("▶️ Iniciar")
            self.acquire_btn.setStyleSheet(self.get_button_style('#2196F3'))
            
            print("Adquisición EOG detenida")
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al detener adquisición:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def _read_data(self):
        """Función que se ejecuta en un hilo separado para leer datos binarios"""
        data_buffer = bytearray()
        serial_conn = Devices.get_master_connection()
        
        if not serial_conn:
            print("Error: No se pudo obtener la conexión serial")
            self.acquiring = False
            return
        
        sample_count = 0
        start_time = time.time()
        
        while self.acquiring and not self.is_closing:
            try:
                # Leer datos del puerto serial
                available = serial_conn.in_waiting
                
                if available > 0:
                    new_data = serial_conn.read(min(available, BUFFER_SIZE * PACKET_SIZE))
                    data_buffer.extend(new_data)
                
                    # Procesar paquetes completos
                    while len(data_buffer) >= PACKET_SIZE and self.acquiring:
                        # Buscar inicio de paquete
                        packet_start = self._find_packet_start(data_buffer)
                        
                        if packet_start < 0:
                            # No se encontró header válido, descartar primer byte
                            if len(data_buffer) > 1:
                                data_buffer = data_buffer[-1:]
                            break
                        
                        # Eliminar datos antes del header
                        if packet_start > 0:
                            data_buffer = data_buffer[packet_start:]
                        
                        # Verificar que tenemos un paquete completo
                        if len(data_buffer) < PACKET_SIZE:
                            break
                        
                        # Extraer el paquete
                        packet = data_buffer[:PACKET_SIZE]
                        data_buffer = data_buffer[PACKET_SIZE:]
                        
                        # Procesar el paquete
                        if self._process_packet(packet):
                            sample_count += 1
                            
                            # Actualizar tasa de muestras cada segundo
                            current_time = time.time()
                            if current_time - start_time >= 1.0:
                                rate = sample_count / (current_time - start_time)
                                self.current_sample_rate = rate
                                sample_count = 0
                                start_time = current_time
                
                # Pequeña pausa para no saturar el CPU
                time.sleep(0.001)
                
            except Exception as e:
                if self.acquiring:  # Solo mostrar error si aún estamos adquiriendo
                    print(f"Error leyendo datos: {e}")
                break
        
        print("Hilo de lectura de datos terminado")

    def _find_packet_start(self, buffer):
        """Encontrar el inicio de un paquete en el buffer"""
        if len(buffer) < 2:
            return -1
            
        for i in range(len(buffer) - 1):
            # Buscar la secuencia de header (Little Endian: 0x55, 0xAA)
            if buffer[i] == (PACKET_HEADER & 0xFF) and buffer[i + 1] == (PACKET_HEADER >> 8) & 0xFF:
                return i
                
        return -1

    def _process_packet(self, packet):
        """Procesar un paquete de datos EOG"""
        try:
            # Verificar header
            header = struct.unpack('<H', packet[0:2])[0]
            if header != PACKET_HEADER:
                return False
            
            # Extraer ID del paquete
            packet_id = struct.unpack('<I', packet[2:6])[0]
            
            # Verificar paquetes duplicados
            if packet_id <= self.last_packet_id:
                return False
            
            self.last_packet_id = packet_id
            
            # Extraer timestamp (4 bytes)
            timestamp_ms = struct.unpack('<I', packet[6:10])[0]
            timestamp_s = timestamp_ms / 1000.0
            
            # Extraer datos EOG (2 bytes cada uno, signed)
            eog_raw = struct.unpack('<h', packet[12:14])[0]
            device_id = packet[14]
            
            # Aplicar filtrado
            eog_filtered = self.eog_filter.filter(eog_raw)
            
            # Convertir a microvoltios
            eog_raw_uv = eog_raw * 0.0078125 * 4.03225806 # Ganacia de 16 del ADS1115 y 248 del AD620 * 1000 uV
            eog_filtered_uv = eog_filtered * 0.0078125 * 4.03225806

            # Actualizar buffers para visualización
            self.times.append(timestamp_s)
            self.eog_raw_values.append(eog_raw_uv)
            self.eog_filtered_values.append(eog_filtered_uv)
            
            # Guardar datos para CSV
            self.csv_data['timestamp'].append(timestamp_ms)
            self.csv_data['index'].append(packet_id)
            self.csv_data['eog_raw'].append(eog_raw)
            self.csv_data['eog_filtered'].append(eog_filtered)
            self.csv_data['signal_quality'].append('good')  # Por ahora fijo
            self.csv_data['event'].append('none')  # Evento 'none' por defecto
            
            # Incrementar contador de muestras
            self.sample_count += 1
            
            return True
            
        except Exception as e:
            print(f"Error procesando paquete: {e}")
            return False
    
    def save_data(self):
        """Guarda los datos adquiridos en archivo CSV"""
        try:
            if not self.csv_data['timestamp']:
                QMessageBox.information(
                    self,
                    "Sin Datos",
                    "No hay datos para guardar.\nInicie la adquisición primero.",
                    QMessageBox.Ok
                )
                return
            
            # Crear DataFrame y guardar
            df = pd.DataFrame(self.csv_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eog_test_data_{timestamp}.csv"
            filepath = Path(__file__).parent.parent / 'data' / filename
            filepath.parent.mkdir(exist_ok=True)
            
            df.to_csv(filepath, index=False)
            
            QMessageBox.information(
                self,
                "Datos Guardados",
                f"Datos guardados exitosamente en:\n{filename}",
                QMessageBox.Ok
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudieron guardar los datos:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def start_calibration(self):
        """Inicia el proceso de verificación del sistema EOG"""
        reply = QMessageBox.question(
            self,
            "Verificación del Sistema EOG",
            "¿Desea verificar el estado del sistema EOG?\n\n"
            "Proceso de verificación:\n"
            "1. Verificación de calidad de señal\n"
            "2. Estado del filtro\n"
            "3. Prueba de conectividad\n\n"
            "Asegúrese de tener:\n"
            "• Adquisición de datos activa\n"
            "• Posición cómoda y estable\n\n"
            "¿Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Mostrar información del filtro
            self.show_filter_info()
    
    # === MÉTODOS DE PRUEBAS OCULOMOTORAS ===
    
    def start_saccadic_test(self):
        """Inicia la prueba de movimientos sacádicos con protocolo Step-Fixation"""
        if not self.connected:
            QMessageBox.warning(
                self,
                "Dispositivo no conectado",
                "Conecte el dispositivo antes de iniciar la prueba."
            )
            return
        
        if not self.acquiring:
            QMessageBox.warning(
                self,
                "Adquisición no activa",
                "Inicie la adquisición de datos antes de comenzar la prueba."
            )
            return
        
        if self.protocol_running:
            QMessageBox.information(
                self,
                "Protocolo en ejecución",
                "Ya hay un protocolo de estimulación ejecutándose."
            )
            return
        
        try:
            # Configurar e iniciar el protocolo Step-Fixation
            self.step_fixation_thread = StepFixationThread(
                devices=Devices,
                mark_event_callback=self.mark_event
            )
            
            # Conectar señales del protocolo
            self.step_fixation_thread.progress_updated.connect(self.on_protocol_progress)
            self.step_fixation_thread.stimulus_started.connect(self.on_stimulus_started)
            self.step_fixation_thread.stimulus_ended.connect(self.on_stimulus_ended)
            self.step_fixation_thread.sequence_finished.connect(self.on_protocol_finished)
            
            # Marcar inicio del protocolo
            self.protocol_running = True
            self.saccadic_test_btn.setText("🔄 Protocolo en curso...")
            self.saccadic_test_btn.setEnabled(False)
            
            # Marcar evento de inicio
            self.mark_event("STEP_FIXATION_START")
            
            # Iniciar el hilo
            self.step_fixation_thread.start()
            
            # Calcular duración estimada
            estimated_duration = self.step_fixation_thread.get_estimated_duration()
            
            QMessageBox.information(
                self,
                "Protocolo Step-Fixation Iniciado",
                f"Se ha iniciado el protocolo de estimulación Step-Fixation.\n\n"
                f"Nuevo patrón de estimulación:\n"
                f"• LED Central: 10 segundos (inicial)\n"
                f"• 4 LEDs laterales aleatorios: -30°, -15°, +15°, +30°\n"
                f"• Cada LED lateral: 5 segundos\n"
                f"• Retorno al centro: 5 segundos (entre cada lateral)\n"
                f"• LED Central final: 5 segundos\n\n"
                f"Duración total estimada: {estimated_duration:.0f} segundos\n"
                f"Los eventos se registrarán automáticamente en el archivo CSV."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error en protocolo",
                f"Error al iniciar el protocolo Step-Fixation:\n{str(e)}"
            )
            self.protocol_running = False
            self.saccadic_test_btn.setText("🎯 Movimientos Sacádicos")
            self.saccadic_test_btn.setEnabled(True)
    
    def start_smooth_pursuit_sinusoidal(self):
        """Inicia la prueba de seguimiento suave senoidal"""
        QMessageBox.information(
            self,
            "Seguimiento Suave Senoidal",
            "Iniciando prueba de seguimiento suave senoidal...\n\n"
            "Esta prueba evaluará:\n"
            "• Capacidad de seguimiento continuo\n"
            "• Respuesta a movimientos predictivos\n"
            "• Estabilidad del seguimiento\n"
            "• Ganancia del sistema oculomotor\n\n"
            "Esta funcionalidad será implementada próximamente.",
            QMessageBox.Ok
        )
    
    def start_smooth_pursuit_linear(self):
        """Inicia la prueba de seguimiento suave lineal"""
        # Verificar conexión
        if not self.connected:
            QMessageBox.warning(
                self,
                "Error",
                "No hay conexión con el dispositivo.\n"
                "Por favor, conecte el dispositivo antes de iniciar la prueba."
            )
            return
        
        # Verificar que la adquisición esté activa
        if not self.acquiring:
            QMessageBox.warning(
                self,
                "Error",
                "La adquisición de datos debe estar activa.\n"
                "Por favor, inicie la adquisición antes de comenzar la prueba."
            )
            return
        
        # Verificar que no haya otro protocolo ejecutándose
        if self.protocol_running:
            QMessageBox.warning(
                self,
                "Error",
                "Ya hay un protocolo en ejecución.\n"
                "Por favor, espere a que termine o deténgalo antes de iniciar uno nuevo."
            )
            return
        
        try:
            # Crear instancia del thread de smooth pursuit (CORREGIDO: usar Devices en lugar de self.devices)
            self.smooth_pursuit_thread = LinealSmoothPursuitThread(
                devices=Devices,  # ✅ Cambiar de self.devices a Devices
                mark_event_callback=self.mark_event
            )
            
            # Obtener duración estimada
            estimated_duration = self.smooth_pursuit_thread.get_estimated_duration()
            
            # Mostrar información del protocolo
            reply = QMessageBox.question(
                self,
                "Seguimiento Suave Lineal",
                f"Protocolo de Seguimiento Suave Lineal\n\n"
                f"Secuencia:\n"
                f"• Baseline: LED central por 10 segundos\n"
                f"• 3 ciclos de barrido lineal (-20° a +20°)\n"
                f"• Velocidad constante: 17°/s\n"
                f"• Fading suave entre LEDs\n"
                f"• Pausas de 0.5s entre ciclos\n\n"
                f"Duración estimada: {estimated_duration:.1f} segundos\n\n"
                f"¿Desea iniciar el protocolo?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Conectar señales del thread
            self.smooth_pursuit_thread.progress_updated.connect(self.update_protocol_progress)
            self.smooth_pursuit_thread.sequence_finished.connect(self.on_smooth_pursuit_finished)
            
            # Marcar que hay un protocolo ejecutándose
            self.protocol_running = True
            
            # Actualizar UI
            self.smooth_pursuit_lin_btn.setText("🔄 Ejecutando...")
            self.smooth_pursuit_lin_btn.setEnabled(False)
            
            # Iniciar el thread
            self.smooth_pursuit_thread.start()
            
            print(f"Protocolo Smooth-Pursuit iniciado (duración estimada: {estimated_duration:.1f}s)")
            
        except Exception as e:
            print(f"Error al iniciar protocolo Smooth-Pursuit: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al iniciar el protocolo:\n{str(e)}"
            )
            # Restaurar estado en caso de error
            self.protocol_running = False
            self.smooth_pursuit_lin_btn.setText("📈 Seguimiento Suave Lineal")
            self.smooth_pursuit_lin_btn.setEnabled(True)
    
    def open_offline_analysis(self):
        """Abre la ventana de análisis offline de señales EOG"""
        try:
            # Importar usando path absoluto
            import sys
            from pathlib import Path
            
            # Añadir el directorio src al path si no está
            src_path = Path(__file__).parent.parent
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            from views.offline_analysis_window import OfflineAnalysisWindow
            
            self.offline_window = OfflineAnalysisWindow()
            self.offline_window.show()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir la ventana de análisis offline:\n{str(e)}"
            )
    
    # === MÉTODOS DE ACTUALIZACIÓN ===
    
    def update_plots(self):
        """Actualiza las gráficas con nuevos datos reales"""
        if not self.acquiring or len(self.times) == 0:
            return
        
        x_data = np.array(self.times)
        eog_raw_data = np.array(self.eog_raw_values)
        eog_filtered_data = np.array(self.eog_filtered_values)
        
        if self.acquiring:
            current_time = x_data[-1]
            times_relative = x_data - current_time  # Tiempo relativo al presente
        else:
            times_relative = x_data
        
        # Actualizar gráficas con datos reales
        self.curve_raw.setData(times_relative, eog_raw_data)
        self.curve_filtered.setData(times_relative, eog_filtered_data)
        
        # Actualizar etiqueta de calidad de señal basada en datos reales
        # if len(self.eog_filtered_values) > 0:
        #     # Calcular estadísticas de calidad simple
        #     recent_data = list(self.eog_filtered_values)[-125:]  # Último segundo
        #     if len(recent_data) > 10:
        #         signal_std = np.std(recent_data)
        #         if signal_std < 10:
        #             quality = "Excelente"
        #         elif signal_std < 50:
        #             quality = "Buena"
        #         elif signal_std < 100:
        #             quality = "Regular"
        #         else:
        #             quality = "Pobre"
                
        #         self.signal_quality_label.setText(f"Calidad de señal: {quality}")
        
        # Fijar el rango X para visualización en tiempo real
        self.plot_raw.setXRange(-DISPLAY_TIME, 0, padding=0.01)
        self.plot_filtered.setXRange(-DISPLAY_TIME, 0, padding=0.01)
    
    def update_sample_rate(self):
        """Actualiza la tasa de muestras mostrada"""
        current_time = time.time()
        elapsed = current_time - self.last_sample_time
        
        if elapsed > 0:
            self.current_sample_rate = self.sample_count / elapsed
            self.sample_rate_label.setText(f"Muestras/s: {self.current_sample_rate:.1f}")
        
        # Reset contador
        self.sample_count = 0
        self.last_sample_time = current_time
    
    def go_back_to_dashboard(self):
        """Regresa al dashboard principal"""
        # Detener adquisición si está activa
        if self.acquiring:
            self.stop_acquisition()
        
        # Desconectar si está conectado
        if self.connected:
            self.disconnect_device()
        
        # Emitir señal para mostrar dashboard
        self.return_to_dashboard.emit()
        
        # Cerrar esta ventana
        self.close()
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de ventana"""
        self.is_closing = True
        
        # Detener protocolo Step-Fixation si está ejecutándose
        if self.protocol_running:
            self.stop_protocol()
        
        # Detener timers
        if hasattr(self, 'plot_timer'):
            self.plot_timer.stop()
        if hasattr(self, 'rate_timer'):
            self.rate_timer.stop()
        
        # Detener adquisición
        if self.acquiring:
            self.stop_acquisition()
        
        # Desconectar dispositivo
        if self.connected:
            self.disconnect_device()
        
        # Esperar a que termine el hilo de lectura
        if hasattr(self, 'reading_thread') and self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=1.0)
        
        event.accept()
    
    def show_filter_info(self):
        """Mostrar información detallada del filtro EOG"""
        filter_info = self.eog_filter.get_filter_info()
        
        info_text = f"""
        INFORMACIÓN DEL FILTRO EOG
        ═══════════════════════════════════════
        
        Frecuencia de muestreo: {filter_info['sample_rate']} Hz
        
        Filtros activos: {filter_info['total_filters']}
        • High-pass: {filter_info['hp_cutoff']} Hz
        • Low-pass: {filter_info['lp_cutoff']} Hz (FIR {filter_info['fir_taps']} taps)
        
        Filtro Notch:
        • Frecuencia: {filter_info['notch_frequency']} Hz
        • Factor Q: {filter_info['notch_q']}
        • Estado: {'ACTIVO' if filter_info['notch_enabled'] else 'INACTIVO'}
        
        Retardo estimado: {filter_info['estimated_delay_ms']:.1f} ms
        
        Banda útil EOG: {filter_info['hp_cutoff']} - {filter_info['lp_cutoff']} Hz
        Optimizado para señales de movimientos oculares.
        """
        
        QMessageBox.information(
            self,
            "Información del Filtro EOG",
            info_text,
            QMessageBox.Ok
        )
    
    def reset_filter(self):
        """Reiniciar el filtro EOG"""
        if hasattr(self, 'eog_filter'):
            self.eog_filter.reset()
            QMessageBox.information(
                self,
                "Filtro Reiniciado",
                "El filtro EOG ha sido reiniciado.\n"
                "El estado interno se ha limpiado.",
                QMessageBox.Ok
            )
    
    def mark_event(self, event_label: str):
        """
        Marca un evento en el último punto de datos CSV.
        
        Args:
            event_label: Etiqueta del evento a registrar
        """
        if self.csv_data['event'] and len(self.csv_data['event']) > 0:
            # Marcar el evento en la última muestra registrada
            self.csv_data['event'][-1] = event_label
            print(f"Evento marcado: {event_label} en timestamp {self.csv_data['timestamp'][-1] if self.csv_data['timestamp'] else 'N/A'}")
    
    def on_protocol_progress(self, current: int, total: int):
        """Maneja la actualización del progreso del protocolo"""
        progress_text = f"🔄 Estímulo {current}/{total}"
        self.saccadic_test_btn.setText(progress_text)
        print(f"Progreso del protocolo: {current}/{total}")
    
    def on_stimulus_started(self, angle: int):
        """Maneja el inicio de un estímulo"""
        print(f"Estímulo iniciado en ángulo: {angle:+03d}°")
        # Actualizar UI si es necesario
        
    def on_stimulus_ended(self, angle: int):
        """Maneja el fin de un estímulo"""
        print(f"Estímulo terminado en ángulo: {angle:+03d}°")
        # Actualizar UI si es necesario
        
    def on_protocol_finished(self):
        """Maneja la finalización del protocolo"""
        self.protocol_running = False
        self.saccadic_test_btn.setText("🎯 Movimientos Sacádicos")
        self.saccadic_test_btn.setEnabled(True)
        
        # Marcar evento de finalización
        self.mark_event("STEP_FIXATION_END")
        
        QMessageBox.information(
            self,
            "Protocolo Completado",
            "El protocolo Step-Fixation ha finalizado correctamente.\n\n"
            "Todos los eventos han sido registrados en el archivo CSV."
        )
        
        print("Protocolo Step-Fixation completado")
    
    def stop_protocol(self):
        """Detiene el protocolo en ejecución si existe"""
        if self.step_fixation_thread and self.step_fixation_thread.isRunning():
            self.step_fixation_thread.stop()
            self.step_fixation_thread.wait(3000)  # Esperar hasta 3 segundos
            
            if self.step_fixation_thread.isRunning():
                self.step_fixation_thread.terminate()
                
            self.mark_event("STEP_FIXATION_ABORTED")
            self.protocol_running = False
            self.saccadic_test_btn.setText("🎯 Movimientos Sacádicos")
            self.saccadic_test_btn.setEnabled(True)
            
            print("Protocolo Step-Fixation detenido")
            
        if self.smooth_pursuit_thread and self.smooth_pursuit_thread.isRunning():
            self.smooth_pursuit_thread.stop()
            self.smooth_pursuit_thread.wait(3000)  # Esperar hasta 3 segundos
            
            if self.smooth_pursuit_thread.isRunning():
                self.smooth_pursuit_thread.terminate()
                
            self.mark_event("PURSUIT_PROTOCOL_ABORTED")
            self.protocol_running = False
            self.smooth_pursuit_lin_btn.setText("📈 Seguimiento Suave Lineal")
            self.smooth_pursuit_lin_btn.setEnabled(True)
            
            print("Protocolo Smooth-Pursuit Lineal detenido")

    # === MÉTODOS DE SEGUIMIENTO SUAVE ===
    # === ============================ ===

    def update_protocol_progress(self, phase: str, cycle: int = 0, total_cycles: int = 0):
        """Maneja la actualización del progreso del protocolo Smooth Pursuit"""
        if phase == "baseline":
            progress_text = "🔄 Baseline en curso..."
        elif phase == "pursuit":
            progress_text = f"🔄 Ciclo {cycle}/{total_cycles}"
        else:
            progress_text = "🔄 Protocolo en curso..."
        
        self.smooth_pursuit_lin_btn.setText(progress_text)
        print(f"Progreso Smooth Pursuit: {phase} - Ciclo {cycle}/{total_cycles}")
    
    def on_smooth_pursuit_finished(self):
        """Maneja la finalización del protocolo Smooth Pursuit"""
        self.protocol_running = False
        self.smooth_pursuit_lin_btn.setText("📈 Seguimiento Suave Lineal")
        self.smooth_pursuit_lin_btn.setEnabled(True)
        
        # Marcar evento de finalización
        self.mark_event("PURSUIT_PROTOCOL_END")
        
        QMessageBox.information(
            self,
            "Protocolo Completado",
            "El protocolo Smooth-Pursuit Lineal ha finalizado correctamente.\n\n"
            "Se completaron 3 ciclos de seguimiento con registro de eventos.\n"
            "Todos los eventos han sido registrados en el archivo CSV."
        )

# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear ventana de prueba de EOG
    window = EOGTestWindow()
    
    # Manejar señal de retorno
    def on_return():
        print("Regreso al dashboard solicitado")
        app.quit()
    
    window.return_to_dashboard.connect(on_return)
    window.showMaximized()
    
    sys.exit(app.exec())
