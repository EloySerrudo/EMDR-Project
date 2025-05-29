import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
from pathlib import Path
from datetime import datetime  # Añadir esta importación

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para componentes específicos
from src.database.database_manager import DatabaseManager
from src.views.control_panel import EMDRControlPanel
from src.views.patient_manager import PatientManagerWidget


class TherapistDashboard(QMainWindow):
    """Dashboard principal para terapeutas autenticados"""
    
    # Señal emitida cuando se solicita cerrar sesión
    logout_requested = Signal()
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.therapist_data = None
        self.control_panel_window = None
        self.patient_manager_window = None
        
        # Cargar datos del terapeuta
        self.load_therapist_data()
        
        # Configurar la ventana
        self.setup_window()
        
        # Configurar la interfaz
        self.setup_ui()
    
    def load_therapist_data(self):
        """Carga los datos del terapeuta desde la base de datos"""
        try:
            self.therapist_data = DatabaseManager.get_therapist_by_username(self.username)
            if not self.therapist_data:
                QMessageBox.critical(self, "Error", "No se pudieron cargar los datos del terapeuta")
                self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos del terapeuta: {str(e)}")
            self.close()
    
    def setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle("EMDR Project - Dashboard Terapéutico")
        self.setFixedSize(600, 600)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'icon.png')))
        
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
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)  # Reducido de 25 a 20
        
        # === HEADER CON LOGO ===
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #1565C0;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)
        
        # Logo o título
        logo_label = QLabel("EMDR PROJECT")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
                padding: 3px;
            }
        """)
        header_layout.addWidget(logo_label)
        
        main_layout.addWidget(header_frame)
        
        # === MENSAJE DE SALUDO ===
        greeting_frame = QFrame()
        greeting_frame.setFrameShape(QFrame.StyledPanel)
        greeting_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        greeting_layout = QVBoxLayout(greeting_frame)
        greeting_layout.setSpacing(6)
        
        # Mensaje de saludo personalizado
        if self.therapist_data:
            nombre_completo = f"{self.therapist_data['nombre']} {self.therapist_data['apellido_paterno']}"
            
            # Determinar saludo según género (0 = masculino, 1 = femenino)
            genero = self.therapist_data.get('genero', 0)
            saludo_genero = "Bienvenido" if genero == 0 else "Bienvenida"
            
            # Determinar saludo según la hora del día
            hora_actual = datetime.now().hour
            
            if 5 <= hora_actual < 12:
                saludo_hora = "Buenos días"
            elif 12 <= hora_actual < 18:
                saludo_hora = "Buenas tardes"
            else:
                saludo_hora = "Buenas noches"
            
            # Etiqueta de saludo
            greeting_label = QLabel(f"{saludo_hora}, Lic. {nombre_completo}")
            greeting_label.setAlignment(Qt.AlignCenter)
            greeting_label.setStyleSheet("""
                QLabel {
                    color: #1565C0;
                    font-size: 18px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
            
            # Etiqueta de bienvenida
            welcome_label = QLabel(f"{saludo_genero} al Sistema EMDR")
            welcome_label.setAlignment(Qt.AlignCenter)
            welcome_label.setStyleSheet("""
                QLabel {
                    color: #1976D2;
                    font-size: 16px;
                    background: transparent;
                }
            """)
            
            greeting_layout.addWidget(greeting_label)
            greeting_layout.addWidget(welcome_label)
        else:
            # Fallback si no hay datos
            fallback_label = QLabel("¡Bienvenido al Sistema EMDR!")
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet("""
                QLabel {
                    color: #1565C0;
                    font-size: 16px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
            greeting_layout.addWidget(fallback_label)
        
        main_layout.addWidget(greeting_frame)
        
        # === MENSAJE INSTRUCTIVO ===
        # Mensaje instructivo (sin QFrame)
        instruction_label = QLabel("💡 Seleccione una opción para continuar con su sesión de trabajo")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                border-radius: 6px;
                border: 1px solid #FFB74D;
                padding: 8px;
                color: #E65100;
                font-size: 14px;
                font-weight: 500;
                font-style: italic;
            }
        """)

        main_layout.addWidget(instruction_label)
        
        # === BOTONES PRINCIPALES GRANDES ===
        main_buttons_frame = QFrame()
        main_buttons_layout = QGridLayout(main_buttons_frame)
        main_buttons_layout.setSpacing(18)  # Reducido de 20 a 18
        
        # Botón Control Panel
        self.control_panel_btn = QPushButton()
        self.control_panel_btn.setText("Panel de Control\nEMDR")
        self.control_panel_btn.setFixedSize(210, 110)  # Reducido ligeramente
        self.control_panel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
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
        """)
        self.control_panel_btn.clicked.connect(self.open_control_panel)
        
        # Botón Patient Manager
        self.patient_manager_btn = QPushButton()
        self.patient_manager_btn.setText("Gestión de\nPacientes")
        self.patient_manager_btn.setFixedSize(210, 110)  # Reducido ligeramente
        self.patient_manager_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #2196F3;
            }
            QPushButton:hover {
                background-color: #42A5F5;
                border: 2px solid #42A5F5;
            }
            QPushButton:pressed {
                background-color: #1976D2;
                border: 2px solid #1976D2;
            }
        """)
        self.patient_manager_btn.clicked.connect(self.open_patient_manager)
        
        # Añadir botones al grid (1 fila, 2 columnas)
        main_buttons_layout.addWidget(self.control_panel_btn, 0, 0, Qt.AlignCenter)
        main_buttons_layout.addWidget(self.patient_manager_btn, 0, 1, Qt.AlignCenter)
        
        main_layout.addWidget(main_buttons_frame)
        
        # === BOTONES SECUNDARIOS PEQUEÑOS ===
        secondary_buttons_frame = QFrame()
        secondary_buttons_layout = QHBoxLayout(secondary_buttons_frame)
        secondary_buttons_layout.setSpacing(15)
        
        # Botón Cerrar Sesión
        self.logout_btn = QPushButton("Cerrar Sesión")
        self.logout_btn.setFixedSize(140, 35)  # Reducido ligeramente
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #FF9800;
            }
            QPushButton:hover {
                background-color: #FFB74D;
                border: 1px solid #FFB74D;
            }
            QPushButton:pressed {
                background-color: #F57C00;
                border: 1px solid #F57C00;
            }
        """)
        self.logout_btn.clicked.connect(self.logout)
        
        # Botón Salir
        self.exit_btn = QPushButton("Salir")
        self.exit_btn.setFixedSize(140, 35)  # Reducido ligeramente
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #F44336;
            }
            QPushButton:hover {
                background-color: #EF5350;
                border: 1px solid #EF5350;
            }
            QPushButton:pressed {
                background-color: #D32F2F;
                border: 1px solid #D32F2F;
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
                color: #757575;
                font-size: 11px;
                font-style: italic;
            }
        """)
        main_layout.addWidget(footer_label)
        
        # Estilo global de la ventana
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FAFAFA;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
    
    def open_control_panel(self):
        """Abre la ventana del panel de control EMDR"""
        try:
            # Cerrar ventana anterior si existe
            if self.control_panel_window:
                self.control_panel_window.close()
            
            # Crear nueva ventana del panel de control
            self.control_panel_window = EMDRControlPanel(self.username)
            self.control_panel_window.showMaximized()
            
            # Ocultar el dashboard
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el panel de control: {str(e)}")
    
    def open_patient_manager(self):
        """Abre la ventana del gestor de pacientes"""
        try:
            # Cerrar ventana anterior si existe
            if self.patient_manager_window:
                self.patient_manager_window.close()
            
            # Crear nueva ventana del gestor de pacientes
            self.patient_manager_window = PatientManagerWidget(self.username)
            self.patient_manager_window.showMaximized()
            
            # Ocultar el dashboard
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el gestor de pacientes: {str(e)}")
    
    def logout(self):
        """Cierra la sesión actual y regresa al login"""
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión actual?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Cerrar ventanas abiertas
            if self.control_panel_window:
                self.control_panel_window.close()
            if self.patient_manager_window:
                self.patient_manager_window.close()
            
            # Emitir señal de logout (NO cerrar la ventana aquí)
            self.logout_requested.emit()
            
            # El cierre de la ventana se manejará desde main.py
            # No llamar self.close() aquí
    
    def exit_application(self):
        """Cierra completamente la aplicación"""
        reply = QMessageBox.question(
            self,
            "Salir",
            "¿Está seguro de que desea salir de la aplicación?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Cerrar todas las ventanas
            if self.control_panel_window:
                self.control_panel_window.close()
            if self.patient_manager_window:
                self.patient_manager_window.close()
            
            # Cerrar aplicación completamente
            QApplication.quit()
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        # Cuando se cierre el dashboard, también cerrar ventanas hijas
        if self.control_panel_window:
            self.control_panel_window.close()
        if self.patient_manager_window:
            self.patient_manager_window.close()
        
        event.accept()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear dashboard de prueba (necesita un username válido en la BD)
    dashboard = TherapistDashboard("dra.valdivia")  # Usar el usuario de ejemplo
    
    # Manejar la señal de logout para pruebas
    def on_logout():
        print("Logout solicitado")
        app.quit()
    
    dashboard.logout_requested.connect(on_logout)
    dashboard.show()
    
    sys.exit(app.exec())