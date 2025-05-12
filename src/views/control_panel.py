import os
import sys
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QTabWidget, QSplitter, QGridLayout, QMessageBox, QFrame, QComboBox,
    QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QIcon
import pyqtgraph as pg

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para componentes específicos
from src.models.devices import Devices, KNOWN_SLAVES
from src.utils.events import event_system
from src.controller.emdr_controller import EMDRControllerWidget
from src.sensor.sensor_monitor import SensorMonitor
from src.database.database_manager import DatabaseManager


class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)
    session_changed = Signal(int)  # Nueva señal para cambios de sesión

class EMDRControlPanel(QMainWindow):
    """Aplicación principal que integra el controlador EMDR y el monitor de sensores"""
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.current_patient = None
        self.current_session = None
        
        self.setWindowTitle(f"EMDR Project - Dashboard Terapéutico")
        self.resize(1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # ===== 1. BARRA SUPERIOR CON INFORMACIÓN CONTEXTUAL =====
        self.header_widget = self.create_header_bar(username)
        main_layout.addWidget(self.header_widget)
        
        # ===== 2. BARRA DE ESTADO DE DISPOSITIVOS =====
        self.device_status_frame = QFrame()
        self.device_status_frame.setFrameShape(QFrame.StyledPanel)
        self.device_status_frame.setStyleSheet("background-color: #E3F2FD; border-radius: 4px;")
        
        device_status_layout = QHBoxLayout(self.device_status_frame)
        device_status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.device_status_label = QLabel("Estado de dispositivos: Verificando...")
        self.device_status_label.setStyleSheet("color: #1565C0; font-weight: bold;")
        device_status_layout.addWidget(self.device_status_label)
        
        self.scan_button = QPushButton("Escanear Dispositivos")
        self.scan_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "resources", "scan_icon.png")))
        self.scan_button.clicked.connect(self.scan_devices)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        device_status_layout.addWidget(self.scan_button)
        
        main_layout.addWidget(self.device_status_frame)
        
        # ===== 3. ÁREA PRINCIPAL DIVIDIDA =====
        # Splitter para dividir la ventana
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1)  # Darle mayor expansión vertical
        
        # ===== 4. PANEL IZQUIERDO: CONTROLADOR EMDR =====
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setStyleSheet("background-color: white; border-radius: 4px;")
        left_layout = QVBoxLayout(self.left_panel)
        
        # Título del panel
        left_header = QLabel("CONTROL DE ESTIMULACIÓN")
        left_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1565C0; padding: 5px;")
        left_header.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_header)
        
        # Añadir el controlador EMDR
        self.emdr_controller = EMDRControllerWidget()
        left_layout.addWidget(self.emdr_controller)
        
        # ===== 5. PANEL DERECHO: MONITOR DE SENSORES =====
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_panel.setStyleSheet("background-color: white; border-radius: 4px;")
        right_layout = QVBoxLayout(self.right_panel)
        
        # Título del panel
        right_header = QLabel("MONITOR DE SEÑALES")
        right_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1565C0; padding: 5px;")
        right_header.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_header)
        
        # Panel para selección de visualización
        view_selector_layout = QHBoxLayout()
        view_selector_layout.addWidget(QLabel("Visualización:"))
        
        self.view_selector = QComboBox()
        self.view_selector.addItems(["Señales en tiempo real", "Historial de sesión", "Estadísticas"])
        self.view_selector.setStyleSheet("""
            QComboBox {
                background-color: #f0f0f0;
                border-radius: 4px;
                padding: 3px;
            }
        """)
        view_selector_layout.addWidget(self.view_selector)
        view_selector_layout.addStretch()
        right_layout.addLayout(view_selector_layout)
        
        # Stack widget para diferentes vistas
        self.view_stack = QStackedWidget()
        
        # Vista 1: Monitor de sensores en tiempo real
        self.sensor_monitor = SensorMonitor()
        self.view_stack.addWidget(self.sensor_monitor)
        
        # Vista 2: Historial de sesión (placeholder)
        self.history_view = QWidget()
        history_layout = QVBoxLayout(self.history_view)
        history_layout.addWidget(QLabel("Historial de sesión"))
        self.view_stack.addWidget(self.history_view)
        
        # Vista 3: Estadísticas (placeholder)
        self.stats_view = QWidget()
        stats_layout = QVBoxLayout(self.stats_view)
        stats_layout.addWidget(QLabel("Estadísticas"))
        self.view_stack.addWidget(self.stats_view)
        
        right_layout.addWidget(self.view_stack)
        
        # Conectar el selector de vistas al stack widget
        self.view_selector.currentIndexChanged.connect(self.view_stack.setCurrentIndex)
        
        # ===== 6. AÑADIR PANELES AL SPLITTER =====
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([400, 800])  # 33% control, 67% monitor
        
        # ===== 7. BARRA INFERIOR DE ESTADO Y ACCIONES =====
        footer_frame = QFrame()
        footer_frame.setFrameShape(QFrame.StyledPanel)
        footer_frame.setStyleSheet("background-color: #E8EAF6; border-radius: 4px;")
        footer_layout = QHBoxLayout(footer_frame)
        
        # Información de sesión
        self.session_info = QLabel("Sesión: No iniciada")
        footer_layout.addWidget(self.session_info)
        
        footer_layout.addStretch()
        
        # Botones de acción
        new_session_btn = QPushButton("Nueva Sesión")
        new_session_btn.clicked.connect(self.start_new_session)
        new_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        footer_layout.addWidget(new_session_btn)
        
        save_btn = QPushButton("Guardar Datos")
        save_btn.clicked.connect(self.save_session_data)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
        """)
        footer_layout.addWidget(save_btn)
        
        exit_btn = QPushButton("Salir")
        exit_btn.clicked.connect(self.close)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
        """)
        footer_layout.addWidget(exit_btn)
        
        main_layout.addWidget(footer_frame)
        
        # ===== 8. CONFIGURACIÓN GENERAL DE LA APLICACIÓN =====
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECEFF1;
            }
            QLabel {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                font-weight: bold;
            }
        """)
        
        # Crear objeto de señales para comunicación interna
        self.signals = SignalsObject()
        self.signals.device_status_updated.connect(self.update_device_status)
        
        # Configurar para que el monitor de sensores también actualice el estado de dispositivos
        self.sensor_monitor.signals.device_status_updated.connect(self.update_device_status)
        
        # Configurar para que el controlador EMDR tenga acceso directo al monitor de sensores
        self.emdr_controller.sensor_monitor = self.sensor_monitor
        
        # Simplificar la barra de estado ocultando la que muestran ambos componentes
        self.emdr_controller.device_status_label.hide()
        self.sensor_monitor.device_status_label.hide()
        
        # Ocultar los botones redundantes de escaneo en los componentes
        self.emdr_controller.btn_scan_usb.hide()
        self.sensor_monitor.btn_scan_usb.hide()
        
        # Mantener las conexiones para centralizar la lógica en scan_devices
        self.emdr_controller.scan_usb_click = self.scan_devices
        self.sensor_monitor.check_slave_connections = self.scan_devices
        
        self.sensor_monitor.btn_exit.hide()  # Ocultar botón de salida del monitor de sensores
        self.sensor_monitor.btn_save.hide()  # Ocultar botón de guardar datos del monitor de sensores
        
        # Ocultar el botón de inicio/detención de adquisición ya que ahora es controlado por el checkbox
        self.sensor_monitor.btn_start_stop.hide()
        
        # Mantener registro de dispositivos conectados
        self.connected_devices = []
        
        # Simplificar la barra de estado ocultando la que muestran ambos componentes
        self.emdr_controller.device_status_label.hide()
        self.sensor_monitor.device_status_label.hide()
        
        # Ocultar los botones redundantes de escaneo en los componentes
        self.emdr_controller.btn_scan_usb.hide()  # Ocultar en lugar de desconectar
        self.sensor_monitor.btn_scan_usb.hide()   # Ocultar en lugar de desconectar
        
        # Mantener las conexiones para centralizar la lógica en scan_devices
        self.emdr_controller.scan_usb_click = self.scan_devices
        self.sensor_monitor.check_slave_connections = self.scan_devices
        
        self.sensor_monitor.btn_exit.hide()  # Ocultar botón de salida del monitor de sensores
        self.sensor_monitor.btn_save.hide()  # Ocultar botón de guardar datos del monitor de sensores
        
        # Cargar pacientes por defecto
        self.load_patients()
    
    def create_header_bar(self, username):
        """Crea la barra superior con información contextual"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("background-color: #1565C0; border-radius: 4px;")
        header_frame.setMinimumHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 5, 15, 5)
        
        # Logo o título
        logo_label = QLabel("EMDR THERAPY")
        logo_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(logo_label)
        
        header_layout.addStretch()
        
        # Información del terapeuta
        therapist_label = QLabel(f"Terapeuta: {username}")
        therapist_label.setStyleSheet("color: white; font-size: 14px;")
        header_layout.addWidget(therapist_label)
        
        header_layout.addSpacing(30)
        
        # Selector de paciente
        patient_label = QLabel("Paciente:")
        patient_label.setStyleSheet("color: white;")
        header_layout.addWidget(patient_label)
        
        self.patient_selector = QComboBox()
        self.patient_selector.setStyleSheet("""
            QComboBox {
                background-color: white;
                border-radius: 3px;
                padding: 3px 10px;
                min-width: 150px;
            }
        """)
        self.patient_selector.currentIndexChanged.connect(self.change_patient)
        header_layout.addWidget(self.patient_selector)
        
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
                
            # Iniciar la adquisición de datos
            self.sensor_monitor.start_acquisition()
            
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
            # Primero guardar datos del sensor si hay alguno
            if self.sensor_monitor.running:
                self.sensor_monitor.save_data_to_csv()
            
            # Aquí podríamos implementar la lógica para guardar los datos
            # actualizados en la base de datos, posiblemente usando los
            # datos del SensorMonitor
            
            QMessageBox.information(self, "Datos guardados", 
                                  "Los datos de la sesión han sido guardados correctamente.")
                                  
        except Exception as e:
            print(f"Error al guardar datos de sesión: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los datos: {str(e)}")

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
        
        # Actualizar estado de dispositivos
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
    
    def update_device_status(self, status_dict, required_connected):
        """Actualizar estado del dispositivo desde señales emitidas por componentes"""
        status_items = []
        
        for slave_id, connected in status_dict.items():
            name, required = KNOWN_SLAVES.get(slave_id, ("Desconocido", False))
            status = "✓" if connected else "✗"
            color = "green" if connected else "red"
            req_text = " *" if required else ""
            
            status_items.append(
                f"<span style='font-weight: bold;'>{name}{req_text}:</span> "
                f"<span style='color: {color};'>{status}</span>"
            )
        
        # Unir todos los elementos con separadores
        status_text = " | ".join(status_items)
        
        # Actualizar texto y estilo
        self.device_status_label.setText(f"Estado de dispositivos: {status_text}")
        
        # Cambiar fondo según estado de conexión
        if required_connected:
            self.device_status_frame.setStyleSheet("background-color: #E8F5E9; border-radius: 4px;")
        else:
            self.device_status_frame.setStyleSheet("background-color: #FFEBEE; border-radius: 4px;")
    
    def update_device_status_from_list(self, found_devices):
        """Actualizar estado de dispositivos a partir de la lista"""
        if not found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_frame.setStyleSheet("background-color: #FFEBEE; border-radius: 4px;")
            return
            
        if "Master Controller" not in found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_frame.setStyleSheet("background-color: #FFEBEE; border-radius: 4px;")
            return
        
        status_items = []
        
        # Comprobar cada tipo de dispositivo
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            is_connected = name in found_devices
            status = "✓" if is_connected else "✗"
            color = "green" if is_connected else "red"
            req_text = " *" if required else ""
            
            status_items.append(
                f"<span style='font-weight: bold;'>{name}{req_text}:</span> "
                f"<span style='color: {color};'>{status}</span>"
            )
        
        # Añadir el controlador maestro
        status_items.append("<span style='font-weight: bold;'>Master Controller:</span> <span style='color: green;'>✓</span>")
        
        # Unir todos los elementos con separadores
        status_text = " | ".join(status_items)
        
        # Actualizar texto
        self.device_status_label.setText(f"Estado de dispositivos: {status_text}")
        
        # Verificar dispositivos requeridos para cada componente
        emdr_required = all(
            name in found_devices
            for slave_id, (name, required) in KNOWN_SLAVES.items()
            if required and name != "Sensor"
        )
        
        sensor_required = "Sensor" in found_devices
        
        # Actualizar estilo según estado global
        if emdr_required and (not sensor_required or self.sensor_monitor.running):
            self.device_status_frame.setStyleSheet("background-color: #E8F5E9; border-radius: 4px;")
        else:
            self.device_status_frame.setStyleSheet("background-color: #FFEBEE; border-radius: 4px;")
    
    def update_component_states(self, found_devices):
        """Actualizar estados de habilitación en ambos componentes"""
        # EMDR Controller
        # Asegurarse que cualquier actualización necesaria para pestañas se realice
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
        # Actualizar el estado interno del monitor de sensores
        self.sensor_monitor.required_devices_connected = "Sensor" in found_devices
        
        # Actualizar estado del botón de adquisición
        if not master_connected or not "Sensor" in found_devices:
            self.sensor_monitor.btn_start_stop.setEnabled(False)
            if self.sensor_monitor.running:
                self.sensor_monitor.stop_acquisition()
                self.sensor_monitor.btn_start_stop.setText("Iniciar Adquisición")
        else:
            self.sensor_monitor.btn_start_stop.setEnabled(True)
    
    def closeEvent(self, event):
        """Manejador del evento de cierre de aplicación"""
        # Detener cualquier adquisición en curso
        if self.sensor_monitor.running:
            self.sensor_monitor.cleanup()
        
        # Cerrar el controlador EMDR
        self.emdr_controller.closeEvent()
        
        # Continuar con el cierre normal
        event.accept()