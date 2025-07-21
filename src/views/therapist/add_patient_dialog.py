from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox, QSizePolicy, QDialog,
    QLineEdit, QTextEdit, QDateEdit, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QIcon
import qtawesome as qta


class AddPatientDialog(QDialog):
    """Diálogo para añadir un nuevo paciente"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir Nuevo Paciente")
        self.setFixedSize(450, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.apply_styles()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título del diálogo
        title_label = QLabel("Registro de Nuevo Paciente")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #00A99D;
                margin-bottom: 10px;
                padding: 10px;
                background-color: rgba(0, 169, 157, 0.1);
                border-radius: 8px;
            }
        """)
        layout.addWidget(title_label)
        
        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Campos del formulario
        self.apellido_paterno_input = QLineEdit()
        self.apellido_paterno_input.setPlaceholderText("Ej: García")
        form_layout.addRow("Apellido Paterno *:", self.apellido_paterno_input)
        
        self.apellido_materno_input = QLineEdit()
        self.apellido_materno_input.setPlaceholderText("Ej: López (opcional)")
        form_layout.addRow("Apellido Materno:", self.apellido_materno_input)
        
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: María Elena")
        form_layout.addRow("Nombre(s) *:", self.nombre_input)
        
        self.fecha_nacimiento_input = QDateEdit()
        self.fecha_nacimiento_input.setDate(QDate.currentDate().addYears(-30))
        self.fecha_nacimiento_input.setCalendarPopup(True)
        self.fecha_nacimiento_input.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Fecha de Nacimiento *:", self.fecha_nacimiento_input)
        
        self.celular_input = QLineEdit()
        self.celular_input.setPlaceholderText("Ej: 78551234")
        self.celular_input.setMaxLength(8)
        form_layout.addRow("Celular *:", self.celular_input)
        
        self.comentarios_input = QTextEdit()
        self.comentarios_input.setPlaceholderText("Comentarios adicionales, condiciones médicas, alergias, etc.")
        self.comentarios_input.setMaximumHeight(100)
        form_layout.addRow("Comentarios:", self.comentarios_input)
        
        layout.addLayout(form_layout)
        
        # Nota informativa con icono
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(5)
        
        # Icono de información
        info_icon = qta.icon('fa5s.info-circle', color='#FF9800')
        info_icon_label = QLabel()
        info_icon_label.setPixmap(info_icon.pixmap(16, 16))
        
        info_label = QLabel("* Campos obligatorios")
        info_label.setStyleSheet("""
            QLabel {
                color: #FF9800;
                font-style: italic;
                font-size: 12px;
                margin-top: 5px;
            }
        """)
        
        info_layout.addWidget(info_icon_label)
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        
        info_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(info_frame)
        
        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText("Guardar Paciente")
        button_box.button(QDialogButtonBox.Cancel).setText("Cancelar")
        
        button_box.accepted.connect(self.accept_patient)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # Guardar referencias a los botones para aplicar estilos
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.cancel_button = button_box.button(QDialogButtonBox.Cancel)
        
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
            }
            
            QLabel {
                background: transparent;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
            
            QLineEdit, QDateEdit, QTextEdit {
                background-color: #525252;
                border: 2px solid #666666;
                border-radius: 6px;
                padding: 8px;
                color: #FFFFFF;
                font-size: 14px;
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
            }
            
            QDateEdit::down-arrow {
                image: none;
                border: none;
                width: 0px;
                height: 0px;
            }
            
            /* === ESTILOS PARA EL CALENDARIO DESPLEGABLE === */
            /* Días del mes */
            QCalendarWidget QTableView::item {
                background-color: #424242;
                color: #FFFFFF;
                border: none;
                padding: 4px;
            }
            
            /* Día seleccionado */
            QCalendarWidget QTableView::item:selected {
                background-color: #00A99D;
                color: #FFFFFF;
                font-weight: bold;
            }
            
            /* Día al pasar el mouse */
            QCalendarWidget QTableView::item:hover {
                background-color: #525252;
                color: #FFFFFF;
            }
            
            /* Días de otros meses (grises) */
            QCalendarWidget QTableView::item:disabled {
                background-color: #2a2a2a;
                color: #888888;
            }
            
            /* === FIN DE ESTILOS DEL CALENDARIO === */
            
            QDialogButtonBox QPushButton {
                background-color: #00A99D;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QDialogButtonBox QPushButton:hover {
                background-color: #00C2B3;
            }
            
            QDialogButtonBox QPushButton:pressed {
                background-color: #008C82;
            }
            
            QDialogButtonBox QPushButton[text="Cancelar"] {
                background-color: #757575;
            }
            
            QDialogButtonBox QPushButton[text="Cancelar"]:hover {
                background-color: #9E9E9E;
            }
            
            QDialogButtonBox QPushButton[text="Cancelar"]:pressed {
                background-color: #616161;
            }
        """)
        
    def accept_patient(self):
        """Valida y acepta los datos del paciente"""
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
            
        # Si todo está correcto, aceptar el diálogo
        self.accept()
        
    def get_patient_data(self):
        """Retorna los datos del paciente ingresados"""
        return {
            'apellido_paterno': self.apellido_paterno_input.text().strip(),
            'apellido_materno': self.apellido_materno_input.text().strip(),
            'nombre': self.nombre_input.text().strip(),
            'fecha_nacimiento': self.fecha_nacimiento_input.date().toString("yyyy-MM-dd"),
            'celular': self.celular_input.text().strip(),
            'comentarios': self.comentarios_input.toPlainText().strip()
        }