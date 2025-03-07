import sys
from PySide6.QtWidgets import QApplication, QPushButton, QMainWindow
from container_qt import Container

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Container")
        self.setGeometry(100, 100, 400, 300)
        
        # Crear botones de prueba
        btn1 = QPushButton("Botón 1")
        btn2 = QPushButton("Botón 2")
        
        # Crear un contenedor con los botones
        self.container = Container([btn1, btn2])
        self.setCentralWidget(self.container)
        
        # Botón para alternar visibilidad
        self.toggle_btn = QPushButton("Mostrar/Ocultar", self)
        self.toggle_btn.setGeometry(10, 10, 100, 30)
        self.toggle_btn.clicked.connect(self.toggle_visibility)
        
    def toggle_visibility(self):
        self.container.set_visible(not self.container.isVisible())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())