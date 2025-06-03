from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import Qt
import qtawesome as qta
import sys

class PasswordToggle(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mostrar/Ocultar Contraseña")

        # Campo de contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Ingrese su contraseña")

        # Botón con ícono de ojo
        self.toggle_button = QPushButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setFixedSize(32, 32)
        self.toggle_button.setIcon(qta.icon('fa6s.eye'))
        self.toggle_button.setToolTip("Mostrar/Ocultar contraseña")
        self.toggle_button.clicked.connect(self.toggle_password_visibility)

        # Diseño horizontal para el campo y el botón
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.password_input)
        h_layout.addWidget(self.toggle_button)

        # Diseño principal
        main_layout = QVBoxLayout()
        main_layout.addLayout(h_layout)
        self.setLayout(main_layout)

    def toggle_password_visibility(self):
        if self.toggle_button.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_button.setIcon(qta.icon('fa6s.eye-slash'))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_button.setIcon(qta.icon('fa6s.eye'))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PasswordToggle()
    window.show()
    sys.exit(app.exec())
