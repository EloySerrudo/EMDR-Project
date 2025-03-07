from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame
from PySide6.QtCore import Qt
from container_qt import Container

class Selector(Container):
    def __init__(self, x, y, title, values, format_str, btn_plus, btn_minus, updater=None, cyclic=False, parent=None):
        super().__init__(parent=parent)
        
        # Crear widgets para reemplazar los elementos thorpy
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("background-color: white; font-size: 14px;")
        self.title_label.setFixedSize(120, 30)
        
        self.value_label = QLabel(format_str)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("background-color: white; font-size: 18px;")
        self.value_label.setFixedSize(120, 30)
        
        # Configurar layout para posicionar los labels
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)
        
        # Geometría
        self.setGeometry(x*120, y*80, 120, 60)
        
        # Almacenar datos
        self.updater = None
        self.values = values
        self.value = 0
        self.format = format_str
        self.value_index = 0
        self.show_value()
        self.updater = updater
        self.cyclic = cyclic
        
        # # Mostrar valor inicial SIN llamar al updater durante la inicialización
        # self.show_value(call_updater=False)
        
        # Conectar botones si se proporcionaron
        if btn_plus:
            btn_plus.clicked.connect(self.next_value)
        if btn_minus:
            btn_minus.clicked.connect(self.prev_value)
    
    def show_value(self):
        if self.values:
            val = self.values[self.value_index]
        else:
            val = self.value
            
        if isinstance(val, tuple):
            text = self.format.format(*val)
        else:
            text = self.format.format(val)
            
        self.value_label.setText(text)
        
        # Opcionalmente llamar al updater
        if self.updater is not None:
            self.updater()
    
    def next_value(self):
        self.value_index += 1
        if self.value_index >= len(self.values):
            if self.cyclic:
                self.value_index = 0
            else:
                self.value_index = len(self.values) - 1
        self.show_value()
    
    def prev_value(self):
        self.value_index -= 1
        if self.value_index < 0:
            if self.cyclic:
                self.value_index = len(self.values) - 1
            else:
                self.value_index = 0
        self.show_value()
    
    def get_value(self):
        if self.values:
            val = self.values[self.value_index]
        else:
            val = self.value
        return val
    
    def set_value(self, value):
        if self.values:
            try:
                idx = self.values.index(value)
                self.value_index = idx
            except ValueError:
                pass
        else:
            self.value = value
        self.show_value()