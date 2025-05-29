import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QSizePolicy, QToolButton, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon
import hashlib

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager

class LoginWidget(QWidget):
    """Widget de login para el sistema EMDR Project"""
    
    # Señal emitida cuando el login es exitoso
    login_successful = Signal(str, str)  # Emite el nombre de usuario y el tipo
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("EMDR Project - Iniciar Sesión")
        self.setFixedSize(550, 750)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'icon.png')))
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 35, 40, 35)
        main_layout.setSpacing(25)
        
        # === HEADER CON TÍTULO ===
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #1565C0;
                border-radius: 12px;
                padding: 5px 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)
        
        # Logo o título principal
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
        else:
            # Si no hay logo, usar texto estilizado
            logo_label.setText("EMDR PROJECT")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 26px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
        
        # Subtítulo
        subtitle_label = QLabel("Iniciar Sesión")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #E3F2FD;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                margin-top: 5px;
            }
        """)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_frame)
        
        # === FORMULARIO DE LOGIN ===
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.StyledPanel)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
                padding: 5px;
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(5, 5, 5, 5)
        form_layout.setSpacing(20)
        
        # Selector de tipo de usuario
        role_container = QFrame()
        role_container.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #DADADA;
            }
        """)
        
        role_layout = QHBoxLayout(role_container)
        role_layout.setContentsMargins(10, 5, 10, 5)
        
        role_label = QLabel("Seleccione su Rol:")
        role_label.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
        """)
        
        self.user_type_combo = QComboBox()
        self.user_type_combo.addItems(["Terapeuta", "Administrador"])
        self.user_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 2px solid #BDBDBD;
                        border-radius: 6px;
                font-size: 14px;
                min-width: 150px;
            }
            QComboBox:focus {
                border: 2px solid #1565C0;
            }
        """)
        
        role_layout.addWidget(role_label)
        role_layout.addStretch()
        role_layout.addWidget(self.user_type_combo)
        
        form_layout.addWidget(role_container)
        
        # Campo de usuario
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ingrese su Usuario")
        self.user_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 12px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #1565C0;
                background-color: #FAFAFA;
            }
            QLineEdit::placeholder {
                color: #9E9E9E;
                font-style: italic;
            }
        """)
        
        form_layout.addWidget(self.user_input)
        
        # Campo de contraseña con botón para ver
        password_container = QFrame()
        password_container.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent;
                padding: 0px;
            }
        """)
        password_container_layout = QHBoxLayout(password_container)
        password_container_layout.setContentsMargins(0, 0, 0, 0)
        password_container_layout.setSpacing(0)
        
        # Campo de contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Ingrese su Contraseña")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 12px;
                border: 2px solid #E0E0E0;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border-right: none;
                background-color: white;
                font-size: 14px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #1565C0;
                border-right: none;
                background-color: #FAFAFA;
            }
            QLineEdit::placeholder {
                color: #9E9E9E;
                font-style: italic;
            }
        """)
        
        # Botón para ver contraseña
        self.toggle_password_button = QToolButton()
        self.toggle_password_button.setToolTip("Mantener presionado para ver contraseña")
        self.toggle_password_button.setText("👁")
        self.toggle_password_button.setFixedSize(50, 49)
        self.toggle_password_button.setCursor(Qt.PointingHandCursor)
        self.toggle_password_button.setStyleSheet("""
            QToolButton {
                border: 2px solid #E0E0E0;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #F5F5F5;
                font-size: 16px;
            }
            QToolButton:hover {
                background-color: #EEEEEE;
                border-color: #BDBDBD;
            }
            QToolButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        
        # Eventos para mostrar/ocultar contraseña
        self.toggle_password_button.pressed.connect(self.show_password)
        self.toggle_password_button.released.connect(self.hide_password)
        
        # Añadir elementos al contenedor de contraseña
        password_container_layout.addWidget(self.password_input)
        password_container_layout.addWidget(self.toggle_password_button)
        
        form_layout.addWidget(password_container)
        
        main_layout.addWidget(form_frame)
        
        # === BOTONES DE ACCIÓN ===
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent;
                padding: 0px;
            }
        """)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(20)
        
        # Botón de login
        self.login_button = QPushButton("Ingresar")
        self.login_button.setFixedSize(180, 50)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #4CAF50;
            }
            QPushButton:hover {
                background-color: #66BB6A;
                border: 2px solid #66BB6A;
            }
            QPushButton:pressed {
                background-color: #388E3C;
                border: 2px solid #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                border: 2px solid #BDBDBD;
                color: #757575;
            }
        """)
        
        # Botón de salir
        self.exit_button = QPushButton("Salir")
        self.exit_button.setFixedSize(180, 50)
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #F44336;
            }
            QPushButton:hover {
                background-color: #EF5350;
                border: 2px solid #EF5350;
            }
            QPushButton:pressed {
                background-color: #D32F2F;
                border: 2px solid #D32F2F;
            }
        """)
        
        # Añadir botones al layout
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.exit_button)
        buttons_layout.addStretch()
        
        main_layout.addWidget(buttons_frame)
        
        # === ETIQUETA DE MENSAJE ===
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFixedHeight(30)
        self.message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                padding: 5px;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.message_label)
        
        # === ESPACIADOR FINAL ===
        main_layout.addStretch()
        
        # === FOOTER ===
        footer_label = QLabel("Sistema de Terapia EMDR - Versión 1.0")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                color: #757575;
                font-size: 12px;
                font-style: italic;
            }
        """)
        main_layout.addWidget(footer_label)
        
        # Conectar señales
        self.login_button.clicked.connect(self.attempt_login)
        self.exit_button.clicked.connect(self.close)
        self.password_input.returnPressed.connect(self.attempt_login)
        self.user_input.returnPressed.connect(lambda: self.password_input.setFocus())
        
        # Estilo global de la ventana
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #F8F9FA;
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
        user_type = "terapeutas" if self.user_type_combo.currentText() == "Terapeuta" else "administradores"
        
        if not username or not password:
            self.show_message("Por favor ingrese usuario y contraseña", error=True)
            return
        
        # Deshabilitar botón durante la validación
        self.login_button.setEnabled(False)
        self.login_button.setText("Verificando...")
        QApplication.processEvents()
        
        # Validar credenciales usando DatabaseManager
        try:
            success = False
            
            if user_type == "terapeutas":
                success = DatabaseManager.validate_therapist_credentials(username, password)
            else:  # administradores
                success = DatabaseManager.validate_admin_credentials(username, password)
            
            if success:
                self.show_message("Login exitoso! Iniciando sesión...", error=False)
                # Emitir señal de éxito después de un breve retraso para dar feedback visual
                QTimer.singleShot(800, lambda: self.login_successful.emit(username, user_type))
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
    def on_login_success(username, user_type):
        QMessageBox.information(login_window, "Login Exitoso", 
                               f"Bienvenido/a, {username}!\nRedirigiendo al sistema principal...")
        login_window.close()
    
    login_window.login_successful.connect(on_login_success)
    login_window.show()
    
    sys.exit(app.exec())