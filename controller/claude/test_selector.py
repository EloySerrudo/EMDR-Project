import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel
from PySide6.QtCore import Qt
from selector_qt import Selector

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Selector")
        self.setGeometry(100, 100, 500, 400)
        
        # Status label para mostrar actualizaciones
        self.status_label = QLabel("Estado: No hay cambios", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setGeometry(150, 350, 200, 30)
        
        # Crear botones para controlar los selectores
        self.btn_plus1 = QPushButton("+", self)
        self.btn_plus1.setGeometry(180, 100, 40, 30)
        
        self.btn_minus1 = QPushButton("-", self)
        self.btn_minus1.setGeometry(80, 100, 40, 30)
        
        self.btn_plus2 = QPushButton("+", self)
        self.btn_plus2.setGeometry(410, 100, 40, 30)
        
        self.btn_minus2 = QPushButton("-", self)
        self.btn_minus2.setGeometry(290, 100, 40, 30)
        
        # Selector con lista de valores (no cíclico)
        self.selector1 = Selector(
            x=0, 
            y=0, 
            title="Velocidad", 
            values=[10, 20, 30, 40, 50],
            format_str="{0} Hz",
            btn_plus=self.btn_plus1,
            btn_minus=self.btn_minus1,
            updater=self.update_status1,
            cyclic=False,
            parent=self
        )
        self.selector1.move(80, 40)
        
        # Selector con lista de valores (cíclico)
        self.selector2 = Selector(
            x=0,
            y=0,
            title="Color",
            values=["Rojo", "Verde", "Azul", "Amarillo"],
            format_str="{0}",
            btn_plus=self.btn_plus2,
            btn_minus=self.btn_minus2,
            updater=self.update_status2,
            cyclic=True,
            parent=self
        )
        self.selector2.move(290, 40)
        
        # Botón para establecer valores directamente
        self.set_btn1 = QPushButton("Establecer 40 Hz", self)
        self.set_btn1.setGeometry(80, 160, 120, 30)
        self.set_btn1.clicked.connect(self.set_value1)
        
        self.set_btn2 = QPushButton("Establecer Azul", self)
        self.set_btn2.setGeometry(290, 160, 120, 30)
        self.set_btn2.clicked.connect(self.set_value2)
        
        # Contador simple (sin lista de valores)
        self.btn_plus3 = QPushButton("+", self)
        self.btn_plus3.setGeometry(410, 230, 40, 30)
        
        self.btn_minus3 = QPushButton("-", self)
        self.btn_minus3.setGeometry(290, 230, 40, 30)
        
        self.cntr = 0
        self.btn_plus3.clicked.connect(self.next_selector3_value)
        self.btn_minus3.clicked.connect(self.prev_selector3_value)
        
        self.selector3 = Selector(
            x=0,
            y=0,
            title="Contador",
            values=None,
            format_str="{0:d}",
            btn_plus=None,
            btn_minus=None,
            updater=self.update_status3,
            parent=self
        )
        self.selector3.move(290, 300)
        self.selector3.set_value(0)
        
    def update_status1(self):
        self.status_label.setText(f"Velocidad: {self.selector1.get_value()} Hz")
        
    def update_status2(self):
        self.status_label.setText(f"Color: {self.selector2.get_value()}")
    
    def update_status3(self):
        self.status_label.setText(f"Contador: {self.selector3.get_value()}")
        
    def set_value1(self):
        self.selector1.set_value(40)
        
    def set_value2(self):
        self.selector2.set_value("Azul")
    
    def next_selector3_value(self):
        self.cntr += 1
        self.selector3.set_value(self.cntr)
    
    def prev_selector3_value(self):
        self.cntr -= 1
        self.selector3.set_value(self.cntr)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())