import sys
import os
import winsound
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QTextEdit, QDateEdit, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager


class PatientEditDialog(QDialog):
    """Diálogo para editar los datos de un paciente"""
    
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.parent = parent
        self.patient_data = None
        
        self.setWindowTitle("Editar Datos del Paciente")
        self.resize(500, 450)
        self.setModal(True)
        
        self.load_patient_data()
        self.setup_ui()
        
    def load_patient_data(self):
        """Carga los datos del paciente desde la base de datos"""
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
        layout.setSpacing(15)
        
        # Título del diálogo
        if self.patient_data:
            title = QLabel(f"Editando: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}")
            title.setStyleSheet("""
                QLabel {
                    font-size: 18px; 
                    font-weight: bold; 
                    color: #00A99D; 
                    padding: 10px;
                    background: transparent;
                }
            """)
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
        
        # === FORMULARIO DE EDICIÓN ===
        form_group = QGroupBox("Datos Personales")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
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
        
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Campos del formulario
        self.apellido_paterno_input = QLineEdit()
        self.apellido_paterno_input.setPlaceholderText("Ej: García")
        if self.patient_data:
            self.apellido_paterno_input.setText(self.patient_data.get('apellido_paterno', ''))
        form_layout.addRow("Apellido Paterno:", self.apellido_paterno_input)
        
        self.apellido_materno_input = QLineEdit()
        self.apellido_materno_input.setPlaceholderText("Ej: López")
        if self.patient_data:
            self.apellido_materno_input.setText(self.patient_data.get('apellido_materno', ''))
        form_layout.addRow("Apellido Materno:", self.apellido_materno_input)
        
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: María Elena")
        if self.patient_data:
            self.nombre_input.setText(self.patient_data.get('nombre', ''))
        form_layout.addRow("Nombre(s):", self.nombre_input)
        
        self.fecha_nacimiento_input = QDateEdit()
        self.fecha_nacimiento_input.setCalendarPopup(True)
        self.fecha_nacimiento_input.setDisplayFormat("dd/MM/yyyy")
        if self.patient_data and self.patient_data.get('fecha_nacimiento'):
            # Convertir fecha de formato YYYY-MM-DD a QDate
            try:
                fecha_str = self.patient_data.get('fecha_nacimiento')
                year, month, day = fecha_str.split('-')
                fecha_qdate = QDate(int(year), int(month), int(day))
                self.fecha_nacimiento_input.setDate(fecha_qdate)
            except:
                self.fecha_nacimiento_input.setDate(QDate.currentDate().addYears(-30))
        else:
            self.fecha_nacimiento_input.setDate(QDate.currentDate().addYears(-30))
        form_layout.addRow("Fecha de Nacimiento:", self.fecha_nacimiento_input)
        
        self.celular_input = QLineEdit()
        self.celular_input.setPlaceholderText("Ej: 78551234")
        self.celular_input.setMaxLength(8)
        if self.patient_data:
            self.celular_input.setText(self.patient_data.get('celular', ''))
        form_layout.addRow("Celular:", self.celular_input)
        
        layout.addWidget(form_group)
        
        # === COMENTARIOS ===
        comments_group = QGroupBox("Comentarios")
        comments_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
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
        
        self.comentarios_input = QTextEdit()
        self.comentarios_input.setPlaceholderText("Comentarios adicionales, condiciones médicas, etc.")
        self.comentarios_input.setMaximumHeight(80)
        if self.patient_data:
            self.comentarios_input.setPlainText(self.patient_data.get('comentarios', ''))
        
        comments_layout.addWidget(self.comentarios_input)
        layout.addWidget(comments_group)
        
        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón Guardar
        save_button = QPushButton("Guardar Cambios")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #00A99D;
                min-width: 120px;
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
        save_button.clicked.connect(self.save_changes)
        
        # Botón Cancelar
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
                min-width: 120px;
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
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Aplicar estilos globales
        self.apply_styles()
        
    def apply_styles(self):
        """Aplica los estilos al diálogo"""
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
            
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
            
            QLineEdit, QDateEdit, QTextEdit {
                background-color: #525252;
                border: 2px solid #666666;
                border-radius: 6px;
                padding: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {
                border: 2px solid #00A99D;
                background-color: #5a5a5a;
            }
            
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #BBBBBB;
                font-style: italic;
            }
            
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #666666;
                background-color: #666666;
                border-radius: 0px;
            }
            
            QDateEdit::down-arrow {
                image: none;
                border: none;
                width: 0px;
                height: 0px;
            }
            
            /* === ESTILOS PARA EL CALENDARIO DESPLEGABLE === */
            QCalendarWidget {
                background-color: #424242;
                color: #FFFFFF;
                border: 2px solid #00A99D;
                border-radius: 8px;
            }
            
            QCalendarWidget QWidget {
                background-color: #424242;
                color: #FFFFFF;
            }
            
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #323232;
                border-bottom: 1px solid #00A99D;
            }
            
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #424242;
                color: #FFFFFF;
                selection-background-color: #00A99D;
                selection-color: #FFFFFF;
            }
            
            QCalendarWidget QTableView QHeaderView::section {
                background-color: #323232;
                color: #00A99D;
                border: 1px solid #555555;
                padding: 4px;
                font-weight: bold;
            }
            
            QCalendarWidget QTableView {
                background-color: #424242;
                gridline-color: #555555;
                alternate-background-color: #383838;
            }
            
            QCalendarWidget QTableView::item {
                background-color: #424242;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 4px;
            }
            
            QCalendarWidget QTableView::item:selected {
                background-color: #00A99D;
                color: #FFFFFF;
                font-weight: bold;
            }
            
            QCalendarWidget QTableView::item:hover {
                background-color: #525252;
                color: #FFFFFF;
            }
            
            QCalendarWidget QTableView::item:disabled {
                background-color: #2a2a2a;
                color: #888888;
            }
            
            QCalendarWidget QToolButton {
                background-color: #525252;
                color: #FFFFFF;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
            }
            
            QCalendarWidget QToolButton:hover {
                background-color: #00A99D;
                border-color: #00C2B3;
            }
            
            QCalendarWidget QToolButton:pressed {
                background-color: #008C82;
            }
            
            QCalendarWidget QComboBox {
                background-color: #525252;
                color: #FFFFFF;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 2px 8px;
            }
            
            QCalendarWidget QComboBox:hover {
                background-color: #5a5a5a;
                border-color: #00A99D;
            }
            
            QCalendarWidget QComboBox::drop-down {
                background-color: #424242;
                border-left: 1px solid #666666;
            }
            
            QCalendarWidget QComboBox QAbstractItemView {
                background-color: #424242;
                color: #FFFFFF;
                selection-background-color: #00A99D;
            }
        """)
        
    def save_changes(self):
        """Guarda los cambios realizados al paciente"""
        try:
            # Validar campos obligatorios
            if not self.apellido_paterno_input.text().strip():
                QMessageBox.warning(self, "Error", "El apellido paterno es obligatorio.")
                self.apellido_paterno_input.setFocus()
                return
                
            if not self.nombre_input.text().strip():
                QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
                self.nombre_input.setFocus()
                return
                
            if not self.celular_input.text().strip():
                QMessageBox.warning(self, "Error", "El número de celular es obligatorio.")
                self.celular_input.setFocus()
                return
                
            # Validar celular (solo números y longitud)
            celular = self.celular_input.text().strip()
            if not celular.isdigit() or len(celular) != 8:
                QMessageBox.warning(self, "Error", "El celular debe tener exactamente 8 dígitos.")
                self.celular_input.setFocus()
                return
                
            # Validar fecha de nacimiento (no puede ser futura)
            fecha_nacimiento = self.fecha_nacimiento_input.date()
            if fecha_nacimiento > QDate.currentDate():
                QMessageBox.warning(self, "Error", "La fecha de nacimiento no puede ser futura.")
                self.fecha_nacimiento_input.setFocus()
                return
            
            # Reproducir sonido de confirmación
            winsound.MessageBeep(winsound.MB_ICONQUESTION)
            
            # Diálogo de confirmación
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirmar Cambios")
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setText("¿Está seguro de que desea guardar los cambios realizados?")
            
            # Crear botones personalizados
            save_button = msg_box.addButton("Guardar", QMessageBox.AcceptRole)
            cancel_button = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(cancel_button)
            
            # Aplicar estilo personalizado
            msg_box.setStyleSheet("""
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
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #00C2B3;
                    border: 2px solid #00C2B3;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #008C82;
                    border: 2px solid #008C82;
                }
                QMessageBox QPushButton[text="Cancelar"] {
                    background-color: #757575;
                    border: 2px solid #757575;
                }
                QMessageBox QPushButton[text="Cancelar"]:hover {
                    background-color: #9E9E9E;
                    border: 2px solid #9E9E9E;
                }
                QMessageBox QPushButton[text="Cancelar"]:pressed {
                    background-color: #616161;
                    border: 2px solid #616161;
                }
            """)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == save_button:
                # Actualizar el paciente en la base de datos
                success = DatabaseManager.update_patient(
                    patient_id=self.patient_id,
                    apellido_paterno=self.apellido_paterno_input.text().strip(),
                    apellido_materno=self.apellido_materno_input.text().strip(),
                    nombre=self.nombre_input.text().strip(),
                    fecha_nacimiento=self.fecha_nacimiento_input.date().toString("yyyy-MM-dd"),
                    celular=self.celular_input.text().strip(),
                    comentarios=self.comentarios_input.toPlainText().strip()
                )
                
                if success:
                    # Reproducir sonido de éxito
                    winsound.MessageBeep(winsound.MB_OK)
                    
                    # Mostrar mensaje de éxito
                    success_msg = QMessageBox(self)
                    success_msg.setWindowTitle("Cambios Guardados")
                    success_msg.setText("Los datos del paciente han sido actualizados exitosamente.")
                    success_msg.setIcon(QMessageBox.Information)
                    
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
                            min-width: 80px;
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
                    
                    # Cerrar el diálogo con éxito
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudieron guardar los cambios. Intente nuevamente.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar los cambios: {str(e)}")
    
    def get_updated_data(self):
        """Retorna los datos actualizados del paciente"""
        return {
            'apellido_paterno': self.apellido_paterno_input.text().strip(),
            'apellido_materno': self.apellido_materno_input.text().strip(),
            'nombre': self.nombre_input.text().strip(),
            'fecha_nacimiento': self.fecha_nacimiento_input.date().toString("yyyy-MM-dd"),
            'celular': self.celular_input.text().strip(),
            'comentarios': self.comentarios_input.toPlainText().strip()
        }
