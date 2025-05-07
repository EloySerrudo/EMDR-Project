from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

class Container(QWidget):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._elements = []
        
        if elements:
            self.add_elements(elements)
        
        self.setLayout(self.layout)
    
    def add_elements(self, elements):
        for element in elements:
            self._elements.append(element)
            # Añadir cada elemento en una fila separada
            self.layout.addWidget(element)
    
    def get_elements(self):
        return self._elements


class SwitchContainer(QWidget):
    """Contenedor para switches que incluye atributos de posición para el Container"""
    def __init__(self, label_text="On/Off:", pos_x=0, pos_y=0):
        super().__init__()
        self.pos_x = pos_x
        self.pos_y = pos_y
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(QLabel(label_text))
        
        # Estilo para hacerlo visible
        self.setStyleSheet("background-color: rgba(230, 230, 255, 100); padding: 5px; border-radius: 5px;")
    
    def add_switch(self, switch):
        self.layout.addWidget(switch)
        return switch