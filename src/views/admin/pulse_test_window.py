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
    QPushButton, QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

import pyqtgraph as pg
import qtawesome as qta

# Importaciones del proyecto
from models.devices import Devices, KNOWN_SLAVES
from utils.signal_processing import OnlinePPGFilter, PPGHeartRateCalculator

# Configuración de constantes
SAMPLE_RATE = 125  # Hz
DISPLAY_TIME = 8   # Segundos de datos a mostrar
GRAPH_PADDING = 0.01
BUFFER_SIZE = 512

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55
PACKET_SIZE = 15


class PulseTestWindow(QMainWindow):
    """Ventana especializada para pruebas de pulso cardíaco"""
    
    # Señal para regresar al dashboard
    return_to_dashboard = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Variables de estado
        self.connected = False
        self.acquiring = False
        self.reading_thread = None
        self.is_closing = False
        
        # Datos para visualización
        self.display_size = DISPLAY_TIME * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Inicializar buffers
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        self.ppg_raw_values = deque(initial_values, maxlen=self.display_size)
        self.ppg_filtered_values = deque(initial_values, maxlen=self.display_size)
        self.pulse_values = deque(initial_values, maxlen=self.display_size)
        
        # Datos para CSV - CORREGIDO
        self.csv_data = {
            'timestamp': [],
            'ppg_raw': [],
            'ppg_filtered': [],
            'pulse_bpm': [],
            'pulse_confidence': []  # ✅ Cambiar a confianza
        }
        
        # Procesamiento de señales
        self.lowcut_freq = 0.2  # Hz
        self.highcut_freq = 10.0  # Hz
        self.ppg_filter = OnlinePPGFilter(
            filter_type='bandpass', 
            fs=SAMPLE_RATE, 
            lowcut=self.lowcut_freq, 
            highcut=self.highcut_freq, 
            order=4
        )
        self.bpm_calculator = PPGHeartRateCalculator(sample_rate=SAMPLE_RATE)
        self.current_heart_rate = 0
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
        self.plot_timer.start(50)  # 20 FPS
        
        # Timer para actualización de tasa de muestras
        self.rate_timer = QTimer()
        self.rate_timer.timeout.connect(self.update_sample_rate)
        self.rate_timer.start(1000)  # Cada segundo
    
    def setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle("EMDR Project - Prueba de Pulso Cardíaco")
        # self.setFixedSize(1000, 700)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent.parent / 'resources' / 'emdr_icon.png')))
        
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
        main_layout.addStretch()  # Esto empuja todo hacia arriba
    
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
        logo_path = Path(__file__).parent.parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            # Usar logo existente
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    border: none;
                    outline: none;
                    background: transparent;
                }
            """)
        else:
            # Usar icono vectorial como alternativa
            icon = qta.icon('fa5s.heartbeat', 
                           color='white', 
                           scale_factor=3.0)
            pixmap = icon.pixmap(120, 120)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    border: none;
                    outline: none;
                    background: transparent;
                }
            """)
    
        # Título principal
        title_label = QLabel("MONITOR DE SEÑALES PPG Y PULSO CARDÍACO")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Arial', 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)
        
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addWidget(header_frame)
    
    def create_status_bar(self, main_layout):
        """Crear barra de estado"""
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 0, 15, 0)
        
        # Estado de conexión
        self.connection_status_label = QLabel("🔴 ESP32: Desconectado")
        self.connection_status_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        # Estado de captura
        self.capture_status_label = QLabel("⏸️ Captura: Detenida")
        self.capture_status_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        # Tasa de muestras
        self.sample_rate_label = QLabel("📊 Tasa: 0.0 SPS")
        self.sample_rate_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        # Contador de muestras
        self.sample_count_label = QLabel("📈 Muestras: 0")
        self.sample_count_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
    
        # Añadir indicador de confianza BPM - CORREGIDO
        self.bpm_confidence_label = QLabel("🎯 Confianza: --")  # ✅ bpm no bpm
        self.bpm_confidence_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        # Botón Conectar ESP32
        self.btn_connect = QPushButton("🔌 Conectar ESP32")
        self.btn_connect.setFixedSize(150, 30)
        self.btn_connect.setStyleSheet(self.get_button_style("#00A99D"))
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        # Botón Iniciar Adquisición
        self.btn_acquire = QPushButton("▶️ Iniciar Captura")
        self.btn_acquire.setFixedSize(150, 30)
        self.btn_acquire.setStyleSheet(self.get_button_style("#00A99D"))
        self.btn_acquire.setEnabled(False)
        self.btn_acquire.clicked.connect(self.toggle_acquisition)
        
        # Botón Guardar CSV
        self.btn_save = QPushButton("💾 Guardar CSV")
        self.btn_save.setFixedSize(150, 30)
        self.btn_save.setStyleSheet(self.get_button_style("#00A99D"))
        self.btn_save.clicked.connect(self.save_data_csv)
        
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.capture_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.sample_rate_label)
        status_layout.addStretch()
        status_layout.addWidget(self.sample_count_label)
        status_layout.addStretch()
        status_layout.addWidget(self.bpm_confidence_label)  # ✅ bpm no bpm
        status_layout.addStretch()
        status_layout.addWidget(self.btn_connect)
        status_layout.addWidget(self.btn_acquire)
        status_layout.addWidget(self.btn_save)
        
        main_layout.addWidget(status_frame)
    
    def create_control_panel(self, main_layout):
        """Crear panel de control con botones"""
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 0px;
                padding: 0px;
            }
        """)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(9, 0, 9, 0)
        control_layout.setSpacing(15)
        
        # Etiqueta de pie de página
        footer_label = QLabel("Sistema de Terapia EMDR - Versión 1.0")
        footer_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                font-style: italic;
                background: transparent;
                padding: 5px;
            }
        """)
        
        # Botón Regresar
        self.btn_return = QPushButton("Regresar")
        self.btn_return.setFixedSize(150, 45)
        self.btn_return.setStyleSheet(self.get_button_style("#6c757d"))
        self.btn_return.clicked.connect(self.return_to_dashboard_clicked)
        
        # Botón Salir
        self.btn_exit = QPushButton("Salir")
        self.btn_exit.setFixedSize(150, 45)
        self.btn_exit.setStyleSheet(self.get_button_style("#424242"))
        self.btn_exit.clicked.connect(self.exit_application)
        
        # Agregar botones al layout
        control_layout.addWidget(footer_label)
        control_layout.addStretch()
        control_layout.addWidget(self.btn_return)
        control_layout.addWidget(self.btn_exit)
        
        main_layout.addWidget(control_frame)
    
    def get_button_style(self, base_color):
        """Generar estilo para botones con color base"""
        # Convertir color hex a RGB para gradientes
        color_variants = {
            "#2196F3": {"light": "#42A5F5", "dark": "#1976D2"},
            "#4CAF50": {"light": "#66BB6A", "dark": "#388E3C"},
            "#FF9800": {"light": "#FFB74D", "dark": "#F57C00"},
            "#9C27B0": {"light": "#BA68C8", "dark": "#7B1FA2"},
            "#F44336": {"light": "#EF5350", "dark": "#D32F2F"},
            "#00A99D": {"light": "#00C2B3", "dark": "#008C82"},
            "#6c757d": {"light": "#5a6268", "dark": "#545b62"},
            "#424242": {"light": "#555555", "dark": "#333333"},
        }
        
        colors = color_variants.get(base_color, {"light": base_color, "dark": base_color})
        
        return f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 {colors["light"]},
                                           stop: 1 {base_color});
                color: white;
                border: 2px solid {base_color};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 {colors["light"]},
                                           stop: 1 {colors["light"]});
                border: 2px solid {colors["light"]};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 {colors["dark"]},
                                           stop: 1 {colors["dark"]});
                border: 2px solid {colors["dark"]};
            }}
            QPushButton:disabled {{
                background-color: #222222;
                border: 2px solid #222222;
                color: #888888;
            }}
        """
    
    def create_plots_area(self, main_layout):
        """Crear área de gráficas"""
        plots_frame = QFrame()
        plots_frame.setFrameShape(QFrame.StyledPanel)
        plots_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 8px;
                border: 2px solid #555555;
            }
        """)
        
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(10, 10, 10, 10)
        plots_layout.setSpacing(2)
        
        # Crear las tres gráficas
        fixed_hight = 147
        self.create_ppg_raw_plot(plots_layout, fixed_hight)
        self.create_ppg_filtered_plot(plots_layout, fixed_hight)
        self.create_pulse_plot(plots_layout, fixed_hight + 26)
        
        main_layout.addWidget(plots_frame)
    
    def create_ppg_raw_plot(self, plots_layout, fixed_hight):
        """Crear gráfica de señal PPG cruda"""
        self.ppg_raw_plot = pg.PlotWidget()
        self.ppg_raw_plot.setFixedHeight(fixed_hight)
        self.ppg_raw_plot.setStyleSheet("QFrame {border: none;}")
        self.ppg_raw_plot.setLabel('left', 'PPG Cruda (mV)', size='10pt', color='#424242')
        self.ppg_raw_plot.setYRange(-400, 900) # (-10000, 20000) (-400, 800)
        self.ppg_raw_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.ppg_raw_plot.setBackground('#FFFFFF')
        self.ppg_raw_plot.showGrid(x=True, y=True, alpha=0.5)
        
        # Configurar ejes
        self.configure_plot_axis(self.ppg_raw_plot)
        
        # Crear curva de datos
        self.ppg_raw_curve = self.ppg_raw_plot.plot(pen=pg.mkPen('#E91E63', width=2))
        
        # Leyenda
        legend = pg.LegendItem(offset=(64, 10), labelTextSize='9pt')
        legend.setParentItem(self.ppg_raw_plot.graphicsItem())
        legend.addItem(self.ppg_raw_curve, "Señal PPG Sin Filtrar")
        legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        
        plots_layout.addWidget(self.ppg_raw_plot)
    
    def create_ppg_filtered_plot(self, plots_layout, fixed_hight):
        """Crear gráfica de señal PPG filtrada"""
        self.ppg_filtered_plot = pg.PlotWidget()
        self.ppg_filtered_plot.setFixedHeight(fixed_hight)
        self.ppg_filtered_plot.setStyleSheet("QFrame {border: none;}")
        self.ppg_filtered_plot.setLabel('left', 'PPG Filtrada (mV)', size='10pt', color='#424242')
        self.ppg_filtered_plot.setYRange(-500, 900) # (-10000, 20000) (-600, 700)
        self.ppg_filtered_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.ppg_filtered_plot.setBackground('#FFFFFF')
        self.ppg_filtered_plot.showGrid(x=True, y=True, alpha=0.5)
        
        # Configurar ejes
        self.configure_plot_axis(self.ppg_filtered_plot)
        
        # Crear curva de datos
        self.ppg_filtered_curve = self.ppg_filtered_plot.plot(pen=pg.mkPen('#00A99D', width=2))
        
        # Leyenda
        legend = pg.LegendItem(offset=(64, 10), labelTextSize='9pt')
        legend.setParentItem(self.ppg_filtered_plot.graphicsItem())
        legend.addItem(self.ppg_filtered_curve, f"Señal PPG Filtrada ({self.lowcut_freq}-{self.highcut_freq}Hz)")
        legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        
        plots_layout.addWidget(self.ppg_filtered_plot)
    
    def create_pulse_plot(self, plots_layout, fixed_hight):
        """Crear gráfica de pulso calculado"""
        self.pulse_plot = pg.PlotWidget()
        self.pulse_plot.setFixedHeight(fixed_hight)
        self.pulse_plot.setStyleSheet("QFrame {border: none;}")
        self.pulse_plot.setLabel('left', 'Frecuencia (BPM)', size='10pt', color='#424242')
        self.pulse_plot.setLabel('bottom', 'Tiempo (s)', size='10pt', color='#424242')
        self.pulse_plot.setYRange(50, 130)
        self.pulse_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.pulse_plot.setBackground('#FFFFFF')
        self.pulse_plot.showGrid(x=True, y=True, alpha=0.5)
        
        # ===== AÑADIR CONFIGURACIÓN PARA REDUCIR ESPACIADO DEL EJE X =====
        x_axis = self.pulse_plot.getAxis('bottom')
        x_axis.setHeight(26)       # Reducir altura total del eje X (valor por defecto ~40)
        
        # Configurar ejes
        self.configure_plot_axis(self.pulse_plot, show_x_values=True)
        
        # Crear curva de datos
        self.pulse_curve = self.pulse_plot.plot(pen=pg.mkPen('#FF5722', width=3))
        
        # Líneas de referencia para rangos normales de BPM
        reference_60 = pg.InfiniteLine(pos=60, angle=0, pen=pg.mkPen('#4CAF50', width=1, style=Qt.DashLine))
        reference_100 = pg.InfiniteLine(pos=100, angle=0, pen=pg.mkPen('#FF9800', width=1, style=Qt.DashLine))
        self.pulse_plot.addItem(reference_60)
        self.pulse_plot.addItem(reference_100)
        
        # Texto para mostrar BPM actual
        self.bpm_text = pg.TextItem(
            text="BPM: --", 
            color=(100, 100, 100),
            anchor=(0, 0),
            fill=pg.mkBrush(255, 255, 255, 200)
        )
        self.bpm_text.setPos(-DISPLAY_TIME + 1.5, 123)
        self.pulse_plot.addItem(self.bpm_text)
        
        # Leyenda
        legend = pg.LegendItem(offset=(64, 10), labelTextSize='9pt')
        legend.setParentItem(self.pulse_plot.graphicsItem())
        legend.addItem(self.pulse_curve, "Frecuencia Cardíaca")
        legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        
        plots_layout.addWidget(self.pulse_plot)
    
    def configure_plot_axis(self, plot_widget, show_x_values=False):
        """Configurar ejes de las gráficas"""
        # Eje X
        x_axis = plot_widget.getAxis('bottom')
        x_axis.setStyle(showValues=show_x_values)
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # Eje Y
        y_axis = plot_widget.getAxis('left')
        y_axis.setWidth(60)
        y_axis.setStyle(tickTextOffset=3, autoExpandTextSpace=False, tickTextHeight=12)
        y_axis.setPen(pg.mkPen('#424242', width=1))
        y_axis.setTextPen(pg.mkPen('#424242'))
    
    def toggle_connection(self):
        """Alternar conexión con ESP32"""
        if not self.connected:
            self.connect_esp32()
        else:
            self.disconnect_esp32()
    
    def connect_esp32(self):
        """Conectar con el ESP32"""
        try:
            # Verificar dispositivos usando la clase Devices
            found_devices = Devices.probe()
            
            if "Master Controller" not in found_devices:
                self.show_message("Error de Conexión", 
                                "No se encontró el controlador maestro.\n"
                                "Verifique que esté conectado y encendido.", 
                                QMessageBox.Critical)
                return
            
            if "Sensor" not in found_devices:
                self.show_message("Error de Conexión", 
                                "No se encontró el sensor de pulso.\n"
                                "Verifique que esté conectado y configurado.", 
                                QMessageBox.Warning)
                return
            
            # Conexión exitosa
            self.connected = True
            self.btn_connect.setText("🔌 Desconectar ESP32")
            self.btn_connect.setStyleSheet(self.get_button_style("#F44336"))
            self.btn_acquire.setEnabled(True)
            
            self.connection_status_label.setText("🟢 ESP32: Conectado")
            self.connection_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(76, 175, 80, 0.8);
                }
            """)
            
            print("ESP32 conectado exitosamente")
            
        except Exception as e:
            self.show_message("Error", f"Error al conectar ESP32:\n{str(e)}", QMessageBox.Critical)
    
    def disconnect_esp32(self):
        """Desconectar ESP32"""
        if self.acquiring:
            self.stop_acquisition()
        
        self.connected = False
        self.btn_connect.setText("🔌 Conectar ESP32")
        self.btn_connect.setStyleSheet(self.get_button_style("#2196F3"))
        self.btn_acquire.setEnabled(False)
        
        self.connection_status_label.setText("🔴 ESP32: Desconectado")
        self.connection_status_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        print("ESP32 desconectado")
    
    def toggle_acquisition(self):
        """Alternar adquisición de datos"""
        if not self.acquiring:
            self.start_acquisition()
        else:
            self.stop_acquisition()
    
    def start_acquisition(self):
        """Iniciar adquisición de datos"""
        if not self.connected:
            self.show_message("Error", "Primero debe conectar el ESP32", QMessageBox.Warning)
            return
        
        try:
            # Reiniciar filtros y detector
            self.ppg_filter.reset()
            self.bpm_calculator = PPGHeartRateCalculator(sample_rate=SAMPLE_RATE)
            self.last_packet_id = -1
            
            # Limpiar buffers
            self.clear_data_buffers()
            
            # Actualizar UI
            self.btn_acquire.setText("⏸️ Detener Captura")
            self.btn_acquire.setStyleSheet(self.get_button_style("#F44336"))
            self.capture_status_label.setText("▶️ Captura: Activa")
            self.capture_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(76, 175, 80, 0.8);
                }
            """)
            
            # Iniciar captura en ESP32
            Devices.start_sensor()
            
            # Cambiar estado
            self.acquiring = True
            self.sample_count = 0
            self.last_sample_time = time.time()
            
            # ✅ GUARDAR TIMESTAMP DE INICIO UNA SOLA VEZ
            self.start_datetime = datetime.now()

            # Iniciar hilo de lectura
            self.reading_thread = threading.Thread(target=self.read_data_thread)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            
            print("Adquisición iniciada")
            
        except Exception as e:
            self.show_message("Error", f"Error al iniciar adquisición:\n{str(e)}", QMessageBox.Critical)
    
    def stop_acquisition(self):
        """Detener adquisición de datos"""
        if not self.acquiring:
            return
        
        try:
            # Detener captura en ESP32
            if self.connected:
                Devices.stop_sensor()
            
            # Cambiar estado
            self.acquiring = False
            
            # Esperar a que termine el hilo
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=1.0)
            
            # Actualizar UI
            self.btn_acquire.setText("▶️ Iniciar Captura")
            self.btn_acquire.setStyleSheet(self.get_button_style("#4CAF50"))
            self.capture_status_label.setText("⏸️ Captura: Detenida")
            self.capture_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }
            """)
            
            print("Adquisición detenida")
            
        except Exception as e:
            self.show_message("Error", f"Error al detener adquisición:\n{str(e)}", QMessageBox.Critical)
    
    def clear_data_buffers(self):
        """Limpiar todos los buffers de datos"""
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times.clear()
        self.ppg_raw_values.clear()
        self.ppg_filtered_values.clear()
        self.pulse_values.clear()
        
        self.times.extend(initial_times)
        self.ppg_raw_values.extend(initial_values)
        self.ppg_filtered_values.extend(initial_values)
        self.pulse_values.extend(initial_values)
        
        # ✅ ESTRUCTURA CSV CORREGIDA
        self.csv_data = {
            'timestamp': [],
            'ppg_raw': [],
            'ppg_filtered': [],
            'pulse_bpm': [],
            'pulse_confidence': []
        }
        
        self.current_heart_rate = 0
    
    def read_data_thread(self):
        """Hilo para leer datos del ESP32"""
        data_buffer = bytearray()
        serial_conn = Devices.get_master_connection()
        
        if not serial_conn:
            print("No hay conexión serial disponible")
            return
        
        while self.acquiring and not self.is_closing:
            try:
                available = serial_conn.in_waiting
                
                if available > 0:
                    new_data = serial_conn.read(min(available, BUFFER_SIZE * PACKET_SIZE))
                    data_buffer.extend(new_data)
                    
                    while len(data_buffer) >= PACKET_SIZE and self.acquiring:
                        # Buscar inicio de paquete
                        packet_start = self.find_packet_start(data_buffer)
                        
                        if packet_start < 0:
                            if len(data_buffer) > 1:
                                data_buffer = data_buffer[-1:]
                            break
                        
                        if packet_start > 0:
                            data_buffer = data_buffer[packet_start:]
                        
                        if len(data_buffer) < PACKET_SIZE:
                            break
                        
                        # Procesar paquete
                        if self.process_packet(data_buffer[:PACKET_SIZE]):
                            self.sample_count += 1
                        
                        data_buffer = data_buffer[PACKET_SIZE:]
                
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error leyendo datos: {e}")
                time.sleep(0.1)
    
    def find_packet_start(self, buffer):
        """Encontrar inicio de paquete en el buffer"""
        if len(buffer) < 2:
            return -1
        
        for i in range(len(buffer) - 1):
            if buffer[i] == (PACKET_HEADER & 0xFF) and buffer[i + 1] == (PACKET_HEADER >> 8) & 0xFF:
                return i
        
        return -1
    
    def process_packet(self, packet_data):
        """Procesar un paquete de datos"""
        try:
            # Extraer datos del paquete
            header = struct.unpack('<H', packet_data[0:2])[0]
            
            if header != PACKET_HEADER:
                return False
            
            packet_id = struct.unpack('<I', packet_data[2:6])[0]
            
            # Verificar duplicados
            if packet_id <= self.last_packet_id:
                return False
            
            self.last_packet_id = packet_id
            
            timestamp_ms = struct.unpack('<I', packet_data[6:10])[0]
            timestamp_s = timestamp_ms / 1000.0
            
            ppg_raw = struct.unpack('<h', packet_data[10:12])[0]
            ppg_raw_mv = ppg_raw * 0.03125  # Convertir a mV para visualización
            device_id = packet_data[14]
            
            # ✅ FILTRAR VALOR RAW (SIN CONVERSIÓN)
            ppg_filtered = self.ppg_filter.filter(ppg_raw)  # Usar valor raw
            ppg_filtered_mv = ppg_filtered * 0.03125  # Convertir resultado para visualización
            
            # ✅ CALCULAR BPM CON VALOR FILTRADO (SIN CONVERSIÓN)
            result = self.bpm_calculator.add_sample(ppg_filtered, timestamp_s)
            
            # ✅ EXTRAER BPM Y CONFIANZA CORRECTAMENTE
            self.current_heart_rate = result['bpm'] if result['bpm'] is not None else 0
            pulse_confidence = result.get('confidence', 0.0)
            pulse_updated = result.get('updated', False)
            
            # Actualizar buffers de visualización
            self.times.append(timestamp_s)
            self.ppg_raw_values.append(ppg_raw_mv)
            self.ppg_filtered_values.append(ppg_filtered_mv)
            
            # ✅ MANEJAR VALORES None EN PULSE_VALUES
            pulse_display_value = self.current_heart_rate if self.current_heart_rate else 0
            self.pulse_values.append(pulse_display_value)
            
            # ✅ GUARDAR DATOS CSV CORRECTAMENTE
            self.csv_data['timestamp'].append(timestamp_ms)
            self.csv_data['ppg_raw'].append(ppg_raw)  # Valor raw sin convertir
            self.csv_data['ppg_filtered'].append(ppg_filtered)  # Valor filtrado sin convertir
            self.csv_data['pulse_bpm'].append(self.current_heart_rate if self.current_heart_rate else 0)
            self.csv_data['pulse_confidence'].append(pulse_confidence)
            
            # ✅ ACTUALIZAR LABEL DE CONFIANZA (cada 125 muestras = 1 segundo)
            if hasattr(self, 'sample_count') and self.sample_count % 125 == 0:
                self.update_confidence_display(pulse_confidence)
            
            return True
            
        except Exception as e:
            print(f"Error procesando paquete: {e}")
            return False
    
    def update_confidence_display(self, confidence):
        """Actualizar display de confianza BPM"""
        if confidence > 0.8:
            confidence_text = f"🎯 Confianza: Excelente ({confidence:.1%})"
            color_style = "background-color: rgba(76, 175, 80, 0.8);"
        elif confidence > 0.6:
            confidence_text = f"🎯 Confianza: Buena ({confidence:.1%})"
            color_style = "background-color: rgba(255, 193, 7, 0.8);"
        elif confidence > 0.4:
            confidence_text = f"🎯 Confianza: Regular ({confidence:.1%})"
            color_style = "background-color: rgba(255, 152, 0, 0.8);"
        else:
            confidence_text = f"🎯 Confianza: Baja ({confidence:.1%})"
            color_style = "background-color: rgba(244, 67, 54, 0.8);"
        
        self.bpm_confidence_label.setText(confidence_text)
        self.bpm_confidence_label.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                {color_style}
                padding: 2px 6px;
                border-radius: 3px;
            }}
        """)
    
    def update_plots(self):
        """Actualizar las gráficas"""
        if len(self.times) > 0:
            x_data = np.array(self.times)
            
            if self.acquiring:
                current_time = x_data[-1]
                normalized_x = x_data - current_time
            else:
                normalized_x = x_data
            
            # Actualizar curvas
            self.ppg_raw_curve.setData(normalized_x, np.array(self.ppg_raw_values))
            self.ppg_filtered_curve.setData(normalized_x, np.array(self.ppg_filtered_values))
            self.pulse_curve.setData(normalized_x, np.array(self.pulse_values))
            
            # ✅ MEJORAR VISUALIZACIÓN BPM CON CONFIANZA
            if self.current_heart_rate and self.current_heart_rate > 0:
                hr_str = f"BPM: {int(self.current_heart_rate)}"
                
                # Obtener confianza del calculador
                confidence = getattr(self.bpm_calculator, 'confidence_score', 0.0)
                
                # Color basado en CONFIANZA y rango fisiológico
                if confidence > 0.7:
                    if 60 <= self.current_heart_rate <= 100:
                        self.bpm_text.setColor((76, 175, 80))  # Verde - excelente
                    elif 50 <= self.current_heart_rate <= 120:
                        self.bpm_text.setColor((255, 193, 7))  # Amarillo - aceptable
                    else:
                        self.bpm_text.setColor((255, 152, 0))  # Naranja - fuera de rango normal
                elif confidence > 0.4:
                    self.bpm_text.setColor((255, 152, 0))  # Naranja - confianza media
                else:
                    self.bpm_text.setColor((244, 67, 54))  # Rojo - baja confianza
            else:
                hr_str = "BPM: --"
                self.bpm_text.setColor((158, 158, 158))  # Gris - sin datos
            
            self.bpm_text.setText(hr_str)
        
        # Fijar rangos X
        for plot in [self.ppg_raw_plot, self.ppg_filtered_plot, self.pulse_plot]:
            plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
    
    def update_sample_rate(self):
        """Actualizar la tasa de muestras mostrada"""
        current_time = time.time()
        time_diff = current_time - self.last_sample_time
        
        if time_diff > 0:
            # Calcular tasa de muestras por segundo basada en muestras procesadas
            if hasattr(self, 'last_sample_count'):
                samples_diff = self.sample_count - self.last_sample_count
                self.current_sample_rate = samples_diff / time_diff
            else:
                self.current_sample_rate = 0
        
        # Actualizar labels
        self.sample_rate_label.setText(f"📊 Tasa: {self.current_sample_rate:.1f} SPS")
        self.sample_count_label.setText(f"📈 Muestras: {self.sample_count}")
        
        # Guardar valores para próxima iteración
        self.last_sample_count = self.sample_count
        self.last_sample_time = current_time
    
    def save_data_csv(self):
        """Guardar datos en archivo CSV"""
        try:
            if not any(self.csv_data.values()) or len(self.csv_data['timestamp']) == 0:
                self.show_message("Sin Datos", 
                                "No hay datos para guardar.\n"
                                "Inicie la captura primero.", 
                                QMessageBox.Warning)
                return
            
            # ✅ CONVERTIR TIMESTAMPS DIRECTAMENTE EN EL DICCIONARIO EXISTENTE
            converted_timestamps = []
            for timestamp_ms in self.csv_data['timestamp']:
                absolute_timestamp = self.start_datetime + pd.Timedelta(milliseconds=timestamp_ms)
                timestamp_formatted = absolute_timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
                converted_timestamps.append(timestamp_formatted)
            
            # ✅ REEMPLAZAR TIMESTAMPS EN EL DICCIONARIO ORIGINAL
            self.csv_data['timestamp'] = converted_timestamps
            
            # Crear DataFrame directamente con el diccionario modificado
            df = pd.DataFrame(self.csv_data)
            
            # Crear directorio si no existe
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            
            # Generar nombre de archivo
            file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = data_dir / f"pulse_test_data_{file_timestamp}.csv"
            
            # ✅ AÑADIR METADATOS AL INICIO DEL ARCHIVO
            session_start = self.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            session_duration = (datetime.now() - self.start_datetime).total_seconds()
            
            with open(filename, 'w') as f:
                f.write("# EMDR Pulse Test Session Data\n")
                f.write(f"# Session Start: {session_start}\n")
                f.write(f"# Session Duration: {session_duration:.1f} seconds\n")
                f.write(f"# Sample Rate: {SAMPLE_RATE} Hz\n")
                f.write(f"# Total Samples: {len(df)}\n")
                f.write(f"# Filter Range: {self.lowcut_freq}-{self.highcut_freq} Hz\n")
                f.write("#\n")
                f.write("# Columns: timestamp (HH:MM:SS.mmm), ppg_raw, ppg_filtered, pulse_bpm, pulse_confidence\n")
                f.write("#\n")
            
            # Guardar datos
            df.to_csv(filename, mode='a', index=False)
            
            self.show_message("Datos Guardados", 
                            f"Los datos se han guardado exitosamente.\n\n"
                            f"Archivo: {filename.name}\n"
                            f"Muestras: {len(df)}\n"
                            f"Duración: {session_duration:.1f} segundos", 
                            QMessageBox.Information)
            
            print(f"Datos guardados en: {filename}")
            
        except Exception as e:
            self.show_message("Error", f"Error al guardar datos:\n{str(e)}", QMessageBox.Critical)
    
    def return_to_dashboard_clicked(self):
        """Manejar clic en botón regresar"""
        winsound.MessageBeep(winsound.MB_ICONQUESTION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirmar Regreso")
        msg_box.setText("¿Está seguro de que desea regresar al Dashboard?")
        msg_box.setInformativeText("Se detendrá cualquier captura en progreso.")
        msg_box.setIcon(QMessageBox.Question)
        
        yes_button = msg_box.addButton("Sí, Regresar", QMessageBox.YesRole)
        no_button = msg_box.addButton("No, Continuar", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        msg_box.setStyleSheet(self.get_messagebox_style())
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            if self.acquiring:
                self.stop_acquisition()
            self.return_to_dashboard.emit()
    
    def exit_application(self):
        """Salir de la aplicación"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirmar Salida")
        msg_box.setText("¿Está seguro de que desea salir de la aplicación?")
        msg_box.setInformativeText("Se perderán todos los datos no guardados.")
        msg_box.setIcon(QMessageBox.Question)
        
        yes_button = msg_box.addButton("Sí, Salir", QMessageBox.YesRole)
        no_button = msg_box.addButton("No, Continuar", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        msg_box.setStyleSheet(self.get_messagebox_style())
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            self.cleanup()
            QApplication.quit()
    
    def get_messagebox_style(self):
        """Estilo para mensajes de diálogo"""
        return """
            QMessageBox {
                background-color: #323232;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 8px;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
                background: transparent;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #00A99D;
                color: white;
                border: 2px solid #00A99D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QMessageBox QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
        """
    
    def show_message(self, title, text, icon):
        """Mostrar mensaje con estilo personalizado"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(icon)
        msg_box.setStyleSheet(self.get_messagebox_style())
        msg_box.exec()
    
    def cleanup(self):
        """Limpiar recursos antes de cerrar"""
        print("Limpiando recursos de PulseTestWindow...")
        self.is_closing = True
        
        # Detener adquisición
        if self.acquiring:
            self.stop_acquisition()
        
        # Detener timers
        if hasattr(self, 'plot_timer'):
            self.plot_timer.stop()
        if hasattr(self, 'rate_timer'):
            self.rate_timer.stop()
        
        # Desconectar ESP32
        if self.connected:
            self.disconnect_esp32()
        
        print("Limpieza completada")
    
    def closeEvent(self, event):
        """Manejar evento de cierre de ventana"""
        self.cleanup()
        event.accept()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = PulseTestWindow()
    window.showMaximized()
    
    sys.exit(app.exec())
    # print("🔴 ESP32: Desconectado")
    # ("🟢 ESP32: Conectado")
