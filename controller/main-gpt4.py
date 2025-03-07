from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QPixmap, QIcon
import sys
import os


class MyPySideApp(QMainWindow):
    def __init__(self, size=(800, 600), caption="EMDR Controller", icon="imgs/icon.png", center=True):
        super().__init__()
        self.setWindowTitle(caption)
        self.setGeometry(100, 100, size[0], size[1])  # Posición y tamaño de la ventana
        
        # Centrar la ventana en pantalla
        if center:
            self.move(  
                QApplication.primaryScreen().geometry().center() - self.frameGeometry().center()
            )

        # Establecer icono
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))

        # Prueba visual (Etiqueta con el nombre de la app)
        self.label = QLabel(f"Bienvenido a {caption}", self)
        self.label.move(20, 20)

class Container(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.elements = []

    def add_element(self, element):
        """Agrega un widget al contenedor"""
        self.elements.append(element)
        self.layout.addWidget(element)

    def set_visible(self, value):
        """Muestra u oculta todos los elementos"""
        for elem in self.elements:
            elem.setVisible(value)

class Selector(QWidget):
    def __init__(self, title, values, format="{0}", cyclic=False, updater=None):
        super().__init__()
        self.values = values
        self.value_index = 0
        self.format = format
        self.cyclic = cyclic
        self.updater = updater

        # Etiquetas
        self.label_title = QLabel(title)
        self.label_value = QLabel(self.format_value())

        # Botones
        self.btn_minus = QPushButton("-")
        self.btn_plus = QPushButton("+")
        
        # Conectar eventos
        self.btn_minus.clicked.connect(self.prev_value)
        self.btn_plus.clicked.connect(self.next_value)

        # Layouts
        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.btn_minus)
        layout_buttons.addWidget(self.label_value)
        layout_buttons.addWidget(self.btn_plus)

        layout_main = QVBoxLayout()
        layout_main.addWidget(self.label_title)
        layout_main.addLayout(layout_buttons)

        self.setLayout(layout_main)

    def format_value(self):
        val = self.values[self.value_index]
        return self.format.format(val)

    def show_value(self):
        self.label_value.setText(self.format_value())
        if self.updater:
            self.updater()

    def next_value(self):
        self.value_index += 1
        if self.value_index >= len(self.values):
            self.value_index = 0 if self.cyclic else len(self.values) - 1
        self.show_value()

    def prev_value(self):
        self.value_index -= 1
        if self.value_index < 0:
            self.value_index = len(self.values) - 1 if self.cyclic else 0
        self.show_value()

    def get_value(self):
        return self.values[self.value_index]

    def set_value(self, value):
        if value in self.values:
            self.value_index = self.values.index(value)
        self.show_value()

class Switch(QWidget):
    def __init__(self, text_on="On", text_off="Off", updater=None):
        super().__init__()
        self.updater = updater

        # Botones
        self.btn_on = QPushButton(text_on)
        self.btn_off = QPushButton(text_off)

        # Configurar botones como toggle
        self.btn_on.setCheckable(True)
        self.btn_off.setCheckable(True)

        # Conectar eventos
        self.btn_on.clicked.connect(self.on_click)
        self.btn_off.clicked.connect(self.off_click)

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self.btn_on)
        layout.addWidget(self.btn_off)
        self.setLayout(layout)

        # Estado inicial
        self.set_value(False)

    def set_value(self, value):
        """Activa uno de los botones y desactiva el otro."""
        self.btn_on.setChecked(value)
        self.btn_off.setChecked(not value)

    def get_value(self):
        """Devuelve True si 'On' está activado, False si 'Off' está activado."""
        return self.btn_on.isChecked()

    def on_click(self):
        """Se activa el botón 'On' y se desactiva 'Off'."""
        self.btn_off.setChecked(False)
        if self.updater:
            self.updater()

    def off_click(self):
        """Se activa el botón 'Off' y se desactiva 'On'."""
        self.btn_on.setChecked(False)
        if self.updater:
            self.updater()

# Prueba rápida para comprobar que funciona
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # window = MyPySideApp()
    # window.show()
    # container = Container()
    
    # Agregar botones de prueba
    # btn1 = QPushButton("Botón 1")
    # btn2 = QPushButton("Botón 2")
    # container.add_element(btn1)
    # container.add_element(btn2)
    
    # container.show()  # Verificar que los botones se agregan y aparecen correctamente
    
    # selector = Selector("Velocidad", [10, 20, 30, 40], "{0} km/h", cyclic=True)
    # selector.show()
    
    switch = Switch("Encender", "Apagar")
    switch.show()
    
    sys.exit(app.exec())