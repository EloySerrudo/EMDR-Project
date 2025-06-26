import sys
import os
import winsound
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
from pathlib import Path
from datetime import datetime

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para componentes específicos
from src.database.database_manager import DatabaseManager
from src.views.admin_panel import AdminPanel


class AdminDashboard(QMainWindow):
    """Dashboard principal para administradores autenticados"""
    
    # Señal emitida cuando se solicita cerrar sesión
    logout_requested = Signal()
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.admin_data = None
        self.eog_test_window = None
        self.admin_panel_window = None
        
        # Cargar datos del administrador
        self.load_admin_data()
        
        # Configurar la ventana
        self.setup_window()
        
        # Configurar la interfaz
        self.setup_ui()
    
    def load_admin_data(self):
        """Carga los datos del administrador desde la base de datos"""
        try:
            self.admin_data = DatabaseManager.get_admin_by_username(self.username)
            if not self.admin_data:
                print(f"No se encontraron datos para el administrador: {self.username}")
        except Exception as e:
            print(f"Error al cargar datos del administrador: {e}")
            self.admin_data = None
    
    def setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle("EMDR Project - Dashboard Administrativo")
        self.setFixedSize(600, 650)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'emdr_icon.png')))
        
        # Centrar ventana en pantalla
        self.center_on_screen()
    
    def center_on_screen(self):
        """Centra la ventana en la pantalla"""
        desktop_rect = QApplication.primaryScreen().availableGeometry()
        center = desktop_rect.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center)
        self.move(frame_geometry.topLeft())
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # === HEADER CON LOGO ===
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
        logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(260, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
        else:
            logo_label.setText("EMDR PROJECT")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setFont(QFont('Arial', 24, QFont.Bold))
            logo_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    background: transparent;
                    border: none;
                    outline: none;
                }
            """)
        
        # Subtítulo
        subtitle_label = QLabel("CONTROL ADMINISTRATIVO")
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
        
        # === MENSAJE DE SALUDO ===
        greeting_frame = QFrame()
        greeting_frame.setFrameShape(QFrame.StyledPanel)
        greeting_frame.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border-radius: 10px;
                padding: 5px;
                border: 1px solid #555555;
            }
        """)
        
        greeting_layout = QVBoxLayout(greeting_frame)
        greeting_layout.setSpacing(0)
        
        # Mensaje de saludo personalizado
        if self.admin_data:
            greeting_text = f"🔧 Bienvenido/a, {self.admin_data.get('nombre', 'Administrador')}"
            role_text = "Administrador del Sistema"
            access_text = f"Último acceso: {datetime.now().strftime('%d/%m/%Y - %H:%M')}"
        else:
            greeting_text = f"🔧 Bienvenido/a, {self.username}"
            role_text = "Administrador del Sistema"
            access_text = f"Último acceso: {datetime.now().strftime('%d/%m/%Y - %H:%M')}"
        
        greeting_label = QLabel(greeting_text)
        greeting_label.setAlignment(Qt.AlignCenter)
        greeting_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                padding: 8px;
            }
        """)
        
        role_label = QLabel(role_text)
        role_label.setAlignment(Qt.AlignCenter)
        role_label.setStyleSheet("""
            QLabel {
                color: #00A99D;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                padding: 2px;
            }
        """)
        
        access_label = QLabel(access_text)
        access_label.setAlignment(Qt.AlignCenter)
        access_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                background: transparent;
                padding: 2px;
            }
        """)
        
        greeting_layout.addWidget(greeting_label)
        greeting_layout.addWidget(role_label)
        greeting_layout.addWidget(access_label)
        
        main_layout.addWidget(greeting_frame)
        
        # === MENSAJE INSTRUCTIVO ===
        instruction_label = QLabel("⚙️ Seleccione una opción para administrar el sistema")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("""
            QLabel {
                background-color: #323232;
                border-radius: 8px;
                border: 1px solid #555555;
                padding: 12px;
                color: #00A99D;
                font-size: 14px;
                font-weight: 500;
                font-style: italic;
            }
        """)

        main_layout.addWidget(instruction_label)
        
        # === BOTONES PRINCIPALES GRANDES ===
        main_buttons_frame = QFrame()
        main_buttons_frame.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent;
                padding: 0px;
            }
        """)
        main_buttons_layout = QHBoxLayout(main_buttons_frame)
        main_buttons_layout.setContentsMargins(0, 0, 0, 0)
        main_buttons_layout.setSpacing(100)
        
        # Botón Prueba de EOG
        self.eog_test_btn = QPushButton()
        self.eog_test_btn.setText("Prueba de\nEOG")
        self.eog_test_btn.setFixedSize(150, 110)
        self.eog_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border-top: 2px solid #00E6D6;
                border-left: 2px solid #00D4C4;
                border-right: 2px solid #006B61;
                border-bottom: 2px solid #005A50;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #00C2B3;
                border-top: 2px solid #00F5E5;
                border-left: 2px solid #00E6D6;
                border-right: 2px solid #007A70;
                border-bottom: 2px solid #00695F;
            }
            QPushButton:pressed {
                background-color: #008C82;
                border-top: 2px solid #005A50;
                border-left: 2px solid #006B61;
                border-right: 2px solid #00C2B3;
                border-bottom: 2px solid #00D4C4;
                padding: 5px 1px 1px 5px;
            }
        """)
        self.eog_test_btn.clicked.connect(self.open_eog_test)
        
        # Botón Gestión de Usuarios
        self.user_management_btn = QPushButton()
        self.user_management_btn.setText("Gestión de\nUsuarios")
        self.user_management_btn.setFixedSize(150, 110)
        self.user_management_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border-top: 2px solid #00E6D6;
                border-left: 2px solid #00D4C4;
                border-right: 2px solid #006B61;
                border-bottom: 2px solid #005A50;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #00C2B3;
                border-top: 2px solid #00F5E5;
                border-left: 2px solid #00E6D6;
                border-right: 2px solid #007A70;
                border-bottom: 2px solid #00695F;
            }
            QPushButton:pressed {
                background-color: #008C82;
                border-top: 2px solid #005A50;
                border-left: 2px solid #006B61;
                border-right: 2px solid #00C2B3;
                border-bottom: 2px solid #00D4C4;
                padding: 5px 1px 1px 5px;
            }
        """)
        self.user_management_btn.clicked.connect(self.open_user_management)
        
        # Añadir botones con espaciado
        main_buttons_layout.addStretch()
        main_buttons_layout.addWidget(self.eog_test_btn)
        main_buttons_layout.addWidget(self.user_management_btn)
        main_buttons_layout.addStretch()
        
        main_layout.addWidget(main_buttons_frame)
        
        # === BOTONES SECUNDARIOS PEQUEÑOS ===
        secondary_buttons_frame = QFrame()
        secondary_buttons_frame.setStyleSheet("""
            QFrame { 
                border: none; 
                background: transparent;
                padding: 0px;
            }
        """)
        secondary_buttons_layout = QHBoxLayout(secondary_buttons_frame)
        secondary_buttons_layout.setContentsMargins(0, 0, 0, 0)
        secondary_buttons_layout.setSpacing(100)
        
        # Botón Cerrar Sesión
        self.logout_btn = QPushButton("Cerrar Sesión")
        self.logout_btn.setFixedSize(150, 50)
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                border-top: 1px solid #777777;
                border-left: 1px solid #666666;
                border-right: 1px solid #222222;
                border-bottom: 1px solid #111111;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #555555;
                border-top: 1px solid #888888;
                border-left: 1px solid #777777;
                border-right: 1px solid #333333;
                border-bottom: 1px solid #222222;
            }
            QPushButton:pressed {
                background-color: #333333;
                border-top: 1px solid #111111;
                border-left: 1px solid #222222;
                border-right: 1px solid #666666;
                border-bottom: 1px solid #777777;
                padding: 4px 0px 0px 4px;
            }
        """)
        self.logout_btn.clicked.connect(self.logout)
        
        # Botón Salir
        self.exit_btn = QPushButton("Salir")
        self.exit_btn.setFixedSize(150, 50)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                border-top: 1px solid #777777;
                border-left: 1px solid #666666;
                border-right: 1px solid #222222;
                border-bottom: 1px solid #111111;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #555555;
                border-top: 1px solid #888888;
                border-left: 1px solid #777777;
                border-right: 1px solid #333333;
                border-bottom: 1px solid #222222;
            }
            QPushButton:pressed {
                background-color: #333333;
                border-top: 1px solid #111111;
                border-left: 1px solid #222222;
                border-right: 1px solid #666666;
                border-bottom: 1px solid #777777;
                padding: 4px 0px 0px 4px;
            }
        """)
        self.exit_btn.clicked.connect(self.exit_application)
        
        # Añadir botones secundarios con espaciado
        secondary_buttons_layout.addStretch()
        secondary_buttons_layout.addWidget(self.logout_btn)
        secondary_buttons_layout.addWidget(self.exit_btn)
        secondary_buttons_layout.addStretch()
        
        main_layout.addWidget(secondary_buttons_frame)
        
        # === ESPACIADOR FINAL ===
        main_layout.addStretch()
        
        # === FOOTER CON INFO ADICIONAL ===
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
    
    def open_eog_test(self):
        """Abre la ventana de prueba de EOG (placeholder por ahora)"""
        try:
            # Placeholder para la futura ventana de prueba de EOG
            QMessageBox.information(
                self,
                "Prueba de EOG",
                "Esta funcionalidad será implementada próximamente.\n\n"
                "Aquí se podrán realizar:\n"
                "• Calibraciones del sistema EOG\n"
                "• Pruebas de señales\n"
                "• Configuración de sensores\n"
                "• Diagnósticos del sistema",
                QMessageBox.Ok
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir la prueba de EOG:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def open_user_management(self):
        """Abre la ventana de gestión de usuarios (AdminPanel)"""
        try:
            # Cerrar ventana anterior si existe
            if self.admin_panel_window:
                self.admin_panel_window.close()
            
            # Crear nueva ventana del panel de administración
            self.admin_panel_window = AdminPanel(self.username)
            
            # Si AdminPanel tiene señal de retorno, conectarla
            if hasattr(self.admin_panel_window, 'return_to_dashboard'):
                self.admin_panel_window.return_to_dashboard.connect(self.show_dashboard_on_return)
            
            # Ocultar el dashboard y mostrar el panel de administración
            self.hide()
            self.admin_panel_window.showMaximized()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir la gestión de usuarios:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def show_dashboard_on_return(self):
        """Muestra el dashboard cuando se regresa desde otra ventana"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def logout(self):
        """Cierra la sesión actual y regresa al login"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Cerrar Sesión")
        msg_box.setText("¿Está seguro de que desea cerrar la sesión actual?")
        msg_box.setIcon(QMessageBox.Question)
        
        # Crear botones personalizados
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        # Aplicar estilo personalizado
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #323232;
                color: #FFFFFF;
                border-top: none;
                border-left: 2px solid #555555;
                border-right: 2px solid #555555;
                border-bottom: 2px solid #555555;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
                background: transparent;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #00A99D;
                color: white;
                border: 2px solid #00A99D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 50px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QMessageBox QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
        """)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            self.logout_requested.emit()
    
    def exit_application(self):
        """Cierra completamente la aplicación"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Salir")
        msg_box.setText("¿Está seguro de que desea salir de la aplicación?")
        msg_box.setIcon(QMessageBox.Question)
        
        # Crear botones personalizados
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_button)
        
        # Aplicar estilo personalizado
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #323232;
                color: #FFFFFF;
                border-top: none;
                border-left: 2px solid #555555;
                border-right: 2px solid #555555;
                border-bottom: 2px solid #555555;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
                background: transparent;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #00A99D;
                color: white;
                border: 2px solid #00A99D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 50px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00C2B3;
                border: 2px solid #00C2B3;
            }
            QMessageBox QPushButton:pressed {
                background-color: #008C82;
                border: 2px solid #008C82;
            }
        """)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            QApplication.quit()
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        # Cuando se cierre el dashboard, también cerrar ventanas hijas
        if self.eog_test_window:
            self.eog_test_window.close()
        if self.admin_panel_window:
            self.admin_panel_window.close()
        
        event.accept()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear dashboard de prueba (necesita un username válido en la BD)
    dashboard = AdminDashboard("admin")  # Usar un usuario administrador de ejemplo
    
    # Manejar la señal de logout para pruebas
    def on_logout():
        print("Logout solicitado")
        app.quit()
    
    dashboard.logout_requested.connect(on_logout)
    dashboard.show()
    
    sys.exit(app.exec())
