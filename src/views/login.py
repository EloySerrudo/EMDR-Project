import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager

class LoginWidget(QWidget):
    """Widget de login para el sistema EMDR Project"""
    
    # Señal emitida cuando el login es exitoso
    login_successful = Signal(str)  # Emite el nombre de usuario
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("EMDR Project - Login")
        self.setFixedSize(550, 400)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)  # Evita redimensionar en Windows
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'icon.png')))
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Logo EMDR
        logo_frame = QFrame()
        logo_layout = QHBoxLayout(logo_frame)
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            # Si no hay logo, usar texto
            logo_label.setText("EMDR Project")
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        
        logo_layout.addWidget(logo_label, 0, Qt.AlignCenter)
        layout.addWidget(logo_frame)
        
        # Campo de usuario
        user_layout = QHBoxLayout()
        user_label = QLabel("Usuario:")
        user_label.setMinimumWidth(80)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ingrese su nombre de usuario")
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_input)
        layout.addLayout(user_layout)
        
        # Campo de contraseña con botón para ver
        password_layout = QHBoxLayout()
        password_label = QLabel("Contraseña:")
        password_label.setMinimumWidth(80)
        
        # Contenedor para campo de contraseña + botón
        password_container = QWidget()
        password_container_layout = QHBoxLayout(password_container)
        password_container_layout.setContentsMargins(0, 0, 0, 0)
        password_container_layout.setSpacing(0)
        
        # Campo de contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Ingrese su contraseña")
        
        # Botón para ver contraseña
        self.toggle_password_button = QToolButton()
        self.toggle_password_button.setToolTip("Presionar para ver contraseña")
        self.toggle_password_button.setText("👁")  # Emoji de ojo como ícono
        self.toggle_password_button.setFixedSize(36, 36)  # Tamaño fijo
        self.toggle_password_button.setCursor(Qt.PointingHandCursor)
        
        # Estilo para el botón de ver contraseña
        self.toggle_password_button.setStyleSheet("""
            QToolButton {
                border: 1px solid #bdc3c7;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f9f9f9;
            }
            QToolButton:hover {
                background-color: #ecf0f1;
            }
            QToolButton:pressed {
                background-color: #d6dbdf;
            }
        """)
        
        # Estilo para coordinar el campo de contraseña con el botón
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                background-color: #f9f9f9;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                background-color: white;
            }
        """)
        
        # Añadir eventos para mostrar/ocultar contraseña
        self.toggle_password_button.pressed.connect(self.show_password)
        self.toggle_password_button.released.connect(self.hide_password)
        
        # Añadir elementos al contenedor de contraseña
        password_container_layout.addWidget(self.password_input)
        password_container_layout.addWidget(self.toggle_password_button)
        
        # Añadir contenedor al layout de contraseña
        password_layout.addWidget(password_label)
        password_layout.addWidget(password_container)
        layout.addLayout(password_layout)
        
        # Botones de login y salir
        btn_layout = QHBoxLayout()
        
        # Botón de login - Más grande
        self.login_button = QPushButton("Ingresar")
        self.login_button.setMinimumHeight(45)  # Altura aumentada
        self.login_button.setMinimumWidth(150)  # Ancho fijo más grande
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 15px;  /* Texto más grande */
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        
        # Botón de salir - Más grande y con mismo estilo visual
        self.exit_button = QPushButton("Salir")
        self.exit_button.setMinimumHeight(45)  # Altura aumentada
        self.exit_button.setMinimumWidth(150)  # Ancho fijo más grande
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 15px;  /* Texto más grande */
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a33428;
            }
        """)
        
        # Añadir botones al layout con espaciado
        btn_layout.addStretch()
        btn_layout.addWidget(self.login_button)
        btn_layout.addSpacing(30)  # Espacio aumentado entre botones
        btn_layout.addWidget(self.exit_button)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Etiqueta de mensaje (errores o éxito)
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(self.message_label)
        
        # Espacio adicional
        layout.addStretch()
        
        # Conectar señales
        self.login_button.clicked.connect(self.attempt_login)
        self.exit_button.clicked.connect(self.close)  # Conectar el botón salir
        self.password_input.returnPressed.connect(self.attempt_login)
        self.user_input.returnPressed.connect(lambda: self.password_input.setFocus())
        
        # Estilo global
        self.setStyleSheet("""
            QWidget {
                font-family: Arial, Helvetica, sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
            }
        """)
        
        # Centrar ventana en pantalla
        self.center_on_screen()
        
    def show_password(self):
        """Muestra la contraseña en texto plano mientras se presiona el botón"""
        self.password_input.setEchoMode(QLineEdit.Normal)
        
    def hide_password(self):
        """Oculta la contraseña cuando se suelta el botón"""
        self.password_input.setEchoMode(QLineEdit.Password)
        
    def center_on_screen(self):
        """Centra la ventana en la pantalla"""
        desktop_rect = QApplication.primaryScreen().availableGeometry()
        center = desktop_rect.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center)
        self.move(frame_geometry.topLeft())
    
    def attempt_login(self):
        """Intenta realizar el login con las credenciales proporcionadas"""
        username = self.user_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.show_message("Por favor ingrese usuario y contraseña", error=True)
            return
        
        # Deshabilitar botón durante la validación
        self.login_button.setEnabled(False)
        self.login_button.setText("Verificando...")
        QApplication.processEvents()
        
        # Validar credenciales usando DatabaseManager
        try:
            if DatabaseManager.validate_therapist(username, password):
                self.show_message("Login exitoso! Iniciando sesión...", error=False)
                # Emitir señal de éxito después de un breve retraso para dar feedback visual
                QTimer.singleShot(800, lambda: self.login_successful.emit(username))
            else:
                self.show_message("Usuario o contraseña incorrectos", error=True)
                self.login_button.setEnabled(True)
                self.login_button.setText("Ingresar")
                # Seleccionar el texto de la contraseña para facilitar reintento
                self.password_input.selectAll()
                self.password_input.setFocus()
        except Exception as e:
            self.show_message(f"Error de conexión: {str(e)}", error=True)
            self.login_button.setEnabled(True)
            self.login_button.setText("Ingresar")
    
    def show_message(self, message, error=True):
        """Muestra un mensaje en la etiqueta de mensajes"""
        self.message_label.setText(message)
        
        if error:
            self.message_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.message_label.setStyleSheet("color: #27ae60; font-weight: bold;")

    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        # Implementa presionar ESC para cerrar la ventana
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWidget()
    
    # Para pruebas, conectamos la señal a una función de ejemplo
    def on_login_success(username):
        QMessageBox.information(login_window, "Login Exitoso", 
                               f"Bienvenido/a, {username}!\nRedirigiendo al sistema principal...")
        login_window.close()
    
    login_window.login_successful.connect(on_login_success)
    login_window.show()
    
    sys.exit(app.exec())