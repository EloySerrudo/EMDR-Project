import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel
from PySide6.QtCore import Qt

class SliderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slider con 10 valores")
        self.setGeometry(300, 300, 400, 200)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Etiqueta para mostrar el valor
        self.value_label = QLabel("Valor: 1")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Slider horizontal
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)  # Valor mínimo: 1
        self.slider.setMaximum(10)  # Valor máximo: 10
        self.slider.setValue(1)  # Valor inicial: 1
        self.slider.setTickPosition(QSlider.TicksBothSides)  # Ticks arriba y abajo
        self.slider.setTickInterval(1)
        
        # Aplicar estilo CSS para hacer los ticks rojos
        self.slider.setStyleSheet("""
            QSlider::handle:horizontal {
                border: 1px #438f99;
                border-style: outset;
                margin: -2px 0;
                width: 3px;
                height: 30px;
                background-color: #438f99;
            }
            QSlider::sub-page:horizontal {
                background: #4B4B4B;
            }
        """)
        
        # Conectar el slider al método de actualización
        self.slider.valueChanged.connect(self.update_value)
        
        layout.addWidget(self.slider)
        
    def update_value(self, value):
        """Actualiza la etiqueta cuando cambia el valor del slider"""
        self.value_label.setText(f"Valor: {value}")

def main():
    app = QApplication(sys.argv)
    window = SliderWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()