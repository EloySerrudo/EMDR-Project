import os
import sys
import time
import winsound
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QTabWidget, QSplitter, QGridLayout, QMessageBox, QFrame, QComboBox,
    QPushButton, QStackedWidget, QDialog, QFormLayout, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize
from PySide6.QtGui import QFont, QIcon, QIntValidator, QPixmap  # Añadir QPixmap
import pyqtgraph as pg
import qtawesome as qta

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para componentes específicos
from src.models.devices import Devices, KNOWN_SLAVES
from src.utils.events import event_system
from src.controller.emdr_controller import EMDRControllerWidget
from src.sensor.sensor_monitor import SensorMonitor
from src.database.database_manager import DatabaseManager
from src.utils.cleanup_interface import CleanupManager

class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)
    session_changed = Signal(int)  # Nueva señal para cambios de sesión

class EMDRControlPanel(QMainWindow):
    """Aplicación principal que integra el controlador EMDR y el monitor de sensores"""
    
    # Señal emitida cuando la ventana se cierra
    window_closed = Signal()  # Nueva señal personalizada
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.current_patient = None
        self.current_session = None
        
        self.setWindowTitle(f"EMDR Project - Dashboard Terapéutico")
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'emdr_icon.png')))
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal - reducir márgenes
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 2)
        main_layout.setSpacing(3)
        
        # ===== 1. BARRA SUPERIOR CON INFORMACIÓN CONTEXTUAL =====
        self.header_widget = self.create_header_bar(username)
        main_layout.addWidget(self.header_widget)
        
        # ===== 2. BARRA DE ESTADO DE DISPOSITIVOS =====
        self.device_status_frame = QFrame()
        self.device_status_frame.setFrameShape(QFrame.StyledPanel)
        self.device_status_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
        """)

        device_status_layout = QHBoxLayout(self.device_status_frame)
        device_status_layout.setContentsMargins(15, 0, 15, 0)
        device_status_layout.setSpacing(20)

        # Texto descriptivo
        status_text_label = QLabel("Estado de dispositivos:")
        status_text_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                background: transparent;
                border-radius: 0px;
                border: none;
                padding: -8px;
                margin-right: -10px;
            }
        """)
        device_status_layout.addWidget(status_text_label)

        # Crear un contenedor para las cajas que estén juntas
        devices_container = QFrame()
        devices_container.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 0px;
                border: 0px;
                padding: 0px;
                margin: 0px;
            }
        """)
        devices_layout = QHBoxLayout(devices_container)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        devices_layout.setSpacing(0)  # Sin espacios entre cajas

        # Crear las 4 cajas de estado con efecto LED
        self.device_boxes = {}
        
        # USB (Master Controller)
        usb_box = self.create_device_status_box("USB", False)
        self.device_boxes["Master Controller"] = usb_box
        devices_layout.addWidget(usb_box)
        
        # Luces (Lightbar)
        lights_box = self.create_device_status_box("Luces", False)
        self.device_boxes["Lightbar"] = lights_box
        devices_layout.addWidget(lights_box)
        
        # Vibración (Buzzer)
        vibration_box = self.create_device_status_box("Vibración", False)
        self.device_boxes["Buzzer"] = vibration_box
        devices_layout.addWidget(vibration_box)
        
        # Sensores (Sensor)
        sensors_box = self.create_device_status_box("Sensores", False)
        self.device_boxes["Sensor"] = sensors_box
        devices_layout.addWidget(sensors_box)

        # Añadir el contenedor al layout principal
        device_status_layout.addWidget(devices_container)

        # Espaciador flexible
        device_status_layout.addStretch()

        # Botón de escaneo
        self.scan_button = QPushButton("Conectar Dispositivos")
        self.scan_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #42A5F5,
                                       stop: 1 #2196F3);
                color: white;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 140px;
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
        self.scan_button.clicked.connect(self.scan_devices)
        device_status_layout.addWidget(self.scan_button)

        main_layout.addWidget(self.device_status_frame)
        
        # ===== 3. ÁREA PRINCIPAL DIVIDIDA =====
        # Splitter para dividir la ventana
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                border: none;
            }
        """)
        main_layout.addWidget(self.splitter, 1) # Darle mayor expansión vertical
        
        # ===== 4. PANEL IZQUIERDO: CONTROLADOR EMDR =====
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 2px solid #555555;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(0)

        # Título del panel con estilo mejorado
        left_header = QLabel("CONTROL DE ESTIMULACIÓN")
        left_header.setStyleSheet("""
            QLabel {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                       stop: 0 rgba(120, 255, 180, 0.3),
                                       stop: 0.5 rgba(0, 169, 157, 0.4),
                                       stop: 1 rgba(120, 255, 180, 0.3));
                color: #FFFFFF;
                font-size: 14px; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 140, 130, 0.6);
            }
        """)
        left_header.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_header)

        # Añadir el controlador EMDR
        self.emdr_controller = EMDRControllerWidget()
        self.emdr_controller.main_layout.setContentsMargins(0, 8, 0, 0)  # Eliminar márgenes del layout interno
        left_layout.addWidget(self.emdr_controller)
        
        # ===== 5. PANEL DERECHO: MONITOR DE SENSORES =====
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_panel.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 2px solid #555555;
                border-radius: 10px;
            }
        """)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)

        # Título del panel con estilo mejorado
        right_header = QLabel("MONITOR DE SEÑALES")
        right_header.setStyleSheet("""
            QLabel {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                       stop: 0 rgba(120, 255, 180, 0.3),
                                       stop: 0.5 rgba(0, 169, 157, 0.4),
                                       stop: 1 rgba(120, 255, 180, 0.3));
                color: #FFFFFF;
                font-size: 14px; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 140, 130, 0.6);
            }
        """)
        right_header.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_header)

        # Panel para selección de visualización con estilo mejorado
        view_selector_frame = QFrame()
        view_selector_frame.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border-radius: 8px;
                padding: 5px;
                margin: 0px;
                border: 1px solid #555555;
            }
        """)
        view_selector_layout = QHBoxLayout(view_selector_frame)
        view_selector_layout.setContentsMargins(10, 5, 10, 5)

        # Label para visualización
        viz_label = QLabel("Visualización:")
        viz_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: 600;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        view_selector_layout.addWidget(viz_label)

        self.view_selector = QComboBox()
        self.view_selector.addItems(["Señales en tiempo real", "Historial de sesión", "Estadísticas"])
        self.view_selector.setStyleSheet("""
            QComboBox {
                background-color: #424242;
                color: white;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 4px 12px;
                min-width: 140px;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox:focus {
                border: 2px solid #00A99D;
                background-color: #383838;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 1px solid #555555;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #333333;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #424242;
                color: white;
                selection-background-color: #00A99D;
                border: 1px solid #555555;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                height: 25px;
                padding: 4px;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #00A99D;
            }
        """)
        view_selector_layout.addWidget(self.view_selector)
        view_selector_layout.addStretch()
        right_layout.addWidget(view_selector_frame)

        # Stack widget para diferentes vistas
        self.view_stack = QStackedWidget()
        self.view_stack.setStyleSheet("""
            QStackedWidget {
                background-color: transparent;
                border: none;
            }
        """)

        # Vista 1: Monitor de sensores en tiempo real
        self.sensor_monitor = SensorMonitor()
        self.sensor_monitor.main_layout.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes del layout interno
        self.view_stack.addWidget(self.sensor_monitor)

        # Vista 2: Historial de sesión (placeholder mejorado)
        self.history_view = QWidget()
        self.history_view.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                       stop: 0 #F8F9FA,
                                       stop: 1 #E9ECEF);
                border-radius: 8px;
            }
        """)
        history_layout = QVBoxLayout(self.history_view)
        history_layout.setContentsMargins(20, 20, 20, 20)

        history_title = QLabel("HISTORIAL DE SESIÓN")
        history_title.setStyleSheet("""
            QLabel {
                background-color: #424242;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #555555;
            }
        """)
        history_title.setAlignment(Qt.AlignCenter)
        history_layout.addWidget(history_title)

        history_placeholder = QLabel("Funcionalidad en desarrollo...")
        history_placeholder.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                font-style: italic;
                background: transparent;
            }
        """)
        history_placeholder.setAlignment(Qt.AlignCenter)
        history_layout.addWidget(history_placeholder)
        history_layout.addStretch()

        self.view_stack.addWidget(self.history_view)

        # Vista 3: Estadísticas (placeholder mejorado)
        self.stats_view = QWidget()
        self.stats_view.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                       stop: 0 #F8F9FA,
                                       stop: 1 #E9ECEF);
                border-radius: 8px;
            }
        """)
        stats_layout = QVBoxLayout(self.stats_view)
        stats_layout.setContentsMargins(20, 20, 20, 20)

        stats_title = QLabel("ESTADÍSTICAS")
        stats_title.setStyleSheet("""
            QLabel {
                background-color: #424242;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #555555;
            }
        """)
        stats_title.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(stats_title)

        stats_placeholder = QLabel("Funcionalidad en desarrollo...")
        stats_placeholder.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                font-style: italic;
                background: transparent;
            }
        """)
        stats_placeholder.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(stats_placeholder)
        stats_layout.addStretch()

        self.view_stack.addWidget(self.stats_view)

        right_layout.addWidget(self.view_stack)
        
        # Conectar el selector de vistas al stack widget
        self.view_selector.currentIndexChanged.connect(self.view_stack.setCurrentIndex)
        
        # ===== 6. AÑADIR PANELES AL SPLITTER =====
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        # Ajustar proporción para pantallas más pequeñas (35% - 65%)
        self.splitter.setSizes([350, 650])
        
        # ===== 7. BARRA INFERIOR DE ESTADO Y ACCIONES =====
        footer_frame = QFrame()
        footer_frame.setFrameShape(QFrame.StyledPanel)
        footer_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
            }
        """)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(12, 0, 12, 0)

        # Información de sesión con estilo mejorado
        self.session_info = QLabel("Sesión: No iniciada")
        self.session_info.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                background-color: rgba(244, 67, 54, 0.1);
                border: 1px solid rgba(244, 67, 54, 0.3);
                padding: 2px 8px;
            }
        """)
        footer_layout.addWidget(self.session_info)

        footer_layout.addStretch()

        # Botones de acción con estilo moderno inspirado en login
        new_session_btn = QPushButton("Nueva Sesión")
        new_session_btn.clicked.connect(self.start_new_session)
        new_session_btn.setStyleSheet("""
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
                min-width: 120px;
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
        footer_layout.addWidget(new_session_btn)

        save_btn = QPushButton("Guardar Datos")
        save_btn.setFixedSize(134, 36)
        save_btn.clicked.connect(self.save_session_data)
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
        footer_layout.addWidget(save_btn)

        back_btn = QPushButton("Regresar")
        back_btn.setFixedSize(134, 36)
        back_btn.clicked.connect(self.return_to_dashboard)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
                border: 2px solid #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
                border: 2px solid #545b62;
            }
        """)
        footer_layout.addWidget(back_btn)
        
        exit_btn = QPushButton("Salir")
        exit_btn.setFixedSize(134, 36)
        exit_btn.clicked.connect(self.exit_application)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #424242;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 2px solid #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
                border: 2px solid #333333;
            }
        """)
        footer_layout.addWidget(exit_btn)

        main_layout.addWidget(footer_frame)
        
        # ===== 8. CONFIGURACIÓN GENERAL DE LA APLICACIÓN =====
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
            }
            QLabel {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QComboBox {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox {
                background-color: #F8F9FA;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QDialog {
                background-color: #F8F9FA;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Crear objeto de señales para comunicación interna
        self.signals = SignalsObject()
        self.signals.device_status_updated.connect(self.update_device_status)
        
        # Configurar para que el monitor de sensores también actualice el estado de dispositivos
        self.sensor_monitor.signals.device_status_updated.connect(self.update_device_status)
        
        # Configurar para que el controlador EMDR tenga acceso directo al monitor de sensores
        self.emdr_controller.sensor_monitor = self.sensor_monitor
        
        # Mantener las conexiones para centralizar la lógica en scan_devices
        self.emdr_controller.scan_usb_click = self.scan_devices
        self.sensor_monitor.check_slave_connections = self.scan_devices
        
        # Mantener registro de dispositivos conectados
        self.connected_devices = []
        
        # Cargar pacientes por defecto
        self.load_patients()

        # Manager de limpieza
        self.cleanup_manager = CleanupManager()
        
        # Registrar componentes cuando se crean
        self.cleanup_manager.register_component(self.emdr_controller)
        self.cleanup_manager.register_component(self.sensor_monitor)
        
        # Conectar señales de limpieza
        self.cleanup_manager.cleanup_completed.connect(self.on_cleanup_completed)
        self.cleanup_manager.cleanup_failed.connect(self.on_cleanup_failed)
    
    def create_device_status_box(self, device_name, is_connected):
        """Crear una caja de estado para un dispositivo con efecto LED e icono"""
        # Frame contenedor
        box_frame = QFrame()
        box_frame.setFrameShape(QFrame.StyledPanel)
        box_frame.setFixedSize(120, 45)  # Aumentar tamaño para icono
        
        # Layout horizontal para icono + LED + texto
        box_layout = QHBoxLayout(box_frame)
        box_layout.setContentsMargins(8, 6, 8, 6)
        box_layout.setSpacing(6)
        
        # Icono del dispositivo
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        
        # Mapear dispositivos a iconos
        device_icons = {
            "USB": "mdi.usb-flash-drive",
            "Luces": "mdi.led-strip",
            "Vibración": "mdi.watch-vibrate",
            "Sensores": "mdi.pulse"
        }
        
        icon_name = device_icons.get(device_name, "fa5s.question")
        icon_color = "#66FF66" if is_connected else "#FF6666"
        
        icon = qta.icon(icon_name, color=icon_color)
        icon_label.setPixmap(icon.pixmap(20, 20))
        
        # LED circular (reducir tamaño)
        led_label = QLabel()
        led_label.setFixedSize(10, 10)
        led_label.setStyleSheet(self.get_led_style(is_connected))
        
        # Texto del dispositivo
        text_label = QLabel(device_name)
        text_label.setAlignment(Qt.AlignHCenter)
        text_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        # Añadir al layout
        box_layout.addWidget(icon_label)
        box_layout.addWidget(led_label)
        box_layout.addWidget(text_label)
        
        # Estilo del frame
        box_frame.setStyleSheet(self.get_box_style(is_connected))
        
        # Guardar referencias para poder actualizar
        box_frame.led_label = led_label
        box_frame.text_label = text_label
        box_frame.icon_label = icon_label
        box_frame.device_name = device_name
        
        return box_frame

    def get_led_style(self, is_connected):
        """Obtener estilo CSS para el LED"""
        if is_connected:
            return """
                QLabel {
                    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.8,
                                               fx: 0.3, fy: 0.3,
                                               stop: 0 #66FF66,
                                               stop: 0.7 #00CC00,
                                               stop: 1 #008800);
                    border: 1px solid #00AA00;
                    border-radius: 6px;
                }
            """
        else:
            return """
                QLabel {
                    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.8,
                                               fx: 0.3, fy: 0.3,
                                               stop: 0 #FF6666,
                                               stop: 0.7 #CC0000,
                                               stop: 1 #880000);
                    border: 1px solid #AA0000;
                    border-radius: 6px;
                }
            """

    def get_box_style(self, is_connected):
        """Obtener estilo CSS para la caja del dispositivo"""
        if is_connected:
            return """
                QFrame {
                    background-color: rgba(76, 175, 80, 0.1);
                    border: 1px solid rgba(76, 175, 80, 0.3);
                    border-radius: 0px;
                    padding: 4px;
                }
            """
        else:
            return """
                QFrame {
                    background-color: rgba(244, 67, 54, 0.1);
                    border: 1px solid rgba(244, 67, 54, 0.3);
                    border-radius: 0px;
                    padding: 4px;
                }
            """

    def update_device_box_status(self, device_key, is_connected):
        """Actualizar el estado visual de una caja de dispositivo"""
        if device_key in self.device_boxes:
            box = self.device_boxes[device_key]
            
            # Actualizar LED
            box.led_label.setStyleSheet(self.get_led_style(is_connected))
            
            # Actualizar frame
            box.setStyleSheet(self.get_box_style(is_connected))
            
            # Actualizar icono
            device_icons = {
                "Master Controller": "mdi.usb-flash-drive",
                "Lightbar": "mdi.led-strip", 
                "Buzzer": "mdi.watch-vibrate",
                "Sensor": "mdi.pulse"
            }
            
            icon_name = device_icons.get(device_key, "fa5s.question")
            icon_color = "#66FF66" if is_connected else "#FF6666"
            
            icon = qta.icon(icon_name, color=icon_color)
            box.icon_label.setPixmap(icon.pixmap(20, 20))

    def create_header_bar(self, username):
        """Crea la barra superior con información contextual"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        # Aplicar el gradiente cónico similar al login
        header_frame.setStyleSheet("""
            QFrame {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                       stop: 0 rgba(120, 255, 180, 0.9),
                                       stop: 0.2 rgba(0, 230, 140, 0.8),
                                       stop: 0.4 rgba(0, 169, 157, 0.85),
                                       stop: 0.6 rgba(0, 140, 130, 0.8),
                                       stop: 0.8 rgba(0, 200, 160, 0.85),
                                       stop: 1 rgba(120, 255, 180, 0.9));
                border-radius: 0px;
                border-top: 2px solid rgba(200, 255, 220, 0.8);
                border-left: 1px solid rgba(255, 255, 255, 0.6);
                border-right: 1px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.4);
                padding: 0px;
            }
        """)
        header_frame.setMinimumHeight(60)
        
        # Layout del header
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 5, 15, 5)
        
        # ESTE FRAGMENT DE CÓDIGO ESTÁ COMENTADO PORQUE NO SE UTILIZA EL LOGO EMDR ACTUALMENTE
        # # ===== LOGO EMDR =====
        # logo_label = QLabel()
        # try:
        #     # Intentar cargar el logo
        #     logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
        #     if os.path.exists(logo_path):
        #         from PySide6.QtGui import QPixmap
        #         pixmap = QPixmap(logo_path)
        #         # Escalar el logo manteniendo proporción
        #         scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        #         logo_label.setPixmap(scaled_pixmap)
        #         logo_label.setStyleSheet("""
        #             QLabel {
        #                 background: transparent;
        #                 border: none;
        #                 padding: 0px;
        #             }
        #         """)
        #     else:
        #         # Si no existe el logo, mostrar texto alternativo
        #         logo_label.setText("EMDR")
        #         logo_label.setStyleSheet("""
        #             QLabel {
        #                 color: white;
        #                 font-size: 16px;
        #                 font-weight: bold;
        #                 background: transparent;
        #                 padding: 4px;
        #             }
        #         """)
        # except Exception as e:
        #     print(f"Error cargando logo: {e}")
        #     # Fallback a texto
        #     logo_label.setText("EMDR")
        #     logo_label.setStyleSheet("""
        #         QLabel {
        #             color: white;
        #             font-size: 16px;
        #             font-weight: bold;
        #             background: transparent;
        #             padding: 4px;
        #         }
        #     """)
        
        # header_layout.addWidget(logo_label)
        
        # Título principal
        title_label = QLabel("PANEL DE CONTROL EMDR")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                border-radius: 12px;
                margin-left: 10px;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Información del terapeuta
        therapist_label = QLabel(f"Terapeuta: {username}")
        therapist_label.setStyleSheet("""
            QLabel {
                color: #003454;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border-radius: 12px;
            }
        """)
        header_layout.addWidget(therapist_label)
        
        # Espaciado
        header_layout.addSpacing(20)
        
        # Selector de paciente
        patient_label = QLabel("Paciente:")
        patient_label.setStyleSheet("""
            QLabel {
                color: #003454;
                font-weight: 600;
                background: transparent;
                border-radius: 12px;
            }
        """)
        header_layout.addWidget(patient_label)

        self.patient_selector = QComboBox()

        # Configurar íconos para las flechas del dropdown
        self.combo_arrow_down = qta.icon('fa6s.chevron-down', color='#FFFFFF')
        self.combo_arrow_up = qta.icon('fa6s.chevron-up', color='#FFFFFF')

        self.patient_selector.setStyleSheet("""
            QComboBox {
                padding: 8px 12px 8px 12px;
                border: 2px solid #555555;
                border-radius: 6px;
                font-size: 13px;
                min-width: 160px;
                background-color: #424242;
                color: white;
                font-weight: 500;
            }
            QComboBox:focus {
                border: 2px solid #00A99D;
                background-color: #383838;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #555555;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #333333;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #424242;
                color: white;
                selection-background-color: #00A99D;
                border: 1px solid #555555;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                height: 30px;
                padding: 5px;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #00A99D;
            }
        """)

        # Crear un contenedor para el ComboBox y la flecha personalizada
        patient_combo_container = QFrame()
        patient_combo_container.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent; 
                padding: 0px; 
            }
        """)
        patient_combo_layout = QHBoxLayout(patient_combo_container)
        patient_combo_layout.setContentsMargins(0, 0, 0, 0)
        patient_combo_layout.setSpacing(0)

        patient_combo_layout.addWidget(self.patient_selector)

        # Crear el ícono de flecha personalizado
        self.patient_dropdown_arrow_label = QLabel()
        self.patient_dropdown_arrow_label.setPixmap(self.combo_arrow_down.pixmap(16, 16))
        self.patient_dropdown_arrow_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        # Posicionar el ícono de flecha sobre el combo box
        self.patient_dropdown_arrow_label.setParent(self.patient_selector)
        self.patient_dropdown_arrow_label.move(self.patient_selector.width() - 25, 
                                          (self.patient_selector.height() - 16) // 2)

        # Sobrescribir métodos para manejar el cambio de ícono
        original_show_popup = self.patient_selector.showPopup
        original_hide_popup = self.patient_selector.hidePopup
        original_resize_event = self.patient_selector.resizeEvent

        def patient_combo_show_popup():
            """Cambia el ícono cuando se despliega el combo"""
            self.patient_dropdown_arrow_label.setPixmap(self.combo_arrow_up.pixmap(16, 16))
            original_show_popup()

        def patient_combo_hide_popup():
            """Cambia el ícono cuando se colapsa el combo"""
            self.patient_dropdown_arrow_label.setPixmap(self.combo_arrow_down.pixmap(16, 16))
            original_hide_popup()

        def patient_combo_resize_event(event):
            """Reposiciona la flecha cuando el combo se redimensiona"""
            original_resize_event(event)
            self.patient_dropdown_arrow_label.move(self.patient_selector.width() - 25, 
                                              (self.patient_selector.height() - 16) // 2)

        # Asignar los métodos sobrescritos
        self.patient_selector.showPopup = patient_combo_show_popup
        self.patient_selector.hidePopup = patient_combo_hide_popup
        self.patient_selector.resizeEvent = patient_combo_resize_event

        # Conectar el evento de cambio
        self.patient_selector.currentIndexChanged.connect(self.change_patient)

        # Añadir el contenedor al layout
        header_layout.addWidget(patient_combo_container)
        
        return header_frame
    
    def load_patients(self):
        """Carga la lista de pacientes desde la base de datos"""
        try:
            patients = DatabaseManager.get_all_patients()
            self.patient_selector.clear()
            self.patient_selector.addItem("-- Seleccione paciente --", None)
            
            for patient in patients:
                self.patient_selector.addItem(f"{patient['nombre']} ({patient['edad']} años)", patient['id'])
                
        except Exception as e:
            print(f"Error al cargar pacientes: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo cargar la lista de pacientes: {str(e)}")
    
    def change_patient(self):
        """Cambia el paciente actual y carga sus datos"""
        patient_id = self.patient_selector.currentData()
        if patient_id is None:
            self.current_patient = None
            self.session_info.setText("Sesión: No iniciada")
            return
            
        try:
            self.current_patient = DatabaseManager.get_patient(patient_id)
            if self.current_patient:
                # Cargar sesiones previas
                sessions = DatabaseManager.get_sessions_for_patient(patient_id)
                
                # Actualizar interfaz con info del paciente
                self.session_info.setText(f"Paciente: {self.current_patient['nombre']} - Sin sesión activa")
                
                # Si queremos hacer más, como cargar historial, sería aquí
                
            else:
                self.current_patient = None
                
        except Exception as e:
            print(f"Error al cambiar de paciente: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo cargar la información del paciente: {str(e)}")
    
    def start_new_session(self):
        """Inicia una nueva sesión para el paciente actual"""
        if not self.current_patient:
            QMessageBox.warning(self, "Advertencia", "Debe seleccionar un paciente antes de iniciar una sesión.")
            return
            
        try:
            # Crear nueva sesión en la base de datos
            session_id = DatabaseManager.add_session(
                id_paciente=self.current_patient["id"],
                notas=f"Sesión iniciada el {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            self.current_session = session_id
            self.session_info.setText(f"Paciente: {self.current_patient['nombre']} - Sesión #{session_id} activa")
            
            # Si el monitor está en ejecución, detenerlo primero
            if self.sensor_monitor.running:
                self.sensor_monitor.stop_acquisition()
            
            QMessageBox.information(self, "Sesión iniciada", 
                                  f"Se ha iniciado una nueva sesión para {self.current_patient['nombre']}.")
                                  
        except Exception as e:
            print(f"Error al iniciar nueva sesión: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo iniciar una nueva sesión: {str(e)}")
    
    def save_session_data(self):
        """Guarda los datos de la sesión actual"""
        if not self.current_session:
            QMessageBox.warning(self, "Advertencia", "No hay sesión activa para guardar.")
            return
            
        try:
            # Si el sensor_monitor está ejecutándose, detenerlo primero
            was_running = False
            if self.sensor_monitor.running:
                was_running = True
                self.sensor_monitor.stop_acquisition()
            
            # Preparar los datos para almacenamiento
            if len(self.sensor_monitor.eog_datos_filtrados) > 0:
                # Serializar datos usando numpy para eficiencia
                import numpy as np
                import pickle
                import zlib
                
                # Comprimir EOG (señal filtrada)
                eog_data = np.array(self.sensor_monitor.eog_datos_filtrados)
                eog_bytes = pickle.dumps(eog_data)
                eog_compressed = zlib.compress(eog_bytes)
                
                # Comprimir PPG (señal filtrada)
                ppg_data = np.array(self.sensor_monitor.ppg_datos_filtrados)
                ppg_bytes = pickle.dumps(ppg_data)
                ppg_compressed = zlib.compress(ppg_bytes)
                
                # Comprimir BPM
                bpm_data = np.array(self.sensor_monitor.bpm_datos)
                bpm_bytes = pickle.dumps(bpm_data)
                bpm_compressed = zlib.compress(bpm_bytes)
                self.sensor_monitor.save_data_to_csv()
                # Actualizar registro en la base de datos
                DatabaseManager.update_session(
                    self.current_session,
                    datos_eog=eog_compressed,
                    datos_ppg=ppg_compressed,
                    datos_bpm=bpm_compressed,
                    notas=f"Sesión actualizada el {time.strftime('%Y-%m-%d %H:%M:%S')}. "
                          f"Datos almacenados: {len(eog_data)} muestras."
                )
                
                # Mensaje de éxito
                QMessageBox.information(
                    self, 
                    "Datos guardados", 
                    f"Se han guardado {len(eog_data)} muestras de datos en la sesión #{self.current_session}."
                )
                
                # Opcionalmente, también guardar en CSV como respaldo
                self.sensor_monitor.save_data_to_csv()
            else:
                QMessageBox.warning(
                    self, 
                    "Sin datos", 
                    "No hay datos de sensores para guardar en esta sesión."
                )
            
            # Reiniciar adquisición si estaba corriendo
            if was_running:
                self.sensor_monitor.start_acquisition()
                
        except Exception as e:
            print(f"Error al guardar datos de sesión: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los datos: {str(e)}")

    def update_device_status_from_list(self, found_devices):
        """Actualizar estado de dispositivos a partir de la lista"""
        # Actualizar cada caja de dispositivo
        self.update_device_box_status("Master Controller", "Master Controller" in found_devices)
        self.update_device_box_status("Lightbar", "Lightbar" in found_devices)
        self.update_device_box_status("Buzzer", "Buzzer" in found_devices)
        self.update_device_box_status("Sensor", "Sensor" in found_devices)

    def update_device_status(self, status_dict, required_connected):
        """Actualizar estado del dispositivo desde señales emitidas por componentes"""
        # Solo actualizar las cajas LED, sin mostrar texto adicional
        for slave_id, connected in status_dict.items():
            # Mapear slave_id a device_key
            device_key_map = {
                1: "Master Controller",  # Asumiendo que slave_id 1 es Master Controller
                2: "Lightbar",          # Asumiendo que slave_id 2 es Lightbar
                3: "Buzzer",            # Asumiendo que slave_id 3 es Buzzer
                4: "Sensor"             # Asumiendo que slave_id 4 es Sensor
            }
            
            device_key = device_key_map.get(slave_id)
            if device_key:
                self.update_device_box_status(device_key, connected)

    def scan_devices(self):
        """Escanear dispositivos manualmente"""
        # Cambiar texto del botón durante el escaneo
        self.scan_button.setText("Escaneando...")
        self.scan_button.setEnabled(False)
        QApplication.processEvents()
        
        # Realizar el escaneo
        found_devices = Devices.probe()
        
        # Verificar si hay cambios desde la última verificación
        old_devices = set(self.connected_devices)
        new_devices = set(found_devices)
        
        # Actualizar la lista de dispositivos
        self.connected_devices = found_devices
        
        # Actualizar estado de dispositivos (solo las cajas LED)
        self.update_device_status_from_list(found_devices)
        
        # Actualizar ambos componentes
        self.update_component_states(found_devices)
        
        # Re-habilitar botón
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Escanear Dispositivos")
        
        # Mostrar estado de conexión en la consola
        if found_devices:
            print("\nDispositivos conectados:")
            for device in found_devices:
                print(f"- {device}")
            print()
            
            # Si hay lightbar, inicializar con LED central
            if "Lightbar" in found_devices:
                Devices.set_led(Devices.led_num // 2 + 1)
        
        # Si hay cambios significativos, mostrar notificación
        if "Master Controller" in new_devices and "Master Controller" not in old_devices:
            QMessageBox.information(self, "Conexión establecida", 
                                "Se ha establecido conexión con el controlador maestro.")
        elif "Master Controller" in old_devices and "Master Controller" not in new_devices:
            QMessageBox.warning(self, "Conexión perdida", 
                            "Se ha perdido la conexión con el controlador maestro.")
    
    def check_devices(self):
        """Verificar dispositivos conectados sin interferir con la UI"""
        # No ejecutar durante acciones EMDR activas
        if self.emdr_controller.mode == 'action':
            return
            
        # Realizar escaneo de dispositivos
        found_devices = Devices.probe()
        
        # Actualizar la lista de dispositivos conectados
        self.connected_devices = found_devices
        self.update_device_status_from_list(found_devices)
        
        # Actualizar estados de habilitación en ambos componentes
        self.update_component_states(found_devices)

    def update_component_states(self, found_devices):
        """Actualizar estados de habilitación en ambos componentes"""
        # Actualizar las cajas de estado visual
        self.update_device_status_from_list(found_devices)
        
        # EMDR Controller
        if hasattr(self.emdr_controller, 'tab_widget'):
            # Verificar lightbar
            lightbar_connected = "Lightbar" in found_devices
            self.emdr_controller.tab_widget.setTabEnabled(1, lightbar_connected)
            
            # Verificar buzzer
            buzzer_connected = "Buzzer" in found_devices
            self.emdr_controller.tab_widget.setTabEnabled(2, buzzer_connected)
            
            # La estimulación auditiva siempre está disponible
            self.emdr_controller.tab_widget.setTabEnabled(0, True)
        
        # Actualizar botones de inicio
        master_connected = "Master Controller" in found_devices
        if self.emdr_controller.mode == 'config' and master_connected:
            self.emdr_controller.activate(self.emdr_controller.btn_start)
            self.emdr_controller.activate(self.emdr_controller.btn_start24)
        else:
            self.emdr_controller.deactivate(self.emdr_controller.btn_start)
            self.emdr_controller.deactivate(self.emdr_controller.btn_start24)
        
        # Sensor Monitor
        self.sensor_monitor.required_devices_connected = "Sensor" in found_devices
        
        # Actualizar estado del botón de adquisición
        if not master_connected or not "Sensor" in found_devices:
            if self.sensor_monitor.running:
                self.sensor_monitor.stop_acquisition()

    def on_cleanup_completed(self):
        """Callback cuando se completa la limpieza"""
        print("Limpieza de todos los componentes completada")
    
    def on_cleanup_failed(self, error_msg):
        """Callback cuando falla la limpieza"""
        print(f"Error en limpieza: {error_msg}")

    def add_new_patient(self):
        """Muestra un diálogo para añadir un nuevo paciente"""
        # Crear el diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle("Añadir Nuevo Paciente")
        dialog.setMinimumWidth(450)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #F8F9FA,
                                       stop: 1 #E9ECEF);
                border-radius: 10px;
            }
            QLabel {
                color: #424242;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 2px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                color: #424242;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #00A99D;
                background-color: #FAFAFA;
            }
        """)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título con estilo del login
        title_label = QLabel("DATOS DEL PACIENTE")
        title_label.setStyleSheet("""
            QLabel {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                       stop: 0 rgba(120, 255, 180, 0.9),
                                       stop: 0.4 rgba(0, 169, 157, 0.85),
                                       stop: 1 rgba(120, 255, 180, 0.9));
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(0, 140, 130, 0.6);
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Frame para el formulario
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid #CCCCCC;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # Campos del formulario
        nombre_edit = QLineEdit()
        nombre_edit.setPlaceholderText("Ingrese el nombre")
        
        apellido_paterno_edit = QLineEdit()
        apellido_paterno_edit.setPlaceholderText("Ingrese el apellido paterno")
        
        apellido_materno_edit = QLineEdit()
        apellido_materno_edit.setPlaceholderText("Ingrese el apellido materno")
        
        edad_edit = QLineEdit()
        edad_edit.setPlaceholderText("Edad (opcional)")
        # Solo permitir números enteros
        edad_edit.setValidator(QIntValidator(0, 120))
        
        celular_edit = QLineEdit()
        celular_edit.setPlaceholderText("Número de contacto")
        
        notas_edit = QTextEdit()
        notas_edit.setPlaceholderText("Notas adicionales (opcional)")
        notas_edit.setMaximumHeight(80)
        
        # Añadir campos al formulario con labels estilizados
        label_style = """
            QLabel {
                color: #424242;
                font-weight: 600;
                font-size: 13px;
            }
        """
        
        nombre_label = QLabel("Nombre:")
        nombre_label.setStyleSheet(label_style)
        form_layout.addRow(nombre_label, nombre_edit)
        
        apellido_p_label = QLabel("Apellido paterno:")
        apellido_p_label.setStyleSheet(label_style)
        form_layout.addRow(apellido_p_label, apellido_paterno_edit)
        
        apellido_m_label = QLabel("Apellido materno:")
        apellido_m_label.setStyleSheet(label_style)
        form_layout.addRow(apellido_m_label, apellido_materno_edit)
        
        edad_label = QLabel("Edad:")
        edad_label.setStyleSheet(label_style)
        form_layout.addRow(edad_label, edad_edit)
        
        celular_label = QLabel("Celular:")
        celular_label.setStyleSheet(label_style)
        form_layout.addRow(celular_label, celular_edit)
        
        notas_label = QLabel("Notas:")
        notas_label.setStyleSheet(label_style)
        form_layout.addRow(notas_label, notas_edit)
        
        layout.addWidget(form_frame)
        
        # Botones de acción con estilo moderno
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #EF5350,
                                       stop: 1 #F44336);
                color: white;
                border: 2px solid #F44336;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 100px;
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
        cancel_btn.clicked.connect(dialog.reject)
        
        save_btn = QPushButton("Guardar")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #66BB6A,
                                       stop: 1 #4CAF50);
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 100px;
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
        save_btn.clicked.connect(lambda: self.save_new_patient(
            dialog,
            nombre_edit.text(),
            apellido_paterno_edit.text(),
            apellido_materno_edit.text(),
            edad_edit.text(),
            celular_edit.text(),
            notas_edit.toPlainText()
        ))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # Mostrar diálogo
        dialog.exec()

    def save_new_patient(self, dialog, nombre, apellido_paterno, apellido_materno, edad, celular, notas):
        """Guarda el nuevo paciente en la base de datos"""
        # Validar campos obligatorios
        if not nombre or not apellido_paterno or not celular:
            QMessageBox.warning(
                dialog,
                "Datos incompletos",
                "Los campos Nombre, Apellido paterno y Celular son obligatorios."
            )
            return
    
        # Convertir edad a entero (si está presente)
        edad_int = None
        if edad:
            try:
                edad_int = int(edad)
            except ValueError:
                QMessageBox.warning(
                    dialog,
                    "Dato inválido",
                    "La edad debe ser un número entero."
                )
                return
    
        # Guardar en la base de datos
        try:
            patient_id = DatabaseManager.add_patient(
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                nombre=nombre,
                edad=edad_int,
                celular=celular,
                notas=notas
            )
            
            if patient_id:
                # Actualizar la lista de pacientes
                self.load_patients()
                
                # Seleccionar el paciente recién creado
                index = -1
                for i in range(self.patient_selector.count()):
                    if self.patient_selector.itemData(i) == patient_id:
                        index = i
                        break
                        
                if index >= 0:
                    self.patient_selector.setCurrentIndex(index)
                    
                # Mostrar mensaje de éxito
                QMessageBox.information(
                    self,
                    "Paciente registrado",
                    f"El paciente {nombre} {apellido_paterno} ha sido registrado correctamente."
                )
                
                # Cerrar el diálogo
                dialog.accept()
                
        except Exception as e:
            QMessageBox.critical(
                dialog,
                "Error de registro",
                f"No se pudo registrar el paciente: {str(e)}"
            )

    def return_to_dashboard(self):
        """Regresa al dashboard del terapeuta"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Regresar")
        msg_box.setText("¿Está seguro de que desea regresar al Control de Usuario?")
        msg_box.setIcon(QMessageBox.Question)
        
        # Crear botones personalizados
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        # Aplicar estilo personalizado
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #323232;
                color: #FFFFFF;
                border-top: none;
                border-left: 2px solid #555555;
                border-right: 2px solid #555555;
                border-bottom: 2px solid #555555;
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
                min-width: 50px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QMessageBox QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
        """)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            try:
                # Emitir señal antes de cerrar
                self.window_closed.emit()
                
                # Cerrar la ventana actual
                self.close()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo regresar al dashboard: {str(e)}")

    def exit_application(self):
        """Cierra completamente la aplicación"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        # Mostrar mensaje de confirmación
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Salir")
        msg_box.setText("¿Está seguro de que desea salir de la aplicación?")
        msg_box.setIcon(QMessageBox.Question)
        
        # Crear botones personalizados
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        # Estilo moderno para el mensaje
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #323232;
                color: #FFFFFF;
                border-top: none;
                border-left: 2px solid #555555;
                border-right: 2px solid #555555;
                border-bottom: 2px solid #555555;
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
                min-width: 50px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QMessageBox QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
        """)
        
        # Mostrar el mensaje
        msg_box.exec()
        
        # Verificar la respuesta
        if msg_box.clickedButton() == yes_button:
            try:
                print("Iniciando cierre de aplicación...")
                
                # Realizar limpieza antes de cerrar
                if self.cleanup_manager.request_close():
                    print("✅ Cierre coordinado exitoso")
                    # Cerrar aplicación completamente
                    QApplication.quit()
                else:
                    print("❌ No se pudo realizar el cierre coordinado")
                    # Mostrar mensaje al usuario
                    reply = QMessageBox.question(
                        self,
                        'Forzar cierre',
                        'Algunos componentes están ocupados. ¿Desea forzar el cierre?',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        print("🔧 Forzando cierre...")
                        # Forzar limpieza y cerrar
                        sys.exit(0)
                        
            except Exception as e:
                print(f"Error al cerrar la aplicación: {e}")
                # Forzar cierre si hay error
                import sys
                sys.exit(0)


    
# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication([])
    
    # Crear dashboard de prueba (necesita un username válido en la BD)
    control_panel = EMDRControlPanel("Lic. Margarita Valdivia")  # Usar el usuario de ejemplo
    # control_panel.setGeometry(0, 0, 1364, 688) # Este ajuste da como resultado una ventana real de 1366 x 722
    
    control_panel.show()
    
    sys.exit(app.exec())