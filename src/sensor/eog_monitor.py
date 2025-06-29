# filepath: d:\Documentos\Projects\Python\EMDR-Project\src\sensor\eog_monitor.py
import sys
import numpy as np
import struct
import threading
import time
import os
from collections import deque
import pandas as pd
from datetime import datetime

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import QTimer, Qt
import pyqtgraph as pg

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para gestión de dispositivos
from src.models.devices import Devices

# Importación del filtro en tiempo real
from src.utils.signal_processing import OnlineEOGFilter

# Configuración constantes
SAMPLE_RATE = 125  # Hz (tasa efectiva: 250 SPS ÷ 2 canales)
DISPLAY_TIME = 5   # Segundos de datos a mostrar en la gráfica
GRAPH_PADDING = 0.01  # Espacio entre el borde de la gráfica y los datos
BUFFER_SIZE = 512  # Tamaño máximo de buffer

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 15        # Tamaño en bytes de cada paquete

class EOGMonitor(QWidget):
    def __init__(self, display_time=DISPLAY_TIME, parent=None):
        super().__init__(parent)
        
        self.running = False
        self.reading_thread = None
        
        # Flag para indicar si estamos cerrando
        self.is_closing_flag = False
        
        # Si parent es QMainWindow, es una app independiente
        self.is_standalone = isinstance(parent, QMainWindow)
        
        # Data storage for display
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Initialize deques with zeros
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        
        # Buffers para EOG (crudo y filtrado)
        self.eog_raw_values = deque(initial_values, maxlen=self.display_size)
        self.eog_filtered_values = deque(initial_values, maxlen=self.display_size)
        
        # For unlimited data storage (for saving to CSV)
        self.idx = []
        self.tiempos = []
        self.eog_datos_crudos = []
        self.eog_datos_filtrados = []
        
        # Filtro para EOG
        self.eog_filter = OnlineEOGFilter(
            fs=SAMPLE_RATE,
            hp_cutoff=0.05,        # Conserva posición ocular sostenida
            lp_cutoff=30.0,        # Banda útil para sacadas
            notch_freq=50.0,       # Soporte 50Hz o 60Hz
            notch_q=30,            # Selectividad alta
            fir_taps=101           # ~400ms retardo
        )
        
        self.last_packet_id = -1  # Para detectar paquetes duplicados
        
        # Slave device tracking
        self.sensor_connected = False
        self.connection_thread = None
        
        # Setup UI
        self.setup_ui(display_time)
    
    def setup_ui(self, display_time):
        """Configura la interfaz de usuario del monitor EOG"""
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
            title_label = QLabel("MONITOR EOG - SEÑAL CRUDA Y FILTRADA")
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
            
            # Botón de control de adquisición
            self.btn_scan = QPushButton("Escanear Dispositivos")
            self.btn_scan.setStyleSheet("""
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
            self.btn_scan.clicked.connect(self.check_slave_connections)
            header_layout.addWidget(self.btn_scan)
            
            # Botón de control de adquisición
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
            self.btn_start_stop.setEnabled(False)  # Deshabilitar hasta que se detecte el sensor
            
            # Botón para guardar datos
            self.save_btn = QPushButton("Guardar CSV")
            self.save_btn.setStyleSheet("""
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
                QPushButton:disabled {
                    background-color: #555555;
                    border: 2px solid #555555;
                    color: #888888;
                }
            """)
            self.save_btn.clicked.connect(self.save_data_to_csv)
            header_layout.addWidget(self.save_btn)
            self.save_btn.setEnabled(False)  # Deshabilitar hasta que se adquiera algún dato
            
            self.main_layout.addWidget(header_frame)
        
        # ===== ÁREA DE GRÁFICAS =====
        # Frame contenedor para las gráficas
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
        
        plots_layout = QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(2, 2, 2, 2)
        plots_layout.setSpacing(2)
        
        GRAPH_HEIGHT = 200  # Altura para cada gráfica EOG
        
        # Crear gráficas para EOG crudo y filtrado
        self.eog_raw_plot = self.create_eog_raw_plot(display_time, height=GRAPH_HEIGHT)
        self.eog_filtered_plot = self.create_eog_filtered_plot(display_time, height=GRAPH_HEIGHT + 25)
        
        plots_layout.addWidget(self.eog_raw_plot)
        plots_layout.addWidget(self.eog_filtered_plot)
        
        # ===== CREAR CURVAS DE DATOS =====
        self.create_data_curves()
        
        # ===== AÑADIR LEYENDAS =====
        self.add_legends(display_time)
        
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
            
            # Labels de estado
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
        
        # Configurar estilo del eje
        y_axis.setStyle(
            tickTextOffset=3,
            autoExpandTextSpace=False,
            tickTextHeight=12
        )
        
        # Configurar colores del eje
        y_axis.setPen(pg.mkPen('#424242', width=1))
        y_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar el label
        plot_widget.setLabel('left', label_text, size='10pt', color='#424242')
        
        return y_axis

    def create_eog_raw_plot(self, display_time, height):
        """Crear y configurar la gráfica EOG cruda"""
        eog_raw_plot = pg.PlotWidget()
        eog_raw_plot.setFixedHeight(height)
        eog_raw_plot.setLabel('bottom', '')
        eog_raw_plot.setYRange(-700, 700)
        eog_raw_plot.setXRange(-display_time, 0, padding=GRAPH_PADDING)
        
        # Aplicar tema moderno
        eog_raw_plot.setBackground('#FFFFFF')
        eog_raw_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar eje X
        x_axis = eog_raw_plot.getAxis('bottom')
        x_axis.setStyle(showValues=False)
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar eje Y
        self.configure_y_axis_spacing(eog_raw_plot, 'EOG Crudo (µV)', axis_width=60)
        
        # Estilo del área de ploteo
        plot_item = eog_raw_plot.getPlotItem()
        plot_item.getViewBox().setDefaultPadding(GRAPH_PADDING)
        
        return eog_raw_plot

    def create_eog_filtered_plot(self, display_time, height):
        """Crear y configurar la gráfica EOG filtrada"""
        eog_filtered_plot = pg.PlotWidget()
        eog_filtered_plot.setFixedHeight(height)
        eog_filtered_plot.setLabel('bottom', 'Tiempo (s)', size='10pt', color='#424242')
        eog_filtered_plot.setYRange(-700, 700)
        eog_filtered_plot.setXRange(-display_time, 0, padding=GRAPH_PADDING)
        
        # Aplicar tema moderno
        eog_filtered_plot.setBackground('#FFFFFF')
        eog_filtered_plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Configurar ejes
        x_axis = eog_filtered_plot.getAxis('bottom')
        x_axis.setTickSpacing(major=1, minor=0.5)
        x_axis.setPen(pg.mkPen('#CCCCCC', width=1))
        x_axis.setTextPen(pg.mkPen('#424242'))
        
        # Configurar espaciado del eje X
        x_axis.setStyle(
            tickTextOffset=2,
            autoExpandTextSpace=False,
            tickTextHeight=10
        )
        x_axis.setHeight(25)
        
        # Configurar eje Y
        self.configure_y_axis_spacing(eog_filtered_plot, 'EOG Filtrado (µV)', axis_width=60)
        
        # Estilo del área de ploteo
        plot_item = eog_filtered_plot.getPlotItem()
        plot_item.getViewBox().setDefaultPadding(GRAPH_PADDING)
        
        return eog_filtered_plot

    def create_data_curves(self):
        """Crear las curvas de datos"""
        # Curvas con colores diferenciados
        self.eog_raw_curve = self.eog_raw_plot.plot(pen=pg.mkPen('#F44336', width=2))  # Rojo para señal cruda
        self.eog_filtered_curve = self.eog_filtered_plot.plot(pen=pg.mkPen('#2196F3', width=2))  # Azul para señal filtrada
    
    def add_legends(self, display_time):
        """Añadir leyendas a las gráficas"""
        # Leyenda para EOG crudo
        eog_raw_legend = pg.LegendItem(
            offset=(75, 10), 
            labelTextSize='9pt',
            spacing=0,
            rowSpacing=0,
            colSpacing=0
        )
        eog_raw_legend.setParentItem(self.eog_raw_plot.graphicsItem())
        eog_raw_legend.addItem(self.eog_raw_curve, "EOG Señal Cruda")
        eog_raw_legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        eog_raw_legend.layout.setContentsMargins(0, 0, 0, 0)
        eog_raw_legend.layout.setSpacing(0)
        eog_raw_legend.setGeometry(pg.QtCore.QRectF(0, 0, 140, 14))
        
        # Leyenda para EOG filtrado
        eog_filtered_legend = pg.LegendItem(
            offset=(75, 10), 
            labelTextSize='9pt',
            spacing=0,
            rowSpacing=0,
            colSpacing=0
        )
        eog_filtered_legend.setParentItem(self.eog_filtered_plot.graphicsItem())
        eog_filtered_legend.addItem(self.eog_filtered_curve, "EOG Señal Filtrada")
        eog_filtered_legend.setBrush(pg.mkBrush(255, 255, 255, 200))
        eog_filtered_legend.layout.setContentsMargins(0, 0, 0, 0)
        eog_filtered_legend.layout.setSpacing(0)
        eog_filtered_legend.setGeometry(pg.QtCore.QRectF(0, 0, 145, 14))

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
        """Iniciar adquisición de datos"""
        # Verificar que el controlador maestro esté conectado
        if self.running:
            print("Ya está adquiriendo datos")
            return
        
        # Verificar que el controlador maestro esté conectado
        if not Devices.master_plugged_in():
            print("No hay conexión con el controlador maestro")
            return
        
        if not self.sensor_connected:
            print("\nSensor no conectado.")
            print("Use el botón 'Escanear Dispositivos' para verificar conexiones.\n")
            return
        
        self.last_packet_id = -1
        
        # Reset filter
        self.eog_filter.reset()
        
        # Clear and reset data buffers
        self.times.clear()
        self.eog_raw_values.clear()
        self.eog_filtered_values.clear()
        
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        self.times.extend(initial_times)
        self.eog_raw_values.extend(initial_values)
        self.eog_filtered_values.extend(initial_values)
        
        # Clear lists for CSV data storage
        self.idx = []
        self.tiempos = []
        self.eog_datos_crudos = []
        self.eog_datos_filtrados = []
        
        # Send command to ESP32 to start capture
        Devices.start_sensor()
        
        # Start capture
        self.running = True
        
        # Start reading thread
        self.reading_thread = threading.Thread(target=self._read_data)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        print("Adquisición EOG iniciada")

    def stop_acquisition(self):
        """Parar adquisición de datos"""
        if Devices.master_plugged_in() and self.running:
            # Send command to ESP32 to stop capture
            Devices.stop_sensor()
            
            # Stop capture
            self.running = False
            if self.reading_thread:
                self.reading_thread.join(timeout=1.0)
            print("Adquisición EOG detenida")

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
        Devices.probe()
        print("Verificando dispositivos conectados...")
        # Reset connection status
        self.sensor_connected = Devices.sensor_plugged_in()
        if not Devices.master_plugged_in():
            print("No se encontró el controlador maestro")
            self.device_status_label.setText("No se encontró el controlador maestro")
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
            self.btn_start_stop.setEnabled(False)  # Deshabilitar botón de inicio
            self.save_btn.setEnabled(False)  # Deshabilitar botón de guardar datos
        elif not self.sensor_connected:
            print("No se encontró el sensor EOG")
            self.device_status_label.setText("No se encontró el sensor EOG")
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
            self.btn_start_stop.setEnabled(False)  # Deshabilitar botón de inicio
            self.save_btn.setEnabled(False)  # Deshabilitar botón de guardar datos
        else:
            print("Sensor EOG conectado")
            self.device_status_label.setText("Sensor EOG conectado")
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
            self.btn_start_stop.setEnabled(True)  # Habilitar botón de inicio
            self.save_btn.setEnabled(True)  # Habilitar botón de guardar datos
    
    def _read_data(self):
        """Function that runs in a separate thread to read binary data"""
        data_buffer = bytearray()
        serial_conn = Devices.get_master_connection()
        
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
                                    # Remove processed packet from buffer and continue
                                    data_buffer = data_buffer[PACKET_SIZE:]
                                    continue
                                
                                # Update last processed ID
                                self.last_packet_id = packet_id
                                
                                # Timestamp (4 bytes)
                                timestamp_ms = struct.unpack('<I', data_buffer[6:10])[0]
                                timestamp_s = timestamp_ms / 1000.0  # Convert to seconds
                                
                                # PPG value (2 bytes) en data_buffer[10:12] - no lo usamos
                                ppg_value = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # EOG value (2 bytes) en data_buffer[12:14]
                                eog_value = struct.unpack('<h', data_buffer[12:14])[0]
                                
                                # Device ID (1 byte) is at position 14
                                device_id = data_buffer[14]
                                
                                # Apply real-time filter to EOG
                                filtered_eog_value = self.eog_filter.filter(eog_value)
                                
                                # Convertir a microvoltios
                                eog_value = eog_value * 0.0078125 * 4.03225806 # Ganacia de 16 del ADS1115 y 248 del AD620 * 1000 uV
                                filtered_eog_value = filtered_eog_value * 0.0078125 * 4.03225806

                                # Add to deques for display
                                self.times.append(timestamp_s)
                                self.eog_raw_values.append(eog_value)
                                self.eog_filtered_values.append(filtered_eog_value)
                                
                                # Add to lists for CSV storage
                                self.idx.append(packet_id)
                                self.tiempos.append(timestamp_ms)
                                self.eog_datos_crudos.append(eog_value)
                                self.eog_datos_filtrados.append(filtered_eog_value)
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
        """Update the plots with new data"""
        if len(self.times) > 0:
            # Convert deques to numpy arrays for plotting
            x_data = np.array(self.times)
            eog_raw_data = np.array(self.eog_raw_values)
            eog_filtered_data = np.array(self.eog_filtered_values)
            
            if self.running:
                # Normalizar los tiempos para que siempre estén entre -5 y 0
                current_time = x_data[-1]
                normalized_x = x_data - current_time  # El tiempo actual será 0, los anteriores negativos
            else:
                # Si está detenido, mantener la última normalización
                normalized_x = x_data
                
            # Update plot data con los tiempos normalizados
            self.eog_raw_curve.setData(normalized_x, eog_raw_data)
            self.eog_filtered_curve.setData(normalized_x, eog_filtered_data)
        
        # Fijar siempre el rango X entre -5 y 0
        self.eog_raw_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)
        self.eog_filtered_plot.setXRange(-DISPLAY_TIME, 0, padding=GRAPH_PADDING)

    def save_data_to_csv(self):
        """Save collected data to CSV file"""
        try:
            if len(self.idx) == 0:
                print("No hay datos para guardar")
                from PySide6.QtWidgets import QMessageBox
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
                
            # Create DataFrame with EOG data
            data = {
                'ID': self.idx,
                'Timestamp_ms': self.tiempos,
                'EOG_raw': self.eog_datos_crudos,
                'EOG_filtrado': self.eog_datos_filtrados
            }
            df = pd.DataFrame(data)
            
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate filename with date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"eog_data_{timestamp}.csv")
            
            # Save data
            df.to_csv(filename, index=False)
            print(f"\nDatos EOG guardados en: {filename}")
            print(f"Total de muestras guardadas: {len(self.idx)}")
            
            # Mostrar mensaje de éxito
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Datos Guardados")
            msg.setText("Los datos EOG se han guardado exitosamente.")
            msg.setInformativeText(f"Archivo: {os.path.basename(filename)}\nMuestras: {len(self.idx)}")
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
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Error al Guardar")
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
        """Método de limpieza"""
        print("Iniciando limpieza de EOGMonitor...")
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
        
        print("Limpieza de EOGMonitor completada")
    
    def is_busy(self) -> bool:
        """Verificar si está ocupado"""
        is_running = self.running
        has_active_thread = self.reading_thread and self.reading_thread.is_alive()
        
        print(f"EOGMonitor.is_busy() - running: {is_running}, active_thread: {has_active_thread}")
        
        return is_running or has_active_thread
    
    def closeEvent(self, event=None):
        """Manejo del evento de cierre"""
        if self.is_standalone:
            self.cleanup()
            if event:
                event.accept()
        else:
            pass


# Solo cuando se ejecuta como aplicación independiente
if __name__ == "__main__":
    """Función principal para ejecutar el monitor EOG como aplicación independiente"""
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
    
    # Crear una ventana principal
    main_window = QMainWindow()
    main_window.setWindowTitle("Monitor EOG - Señal Cruda y Filtrada")
    main_window.setGeometry(100, 100, 1000, 600)
    
    # Crear la instancia del monitor EOG
    monitor_widget = EOGMonitor(parent=main_window)
    main_window.setCentralWidget(monitor_widget)
    
    # Crear cleanup manager
    from src.utils.cleanup_interface import CleanupManager
    cleanup_manager = CleanupManager()
    cleanup_manager.register_component(monitor_widget)
    
    # Conectar cierre de aplicación
    app.aboutToQuit.connect(lambda: cleanup_manager.request_close())
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Start Qt event loop
    sys.exit(app.exec())