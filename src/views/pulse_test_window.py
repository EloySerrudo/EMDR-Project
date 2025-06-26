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

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones del proyecto
from src.models.devices import Devices, KNOWN_SLAVES
from src.utils.signal_processing import RealTimeFilter, PulseDetector

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
        
        # Datos para CSV
        self.csv_data = {
            'timestamp': [],
            'ppg_raw': [],
            'ppg_filtered': [],
            'pulse_bpm': [],
            'pulse_detected': []
        }
        
        # Procesamiento de señales
        self.lowcut_freq = 0.5  # Hz
        self.highcut_freq = 20.0  # Hz
        self.ppg_filter = RealTimeFilter(
            filter_type='bandpass', 
            fs=SAMPLE_RATE, 
            lowcut=self.lowcut_freq, 
            highcut=self.highcut_freq, 
            order=4
        )
        self.pulse_detector = PulseDetector(sample_rate=SAMPLE_RATE)
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
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # === HEADER ===
        self.create_header(main_layout)
        
        # === PANEL DE CONTROL ===
        self.create_control_panel(main_layout)
        
        # === ÁREA DE GRÁFICAS ===
        self.create_plots_area(main_layout)
        
        # === BARRA DE ESTADO ===
        self.create_status_bar(main_layout)
        
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
                border-radius: 12px;
                border-top: 2px solid rgba(200, 255, 220, 0.8);
                border-left: 1px solid rgba(255, 255, 255, 0.6);
                border-right: 1px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.4);
                padding: 8px 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(5)
        
        # Título principal
        title_label = QLabel("ANÁLISIS DE PULSO CARDÍACO")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Arial', 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)
        
        # Subtítulo
        subtitle_label = QLabel("Monitor especializado para señales PPG y frecuencia cardíaca")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                margin-top: 5px;
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_frame)
    
    def create_control_panel(self, main_layout):
        """Crear panel de control con botones"""
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border-radius: 10px;
                border: 1px solid #555555;
                padding: 10px;
            }
        """)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(15)
        
        # Botón Conectar ESP32
        self.btn_connect = QPushButton("🔌 Conectar ESP32")
        self.btn_connect.setFixedSize(150, 45)
        self.btn_connect.setStyleSheet(self.get_button_style("#2196F3"))
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        # Botón Iniciar Adquisición
        self.btn_acquire = QPushButton("▶️ Iniciar Captura")
        self.btn_acquire.setFixedSize(150, 45)
        self.btn_acquire.setStyleSheet(self.get_button_style("#4CAF50"))
        self.btn_acquire.setEnabled(False)
        self.btn_acquire.clicked.connect(self.toggle_acquisition)
        
        # Botón Guardar CSV
        self.btn_save = QPushButton("💾 Guardar CSV")
        self.btn_save.setFixedSize(150, 45)
        self.btn_save.setStyleSheet(self.get_button_style("#FF9800"))
        self.btn_save.clicked.connect(self.save_data_csv)
        
        # Botón Regresar
        self.btn_return = QPushButton("🔙 Regresar")
        self.btn_return.setFixedSize(150, 45)
        self.btn_return.setStyleSheet(self.get_button_style("#9C27B0"))
        self.btn_return.clicked.connect(self.return_to_dashboard_clicked)
        
        # Botón Salir
        self.btn_exit = QPushButton("❌ Salir")
        self.btn_exit.setFixedSize(150, 45)
        self.btn_exit.setStyleSheet(self.get_button_style("#F44336"))
        self.btn_exit.clicked.connect(self.exit_application)
        
        # Agregar botones al layout
        control_layout.addStretch()
        control_layout.addWidget(self.btn_connect)
        control_layout.addWidget(self.btn_acquire)
        control_layout.addWidget(self.btn_save)
        control_layout.addWidget(self.btn_return)
        control_layout.addWidget(self.btn_exit)
        control_layout.addStretch()
        
        main_layout.addWidget(control_frame)
    
    def get_button_style(self, base_color):
        """Generar estilo para botones con color base"""
        # Convertir color hex a RGB para gradientes
        color_variants = {
            "#2196F3": {"light": "#42A5F5", "dark": "#1976D2"},
            "#4CAF50": {"light": "#66BB6A", "dark": "#388E3C"},
            "#FF9800": {"light": "#FFB74D", "dark": "#F57C00"},
            "#9C27B0": {"light": "#BA68C8", "dark": "#7B1FA2"},
            "#F44336": {"light": "#EF5350", "dark": "#D32F2F"}
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
                background-color: #555555;
                border: 2px solid #555555;
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
                border: 2px solid #444444;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(5, 5, 5, 5)
        plots_layout.setSpacing(3)
        
        # Crear las tres gráficas
        self.create_ppg_raw_plot(plots_layout)
        self.create_ppg_filtered_plot(plots_layout)
        self.create_pulse_plot(plots_layout)
        
        main_layout.addWidget(plots_frame)
    
    def create_ppg_raw_plot(self, plots_layout):
        """Crear gráfica de señal PPG cruda"""
        self.ppg_raw_plot = pg.PlotWidget()
        self.ppg_raw_plot.setFixedHeight(140)
        self.ppg_raw_plot.setLabel('left', 'PPG Cruda (ADU)', size='10pt', color='#424242')
        self.ppg_raw_plot.setYRange(-10000, 20000)
        self.ppg_raw_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.ppg_raw_plot.setBackground('#FFFFFF')
        self.ppg_raw_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar ejes
        self.configure_plot_axis(self.ppg_raw_plot)
        
        # Crear curva de datos
        self.ppg_raw_curve = self.ppg_raw_plot.plot(pen=pg.mkPen('#E91E63', width=2))
        
        # Leyenda
        legend = pg.LegendItem(offset=(10, 10), labelTextSize='9pt')
        legend.setParentItem(self.ppg_raw_plot.graphicsItem())
        legend.addItem(self.ppg_raw_curve, "Señal PPG Sin Filtrar")
        legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        
        plots_layout.addWidget(self.ppg_raw_plot)
    
    def create_ppg_filtered_plot(self, plots_layout):
        """Crear gráfica de señal PPG filtrada"""
        self.ppg_filtered_plot = pg.PlotWidget()
        self.ppg_filtered_plot.setFixedHeight(140)
        self.ppg_filtered_plot.setLabel('left', 'PPG Filtrada (ADU)', size='10pt', color='#424242')
        self.ppg_filtered_plot.setYRange(-10000, 20000)
        self.ppg_filtered_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.ppg_filtered_plot.setBackground('#FFFFFF')
        self.ppg_filtered_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar ejes
        self.configure_plot_axis(self.ppg_filtered_plot)
        
        # Crear curva de datos
        self.ppg_filtered_curve = self.ppg_filtered_plot.plot(pen=pg.mkPen('#00A99D', width=2))
        
        # Leyenda
        legend = pg.LegendItem(offset=(10, 10), labelTextSize='9pt')
        legend.setParentItem(self.ppg_filtered_plot.graphicsItem())
        legend.addItem(self.ppg_filtered_curve, f"Señal PPG Filtrada ({self.lowcut_freq}-{self.highcut_freq}Hz)")
        legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        
        plots_layout.addWidget(self.ppg_filtered_plot)
    
    def create_pulse_plot(self, plots_layout):
        """Crear gráfica de pulso calculado"""
        self.pulse_plot = pg.PlotWidget()
        self.pulse_plot.setFixedHeight(160)
        self.pulse_plot.setLabel('left', 'Frecuencia (BPM)', size='10pt', color='#424242')
        self.pulse_plot.setLabel('bottom', 'Tiempo (s)', size='10pt', color='#424242')
        self.pulse_plot.setYRange(40, 130)
        self.pulse_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        
        # Configurar estilo
        self.pulse_plot.setBackground('#FFFFFF')
        self.pulse_plot.showGrid(x=True, y=True, alpha=0.2)
        
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
        self.bpm_text.setPos(-DISPLAY_TIME + 0.5, 135)
        self.pulse_plot.addItem(self.bpm_text)
        
        # Leyenda
        legend = pg.LegendItem(offset=(10, 10), labelTextSize='9pt')
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
    
    def create_status_bar(self, main_layout):
        """Crear barra de estado"""
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 5, 15, 5)
        
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
        self.sample_rate_label = QLabel("📊 Tasa: 0.0 Hz")
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
        
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.capture_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.sample_rate_label)
        status_layout.addStretch()
        status_layout.addWidget(self.sample_count_label)
        
        main_layout.addWidget(status_frame)
    
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
                    border-radius: 4px;
                    padding: 5px;
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
            self.pulse_detector = PulseDetector(sample_rate=SAMPLE_RATE)
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
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            
            # Iniciar captura en ESP32
            Devices.start_sensor()
            
            # Cambiar estado
            self.acquiring = True
            self.sample_count = 0
            self.last_sample_time = time.time()
            
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
        
        # Limpiar datos CSV
        for key in self.csv_data:
            self.csv_data[key] = []
        
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
            # eog_value = struct.unpack('<h', packet_data[12:14])[0]  # No usado en esta ventana
            device_id = packet_data[14]
            
            # Aplicar filtro PPG
            ppg_filtered = self.ppg_filter.filter(ppg_raw)
            
            # Detectar pulso
            pulse_detected, pulse_state = self.pulse_detector.add_sample(ppg_filtered, timestamp_s)
            
            if pulse_detected:
                self.current_heart_rate = self.pulse_detector.get_heart_rate()
            
            # Actualizar buffers de visualización
            self.times.append(timestamp_s)
            self.ppg_raw_values.append(ppg_raw)
            self.ppg_filtered_values.append(ppg_filtered)
            self.pulse_values.append(self.current_heart_rate)
            
            # Guardar datos para CSV
            self.csv_data['timestamp'].append(timestamp_ms)
            self.csv_data['ppg_raw'].append(ppg_raw)
            self.csv_data['ppg_filtered'].append(ppg_filtered)
            self.csv_data['pulse_bpm'].append(self.current_heart_rate)
            self.csv_data['pulse_detected'].append(1 if pulse_detected else 0)
            
            return True
            
        except Exception as e:
            print(f"Error procesando paquete: {e}")
            return False
    
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
            
            # Actualizar texto de BPM
            hr_str = f"BPM: {int(self.current_heart_rate)}" if self.current_heart_rate > 0 else "BPM: --"
            self.bpm_text.setText(hr_str)
            
            # Cambiar color según rango
            if 60 <= self.current_heart_rate <= 100:
                self.bpm_text.setColor((76, 175, 80))
            elif self.current_heart_rate > 100:
                self.bpm_text.setColor((255, 152, 0))
            else:
                self.bpm_text.setColor((100, 100, 100))
        
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
        self.sample_rate_label.setText(f"📊 Tasa: {self.current_sample_rate:.1f} Hz")
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
            
            # Crear DataFrame
            df = pd.DataFrame(self.csv_data)
            
            # Crear directorio si no existe
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = data_dir / f"pulse_test_data_{timestamp}.csv"
            
            # Guardar archivo
            df.to_csv(filename, index=False)
            
            self.show_message("Datos Guardados", 
                            f"Los datos se han guardado exitosamente.\n\n"
                            f"Archivo: {filename.name}\n"
                            f"Muestras: {len(df)}", 
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
    window.show()
    
    sys.exit(app.exec())
