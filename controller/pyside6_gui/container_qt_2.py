from PySide6.QtWidgets import QWidget, QGridLayout

class Container(QWidget):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._elements = []
        
        if elements:
            self.add_elements(elements)
        
        self.setLayout(self.layout)
    
    def add_elements(self, elements):
        for element in elements:
            self._elements.append(element)
            self.layout.addWidget(element, element.pos_y, element.pos_x)
    
    def get_elements(self):
        return self._elements