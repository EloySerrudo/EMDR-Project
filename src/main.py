import sys
import os
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QTabWidget, QSplitter, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
import pyqtgraph as pg

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importaciones para componentes específicos
from src.models.devices import Devices, KNOWN_SLAVES
from src.utils.events import event_system
from src.controller.emdr_controller import EMDRControllerWidget
from src.sensor.sensor_monitor import SensorMonitor
from src.views.login import LoginWidget
from src.database.db_connection import init_db

class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)

class EMDRApp(QMainWindow):
    """Aplicación principal que integra el controlador EMDR y el monitor de sensores"""
    
    def __init__(self, username=None):
        super().__init__()
        self.setWindowTitle(f"EMDR Project - Sistema integrado - Usuario: {username}")
        self.resize(1200, 800)  # Tamaño inicial antes de maximizar
        
        # Widget central que contendrá todo
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Barra de estado de dispositivos compartida
        self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
        self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 8px;")
        main_layout.addWidget(self.device_status_label)
        
        # Splitter para dividir la ventana
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1)  # Darle mayor expansión vertical
        
        # Crear los componentes principales
        self.emdr_controller = EMDRControllerWidget()
        self.sensor_monitor = SensorMonitor()
        
        # Agregar widgets al splitter
        self.splitter.addWidget(self.emdr_controller)
        self.splitter.addWidget(self.sensor_monitor)
        
        # Establecer proporciones iniciales (40% controlador, 60% monitor)
        self.splitter.setSizes([400, 600])
        
        # Crear objeto de señales para comunicación interna
        self.signals = SignalsObject()
        self.signals.device_status_updated.connect(self.update_device_status)
        
        # Configurar para que el monitor de sensores también actualice el estado de dispositivos
        self.sensor_monitor.signals.device_status_updated.connect(self.update_device_status)
        
        # Mantener registro de dispositivos conectados
        self.connected_devices = []
        
        # Simplificar la barra de estado ocultando la que muestran ambos componentes
        self.emdr_controller.device_status_label.hide()
        self.sensor_monitor.device_status_label.hide()
        
        # Modificar referencias de botones de escaneo para que actualicen el estado global
        self.emdr_controller.btn_scan_usb.clicked.disconnect()
        self.emdr_controller.btn_scan_usb.clicked.connect(self.scan_devices)
        self.sensor_monitor.btn_scan_usb.clicked.disconnect()
        self.sensor_monitor.btn_scan_usb.clicked.connect(self.scan_devices)
        
        # Ejecutar un escaneo inicial de dispositivos
        QTimer.singleShot(500, self.scan_devices)

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
        # Cambiar texto de ambos botones durante el escaneo
        self.emdr_controller.btn_scan_usb.setText("Escaneando...")
        self.sensor_monitor.btn_scan_usb.setText("Escaneando...")
        self.emdr_controller.btn_scan_usb.setEnabled(False)
        self.sensor_monitor.btn_scan_usb.setEnabled(False)
        QApplication.processEvents()  # Forzar actualización de la interfaz
        
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
        
        # Re-habilitar botones
        self.emdr_controller.btn_scan_usb.setEnabled(True)
        self.sensor_monitor.btn_scan_usb.setEnabled(True)
        self.emdr_controller.btn_scan_usb.setText("Escanear")
        self.sensor_monitor.btn_scan_usb.setText("Escanear")
        
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
        # Crear texto para la barra de estado
        status_text = "Estado de dispositivos: "
        
        for slave_id, connected in status_dict.items():
            name, required = KNOWN_SLAVES.get(slave_id, ("Desconocido", False))
            status = "CONECTADO" if connected else "DESCONECTADO"
            req = " (Requerido)" if required else ""
            status_text += f"{name}{req}: {status} | "
        
        # Actualizar texto y estilo
        self.device_status_label.setText(status_text.rstrip(" | "))
        
        # Cambiar fondo según estado de conexión
        if required_connected:
            self.device_status_label.setStyleSheet("background-color: rgba(200, 255, 200, 180); padding: 8px;")
        else:
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 8px;")
    
    def update_device_status_from_list(self, found_devices):
        """Actualizar estado de dispositivos a partir de la lista de dispositivos encontrados"""
        if not found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 8px;")
            return
            
        if "Master Controller" not in found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 8px;")
            return
        
        # Crear texto de estado para cada dispositivo
        status_text = "Estado de dispositivos: "
        
        # Comprobar cada tipo de dispositivo
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            is_connected = name in found_devices
            status = "CONECTADO" if is_connected else "DESCONECTADO"
            req = " (Requerido)" if required else ""
            status_text += f"{name}{req}: {status} | "
        
        # Añadir el controlador maestro
        status_text += "Master Controller: CONECTADO"
        
        # Actualizar texto
        self.device_status_label.setText(status_text)
        
        # Verificar dispositivos requeridos para cada componente
        emdr_required = all(
            name in found_devices
            for slave_id, (name, required) in KNOWN_SLAVES.items()
            if required and name != "Sensor"
        )
        
        sensor_required = "Sensor" in found_devices
        
        # Actualizar estilo según estado global
        if emdr_required and (not sensor_required or self.sensor_monitor.running):
            self.device_status_label.setStyleSheet("background-color: rgba(200, 255, 200, 180); padding: 8px;")
        else:
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 8px;")
    
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

def main():
    """Función principal que inicia la aplicación con autenticación"""
    # Inicializar la aplicación Qt
    app = QApplication(sys.argv)
    
    # Asegurarse de que la base de datos esté inicializada
    init_db()
    
    # Crear y mostrar la ventana de login
    login_window = LoginWidget()
    
    # Variable para la ventana principal
    main_window = None
    
    # Función para manejar el login exitoso
    def on_login_success(username):
        nonlocal main_window
        # Cerrar ventana de login
        login_window.close()
        
        # Crear y mostrar ventana principal
        main_window = EMDRApp(username)
        main_window.showMaximized()
    
    # Conectar señal de login exitoso
    login_window.login_successful.connect(on_login_success)
    
    # Mostrar ventana de login
    login_window.show()
    
    # Ejecutar el bucle de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()