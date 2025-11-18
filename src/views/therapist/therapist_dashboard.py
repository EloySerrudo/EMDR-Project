import sys
import os
import winsound
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox, QSizePolicy, QDialog,
    QLineEdit, QTextEdit, QDateEdit, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QPixmap, QIcon
from pathlib import Path
from datetime import datetime  # Añadir esta importación

# Importaciones para componentes específicos
from views.therapist.add_patient_dialog import AddPatientDialog
from database.database_manager import DatabaseManager
from views.therapist.patient_manager import PatientManagerWidget


class TherapistDashboard(QMainWindow):
    """Dashboard principal para terapeutas autenticados"""
    
    # Señal emitida cuando se solicita cerrar sesión
    logout_requested = Signal()
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.therapist_data = None
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
        self.setFixedSize(600, 650)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent.parent / 'resources' / 'emdr_icon.png')))
        
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
        subtitle_label = QLabel("CONTROL DE USUARIO")
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
        if self.therapist_data:
            self.nombre_completo = f"{self.therapist_data['nombre']} {self.therapist_data['apellido_paterno']}"
            
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
            greeting_label = QLabel(f"{saludo_hora}, Lic. {self.nombre_completo}")
            greeting_label.setAlignment(Qt.AlignCenter)
            greeting_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 18px;
                    font-weight: bold;
                    background: transparent;
                    padding: 0px;
                    border: none;
                    outline: none;
                }
            """)
            
            # Etiqueta de bienvenida
            welcome_label = QLabel(f"{saludo_genero} al Sistema de apoyo de EMDR")
            welcome_label.setAlignment(Qt.AlignCenter)
            welcome_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 16px;
                    background: transparent;
                    padding: 0px;
                    border: none;
                    outline: none;
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
                    color: #FFFFFF;
                    font-size: 16px;
                    font-weight: bold;
                    background: transparent;
                    padding: 0px;
                    border: none;
                    outline: none;
                }
            """)
            greeting_layout.addWidget(fallback_label)
    
        main_layout.addWidget(greeting_frame)
        
        # === MENSAJE INSTRUCTIVO ===
        instruction_label = QLabel("💡 Seleccione una opción para continuar con su sesión de trabajo")
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
        main_buttons_layout.setSpacing(30)  # Reducir espacio entre botones
        
        # Botón Añadir Paciente (NUEVO)
        self.add_patient_btn = QPushButton()
        self.add_patient_btn.setText("Añadir\nPaciente")
        self.add_patient_btn.setFixedSize(150, 110)
        self.add_patient_btn.setStyleSheet("""
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
        self.add_patient_btn.clicked.connect(self.open_add_patient_dialog)
        
        # Botón Patient Manager
        self.patient_manager_btn = QPushButton()
        self.patient_manager_btn.setText("Gestión de\nPacientes")
        self.patient_manager_btn.setFixedSize(150, 110)
        self.patient_manager_btn.setStyleSheet("""
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
        self.patient_manager_btn.clicked.connect(self.open_patient_manager)
        
        # Añadir botones con espaciado
        main_buttons_layout.addStretch()
        main_buttons_layout.addWidget(self.add_patient_btn)
        main_buttons_layout.addWidget(self.patient_manager_btn)
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
    
    def open_add_patient_dialog(self):
        """Abre el diálogo para añadir un nuevo paciente"""
        try:
            dialog = AddPatientDialog(self)
            
            if dialog.exec() == QDialog.Accepted:
                # Obtener datos del formulario
                patient_data = dialog.get_patient_data()
                
                # Intentar guardar en la base de datos
                patient_id = DatabaseManager.add_patient(
                    apellido_paterno=patient_data['apellido_paterno'],
                    apellido_materno=patient_data['apellido_materno'],
                    nombre=patient_data['nombre'],
                    fecha_nacimiento=patient_data['fecha_nacimiento'],
                    celular=patient_data['celular'],
                    fecha_registro=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    comentarios=patient_data['comentarios']
                )
                
                if patient_id:
                    # Reproducir sonido de éxito
                    winsound.MessageBeep(winsound.MB_OK)
                    
                    # Mostrar mensaje de éxito
                    success_msg = QMessageBox(self)
                    success_msg.setWindowTitle("Éxito")
                    success_msg.setText(f"¡Paciente registrado exitosamente!\n\nNombre: {patient_data['nombre']} {patient_data['apellido_paterno']}\nID: {patient_id}")
                    success_msg.setIcon(QMessageBox.Information)
                    
                    # Aplicar estilo al mensaje
                    success_msg.setStyleSheet("""
                        QMessageBox {
                            background-color: #323232;
                            color: #FFFFFF;
                            border: none;
                        }
                        QMessageBox QLabel {
                            color: #FFFFFF;
                            background: transparent;
                            font-size: 14px;
                        }
                        QMessageBox QPushButton {
                            background-color: #00A99D;
                            color: white;
                            border: none;
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
                    
                    success_msg.exec()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo registrar el paciente.\nVerifique los datos e intente nuevamente.")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar el registro del paciente:\n{str(e)}")
    
    def open_patient_manager(self):
        """Abre la ventana del gestor de pacientes"""
        try:
            # Cerrar ventana anterior si existe
            if self.patient_manager_window:
                self.patient_manager_window.close()
    
            # Crear nueva ventana del gestor de pacientes
            self.patient_manager_window = PatientManagerWidget(self.username)
            
            # Conectar señal personalizada para mostrar el dashboard cuando se cierre
            self.patient_manager_window.window_closed.connect(self.show_dashboard_on_return)
            
            self.patient_manager_window.showMaximized()
            
            # Ocultar el dashboard
            self.hide()
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el gestor de pacientes: {str(e)}")
    
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
            # Cerrar ventanas abiertas
            if self.patient_manager_window:
                self.patient_manager_window.close()
            
            # Emitir señal de logout (NO cerrar la ventana aquí)
            self.logout_requested.emit()
            
            # El cierre de la ventana se manejará desde main.py
            # No llamar self.close() aquí
    
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
            # Cerrar todas las ventanas
            if self.patient_manager_window:
                self.patient_manager_window.close()
            
            # Cerrar aplicación completamente
            QApplication.quit()
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        # Cuando se cierre el dashboard, también cerrar ventanas hijas
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