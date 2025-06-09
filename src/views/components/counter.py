from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

class Counter(QLabel):
    """Widget contador basado en QLabel con métodos get_value y set_value"""
    
    def __init__(self, initial_value=0, format_str='{0:d}', parent=None):
        super().__init__(parent)
        
        # Configuración inicial
        self.value = initial_value
        self.format_str = format_str
        
        # Configurar alineación y estilo por defecto
        self.setAlignment(Qt.AlignCenter)
        
        # Aplicar estilo moderno por defecto
        self.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 18px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 rgba(0, 169, 157, 0.3),
                                          stop: 0.5 rgba(0, 200, 170, 0.4),
                                          stop: 1 rgba(0, 169, 157, 0.3));
                border: 2px solid rgba(0, 200, 170, 0.5);
                border-radius: 8px;
                padding: 5px 5px;
                min-width: 60px;
                min-height: 10px;
            }
        """)
        
        # Mostrar valor inicial
        self.update_display()
    
    def get_value(self):
        """Obtiene el valor actual del contador"""
        return self.value
    
    def set_value(self, value):
        """Establece un nuevo valor para el contador"""
        self.value = value
        self.update_display()
    
    def update_display(self):
        """Actualiza el texto mostrado según el valor actual"""
        text = self.format_str.format(self.value)
        self.setText(text)
    
    def reset(self):
        """Reinicia el contador a 0"""
        self.set_value(0)
    
    def increment(self, amount=1):
        """Incrementa el contador en la cantidad especificada"""
        self.set_value(self.value + amount)
    
    def decrement(self, amount=1):
        """Decrementa el contador en la cantidad especificada"""
        self.set_value(max(0, self.value - amount))