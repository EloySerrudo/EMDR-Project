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

# Importar la clase DatabaseManager
from database.database_manager import DatabaseManager


class PatientDetailsDialog(QDialog):
    """Diálogo para mostrar los detalles completos de un paciente"""
    
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.parent = parent
        self.patient_data = None
        self.sessions_data = None
        
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
        personal_group = self.create_info_field()
        
        layout.addWidget(personal_group)
        
        # === COMENTARIOS ===
        comments_group = QGroupBox("Comentarios")
        comments_group.setStyleSheet("""
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
        
        comments_layout = QVBoxLayout(comments_group)

        # Campo de texto para los comentarios (solo lectura)
        self.comments_display = QTextEdit()
        self.comments_display.setReadOnly(True)
        self.comments_display.setMaximumHeight(50)
        self.comments_display.setStyleSheet("""
            QTextEdit {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: white;
            }
        """)
        
        if self.patient_data and self.patient_data.get('comentarios'):
            self.comments_display.setPlainText(self.patient_data.get('comentarios'))
        else:
            self.comments_display.setPlainText("No hay comentarios registrados para este paciente.")

        comments_layout.addWidget(self.comments_display)
        layout.addWidget(comments_group)
        
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
        self.view_session_button.clicked.connect(self.view_session)
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
        button_layout.addWidget(self.view_session_button)
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
    
    def create_info_field(self):
        """Crea un campo de información con etiqueta y valor"""
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
        
        personal_layout = QVBoxLayout(personal_group)
        personal_layout.setSpacing(15)
        
        if self.patient_data:
            # PRIMERA FILA: Nombre completo (horizontal)
            first_row_layout = QHBoxLayout()
            first_row_layout.setSpacing(10)

            # Nombre completo
            name_container = QHBoxLayout()
            name_label = QLabel("Nombre completo:")
            name_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            full_name = f"{self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')} {self.patient_data.get('apellido_materno', '')}"
            name_value = QLabel(full_name)
            name_value.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    min-width: 270px;
                }
            """)
            name_value.setWordWrap(True)
            name_container.addWidget(name_label)
            name_container.addWidget(name_value)
            
            # Edad
            age_container = QHBoxLayout()
            age_label = QLabel("Edad:")
            age_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                }
            """)
            age_value = QLabel(str(self.patient_data.get('edad', '')))
            age_value.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    max-width: 20px;
                }
            """)
            age_container.addWidget(age_label)
            age_container.addWidget(age_value)
            
            # Añadir todos los contenedores a la primera fila
            first_row_layout.addLayout(name_container)
            first_row_layout.addLayout(age_container)
            first_row_layout.addStretch()  # Para empujar todo hacia la izquierda

            # SEGUNDA FILA: Teléfono, Fecha y Hora de registro (horizontal)
            second_row_layout = QHBoxLayout()
            second_row_layout.setSpacing(10)
            
            # Teléfono/Celular
            phone_container = QHBoxLayout()
            phone_label = QLabel("Teléfono/Celular:")
            phone_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                }
            """)
            phone_value = QLabel(self.patient_data.get('celular', ''))
            phone_value.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    min-width: 100px;
                }
            """)
            phone_container.addWidget(phone_label)
            phone_container.addWidget(phone_value)
            
            # Fecha de registro
            date_container = QHBoxLayout()
            date_label = QLabel("Fecha de registro:")
            date_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                }
            """)
            
            # Usar format_datetime_string para separar fecha y hora
            fecha_registro_str = self.patient_data.get('fecha_registro', '')
            if fecha_registro_str:
                fecha_formatted, _ = self.format_datetime_string(fecha_registro_str)
            else:
                fecha_formatted = 'N/A'
                
            date_value = QLabel(fecha_formatted)
            date_value.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    min-width: 80px;
                }
            """)
            date_container.addWidget(date_label)
            date_container.addWidget(date_value)
            
            # Hora de registro
            time_container = QHBoxLayout()
            time_label = QLabel("Hora de registro:")
            time_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                }
            """)
            
            if fecha_registro_str:
                _, hora_formatted = self.format_datetime_string(fecha_registro_str)
            else:
                hora_formatted = 'N/A'
                
            time_value = QLabel(hora_formatted)
            time_value.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    min-width: 60px;
                }
            """)
            time_container.addWidget(time_label)
            time_container.addWidget(time_value)
            
            # Añadir todos los contenedores a la segunda fila
            second_row_layout.addLayout(phone_container)
            second_row_layout.addLayout(date_container)
            second_row_layout.addLayout(time_container)
            second_row_layout.addStretch()  # Para empujar todo hacia la izquierda
            
            personal_layout.addLayout(first_row_layout)
            personal_layout.addLayout(second_row_layout)
            
            return personal_group
    
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
                self.sessions_table.setMaximumHeight(164)
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
    def view_session(self):
        """Abre el diálogo de detalles para una sesión específica"""
        selected_rows = self.sessions_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione una sesión de la tabla para ver.")
            return
        
        try:
            # Obtener los datos de la sesión seleccionada
            row_index = selected_rows[0].row()
            selected_session = self.sessions_data[row_index]
            session_id = selected_session.get('id')
            
            if not session_id:
                QMessageBox.warning(self, "Error", "No se pudo obtener el ID de la sesión.")
                return
            
            from views.therapist.session_details_dialog import SessionDetailsDialog
            
            # Crear y mostrar el diálogo de detalles de sesión
            session_dialog = SessionDetailsDialog(session_id, self)
            session_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir los detalles de la sesión:\n{str(e)}"
            )
    
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

    def edit_patient(self):
        """Abre un diálogo para editar los datos del paciente"""
        try:
            # Importar el diálogo de edición
            from src.views.therapist.patient_edit_dialog import PatientEditDialog
            
            # Crear y mostrar el diálogo de edición
            edit_dialog = PatientEditDialog(self.patient_id, self)
            
            if edit_dialog.exec() == QDialog.Accepted:
                # Los datos se guardaron exitosamente, recargar los datos del paciente
                try:
                    # Recargar datos del paciente
                    self.load_patient_data()
                    
                    # Actualizar la interfaz con los nuevos datos
                    if self.patient_data:
                        # Actualizar título
                        title_text = f"Información de {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}"
                        title_widgets = self.findChildren(QLabel)
                        for widget in title_widgets:
                            if "Información de" in widget.text():
                                widget.setText(title_text)
                                break
                        
                        # Actualizar comentarios
                        if self.patient_data.get('comentarios'):
                            self.comments_display.setPlainText(self.patient_data.get('comentarios'))
                        else:
                            self.comments_display.setPlainText("No hay comentarios registrados para este paciente.")
                        
                        # Recrear el grupo de datos personales con los datos actualizados
                        # Encontrar y eliminar el grupo existente
                        for child in self.findChildren(QGroupBox):
                            if child.title() == "Datos Personales":
                                child.deleteLater()
                                break
                        
                        # Insertar el nuevo grupo en la posición correcta
                        personal_group = self.create_info_field()
                        self.layout().insertWidget(1, personal_group)  # Después del título
                        
                        # Actualizar la tabla de pacientes en el parent si existe
                        if hasattr(self, 'parent') and self.parent:
                            from src.views.therapist.patient_manager import PatientManagerWidget
                            if isinstance(self.parent, PatientManagerWidget):
                                try:
                                    self.parent.load_patients()
                                    print("Tabla de pacientes actualizada tras edición")
                                except Exception as e:
                                    print(f"Error al actualizar tabla de pacientes: {e}")
                    
                except Exception as e:
                    QMessageBox.warning(self, "Advertencia", 
                                      f"Los datos se guardaron pero hubo un error al actualizar la vista: {str(e)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir el diálogo de edición: {str(e)}")
    
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
