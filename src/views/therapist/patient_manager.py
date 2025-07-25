import sys
import os
import winsound
from pathlib import Path
from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QTextEdit, QGroupBox, QSplitter,
    QMainWindow, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager
from src.views.therapist.new_session_dialog import NewSessionDialog
from src.views.therapist.session_viewer import SessionViewerWindow

class PatientDetailsDialog(QDialog):
    """Diálogo para mostrar los detalles completos de un paciente"""
    
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.parent = parent
        self.patient_data = None
        self.sessions_data = None
        
        # Añadir referencia para la ventana del visor
        self.session_viewer_window = None
        
        self.setWindowTitle("Detalles del Paciente")
        self.resize(600, 600)
        self.setModal(True)
        
        self.load_patient_data()
        self.setup_ui()
        
    def load_patient_data(self):
        """Carga los datos completos del paciente desde la base de datos"""
        try:
            self.patient_data = DatabaseManager.get_patient(self.patient_id)
            if not self.patient_data:
                QMessageBox.warning(self, "Error", "No se encontraron datos del paciente")
                self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos del paciente: {str(e)}")
            self.reject()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        # Título con nombre del paciente
        if self.patient_data:
            title = QLabel(f"Información de {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}")
            title.setStyleSheet("""
                QLabel {
                    font-size: 18px; 
                    font-weight: bold; 
                    color: #00A99D; 
                    padding: 0 10px;
                    background: transparent;
                }
            """)
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
        
        # === DATOS PERSONALES ===
        personal_group = QGroupBox("Datos Personales")
        personal_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: transparent;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
        """)
        
        personal_layout = QFormLayout(personal_group)
        personal_layout.setSpacing(10)
        
        if self.patient_data:
            # Crear etiquetas con los datos
            self.create_info_field(personal_layout, "Nombre completo:", 
                                   f"{self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')} {self.patient_data.get('apellido_materno', '')}")
            self.create_info_field(personal_layout, "Edad:", str(self.patient_data.get('edad', '')))
            self.create_info_field(personal_layout, "Teléfono/Celular:", self.patient_data.get('celular', ''))
            self.create_info_field(personal_layout, "Fecha de registro:", self.patient_data.get('fecha_registro', ''))
        
        layout.addWidget(personal_group)
        
        # === NOTAS CLÍNICAS ===
        notes_group = QGroupBox("Notas Clínicas")
        notes_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: transparent;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
        """)
        
        notes_layout = QVBoxLayout(notes_group)
        
        # Campo de texto para las notas (solo lectura)
        self.notes_display = QTextEdit()
        self.notes_display.setReadOnly(True)
        self.notes_display.setMaximumHeight(50)
        self.notes_display.setStyleSheet("""
            QTextEdit {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: white;
            }
        """)
        
        if self.patient_data and self.patient_data.get('notas'):
            self.notes_display.setPlainText(self.patient_data.get('notas'))
        else:
            self.notes_display.setPlainText("No hay notas registradas para este paciente.")
        
        notes_layout.addWidget(self.notes_display)
        layout.addWidget(notes_group)
        
        # === HISTORIAL DE SESIONES ===
        sessions_group = QGroupBox("Historial de Sesiones")
        sessions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: transparent;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
        """)
        
        self.sessions_layout = QVBoxLayout(sessions_group)
        
        # Cargar historial de sesiones
        self.load_session_history()

        layout.addWidget(sessions_group)
        
        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón para editar paciente
        edit_button = QPushButton("Editar Datos")
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
        """)
        edit_button.clicked.connect(self.edit_patient)

        # Botón para borrar sesión
        self.delete_session_button = QPushButton("Borrar Sesión")
        self.delete_session_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
                color: #AAAAAA;
            }
        """)
        self.delete_session_button.clicked.connect(self.delete_session)
        self.delete_session_button.setEnabled(False)

        # Botón para cerrar
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
        cancel_button.clicked.connect(self.accept)
        
        button_layout.addWidget(edit_button)
        button_layout.addWidget(self.delete_session_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
        # Estilo global del diálogo
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
    
    def create_info_field(self, layout, label_text, value_text):
        """Crea un campo de información con etiqueta y valor"""
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
            }
        """)
        
        value_label = QLabel(str(value_text))
        value_label.setStyleSheet("""
            QLabel {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-weight: normal;
                color: white;
            }
        """)
        value_label.setWordWrap(True)
        layout.addRow(label, value_label)
    
    def load_session_history(self):
        """Carga el historial de sesiones del paciente"""
        try:
            self.sessions_data = DatabaseManager.get_sessions_for_patient(self.patient_id)

            if not self.sessions_data:
                no_sessions_label = QLabel("No hay sesiones registradas para este paciente.")
                no_sessions_label.setStyleSheet("""
                    QLabel {
                        color: #AAAAAA; 
                        font-style: italic; 
                        padding: 10px;
                        background: transparent;
                    }
                """)
                self.sessions_layout.addWidget(no_sessions_label)
            else:
                # Crear tabla para mostrar las sesiones
                self.sessions_table = QTableWidget()
                self.sessions_table.setColumnCount(5)
                self.sessions_table.setHorizontalHeaderLabels(["Fecha", "Hora", "Objetivo", "Comentarios", "Acción"])
                self.sessions_table.setRowCount(len(self.sessions_data))

                # Configurar tabla
                self.sessions_table.setAlternatingRowColors(True)
                self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
                self.sessions_table.verticalHeader().setVisible(False)
                self.sessions_table.setMaximumHeight(104)
                self.sessions_table.setStyleSheet("""
                    QTableWidget {
                        background-color: #323232;
                        alternate-background-color: #2a2a2a;
                        border: 1px solid #555555;
                        border-radius: 4px;
                        color: white;
                        gridline-color: #555555;
                    }
                    QHeaderView::section {
                        background-color: #00A99D;
                        padding: 8px;
                        font-weight: bold;
                        border: 1px solid #008C82;
                        color: white;
                    }
                    QTableWidget::item {
                        padding: 8px;
                        border-bottom: 1px solid #555555;
                    }
                    QTableWidget::item:selected {
                        background-color: #00A99D;
                        color: white;
                    }
                """)
                
                # Llenar tabla con datos de sesiones
                for i, session in enumerate(self.sessions_data):
                    fecha, hora = self.format_datetime_string(session.get('fecha'))
                    self.sessions_table.setItem(i, 0, QTableWidgetItem(fecha))
                    self.sessions_table.setItem(i, 1, QTableWidgetItem(hora))
                    self.sessions_table.setItem(i, 2, QTableWidgetItem(session.get('objetivo')))
                    self.sessions_table.setItem(i, 3, QTableWidgetItem(session.get('comentarios')))

                    # === BOTÓN PARA VER ANÁLISIS ===
                    view_btn = QPushButton("Ver Análisis")
                    view_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2196F3;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 11px;
                        }
                        QPushButton:hover {
                            background-color: #42A5F5;
                        }
                        QPushButton:pressed {
                            background-color: #1976D2;
                        }
                    """)
                    
                    # Conectar el botón con la sesión específica
                    session_id = session.get('id')
                    view_btn.clicked.connect(partial(self.view_session_analysis, session_id))

                    self.sessions_table.setCellWidget(i, 4, view_btn)
                
                # Ajustar columnas
                header = self.sessions_table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(3, QHeaderView.Stretch)
                header.setSectionResizeMode(4, QHeaderView.Stretch)

                self.sessions_layout.addWidget(self.sessions_table)

                # Conectar selección de tabla
                self.sessions_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        except Exception as e:
            error_label = QLabel(f"Error al cargar sesiones: {str(e)}")
            error_label.setStyleSheet("""
                QLabel {
                    color: #FF6B6B; 
                    padding: 10px;
                    background: transparent;
                }
            """)
            self.sessions_layout.addWidget(error_label)
    
    # === NUEVO MÉTODO: VER ANÁLISIS DE SESIÓN ===
    def view_session_analysis(self, session_id: int):
        """Abre el visor de análisis para una sesión específica"""
        try:
            # Si ya hay una ventana abierta, cerrarla
            if self.session_viewer_window:
                self.session_viewer_window.close()
            
            # Crear nueva ventana del visor
            self.session_viewer_window = SessionViewerWindow(
                session_id=session_id,
                parent=self
            )
            
            # Configurar para mostrar solo sesiones de este paciente
            self.filter_sessions_for_patient()
            
            # Conectar señal de cierre
            self.session_viewer_window.window_closed.connect(self.on_session_viewer_closed)
            
            # Mostrar ventana
            self.session_viewer_window.show()
            
            # Cerrar este diálogo para no abarrotar la pantalla
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir el análisis de la sesión:\n{str(e)}"
            )
    
    def filter_sessions_for_patient(self):
        """Filtra las sesiones en el visor para mostrar solo de este paciente"""
        if not self.session_viewer_window:
            return
        
        try:
            # Obtener sesiones del paciente
            patient_sessions = DatabaseManager.get_sessions_for_patient(self.patient_id)
            
            # Limpiar y llenar el combo del visor
            self.session_viewer_window.session_combo.clear()
            
            for session in patient_sessions:
                patient_name = f"{self.patient_data['nombre']} {self.patient_data['apellido_paterno']}"
                display_text = f"Sesión {session['id']} - {patient_name} ({session['fecha']})"
                self.session_viewer_window.session_combo.addItem(display_text, session['id'])
            
            # Actualizar título
            patient_name = f"{self.patient_data['nombre']} {self.patient_data['apellido_paterno']}"
            self.session_viewer_window.setWindowTitle(f"EMDR Project - Análisis de Sesiones: {patient_name}")
            
        except Exception as e:
            print(f"Error filtrando sesiones para paciente: {e}")
    
    def format_datetime_string(self, datetime_str):
        """
        Convierte una cadena datetime a formato separado
        Args:
            datetime_str: String en formato "YYYY-MM-DD HH:MM:SS.fff"
        Returns:
            tuple: (date_str, time_str) en formatos "DD/MM/YYYY", "HH:MM"
        """
        try:
            fecha_parte, hora_parte = datetime_str.split(' ')
            year, month, day = fecha_parte.split('-')
            date = f"{day}/{month}/{year}"
            hour, minute = hora_parte.split(':')[:2]
            time = f"{hour}:{minute}"
            return date, time
        except:
            return 'N/A', 'N/A'
    
    def on_selection_changed(self):
        """Maneja el cambio de selección en la tabla"""
        selected_rows = self.sessions_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        self.delete_session_button.setEnabled(has_selection)
    
    def on_session_viewer_closed(self):
        """Maneja el cierre de la ventana del visor"""
        self.session_viewer_window = None
    
    def edit_patient(self):
        """Abre un diálogo para editar los datos del paciente"""
        QMessageBox.information(self, "Función en desarrollo", 
                               "La función de editar paciente estará disponible pronto.")
    
    def delete_session(self):
        """Elimina la sesión seleccionada del paciente"""
        selected_rows = self.sessions_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione una sesión de la tabla para eliminar.")
            return
        
        try:
            # Obtener los datos de la sesión seleccionada
            row_index = selected_rows[0].row()
            selected_session = self.sessions_data[row_index]
            session_id = selected_session.get('id')
            session_date = selected_session.get('fecha', 'N/A')
            session_comments = selected_session.get('comentarios', 'Sin comentarios')
            
            if not session_id:
                QMessageBox.warning(self, "Error", "No se pudo obtener el ID de la sesión.")
                return
            
            # Reproducir sonido de advertencia
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            
            # Crear mensaje de confirmación detallado
            fecha_formatted, hora_formatted = self.format_datetime_string(session_date)
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirmar Eliminación de Sesión")
            msg_box.setIcon(QMessageBox.Warning)
            
            warning_text = f"¿Está seguro de que desea eliminar la siguiente sesión?\n\n"
            warning_text += f"• Paciente: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}.\n"
            warning_text += f"• Sesión N°: {len(self.sessions_data) - row_index}.\n"
            warning_text += f"• Fecha: {fecha_formatted}.\n"
            warning_text += f"• Hora: {hora_formatted}.\n"
            warning_text += f"• Comentarios: {session_comments[:50]}{'...' if len(session_comments) > 50 else ''}.\n\n"
            warning_text += "⚠️  TODOS los datos fisiológicos registrados (si existen) en esta sesión serán eliminados PERMANENTEMENTE:\n"
            warning_text += "   • Datos de frecuencia cardiaca.\n"
            warning_text += "   • Datos de movimientos oculares.\n\n"
            warning_text += "❌  Esta acción NO se puede deshacer."
            
            msg_box.setText(warning_text)
            
            # Crear botones personalizados
            delete_button = msg_box.addButton("Eliminar Sesión", QMessageBox.DestructiveRole)
            cancel_button = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(cancel_button)
            
            # Aplicar estilo personalizado
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #323232;
                    color: #FFFFFF;
                    border: 2px solid #FF6B6B;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #FFFFFF;
                    background: transparent;
                    font-size: 13px;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-width: 80px;
                    margin: 2px;
                }
                QMessageBox QPushButton[text="Eliminar Sesión"] {
                    background-color: #FF6B6B;
                    border: 2px solid #FF6B6B;
                }
                QMessageBox QPushButton[text="Eliminar Sesión"]:hover {
                    background-color: #FF8E8E;
                    border: 2px solid #FF8E8E;
                }
                QMessageBox QPushButton[text="Eliminar Sesión"]:pressed {
                    background-color: #E55555;
                    border: 2px solid #E55555;
                }
                QMessageBox QPushButton[text="Cancelar"] {
                    background-color: #6c757d;
                    border: 2px solid #6c757d;
                }
                QMessageBox QPushButton[text="Cancelar"]:hover {
                    background-color: #5a6268;
                    border: 2px solid #5a6268;
                }
                QMessageBox QPushButton[text="Cancelar"]:pressed {
                    background-color: #545b62;
                    border: 2px solid #545b62;
                }
            """)
            
            # Ejecutar diálogo
            msg_box.exec()
            
            if msg_box.clickedButton() == delete_button:
                try:
                    # Eliminar la sesión de la base de datos
                    if DatabaseManager.delete_session(session_id):
                        # Reproducir sonido de éxito
                        winsound.MessageBeep(winsound.MB_OK)
                        
                        # Mostrar mensaje de éxito
                        success_msg = QMessageBox(self)
                        success_msg.setWindowTitle("Eliminación Exitosa")
                        success_msg.setIcon(QMessageBox.Information)
                        success_msg.setText(
                            f"La sesión del {fecha_formatted} a las {hora_formatted} "
                            f"ha sido eliminada exitosamente.\n\n"
                            f"Todos los datos fisiológicos asociados también fueron eliminados."
                        )
                        
                        # Aplicar estilo al mensaje de éxito
                        success_msg.setStyleSheet("""
                            QMessageBox {
                                background-color: #323232;
                                color: #FFFFFF;
                                border: 2px solid #00A99D;
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
                        
                        success_msg.exec()
                        
                        # Recargar el historial de sesiones
                        self.refresh_session_history()
                        
                        self.parent.load_patients()
                        
                    else:
                        QMessageBox.critical(
                            self,
                            "Error",
                            "No se pudo eliminar la sesión. Verifique que la sesión "
                            "exista o contacte al administrador."
                        )
                        
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Error durante la eliminación de la sesión:\n{str(e)}\n\n"
                        "La operación ha sido cancelada para preservar la integridad de los datos."
                    )
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar sesión: {str(e)}")

    def refresh_session_history(self):
        """Recarga el historial de sesiones en el diálogo"""
        try:
            # Limpiar el layout actual del historial de sesiones
            if hasattr(self, 'sessions_layout'):
                # Eliminar todos los widgets del layout
                while self.sessions_layout.count():
                    child = self.sessions_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Recargar el historial de sesiones
                self.load_session_history()
            self.delete_session_button.setEnabled(False)
                
        except Exception as e:
            print(f"Error al refrescar historial de sesiones: {e}")


class PatientManagerWidget(QMainWindow):
    """Widget principal para gestionar pacientes"""
    
    # Señal emitida cuando se selecciona un paciente
    patient_selected = Signal(int, str)  # ID del paciente, nombre completo
    
    # Señal emitida cuando la ventana se cierra
    window_closed = Signal()  # Nueva señal personalizada
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.control_panel = None  # Inicializar referencia del control panel
        
        self.setWindowTitle("EMDR Project - Gestión de Pacientes")
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent.parent / 'resources' / 'emdr_icon.png')))
        self.resize(800, 600)
        self.patients_data = []
        
        self.setup_ui()
        self.load_patients()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # === HEADER ===
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
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        # Logo o título principal
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent.parent / 'resources' / 'emdr_logo.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
            logo_label.setText("EMDR")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    background: transparent;
                }
            """)
        
        title_label = QLabel("GESTIÓN DE PACIENTES")
        title_label.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 20px; 
                font-weight: bold;
                background: transparent;
            }
        """)
        
        if self.username:
            # Cargar datos del terapeuta para mostrar nombre completo
            try:
                therapist_data = DatabaseManager.get_therapist_by_username(self.username)
                if therapist_data:
                    nombre_completo = f"Lic. {therapist_data['nombre']} {therapist_data['apellido_paterno']}"
                else:
                    nombre_completo = self.username  # Fallback
            except Exception:
                nombre_completo = self.username  # Fallback en caso de error
            
            user_label = QLabel(f"Terapeuta: {nombre_completo}")
            user_label.setStyleSheet("""
                QLabel {
                    color: #003454; 
                    font-size: 16px;
                    background: transparent;
                }
            """)
            
            header_layout.addWidget(logo_label)
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(user_label)
        else:
            header_layout.addWidget(logo_label)
            header_layout.addWidget(title_label, 0, Qt.AlignCenter)
        
        main_layout.addWidget(header_frame)
        
        # === BARRA DE BÚSQUEDA ===
        search_frame = QFrame()
        search_frame.setFrameShape(QFrame.StyledPanel)
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #424242; 
                border-radius: 6px;
                border: 1px solid #555555;
            }
        """)
        
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 10, 10, 10)
        
        search_label = QLabel("Buscar paciente:")
        search_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escriba el nombre, apellido o código de paciente...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #555555;
                border-radius: 4px;
                font-size: 13px;
                background-color: #323232;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #00A99D;
            }
            QLineEdit::placeholder {
                color: #AAAAAA;
            }
        """)
        self.search_input.textChanged.connect(self.filter_patients)
        
        self.search_button = QPushButton("Buscar")
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
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
        """)
        self.search_button.clicked.connect(self.filter_patients)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        
        main_layout.addWidget(search_frame)
        
        # === TABLA DE PACIENTES ===
        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(7)
        self.patients_table.setHorizontalHeaderLabels([
            "Código Paciente", "Apellido Paterno", "Apellido Materno", "Nombre", "Edad", "Teléfono", "Sesiones"
        ])
        
        # Configurar tabla
        self.patients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patients_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patients_table.setAlternatingRowColors(True)
        self.patients_table.verticalHeader().setVisible(False)
        
        # Estilo de la tabla
        self.patients_table.setStyleSheet("""
            QTableWidget {
                background-color: #323232;
                alternate-background-color: #2a2a2a;
                border: 1px solid #555555;
                border-radius: 6px;
                gridline-color: #555555;
                color: white;
            }
            QHeaderView::section {
                background-color: #00A99D;
                padding: 10px;
                font-weight: bold;
                border: 0;
                color: white;
                border-bottom: 2px solid #008C82;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555555;
            }
            QTableWidget::item:selected {
                background-color: #00A99D;
                color: white;
            }
        """)
        
        # Ajustar columnas
        header = self.patients_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Código Paciente
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Apellido Paterno
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Apellido Materno
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Nombre
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Edad
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Teléfono
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Sesiones
        
        # Doble clic para ver detalles
        self.patients_table.doubleClicked.connect(self.show_patient_details)
        
        main_layout.addWidget(self.patients_table)
        
        # === BOTONES DE ACCIÓN ===
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        
        # Botón para ver detalles
        self.details_button = QPushButton("Ver Detalles")
        self.details_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
                color: #AAAAAA;
            }
        """)
        self.details_button.clicked.connect(self.show_patient_details)
        self.details_button.setEnabled(False)
        
        # Botón para crear nueva sesión
        self.session_button = QPushButton("Nueva Sesión")
        self.session_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
                color: #AAAAAA;
            }
        """)
        self.session_button.clicked.connect(self.new_session)
        self.session_button.setEnabled(False)
        
        # Botón para eliminar paciente
        self.delete_button = QPushButton("Eliminar Paciente")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
                color: #AAAAAA;
            }
        """)
        self.delete_button.clicked.connect(self.delete_patient)
        self.delete_button.setEnabled(False)
        
        # Botón para salir
        exit_btn = QPushButton("Salir")
        exit_btn.setFixedSize(134, 43)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
        exit_btn.clicked.connect(self.exit_application)
        
        # Botón para regresar al dashboard
        back_btn = QPushButton("Regresar")
        back_btn.setFixedSize(134, 43)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
                border: 2px solid #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
                border: 2px solid #545b62;
            }
        """)
        back_btn.clicked.connect(self.return_to_dashboard)

        button_layout.addWidget(self.details_button)
        button_layout.addWidget(self.session_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(back_btn)
        button_layout.addWidget(exit_btn)
        
        main_layout.addWidget(button_frame)
        
        # === BARRA DE ESTADO ===
        footer_layout = QHBoxLayout()
        
        self.status_label = QLabel("Cargando pacientes...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA; 
                font-style: italic;
                background: transparent;
            }
        """)
        
        footer_label = QLabel("Sistema de Terapia EMDR - Versión 1.0")
        footer_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                font-style: italic;
                background: transparent;
            }
        """)
        
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        
        main_layout.addLayout(footer_layout)
        
        # Conectar selección de tabla
        self.patients_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        # Estilo global de la ventana
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
    
    def load_patients(self):
        """Carga la lista de pacientes desde la base de datos"""
        try:
            self.status_label.setText("Cargando pacientes...")
            QApplication.processEvents()
            
            # Obtener pacientes de la base de datos
            self.patients_data = DatabaseManager.get_all_patients()
            
            # Actualizar tabla
            self.populate_table(self.patients_data)
            
            # Actualizar estado
            count = len(self.patients_data)
            self.status_label.setText(f"Se encontraron {count} paciente(s) registrado(s)")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los pacientes: {str(e)}")
            self.status_label.setText("Error al cargar pacientes")
    
    def populate_table(self, patients):
        """Llena la tabla con los datos de pacientes"""
        self.patients_table.setRowCount(len(patients))
        
        for i, patient in enumerate(patients):
            # Código Paciente
            self.patients_table.setItem(i, 0, QTableWidgetItem(str(patient.get('id', ''))))
            # Apellido Paterno
            self.patients_table.setItem(i, 1, QTableWidgetItem(patient.get('apellido_paterno', '')))
            # Apellido Materno
            self.patients_table.setItem(i, 2, QTableWidgetItem(patient.get('apellido_materno', '')))
            # Nombre
            self.patients_table.setItem(i, 3, QTableWidgetItem(patient.get('nombre', '')))
            # Edad
            self.patients_table.setItem(i, 4, QTableWidgetItem(str(patient.get('edad', ''))))
            # Teléfono
            self.patients_table.setItem(i, 5, QTableWidgetItem(patient.get('celular', '')))
            
            # Sesiones - obtener número de sesiones para este paciente
            try:
                patient_id = patient.get('id')
                if patient_id:
                    sessions = DatabaseManager.get_sessions_for_patient(patient_id)
                    session_count = len(sessions) if sessions else 0
                else:
                    session_count = 0
                
                self.patients_table.setItem(i, 6, QTableWidgetItem(str(session_count)))
                
            except Exception as e:
                print(f"Error obteniendo sesiones para paciente {patient.get('id', 'N/A')}: {e}")
                self.patients_table.setItem(i, 6, QTableWidgetItem("0"))
        
        # Resetear selección
        self.patients_table.clearSelection()
        self.details_button.setEnabled(False)
        self.session_button.setEnabled(False)
    
    def filter_patients(self):
        """Filtra los pacientes según el texto de búsqueda"""
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            # Si no hay texto, mostrar todos los pacientes
            self.populate_table(self.patients_data)
            return
        
        # Filtrar pacientes
        filtered_patients = []
        for patient in self.patients_data:
            # Buscar en ID, nombre, apellidos
            if (search_text in str(patient.get('id', '')).lower() or
                search_text in patient.get('nombre', '').lower() or
                search_text in patient.get('apellido_paterno', '').lower() or
                search_text in patient.get('apellido_materno', '').lower()):
                filtered_patients.append(patient)
        
        # Actualizar tabla con resultados filtrados
        self.populate_table(filtered_patients)
        
        # Actualizar estado
        count = len(filtered_patients)
        total = len(self.patients_data)
        self.status_label.setText(f"Mostrando {count} de {total} paciente(s)")
    
    def on_selection_changed(self):
        """Maneja el cambio de selección en la tabla"""
        selected_rows = self.patients_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        self.details_button.setEnabled(has_selection)
        self.session_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
    
    def show_patient_details(self):
        """Muestra los detalles del paciente seleccionado"""
        selected_rows = self.patients_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un paciente de la lista")
            return
        
        # Obtener el ID del paciente seleccionado
        row_index = selected_rows[0].row()
        patient_id_item = self.patients_table.item(row_index, 0)
        
        if not patient_id_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener el código de paciente")
            return
        
        try:
            patient_id = int(patient_id_item.text())
            
            # Abrir diálogo de detalles
            details_dialog = PatientDetailsDialog(patient_id, self)
            details_dialog.exec()
            
        except ValueError:
            QMessageBox.warning(self, "Error", "Código de paciente inválido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mostrar detalles: {str(e)}")

    def new_session(self):
        """Abre el diálogo para crear una nueva sesión"""
        selected_rows = self.patients_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un paciente de la lista")
            return
        
        # Obtener los datos del paciente seleccionado
        row_index = selected_rows[0].row()
        patient_id_item = self.patients_table.item(row_index, 0)
        
        if not patient_id_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener el código de paciente")
            return
        
        try:
            patient_id = int(patient_id_item.text())
            
            # Obtener datos completos del paciente
            patient_data = DatabaseManager.get_patient(patient_id)
            if not patient_data:
                QMessageBox.warning(self, "Error", "No se encontraron datos del paciente")
                return
            
            # Abrir diálogo de nueva sesión
            new_session_dialog = NewSessionDialog(patient_data, self, self.username)
            # Conectar la señal del diálogo para abrir el control panel
            new_session_dialog.open_control_panel.connect(self.open_control_panel)
            new_session_dialog.exec()
            
        except ValueError:
            QMessageBox.warning(self, "Error",  "Código de paciente inválido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al crear nueva sesión: {str(e)}")
    
    def open_control_panel(self, therapist_name, patient_name, patient_id, current_session, session_datetime, session_type):
        """Abre la ventana de control panel con los datos de la sesión"""
        try:
            # Importar aquí para evitar importaciones circulares
            from src.views.therapist.control_panel import EMDRControlPanel
            
            # Crear ventana de control panel
            self.control_panel = EMDRControlPanel(
                therapist_name=therapist_name,
                patient_name=patient_name,
                patient_id=patient_id,
                current_session=current_session,
                session_datetime=session_datetime,
                session_type=session_type,
                parent=self
            )
            
            # Conectar señal para cuando se cierre el control panel
            self.control_panel.window_closed.connect(self.on_control_panel_closed)
            
            # Mostrar control panel
            self.control_panel.show()
            
            # Ocultar esta ventana
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el control panel: {str(e)}")
    
    def on_control_panel_closed(self):
        """Maneja el cierre de la ventana de control panel"""
        # Mostrar nuevamente esta ventana
        self.show()
        # Limpiar referencia
        self.control_panel = None
    
    def delete_patient(self):
        """Elimina el paciente seleccionado y todas sus sesiones relacionadas"""
        selected_rows = self.patients_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un paciente de la lista")
            return
        
        # Obtener los datos del paciente seleccionado
        row_index = selected_rows[0].row()
        patient_id_item = self.patients_table.item(row_index, 0)
        patient_name_item = self.patients_table.item(row_index, 1)
        patient_lastname_item = self.patients_table.item(row_index, 2)
        
        if not patient_id_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener el código de paciente")
            return
        
        try:
            patient_id = int(patient_id_item.text())
            patient_name = patient_name_item.text() if patient_name_item else "N/A"
            patient_lastname = patient_lastname_item.text() if patient_lastname_item else "N/A"
            full_name = f"{patient_name} {patient_lastname}"
            
            # Verificar si el paciente tiene sesiones
            sessions = DatabaseManager.get_sessions_for_patient(patient_id)
            session_count = len(sessions) if sessions else 0
            
            # Verificar si el paciente tiene diagnósticos
            diagnoses = DatabaseManager.get_diagnoses_for_patient(patient_id, include_resolved=True)
            diagnosis_count = len(diagnoses) if diagnoses else 0
            
            # Crear mensaje de confirmación detallado
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirmar Eliminación")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Construir mensaje informativo
            warning_text = f"¿Está seguro de que desea eliminar al paciente:\n\n"
            warning_text += f"• Nombre: {full_name}\n"
            warning_text += f"• ID: {patient_id}\n\n"
            
            if session_count > 0:
                warning_text += f"⚠️  Este paciente tiene {session_count} sesión(es) registrada(s)\n"
            
            if diagnosis_count > 0:
                warning_text += f"⚠️  Este paciente tiene {diagnosis_count} diagnóstico(s) registrado(s)\n"
            
            if session_count > 0 or diagnosis_count > 0:
                warning_text += "\n🗑️  TODA la información relacionada será eliminada PERMANENTEMENTE:\n"
                if session_count > 0:
                    warning_text += f"   • {session_count} sesión(es) con datos fisiológicos\n"
                if diagnosis_count > 0:
                    warning_text += f"   • {diagnosis_count} diagnóstico(s) clínico(s)\n"
                warning_text += "\n❌  Esta acción NO se puede deshacer."
            else:
                warning_text += "\n❌  Esta acción NO se puede deshacer."
            
            msg_box.setText(warning_text)
            
            # Crear botones personalizados
            delete_button = msg_box.addButton("Eliminar Definitivamente", QMessageBox.DestructiveRole)
            cancel_button = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(cancel_button)
            
            # Aplicar estilo personalizado
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #323232;
                    color: #FFFFFF;
                    border: 2px solid #FF6B6B;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #FFFFFF;
                    background: transparent;
                    font-size: 13px;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-width: 80px;
                    margin: 2px;
                }
                QMessageBox QPushButton[text="Eliminar Definitivamente"] {
                    background-color: #FF6B6B;
                    border: 2px solid #FF6B6B;
                }
                QMessageBox QPushButton[text="Eliminar Definitivamente"]:hover {
                    background-color: #FF8E8E;
                    border: 2px solid #FF8E8E;
                }
                QMessageBox QPushButton[text="Eliminar Definitivamente"]:pressed {
                    background-color: #E55555;
                    border: 2px solid #E55555;
                }
                QMessageBox QPushButton[text="Cancelar"] {
                    background-color: #6c757d;
                    border: 2px solid #6c757d;
                }
                QMessageBox QPushButton[text="Cancelar"]:hover {
                    background-color: #5a6268;
                    border: 2px solid #5a6268;
                }
                QMessageBox QPushButton[text="Cancelar"]:pressed {
                    background-color: #545b62;
                    border: 2px solid #545b62;
                }
            """)
            
            # Ejecutar diálogo
            msg_box.exec()
            
            if msg_box.clickedButton() == delete_button:
                try:
                    # Mostrar indicador de progreso
                    self.status_label.setText("Eliminando paciente...")
                    QApplication.processEvents()
                    
                    # Primero eliminar sesiones (por restricciones de clave foránea)
                    if session_count > 0:
                        for session in sessions:
                            DatabaseManager.delete_session(session['id'])
                    
                    # Luego eliminar diagnósticos
                    if diagnosis_count > 0:
                        for diagnosis in diagnoses:
                            DatabaseManager.delete_diagnosis(diagnosis['id'])
                    
                    # Finalmente eliminar el paciente
                    if DatabaseManager.delete_patient(patient_id):
                        # Recargar la lista de pacientes
                        self.load_patients()
                        
                        # Mostrar mensaje de éxito
                        QMessageBox.information(
                            self,
                            "Eliminación Exitosa",
                            f"El paciente {full_name} y toda su información relacionada "
                            f"han sido eliminados exitosamente.\n\n"
                            f"Elementos eliminados:\n"
                            f"• 1 registro de paciente\n" +
                            (f"• {session_count} sesión(es)\n" if session_count > 0 else "") +
                            (f"• {diagnosis_count} diagnóstico(s)" if diagnosis_count > 0 else "")
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Error",
                            "No se pudo eliminar el paciente. Verifique que no tenga "
                            "información relacionada o contacte al administrador."
                        )
                        
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Error durante la eliminación:\n{str(e)}\n\n"
                        "La operación ha sido cancelada para preservar la integridad de los datos."
                    )
                    # Recargar datos por seguridad
                    self.load_patients()
                finally:
                    # Restaurar estado normal
                    count = len(self.patients_data)
                    self.status_label.setText(f"Se encontraron {count} paciente(s) registrado(s)")
            
        except ValueError:
            QMessageBox.warning(self, "Error",  "Código de paciente inválido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar paciente: {str(e)}")
    
    def return_to_dashboard(self):
        """Regresa al dashboard del terapeuta"""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Regresar")
        msg_box.setText("¿Está seguro de que desea regresar al Control de Usuario?")
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
            try:
                # Emitir señal antes de cerrar
                self.window_closed.emit()
                
                # Cerrar la ventana actual
                self.close()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo regresar al dashboard: {str(e)}")

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
            # Cerrar aplicación completamente
            QApplication.quit()

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        # Emitir señal cuando la ventana se cierre
        self.window_closed.emit()
        event.accept()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear ventana principal
    patient_manager = PatientManagerWidget("Lic. Juan Pérez")
    patient_manager.show()
    
    sys.exit(app.exec())