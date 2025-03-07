import sys
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from app_qt import MyQtApp
from events_qt import event_system

class TestApp:
    def __init__(self, fullscreen=False):
        # Crear la aplicación
        flags = 1 if fullscreen else 0  # 1 es equivalente a pygame.FULLSCREEN
        self.app = MyQtApp(size=(480, 320), caption="Test EMDR App", icon="imgs/icon.png", flags=flags)
        
        # Crear un widget central para la ventana
        central_widget = QWidget()
        self.app.window.setCentralWidget(central_widget)
        
        # Crear un layout vertical
        layout = QVBoxLayout(central_widget)
        
        # Añadir etiqueta de estado
        self.status_label = QLabel("Estado: Esperando eventos")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Añadir botón para generar evento de prueba
        probe_btn = QPushButton("Simular Probe Event")
        probe_btn.clicked.connect(self._simulate_probe_event)
        layout.addWidget(probe_btn)
        
        action_btn = QPushButton("Simular Action Event")
        action_btn.clicked.connect(self._simulate_action_event)
        layout.addWidget(action_btn)
        
        # Conectar handlers de eventos
        event_system.probe_event.connect(self._handle_probe)
        event_system.action_event.connect(self._handle_action)
    
    def _simulate_probe_event(self):
        """Simula un evento PROBE_EVENT"""
        self.status_label.setText("Emitiendo evento probe...")
        event_system.probe_event.emit()
    
    def _simulate_action_event(self):
        """Simula un evento ACTION_EVENT"""
        self.status_label.setText("Emitiendo evento action...")
        event_system.action_event.emit()
    
    def _handle_probe(self):
        """Maneja el evento probe"""
        self.status_label.setText("Estado: Evento PROBE recibido")
    
    def _handle_action(self):
        """Maneja el evento action"""
        self.status_label.setText("Estado: Evento ACTION recibido")
        
    def run(self):
        """Ejecuta la aplicación"""
        self.app.window.show()
        return self.app.exec()

if __name__ == "__main__":
    fullscreen = "--fullscreen" in sys.argv
    app = TestApp(fullscreen)
    sys.exit(app.run())