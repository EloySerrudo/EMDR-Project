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
import qtawesome as qta

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

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
        self.setFixedSize(400, 650)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent.parent / 'resources' / 'emdr_icon.png')))
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # === HEADER CON TÍTULO ===
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background: qconicalgradient(cx: 0.5, cy: 0.5, angle: 0,
                                           stop: 0 rgba(120, 255, 180, 0.9),
                                           stop: 0.2 rgba(0, 230, 140, 0.8),
                                           stop: 0.4 rgba(0, 169, 157, 0.85),
                                           stop: 0.6 rgba(0, 140, 130, 0.8),
                                           stop: 0.8 rgba(0, 200, 160, 0.85),
                                           stop: 1 rgba(120, 255, 180, 0.9));
                border-radius: 12px;
                border-top: 2px solid rgba(200, 255, 220, 0.8);
                border-left: 1px solid rgba(255, 255, 255, 0.6);
                border-right: 1px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.4);
                padding: 5px 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(5)
        
        # Logo o título principal
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    border: none;
                    outline: none;
                    background: transparent;
                }
            """)
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
        subtitle_label = QLabel("INGRESO AL SISTEMA")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                margin-top: 5px;
                border: none;
                outline: none;
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
                background-color: #323232;
                border-radius: 10px;
                border: 2px solid #444444;
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
                background-color: #424242;
                border-radius: 8px;
                padding: 4px 8px;
                border: 2px solid #555555;
            }
        """)
        
        role_layout = QHBoxLayout(role_container)
        role_layout.setContentsMargins(7, 2, 7, 2)
        
        role_label = QLabel("Seleccione su Rol:")
        role_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                padding: 0px;
                border: none;
                outline: none;
            }
        """)
        
        self.user_type_combo = QComboBox()
        self.user_type_combo.addItems(["Terapeuta", "Administrador"])

        # Configurar íconos para el combo box usando setItemIcon
        self.combo_arrow_down = qta.icon('fa5s.chevron-down', color='#FFFFFF')
        self.combo_arrow_up = qta.icon('fa5s.chevron-up', color='#FFFFFF')
        self.user_icon = qta.icon('fa5s.user', color='#FFFFFF')
        self.admin_icon = qta.icon('fa5s.user-shield', color='#FFFFFF')

        # Establecer íconos para cada elemento del combo
        self.user_type_combo.setItemIcon(0, self.user_icon)  # Terapeuta
        self.user_type_combo.setItemIcon(1, self.admin_icon)  # Administrador

        self.user_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px 8px 12px;
                border: 2px solid #555555;
                border-radius: 6px;
                font-size: 14px;
                min-width: 100px;
                background-color: #424242;
                color: white;
                icon-size: 16px;
            }
            QComboBox:focus {
                border: 2px solid #00A99D;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #555555;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #333333;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #424242;
                color: white;
                selection-background-color: #00A99D;
                border: 1px solid #555555;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                height: 30px;
                padding: 5px;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #00A99D;
            }
        """)

        # Para el ícono del dropdown, usaremos un QLabel personalizado
        self.dropdown_arrow_label = QLabel()
        self.dropdown_arrow_label.setPixmap(self.combo_arrow_down.pixmap(16, 16))
        self.dropdown_arrow_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        # Crear un layout para superponer el ícono de flecha
        combo_container = QFrame()
        combo_container.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent; 
                padding: 0px; 
            }
        """)
        combo_layout = QHBoxLayout(combo_container)
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(0)

        combo_layout.addWidget(self.user_type_combo)

        # Posicionar el ícono de flecha sobre el combo box
        self.dropdown_arrow_label.setParent(self.user_type_combo)
        self.dropdown_arrow_label.move(self.user_type_combo.width() - 25, 
                                       (self.user_type_combo.height() - 16) // 2)

        # Conectar eventos para cambiar el ícono cuando se despliega/colapsa
        self.user_type_combo.showPopup = self.combo_show_popup
        self.user_type_combo.hidePopup = self.combo_hide_popup

        # También conectar el evento de resize para reposicionar la flecha
        self.user_type_combo.resizeEvent = self.combo_resize_event

        role_layout.addWidget(role_label)
        role_layout.addStretch()
        role_layout.addWidget(combo_container)
        
        form_layout.addWidget(role_container)
        
        # Campo de usuario
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ingrese su Usuario")
        self.user_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 12px;
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #424242;
                font-size: 14px;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #00A99D;
                background-color: #383838;
            }
            QLineEdit::placeholder {
                color: #AAAAAA;
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
                border: 2px solid #555555;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border-right: none;
                background-color: #424242;
                font-size: 14px;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #00A99D;
                border-right: none;
                background-color: #383838;
            }
            QLineEdit::placeholder {
                color: #AAAAAA;
                font-style: italic;
            }
        """)
        
        # Botón para ver contraseña
        self.toggle_password_button = QToolButton()
        self.toggle_password_button.setToolTip("Mantener presionado para ver contraseña")
        
        # Configurar ícono inicial (ojo cerrado/tachado)
        self.eye_closed_icon = qta.icon('fa5s.eye-slash', color='#FFFFFF')
        self.eye_open_icon = qta.icon('fa5s.eye', color='#FFFFFF')

        # Establecer ícono inicial (cerrado)
        self.toggle_password_button.setIcon(self.eye_closed_icon)
        
        self.toggle_password_button.setFixedSize(50, 49)
        self.toggle_password_button.setCursor(Qt.PointingHandCursor)
        
        # Estilos inicial y focused para el botón
        self.toggle_button_normal_style = """
            QToolButton {
                border: 2px solid #555555;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #333333;
                font-size: 16px;
                color: #FFFFFF;
            }
            QToolButton:hover {
                background-color: #424242;
            }
            QToolButton:pressed {
                border: 2px solid #00A99D;
                border-left: none;
                background-color: #00A99D;
            }
        """
        
        self.toggle_button_focused_style = """
            QToolButton {
                border: 2px solid #00A99D;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #333333;
                font-size: 16px;
                color: #FFFFFF;
            }
            QToolButton:hover {
                background-color: #424242;
            }
            QToolButton:pressed {
                border: 2px solid #00A99D;
                border-left: none;
                background-color: #00A99D;
            }
        """
        
        # Aplicar estilo inicial
        self.toggle_password_button.setStyleSheet(self.toggle_button_normal_style)
        
        # Conectar eventos de focus del password_input
        self.password_input.focusInEvent = self.on_password_focus_in
        self.password_input.focusOutEvent = self.on_password_focus_out
        
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
        self.login_button.setFixedSize(150, 50)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #00A99D;
            }
            QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
            QPushButton:disabled {
                background-color: #555555;
                border: 2px solid #555555;
                color: #888888;
            }
        """)
        
        # Botón de salir
        self.exit_button = QPushButton("Salir")
        self.exit_button.setFixedSize(150, 50)
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #424242;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 2px solid #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
                border: 2px solid #333333;
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
                background: transparent;
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
                color: #AAAAAA;
                font-size: 12px;
                font-style: italic;
                background: transparent;
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
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
                color: #FFFFFF;
            }
        """)
        
        # Centrar ventana en pantalla
        self.center_on_screen()
        
    def show_password(self):
        """Muestra la contraseña en texto plano mientras se presiona el botón"""
        self.password_input.setEchoMode(QLineEdit.Normal)
        # Cambiar ícono a ojo abierto
        self.toggle_password_button.setIcon(self.eye_open_icon)
        
    def hide_password(self):
        """Oculta la contraseña cuando se suelta el botón"""
        self.password_input.setEchoMode(QLineEdit.Password)
        # Cambiar ícono a ojo cerrado/tachado
        self.toggle_password_button.setIcon(self.eye_closed_icon)
        
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
            self.message_label.setStyleSheet("color: #e74c3c; font-weight: bold; background: transparent;")
        else:
            self.message_label.setStyleSheet("color: #27ae60; font-weight: bold; background: transparent;")

    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        # Implementa presionar ESC para cerrar la ventana
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def on_password_focus_in(self, event):
        """Se ejecuta cuando password_input recibe el focus"""
        # Aplicar estilo con border azul al botón
        self.toggle_password_button.setStyleSheet(self.toggle_button_focused_style)
        # Llamar al evento original
        QLineEdit.focusInEvent(self.password_input, event)

    def on_password_focus_out(self, event):
        """Se ejecuta cuando password_input pierde el focus"""
        # Aplicar estilo normal al botón
        self.toggle_password_button.setStyleSheet(self.toggle_button_normal_style)
        # Llamar al evento original
        QLineEdit.focusOutEvent(self.password_input, event)

    def combo_show_popup(self):
        """Sobrescribe el método showPopup para cambiar el ícono"""
        self.dropdown_arrow_label.setPixmap(self.combo_arrow_up.pixmap(16, 16))
        QComboBox.showPopup(self.user_type_combo)

    def combo_hide_popup(self):
        """Sobrescribe el método hidePopup para cambiar el ícono"""
        self.dropdown_arrow_label.setPixmap(self.combo_arrow_down.pixmap(16, 16))
        QComboBox.hidePopup(self.user_type_combo)

    def combo_resize_event(self, event):
        """Reposiciona la flecha cuando el combo se redimensiona"""
        QComboBox.resizeEvent(self.user_type_combo, event)
        self.dropdown_arrow_label.move(self.user_type_combo.width() - 25, 
                                       (self.user_type_combo.height() - 16) // 2)

    def on_combo_expanded(self):
        """Se ejecuta cuando el combo box se expande"""
        self.dropdown_arrow_label.setPixmap(self.combo_arrow_up.pixmap(16, 16))

    def on_combo_collapsed(self):
        """Se ejecuta cuando el combo box se colapsa"""
        self.dropdown_arrow_label.setPixmap(self.combo_arrow_down.pixmap(16, 16))


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