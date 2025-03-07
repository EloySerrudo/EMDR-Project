import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt
from custom_button import CustomButton

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test CustomButton")
        self.setGeometry(100, 100, 480, 320)  # Mismo tamaño que la app original
        
        # Crear etiqueta para mostrar feedback
        self.status_label = QLabel("Estado: Esperando acción", self)
        self.status_label.setGeometry(150, 250, 200, 30)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Crear botones de prueba en diferentes posiciones
        self.btn1 = self.button(0, 0, "Play", self.btn1_clicked, togglable=True)
        self.btn2 = self.button(1, 0, "Stop", self.btn2_clicked, togglable=True)
        self.btn3 = self.button(2, 0, "Pause", self.btn3_clicked, togglable=True)
        
        # Botón para probar activar/desactivar
        self.btn4 = self.button(3, 0, "Light", self.btn4_clicked)
        self.btn4.setActive(False)  # Inicialmente inactivo
        
    def button(self, x, y, title, callback=None, togglable=False):
        """Réplica de la función button() del controlador"""
        btn = CustomButton(title, callback, togglable, self)
        
        # Calcular posición similar a thorpy
        pos_x = 60 + 120 * x
        pos_y = 40 + 80 * y
        
        btn.move(pos_x - btn.width()//2, pos_y - btn.height()//2)
        return btn
    
    def btn1_clicked(self):
        state = "ACTIVADO" if self.btn1.isChecked() else "DESACTIVADO"
        self.status_label.setText(f"Estado: Play {state}")
        
    def btn2_clicked(self):
        state = "ACTIVADO" if self.btn2.isChecked() else "DESACTIVADO"
        self.status_label.setText(f"Estado: Stop {state}")
    
    def btn3_clicked(self):
        state = "ACTIVADO" if self.btn3.isChecked() else "DESACTIVADO"
        self.status_label.setText(f"Estado: Pause {state}")
    
    def btn4_clicked(self):
        # Alternar estado activo/inactivo
        new_state = not self.btn4.active
        self.btn4.setActive(new_state)
        state = "activado" if new_state else "desactivado"
        self.status_label.setText(f"Estado: Light {state}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())