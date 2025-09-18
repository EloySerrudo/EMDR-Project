import sys
import numpy as np
import struct
import threading
import time
import os
from collections import deque
import pandas as pd
from datetime import datetime
from scipy import signal

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
import pyqtgraph as pg
import qtawesome as qta

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para gestión de dispositivos
from src.models.devices import Devices, KNOWN_SLAVES

# Importación del filtro en tiempo real
from src.utils.signal_processing import OnlinePPGFilter, OnlineEOGFilter, PPGHeartRateCalculator

# Configuración constantes
SAMPLE_RATE = 125  # Hz (tasa efectiva: 250 SPS ÷ 2 canales)
DISPLAY_TIME = 5   # Segundos de datos a mostrar en la gráfica
GRAPH_PADDING = 0.01  # Espacio entre el borde de la gráfica y los datos
BUFFER_SIZE = 512  # Tamaño máximo de buffer

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 15        # Tamaño en bytes de cada paquete

class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)
    
class SensorMonitor(QWidget):
    def __init__(self, display_time=DISPLAY_TIME, parent=None):
        super().__init__(parent)
        
        # Ya no necesitamos configuración de puerto y baudrate
        self.running = False
        self.reading_thread = None
        
        # Flag para indicar si estamos cerrando
        self.is_closing_flag = False
        
        # Si parent es QMainWindow , es una app independiente
        self.is_standalone = isinstance(parent, QMainWindow)
        
        # Data storage for display
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Initialize deques with zeros
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        
        # Buffers para EOG
        self.eog_values = deque(initial_values, maxlen=self.display_size)
        self.filtered_eog_values = deque(initial_values, maxlen=self.display_size)
        
        # Buffers para PPG
        self.ppg_values = deque(initial_values, maxlen=self.display_size)
        self.filtered_ppg_values = deque(initial_values, maxlen=self.display_size)
        
        # Datos para CSV
        self.csv_data = {
            'index': [],
            'timestamp': [],
            'eog_raw': [],
            'ppg_raw': [],
            'pulse_bpm': [],
        }
        
        # Filtros para ambas señales
        self.eog_filter = OnlineEOGFilter(
            fs=SAMPLE_RATE, 
            hp_cutoff=0.05,     # Conserva movimientos oculares lentos
            lp_cutoff=30.0,     # Banda útil para EOG
            notch_freq=50,      # Elimina interferencia de 50Hz
            notch_q=30,         # Factor de calidad del notch
            fir_taps=101        # Filtro FIR con fase lineal
        )
        self.ppg_filter = OnlinePPGFilter(
            filter_type='bandpass', 
            fs=SAMPLE_RATE, 
            lowcut=0.2,     # 0.5 Hz 
            highcut=10.0, 
            order=4
        )
        
        # Añadir detector de pulsos y variables para BPM
        self.bpm_calculator = PPGHeartRateCalculator(sample_rate=SAMPLE_RATE)
        self.current_heart_rate = 0
        self.bpm_values = deque(initial_values, maxlen=self.display_size)
        self.bpm_datos = []  # Para almacenar BPM para CSV
        self.last_packet_id = -1  # Para detectar paquetes duplicados
        
        # Variables para control del LED de pulsaciones
        self.led_is_active = False
        
        # Slave device tracking
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        self.slave_count = 0
        self.connection_thread = None
        self.signals = SignalsObject()
        self.signals.device_status_updated.connect(self.update_device_status)
        
        # Setup UI
        self.setup_ui(display_time)
    
    def setup_ui(self, display_time):
        """Configura la interfaz de usuario del monitor"""
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(5)
        
        # ===== HEADER CON CONTROLES =====
        if self.is_standalone:
            header_frame = QFrame()
            header_frame.setFrameShape(QFrame.StyledPanel)
            header_frame.setStyleSheet("""
                QFrame {
                    background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                            stop: 0 rgba(120, 255, 180, 0.3),
                                            stop: 0.5 rgba(0, 169, 157, 0.4),
                                            stop: 1 rgba(120, 255, 180, 0.3));
                    border-radius: 8px;
                    border: 1px solid rgba(0, 140, 130, 0.6);
                    padding: 8px;
                    margin: 2px;
                }
            """)
            header_layout = QHBoxLayout(header_frame)
            header_layout.setContentsMargins(10, 6, 10, 6)
            
            # Título del monitor
            title_label = QLabel("MONITOR DE BIOSEÑALES")
            title_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: bold;
                    background: transparent;
                    padding: 4px;
                }
            """)
            header_layout.addWidget(title_label)
            
            header_layout.addStretch()
            
            # Botón de escaneo de dispositivos
            scan_btn = QPushButton("Escanear")
            scan_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #9C27B0,
                                            stop: 1 #7B1FA2);
                    color: white;
                    border: 2px solid #7B1FA2;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #AB47BC,
                                            stop: 1 #9C27B0);
                    border: 2px solid #9C27B0;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #7B1FA2,
                                            stop: 1 #6A1B9A);
                    border: 2px solid #6A1B9A;
                }
            """)
            scan_btn.clicked.connect(self.check_slave_connections)
            header_layout.addWidget(scan_btn)
            
            # Botón de control de adquisición con estilo moderno
            self.btn_start_stop = QPushButton("Iniciar Adquisición")
            self.btn_start_stop.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #66BB6A,
                                            stop: 1 #4CAF50);
                    color: white;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #81C784,
                                            stop: 1 #66BB6A);
                    border: 2px solid #66BB6A;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #4CAF50,
                                            stop: 1 #388E3C);
                    border: 2px solid #388E3C;
                }
                QPushButton:disabled {
                    background-color: #555555;
                    border: 2px solid #555555;
                    color: #888888;
                }
            """)
            self.btn_start_stop.clicked.connect(self.toggle_acquisition)
            header_layout.addWidget(self.btn_start_stop)
            
            # Botón para guardar datos
            save_btn = QPushButton("Guardar CSV")
            save_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #42A5F5,
                                            stop: 1 #2196F3);
                    color: white;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #64B5F6,
                                            stop: 1 #42A5F5);
                    border: 2px solid #42A5F5;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #2196F3,
                                            stop: 1 #1976D2);
                    border: 2px solid #1976D2;
                }
            """)
            save_btn.clicked.connect(self.save_data_to_csv)
            header_layout.addWidget(save_btn)
            
            self.main_layout.addWidget(header_frame)
        
        # ===== ÁREA DE PULSACIONES =====
        pulse_monitor_frame = QFrame()
        pulse_monitor_frame.setFrameShape(QFrame.StyledPanel)
        pulse_monitor_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 rgba(0, 169, 157, 0.2),
                                          stop: 0.5 rgba(0, 200, 170, 0.25),
                                          stop: 1 rgba(0, 169, 157, 0.2));
                border-radius: 12px;
                border: 2px solid rgba(0, 200, 170, 0.4);
                padding: 0px;
                margin: 0px;
            }
        """)
        pulse_monitor_frame.setFixedHeight(50)
        
        pulse_layout = QHBoxLayout(pulse_monitor_frame)
        pulse_layout.setContentsMargins(15, 2, 15, 2)
        pulse_layout.setSpacing(15)
        
        # ===== SECCIÓN IZQUIERDA: ESTADO DE PULSACIONES =====
        left_section = QHBoxLayout()
        left_section.setSpacing(0)
        
        # # Texto "Pulsaciones"
        # pulse_label = QLabel("Pulsaciones:")
        # pulse_label.setStyleSheet("""
        #     QLabel {
        #         color: #FFFFFF;
        #         font-size: 14px;
        #         font-weight: bold;
        #         background: transparent;
        #         min-height: 16px;
        #         max-height: 16px;
        #         border: none;
        #     }
        # """)
        # left_section.addWidget(pulse_label)
        
        # # LED en forma de corazón simulado para pulsaciones
        # self.pulse_led = QLabel()
        # self.pulse_led.setFixedSize(42, 42)
        # self.pulse_led.setPixmap(qta.icon('fa5s.heart', color="#00C8AA00").pixmap(40, 40))
        # self.pulse_led.setStyleSheet("""
        #     QLabel {
        #         background: transparent;
        #         border-radius: 0px;
        #         border: none;
        #         padding: 0px;
        #     }
        # """)
        # self.pulse_led.setAlignment(Qt.AlignCenter)
        # left_section.addWidget(self.pulse_led)
        
        # ===== SEPARADOR VISUAL =====
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: rgba(255, 255, 255, 0.3);
                background-color: rgba(255, 255, 255, 0.3);
                border: none;
                max-width: 2px;
                min-height: 40px;
                margin: 0px 10px;
            }
        """)
        
        # ===== SECCIÓN DERECHA: FRECUENCIA CARDÍACA =====
        right_section = QHBoxLayout()
        right_section.setSpacing(4)
        
        # Label estático para "Pulsaciones / min:"
        pulse_rate_static_label = QLabel("Pulsaciones / min:")
        pulse_rate_static_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                min-height: 16px;
                max-height: 16px;
                border: none;
            }
        """)
        right_section.addWidget(pulse_rate_static_label)
        
        # Label dinámico para el valor de BPM
        self.pulse_rate_value_label = QLabel("--")
        self.pulse_rate_value_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 20px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 rgba(33, 150, 243, 0.3),
                                          stop: 0.5 rgba(63, 169, 245, 0.4),
                                          stop: 1 rgba(33, 150, 243, 0.3));
                border: 2px solid rgba(63, 169, 245, 0.5);
                border-radius: 8px;
                padding: 4px 12px;
                min-width: 45px;
                max-width: 70px;
            }
        """)
        self.pulse_rate_value_label.setAlignment(Qt.AlignCenter)
        right_section.addWidget(self.pulse_rate_value_label)
        
        pulse_layout.addStretch()
        pulse_layout.addLayout(left_section)
        pulse_layout.addWidget(separator)
        pulse_layout.addLayout(right_section)
        pulse_layout.addStretch()

        self.main_layout.addWidget(pulse_monitor_frame)
        
        # Variables para control del LED
        self.led_timer = QTimer()
        self.led_timer.timeout.connect(self.reset_led)
        self.led_is_active = False
        
        # ===== ÁREA DE GRÁFICAS =====
        # Frame contenedor para las gráficas con estilo moderno
        plots_frame = QFrame()
        plots_frame.setFrameShape(QFrame.StyledPanel)
        plots_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 2px solid #444444;
                border-radius: 0px;
                margin: 0px;
                padding: -2px;
            }
        """)
        # ===== CREAR LAYOUT ESPECÍFICO PARA LAS GRÁFICAS =====
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(2, 2, 2, 2)
        plots_layout.setSpacing(2)
        
        GRAPH_HEIGHT = 122  # Altura uniforme para todas las gráficas
        
        # Crear gráficas individuales
        if self.is_standalone:
            self.ppg_plot = self.create_ppg_plot(display_time, height=GRAPH_HEIGHT)
        self.bpm_plot = self.create_bpm_plot(display_time, height=GRAPH_HEIGHT)
        self.eog_plot = self.create_eog_plot(display_time, height=GRAPH_HEIGHT + 25)
        
        if self.is_standalone:
            plots_layout.addWidget(self.ppg_plot)
        plots_layout.addWidget(self.bpm_plot)
        plots_layout.addWidget(self.eog_plot)
        # plots_layout.addStretch()
        
        # ===== CREAR CURVAS DE DATOS =====
        self.create_data_curves()
        
        # ===== AÑADIR LEYENDAS Y ELEMENTOS ADICIONALES =====
        self.add_legends_and_extras(display_time)
        
        # Añadir plots a main layout
        self.main_layout.addWidget(plots_frame)
        
        # ===== BARRA DE ESTADO =====
        if self.is_standalone:
            status_frame = QFrame()
            status_frame.setFrameShape(QFrame.StyledPanel)
            status_frame.setStyleSheet("""
                QFrame {
                    background-color: #424242;
                    border: 2px solid #555555;
                    border-radius: 8px;
                    padding: 6px;
                    margin: 2px;
                }
            """)
            status_layout = QHBoxLayout(status_frame)
            status_layout.setContentsMargins(10, 4, 10, 4)
            
            # Labels de estado con estilo moderno
            self.device_status_label = QLabel("Estado: Esperando conexión...")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }
            """)
            status_layout.addWidget(self.device_status_label)
            
            status_layout.addStretch()
            
            self.samples_label = QLabel("Muestras: 0")
            self.samples_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }
            """)
            status_layout.addWidget(self.samples_label)
            
            self.rate_label = QLabel("Tasa: 0 Hz")
            self.rate_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }
            """)
            status_layout.addWidget(self.rate_label)
            
            self.main_layout.addWidget(status_frame)
        
        # Configurar timer para actualización de gráficas
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # 20 FPS
    
    def configure_y_axis_spacing(self, plot_widget, label_text, axis_width=35):
        """Configurar el espaciado del eje Y de forma consistente"""
        y_axis = plot_widget.getAxis('left')
        
        # Reducir ancho del eje
        y_axis.setWidth(axis_width)
        
        # Configurar estilo del eje con colores del tema
        y_axis.setStyle(
            tickTextOffset=3,
            autoExpandTextSpace=False,
            tickTextHeight=12
        )
        
        # Configurar colores del eje
        y_axis.setPen(pg.mkPen('#424242', width=1))
        y_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar el label con estilo moderno
        plot_widget.setLabel('left', label_text, size='10pt', color='#424242')
        
        return y_axis

    def create_eog_plot(self, display_time, height):
        """Crear y configurar la gráfica EOG con estilo moderno"""
        eog_plot = pg.PlotWidget()
        eog_plot.setFixedHeight(height)
        eog_plot.setLabel('bottom', 'Tiempo (s)', size='10pt', color='#424242')
        eog_plot.setYRange(-20000, 16000)
        eog_plot.setXRange(-display_time, 0, padding=GRAPH_PADDING)
        
        # Aplicar tema moderno
        eog_plot.setBackground('#FFFFFF')
        eog_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar ejes con estilo moderno
        y_axis = eog_plot.getAxis('left')
        y_axis.setStyle(showValues=False)

        x_axis = eog_plot.getAxis('bottom')
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # ===== AÑADIR CONFIGURACIÓN PARA REDUCIR ESPACIADO DEL EJE X =====
        x_axis.setStyle(
            tickTextOffset=2,      # Reducir distancia entre ticks y valores numéricos
            autoExpandTextSpace=False,  # No expandir automáticamente
            tickTextHeight=10      # Reducir altura del área de texto
        )
        x_axis.setHeight(25)       # Reducir altura total del eje X (valor por defecto ~40)
    
        # Configurar eje Y con espaciado personalizado
        self.configure_y_axis_spacing(eog_plot, 'EOG', axis_width=35)
        
        # Estilo del área de ploteo
        plot_item = eog_plot.getPlotItem()
        plot_item.getViewBox().setDefaultPadding(GRAPH_PADDING)
        
        # Configurar líneas de grilla con colores suaves
        plot_item.getAxis('bottom').setGrid(200)
        plot_item.getAxis('left').setGrid(200)
        
        return eog_plot

    def create_bpm_plot(self, display_time, height):
        """Crear y configurar la gráfica BPM con estilo moderno"""
        bpm_plot = pg.PlotWidget()
        bpm_plot.setFixedHeight(height)
        bpm_plot.setLabel('bottom', '')
        bpm_plot.setYRange(50, 120)
        bpm_plot.setXRange(-display_time, 0, padding=GRAPH_PADDING)
        
        # Aplicar tema moderno
        bpm_plot.setBackground('#FFFFFF')
        bpm_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar eje X con estilo moderno
        x_axis = bpm_plot.getAxis('bottom')
        x_axis.setStyle(showValues=False)
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar eje Y con espaciado personalizado
        self.configure_y_axis_spacing(bpm_plot, 'BPM', axis_width=35)
        
        # Estilo del área de ploteo
        plot_item = bpm_plot.getPlotItem()
        plot_item.getViewBox().setDefaultPadding(GRAPH_PADDING)
        
        # Configurar líneas de grilla con colores suaves
        plot_item.getAxis('bottom').setGrid(200)
        plot_item.getAxis('left').setGrid(200)
        
        # Añadir líneas de referencia para rangos normales de BPM
        reference_line_60 = pg.InfiniteLine(
            pos=60, 
            angle=0, 
            pen=pg.mkPen('#4CAF50', width=1, style=pg.QtCore.Qt.DashLine)
        )
        reference_line_100 = pg.InfiniteLine(
            pos=100, 
            angle=0, 
            pen=pg.mkPen('#FF9800', width=1, style=pg.QtCore.Qt.DashLine)
        )
        bpm_plot.addItem(reference_line_60)
        bpm_plot.addItem(reference_line_100)
        
        return bpm_plot

    def create_ppg_plot(self, display_time, height):
        """Crear y configurar la gráfica PPG con estilo moderno"""
        ppg_plot = pg.PlotWidget()
        ppg_plot.setFixedHeight(height)
        ppg_plot.setLabel('bottom', '')
        ppg_plot.setYRange(-20000, 40000)
        ppg_plot.setXRange(-display_time, 0, padding=GRAPH_PADDING)
        
        # Aplicar tema moderno
        ppg_plot.setBackground('#FFFFFF')
        ppg_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar eje X con estilo moderno
        x_axis = ppg_plot.getAxis('bottom')
        x_axis.setStyle(showValues=False)
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar eje Y con espaciado personalizado
        self.configure_y_axis_spacing(ppg_plot, 'PPG (ADU)', axis_width=60)
        
        # Estilo del área de ploteo
        plot_item = ppg_plot.getPlotItem()
        plot_item.getViewBox().setDefaultPadding(GRAPH_PADDING)
        
        # Configurar líneas de grilla con colores suaves
        plot_item.getAxis('bottom').setGrid(200)
        plot_item.getAxis('left').setGrid(200)
        
        return ppg_plot

    def create_data_curves(self):
        """Crear las curvas de datos con colores consistentes del tema"""
        # Curvas con colores del tema login y líneas optimizadas
        self.eog_curve = self.eog_plot.plot(pen=pg.mkPen('#2196F3', width=2))  # Azul principal
        self.bpm_curve = self.bpm_plot.plot(pen=pg.mkPen('#FF9800', width=2))  # Naranja para BPM
        if self.is_standalone:
            self.ppg_curve = self.ppg_plot.plot(pen=pg.mkPen('#00A99D', width=2))  # Verde tema principal
    
    def add_legends_and_extras(self, display_time):
        """Añadir leyendas y elementos adicionales con estilo moderno"""
        # Leyenda para EOG con estilo moderno
        eog_legend = pg.LegendItem(
            offset=(75, 10), 
            labelTextSize='9pt',
            spacing=0,      # Sin espaciado extra
            rowSpacing=0,   # Sin espaciado entre filas
            colSpacing=0    # Mínimo espaciado entre ícono y texto
        )
        eog_legend.setParentItem(self.eog_plot.graphicsItem())
        eog_legend.addItem(self.eog_curve, "Movimiento Ocular")
        eog_legend.setBrush(pg.mkBrush(255, 255, 255, 200))  # Fondo semi-transparente
        eog_legend.layout.setContentsMargins(0, 0, 0, 0)  # izq, arr, der, aba
        eog_legend.layout.setSpacing(0)  # Espaciado entre elementos
        eog_legend.setGeometry(pg.QtCore.QRectF(0, 0, 134, 14))  # Tamaño fijo
        
        # Texto para mostrar el valor de BPM actual con estilo moderno
        self.bpm_text = pg.TextItem(
            text="BPM: --", 
            color=(150, 150, 150),  # Color #969696
            anchor=(0, 0),
            fill=pg.mkBrush(255, 255, 255, 200)
        )
        self.bpm_text.setPos(-3.5, 116)
        self.bpm_plot.addItem(self.bpm_text)
        
        # Leyenda para BPM con estilo moderno
        bpm_legend = pg.LegendItem(
            offset=(75, 10), 
            labelTextSize='9pt', 
            spacing=0, 
            rowSpacing=0, 
            colSpacing=0
        )
        bpm_legend.setParentItem(self.bpm_plot.graphicsItem())
        bpm_legend.addItem(self.bpm_curve, "Frecuencia Cardíaca")
        bpm_legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        bpm_legend.layout.setContentsMargins(0, 0, 0, 0)
        bpm_legend.layout.setSpacing(0)
        bpm_legend.setGeometry(pg.QtCore.QRectF(0, 0, 137, 14))
        
        # Leyenda para PPG con estilo moderno
        if self.is_standalone:
            ppg_legend = pg.LegendItem(
                offset=(75, 10), 
                labelTextSize='9pt', 
                spacing=0, 
                rowSpacing=0, 
                colSpacing=0
            )
            ppg_legend.setParentItem(self.ppg_plot.graphicsItem())
            ppg_legend.addItem(self.ppg_curve, "Señal PPG")
            ppg_legend.setBrush(pg.mkBrush(255, 255, 255, 200))
            ppg_legend.layout.setContentsMargins(0, 0, 0, 0)
            ppg_legend.layout.setSpacing(0)
            # ppg_legend.setPen(pg.mkPen('#CCCCCC', width=1))
            ppg_legend.setGeometry(pg.QtCore.QRectF(0, 0, 85, 14))

    def toggle_acquisition(self):
        """Toggle between start and stop acquisition"""
        if self.running:
            self.stop_acquisition()
            self.btn_start_stop.setText("Iniciar Adquisición")
            self.btn_start_stop.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #66BB6A,
                                               stop: 1 #4CAF50);
                    color: white;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #81C784,
                                               stop: 1 #66BB6A);
                    border: 2px solid #66BB6A;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #4CAF50,
                                               stop: 1 #388E3C);
                    border: 2px solid #388E3C;
                }
            """)
        else:
            self.start_acquisition()
            self.btn_start_stop.setText("Detener Adquisición")
            self.btn_start_stop.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #EF5350,
                                               stop: 1 #F44336);
                    color: white;
                    border: 2px solid #F44336;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #E57373,
                                               stop: 1 #EF5350);
                    border: 2px solid #EF5350;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #F44336,
                                               stop: 1 #D32F2F);
                    border: 2px solid #D32F2F;
                }
            """)

    def start_acquisition(self):
        """Start data acquisition"""
        # Verificar que el controlador maestro esté conectado
        if not Devices.master_plugged_in() or self.running:
            print("No hay conexión con el controlador maestro o ya está adquiriendo datos")
            return
        
        if not self.required_devices_connected:
            print("\nNo se puede iniciar la adquisición: dispositivos requeridos no conectados.")
            print("Use el botón 'Escanear Dispositivos' para verificar conexiones.\n")
            return
        
        # Reset filter
        self.eog_filter.reset()
        self.ppg_filter.reset()
        self.last_packet_id = -1
        
        # Crear una nueva instancia:
        self.bpm_calculator = PPGHeartRateCalculator(sample_rate=SAMPLE_RATE)
        self.current_heart_rate = 0
        
        # Reset LED estado
        self.led_is_active = False
        
        # Clear and reset data buffers
        self.times.clear()
        self.eog_values.clear()
        self.filtered_eog_values.clear()
        self.ppg_values.clear()
        self.filtered_ppg_values.clear()
        self.bpm_values.clear()  # Limpiar buffer de BPM
        
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        self.times.extend(initial_times)
        self.eog_values.extend(initial_values)
        self.filtered_eog_values.extend(initial_values)
        self.ppg_values.extend(initial_values)
        self.filtered_ppg_values.extend(initial_values)
        self.bpm_values.extend(initial_values)  # Inicializar buffer de BPM
        
        # Limpiar datos previos
        self.csv_data = {
            'index': [],
            'timestamp': [],
            'eog_raw': [],
            'ppg_raw': [],
            'pulse_bpm': [],
        }
        
        # Send command to ESP32 to start capture usando Devices
        Devices.start_sensor()
        
        # Start capture
        self.running = True
        
        # GUARDAR TIMESTAMP DE INICIO UNA SOLA VEZ
        self.start_datetime = datetime.now()

        # Start reading thread
        self.reading_thread = threading.Thread(target=self._read_data)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        print("Adquisición iniciada")

    def stop_acquisition(self):
        """Stop data acquisition"""
        if Devices.master_plugged_in() and self.running:
            # Send command to ESP32 to stop capture
            Devices.stop_sensor()
            
            # Stop capture
            self.running = False
            if self.reading_thread:
                self.reading_thread.join(timeout=1.0)
            print("Adquisición detenida")

    def _find_packet_start(self, buffer):
        """Find the start of a packet in the buffer"""
        if len(buffer) < 2:
            return -1
            
        for i in range(len(buffer) - 1):
            # Look for the header byte sequence (Little Endian: 0x55, 0xAA)
            if buffer[i] == (PACKET_HEADER & 0xFF) and buffer[i + 1] == (PACKET_HEADER >> 8) & 0xFF:
                return i
                
        return -1

    def check_slave_connections(self):
        """Send command to check for connected slaves"""
        # Escanear dispositivos usando Devices
        found_devices = Devices.probe()
        
        if not found_devices:
            print("No se encontraron dispositivos")
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(244, 67, 54, 0.8);
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            return
            
        if "Master Controller" not in found_devices:
            print("No se encontró el controlador maestro")
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(244, 67, 54, 0.8);
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            return
            
        print("Verificando dispositivos conectados...")
        
        # Reset connection status
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        
        # Update status from found devices
        status_dict = {}
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            is_connected = name in found_devices
            self.slave_status[slave_id] = is_connected
            status_dict[slave_id] = is_connected
            
        # Check for required devices
        required_connected = all(
            self.slave_status.get(slave_id, False) 
            for slave_id, (_, required) in KNOWN_SLAVES.items() 
            if required
        )
        
        self.required_devices_connected = required_connected
        self.signals.device_status_updated.emit(status_dict, required_connected)
        self._print_connection_status()
    
    def update_device_status(self, status_dict, required_connected):
        """Update the device status UI - called from main thread"""
        self.required_devices_connected = required_connected
        
        # Update status label
        status_text = "Estado de dispositivos: "
        for slave_id, connected in status_dict.items():
            name, required = KNOWN_SLAVES.get(slave_id, ("Desconocido", False))
            status = "CONECTADO" if connected else "DESCONECTADO"
            req = " (Requerido)" if required else ""
            status_text += f"{name}{req}: {status} | "
        
        self.device_status_label.setText(status_text.rstrip(" | "))
        
        # Change background color based on connection status with modern styling
        if required_connected:
            self.device_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(76, 175, 80, 0.8);
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
        else:
            self.device_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: rgba(244, 67, 54, 0.8);
                    border-radius: 4px;
                    padding: 5px;
                }
            """)

    def _print_connection_status(self):
        """Print connection status to terminal"""
        print("\n--- Estado de conexión de esclavos ---")
        
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            connected = self.slave_status.get(slave_id, False)
            status = "CONECTADO" if connected else "DESCONECTADO"
            req_text = "(Requerido)" if required else "(Opcional)"
            print(f"Esclavo ID:{slave_id} - {name} {req_text}: {status}")
        
        print("-------------------------------------\n")
        
        if self.required_devices_connected:
            print("Todos los dispositivos requeridos están conectados.\n")
        else:
            print("ADVERTENCIA: Uno o más dispositivos requeridos no están conectados.")
            print("La adquisición de datos está deshabilitada hasta que todos los dispositivos requeridos estén conectados.\n")

    def _read_data(self):
        """Function that runs in a separate thread to read binary data"""
        data_buffer = bytearray()
        serial_conn = Devices.get_master_connection()  # Obtener la conexión serial del controlador maestro
        
        if not serial_conn:
            print("No hay conexión serial disponible")
            self.running = False
            return
        
        while self.running:
            try:
                # Read available data
                available = serial_conn.in_waiting
                
                if available > 0:
                    # Read available data
                    new_data = serial_conn.read(min(available, BUFFER_SIZE * PACKET_SIZE))
                    data_buffer.extend(new_data)
                    
                    # Process while we have enough data for a complete packet
                    while len(data_buffer) >= PACKET_SIZE:
                        # Look for packet start
                        packet_start = self._find_packet_start(data_buffer)
                        
                        if packet_start < 0:
                            # No valid header found, keep only the last byte
                            if len(data_buffer) > 1:
                                data_buffer = data_buffer[-1:]
                            break
                            
                        # If packet doesn't start at buffer beginning, discard preceding bytes
                        if packet_start > 0:
                            data_buffer = data_buffer[packet_start:]
                            
                        # Check if we have a complete packet
                        if len(data_buffer) < PACKET_SIZE:
                            break
                            
                        # Extract packet data
                        try:
                            # Header (2 bytes)
                            header = struct.unpack('<H', data_buffer[0:2])[0]
                            
                            if header == PACKET_HEADER:
                                # ID (4 bytes)
                                packet_id = struct.unpack('<I', data_buffer[2:6])[0]
                                
                                # Check for duplicate packets
                                if packet_id <= self.last_packet_id:
                                    self.duplicate_packets += 1
                                    # Remove processed packet from buffer and continue
                                    data_buffer = data_buffer[PACKET_SIZE:]
                                    continue
                                
                                # Update last processed ID
                                self.last_packet_id = packet_id
                                
                                # Timestamp (4 bytes)
                                timestamp_ms = struct.unpack('<I', data_buffer[6:10])[0]
                                timestamp_s = timestamp_ms / 1000.0  # Convert to seconds
                                
                                # PPG crudo (2 bytes) en data_buffer[10:12]
                                ppg_raw = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # EOG crudo (2 bytes) en data_buffer[12:14]
                                eog_raw = struct.unpack('<h', data_buffer[12:14])[0]
                                
                                # Device ID (1 byte) is at position 14
                                device_id = data_buffer[14]
                                
                                # Apply real-time filters
                                ppg_filtered = self.ppg_filter.filter(ppg_raw)
                                eog_filtered = self.eog_filter.filter(eog_raw)
                                
                                # Calcular BPM
                                result = self.bpm_calculator.add_sample(ppg_filtered, timestamp_s)
                                
                                # Actualizar BPM
                                self.current_heart_rate = result['bpm'] if result['bpm'] is not None else 0
                                
                                # Actualizar buffers de visualización
                                self.times.append(timestamp_s)
                                
                                # PPG data (para procesamiento y datos crudos)
                                self.ppg_values.append(ppg_raw)
                                self.filtered_ppg_values.append(ppg_filtered)
                                
                                # EOG data
                                self.eog_values.append(eog_raw)
                                self.filtered_eog_values.append(eog_filtered)
                                
                                # BPM data
                                pulse_display_value = self.current_heart_rate if self.current_heart_rate else 0
                                self.bpm_values.append(pulse_display_value)
                                
                                # Guardar datos para CSV
                                self.csv_data['index'].append(packet_id)
                                self.csv_data['timestamp'].append(timestamp_ms)
                                self.csv_data['eog_raw'].append(eog_raw)
                                self.csv_data['ppg_raw'].append(ppg_raw)
                                self.csv_data['pulse_bpm'].append(pulse_display_value)
                            else:
                                # Invalid header, discard initial byte and continue
                                data_buffer = data_buffer[1:]
                                continue
                                
                            # Remove processed packet from buffer
                            data_buffer = data_buffer[PACKET_SIZE:]
                        except Exception as e:
                            print(f"Error processing packet: {e}")
                            # On error, discard initial byte and continue
                            data_buffer = data_buffer[1:]
                
                # Small pause to not saturate CPU
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error reading data: {e}")
                time.sleep(0.1)  # Longer pause on error

    def update_plot(self):
        """Actualizar las gráficas"""
        if len(self.times) > 0:
            # Convert deques to numpy arrays for plotting
            x_data = np.array(self.times)
            
            # Datos para mostrar
            filtered_ppg_data = np.array(self.filtered_ppg_values)
            bpm_data = np.array(self.bpm_values)
            filtered_eog_data = np.array(self.filtered_eog_values)
            
            if self.running:
                # Normalizar los tiempos para que siempre estén entre -5 y 0
                current_time = x_data[-1]
                normalized_x = x_data - current_time  # El tiempo actual será 0, los anteriores negativos
            else:
                # Si está detenido, mantener la última normalización
                normalized_x = x_data
                
            # Update plot data con los tiempos normalizados
            self.eog_curve.setData(normalized_x, filtered_eog_data)
            self.bpm_curve.setData(normalized_x, bpm_data)
            if self.is_standalone:
                self.ppg_curve.setData(normalized_x, filtered_ppg_data)
            
            # Actualizar el texto de BPM con estilo mejorado
            hr_str = f"BPM: {int(self.current_heart_rate)}" if self.current_heart_rate > 0 else "BPM: --"
            if hasattr(self, 'bpm_text'):
                self.bpm_text.setText(hr_str)
                # Cambiar color según el rango de BPM
                if 60 <= self.current_heart_rate <= 100:
                    self.bpm_text.setColor((76, 175, 80))  # Verde para normal
                elif self.current_heart_rate > 100:
                    self.bpm_text.setColor((255, 152, 0))  # Naranja para elevado
                else:
                    self.bpm_text.setColor((66, 66, 66))   # Gris para otros casos
            
            # Detectar picos para activar LED y actualizar display de pulsaciones
            if self.running and len(filtered_ppg_data) > 0:
                current_time = time.time()
                self.detect_pulse_peaks(self.filtered_ppg_values, current_time)
                self.update_pulse_rate_display(self.current_heart_rate)
        
        # Fijar siempre el rango X entre -5 y 0
        self.eog_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        self.bpm_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        if self.is_standalone:
            self.ppg_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)

    def save_data_to_csv(self):
        """Save collected data to CSV file with modern dialog"""
        try:
            if not any(self.csv_data.values()) or len(self.csv_data['index']) == 0:
                print("No hay datos para guardar")
                # Mostrar mensaje con estilo moderno
                msg = QMessageBox(self)
                msg.setWindowTitle("Sin Datos")
                msg.setText("No hay datos para guardar.")
                msg.setInformativeText("Inicie la adquisición de datos primero.")
                msg.setIcon(QMessageBox.Warning)
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #F8F9FA;
                        font-family: 'Segoe UI', Arial, sans-serif;
                    }
                    QMessageBox QLabel {
                        color: #424242;
                        font-size: 13px;
                    }
                    QMessageBox QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                   stop: 0 #42A5F5,
                                                   stop: 1 #2196F3);
                        color: white;
                        border: 2px solid #2196F3;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                    }
                    QMessageBox QPushButton:hover {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                   stop: 0 #64B5F6,
                                                   stop: 1 #42A5F5);
                    }
                """)
                msg.exec()
                return
                
            # Crear DataFrame directamente con el diccionario modificado
            df = pd.DataFrame(self.csv_data)
            
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate filename with date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"sensor_data_{timestamp}.csv")
            
            # Save data
            df.to_csv(filename, index=False)
            print(f"\nDatos guardados en: {filename}")
            print(f"Total de muestras guardadas: {len(df)}")
            
            # Mostrar mensaje de éxito con estilo moderno
            msg = QMessageBox(self)
            msg.setWindowTitle("Datos Guardados")
            msg.setText("Los datos se han guardado exitosamente.")
            msg.setInformativeText(f"Archivo: {os.path.basename(filename)}\nMuestras: {len(df)}")
            msg.setIcon(QMessageBox.Information)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #F8F9FA;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QMessageBox QLabel {
                    color: #424242;
                    font-size: 13px;
                }
                QMessageBox QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #66BB6A,
                                               stop: 1 #4CAF50);
                    color: white;
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QMessageBox QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #81C784,
                                               stop: 1 #66BB6A);
                }
            """)
            msg.exec()
            
        except Exception as e:
            print(f"Error al guardar datos: {e}")
            # Mostrar mensaje de error con estilo moderno
            msg = QMessageBox(self)
            msg.setWindowTitle("Error al Guardar CSV")
            msg.setText("Ocurrió un error al guardar los datos.")
            msg.setInformativeText(f"Error: {str(e)}")
            msg.setIcon(QMessageBox.Critical)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #F8F9FA;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QMessageBox QLabel {
                    color: #424242;
                    font-size: 13px;
                }
                QMessageBox QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #EF5350,
                                               stop: 1 #F44336);
                    color: white;
                    border: 2px solid #F44336;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QMessageBox QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #E57373,
                                               stop: 1 #EF5350);
                }
            """)
            msg.exec()

    def cleanup(self):
        """Método de limpieza - maneja el evento de cierre de la ventana"""
        print("Iniciando limpieza de SensorMonitor...")
        self.is_closing_flag = True
        
        # Detener adquisición si está corriendo
        if self.running:
            self.stop_acquisition()
            
        # Detener timer de actualización
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            
        # Esperar a que termine el thread de lectura
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=2.0)
            if self.reading_thread.is_alive():
                print("Advertencia: Thread de lectura no terminó correctamente")
        
        print("Limpieza de SensorMonitor completada")
    
    def reset_led(self):
        """Resetear el LED a su estado normal"""
        self.pulse_led.setPixmap(qta.icon('fa5s.heart', color='#00C8AA00').pixmap(38, 38))
        self.led_is_active = False
        self.led_timer.stop()
    
    def activate_pulse_led(self):
        """Activar el LED cuando se detecta una pulsación"""
        if not self.led_is_active:
            self.pulse_led.setPixmap(qta.icon('fa5s.heart', color="#D30E0E").pixmap(38, 38))
            self.led_is_active = True
            self.led_timer.start(200)  # LED activo por 200ms
    
    def detect_pulse_peaks(self, filtered_ppg_data, timestamp):
        """Detectar picos en la señal PPG filtrada y activar LED"""
        if len(filtered_ppg_data) < 3:
            return
        
        # Usar una ventana pequeña para detección en tiempo real
        window_size = min(len(filtered_ppg_data), int(2 * SAMPLE_RATE))  # 2 segundos
        recent_data = list(filtered_ppg_data)[-window_size:]
        
        if len(recent_data) < SAMPLE_RATE:  # Necesitamos al menos 1 segundo
            return
        
        try:
            # Normalizar datos
            data_array = np.array(recent_data)
            data_norm = (data_array - np.mean(data_array)) / (np.std(data_array) + 1e-10)
            
            # Parámetros para detección de picos
            min_distance = int(SAMPLE_RATE * 60 / 180)  # Máximo 180 BPM
            min_height = 0.5  # Altura mínima normalizada
            
            # Detectar picos
            peaks, properties = signal.find_peaks(
                data_norm,
                height=min_height,
                distance=min_distance,
                prominence=0.3
            )
            
            # Si hay picos en los últimos 100ms, activar LED
            recent_threshold = len(recent_data) - int(0.1 * SAMPLE_RATE)  # Últimos 100ms
            recent_peaks = peaks[peaks > recent_threshold]
            
            # if len(recent_peaks) > 0:
            #     self.activate_pulse_led()
        
        except Exception as e:
            print(f"Error en detección de picos: {e}")
    
    def update_pulse_rate_display(self, bpm_value):
        """Actualizar el display de pulsaciones por minuto"""
        if bpm_value is not None and bpm_value > 0:
            self.pulse_rate_value_label.setText(f"{int(bpm_value)}")
        else:
            self.pulse_rate_value_label.setText("--")
    
    def is_busy(self) -> bool:
        """Verificar si está ocupado"""
        is_running = self.running
        has_active_thread = self.reading_thread and self.reading_thread.is_alive()
        
        # Debug: imprimir estado actual
        print(f"SensorMonitor.is_busy() - running: {is_running}, active_thread: {has_active_thread}")
        
        return is_running or has_active_thread
    
    def closeEvent(self, event=None):
        """Manejo del evento de cierre"""
        # Actualmente este método nunca se usa, debido a que el widget cuando 
        # se ejecut 'independientemente', en realidad se hereda de QMainWindow
        # y cuando no, es parte de control_panel.
        if self.is_standalone:
            # Solo manejar closeEvent si es aplicación independiente
            self.cleanup()
            if event:
                event.accept()
        else:
            # Si es widget integrado, no manejar closeEvent aquí
            # El parent se encargará de llamar cleanup()
            pass


# Solo cuando se ejecuta como aplicación independiente
if __name__ == "__main__":
    """Función principal para ejecutar el monitor como aplicación independiente"""
    app = QApplication([])
    
    # Configurar estilo global de la aplicación
    app.setStyleSheet("""
        QMainWindow {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    
    # Crear una ventana principal que contendrá el widget
    main_window = QMainWindow()
    main_window.setWindowTitle("Monitor de Bioseñales EMDR - Tiempo Real")
    main_window.setGeometry(100, 100, 1000, 700)
    
    # Crear la instancia del monitor como widget
    monitor_widget = SensorMonitor(parent=main_window)
    main_window.setCentralWidget(monitor_widget)
    
    # Crear cleanup manager para app independiente
    from src.utils.cleanup_interface import CleanupManager
    cleanup_manager = CleanupManager()
    cleanup_manager.register_component(monitor_widget)
    
    # Conectar cierre de aplicación
    app.aboutToQuit.connect(lambda: cleanup_manager.request_close())
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Start Qt event loop
    sys.exit(app.exec())