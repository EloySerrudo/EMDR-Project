import sys
import os
import winsound
from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QTextEdit, QGroupBox, QSplitter,
    QMainWindow, QScrollArea
)
from PySide6.QtCore import Qt, Signal

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager
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
        self.resize(700, 600)
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

        # Botón para ver sesión
        self.view_session_button = QPushButton("Ver Sesión")
        self.view_session_button.setStyleSheet("""
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
        # self.view_session_button.clicked.connect(self.view_session)
        self.view_session_button.setEnabled(False)

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
        button_layout.addWidget(self.view_session_button)
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
                self.sessions_table.setColumnCount(4)
                self.sessions_table.setHorizontalHeaderLabels(["Fecha", "Hora", "Objetivo", "Comentarios"])
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
                
                # Ajustar columnas
                header = self.sessions_table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(3, QHeaderView.Stretch)

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
        self.view_session_button.setEnabled(has_selection)

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
            self.view_session_button.setEnabled(False)
                
        except Exception as e:
            print(f"Error al refrescar historial de sesiones: {e}")
