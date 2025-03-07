import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QStyleOption, QStyle
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from switch_qt import Switch

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Switch")
        self.setGeometry(100, 100, 300, 200)
        
        # Widget central y layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Etiqueta para mostrar estado
        self.status_label = QLabel("Estado: OFF")
        layout.addWidget(self.status_label)
        
        # Crear botones para el switch
        self.btn_on = StyleButton("ON")
        self.btn_on.setCheckable(True)
        self.btn_off = StyleButton("OFF")
        self.btn_off.setCheckable(True)
        
        # Crear el switch
        self.switch = Switch(self.btn_on, self.btn_off, self.update_status)
        
        # Añadir botones al layout
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.btn_on)
        btn_layout.addWidget(self.btn_off)
        layout.addLayout(btn_layout)
        
        # Botón para cambiar por programación
        toggle_btn = QPushButton("Alternar estado")
        toggle_btn.clicked.connect(self.toggle_switch)
        layout.addWidget(toggle_btn)
        
        # Aplicar estilos
        self.setStyleSheet("""
            QPushButton[active="true"] {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton[active="false"] {
                background-color: #f0f0f0;
                color: black;
            }
        """)
        
    def update_status(self):
        """Actualiza la etiqueta de estado según el valor del switch"""
        state = "ON" if self.switch.get_value() else "OFF"
        self.status_label.setText(f"Estado: {state}")
        
    def toggle_switch(self):
        """Cambia el estado del switch por programación"""
        new_state = not self.switch.get_value()
        self.switch.set_value(new_state)
        self.update_status()

class StyleButton(QPushButton):
    """Botón con soporte para propiedades de estilo personalizadas"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setProperty("active", False)
        
    def paintEvent(self, event):
        """Sobrescribir paintEvent para que aplique correctamente los estilos"""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        super().paintEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())