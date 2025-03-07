from PySide6.QtWidgets import QWidget, QVBoxLayout

class Container(QWidget):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._elements = []
        
        if elements:
            self.add_elements(elements)
    
    def add_elements(self, elements):
        for element in elements:
            self._elements.append(element)
            self.layout.addWidget(element)
    
    def get_elements(self):
        return self._elements
    
    def set_visible(self, value):
        super().setVisible(value)
        for elem in self._elements:
            elem.setVisible(value)
            elem.setEnabled(value)  # Equivalente a set_active en thorpy