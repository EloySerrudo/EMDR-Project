from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QDialog, QGroupBox, QRadioButton, QButtonGroup
)


class NewSessionDialog(QDialog):
    """Diálogo para crear una nueva sesión"""
    
    def __init__(self, patient_data, parent=None):
        super().__init__(parent)
        self.patient_data = patient_data
        self.session_datetime = datetime.now()  # Capturar fecha y hora con precisión de milisegundos
        
        self.setWindowTitle("Nueva Sesión")
        self.resize(500, 400)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # === INFORMACIÓN DEL PACIENTE ===
        patient_group = QGroupBox("Información del Paciente")
        patient_group.setStyleSheet("""
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
        
        patient_layout = QVBoxLayout(patient_group)
        
        # Nombre del paciente
        patient_name = f"{self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}"
        name_label = QLabel(f"Paciente: {patient_name}")
        name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                padding: 5px;
            }
        """)
        patient_layout.addWidget(name_label)
        
        layout.addWidget(patient_group)
        
        # === FECHA Y HORA DE LA SESIÓN ===
        datetime_group = QGroupBox("Fecha y Hora de la Sesión")
        datetime_group.setStyleSheet("""
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
        
        datetime_layout = QHBoxLayout(datetime_group)
        
        # Fecha (solo fecha)
        date_str = self.session_datetime.strftime("%d/%m/%Y")
        date_label = QLabel(f"Fecha: {date_str}")
        date_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # Hora (solo hora y minutos)
        time_str = self.session_datetime.strftime("%H:%M")
        time_label = QLabel(f"Hora: {time_str}")
        time_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        datetime_layout.addWidget(date_label)
        datetime_layout.addWidget(time_label)
        
        layout.addWidget(datetime_group)
        
        # === TIPO DE SESIÓN ===
        session_type_group = QGroupBox("Tipo de Sesión")
        session_type_group.setStyleSheet("""
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
        
        session_type_layout = QVBoxLayout(session_type_group)
        
        # Crear grupo de botones radio
        self.session_type_group = QButtonGroup(self)
        
        # Opción 1: Desensibilización de recuerdo traumático
        self.radio_desensitization = QRadioButton("Desensibilización de recuerdo traumático")
        self.radio_desensitization.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 13px;
                background: transparent;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #323232;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #00A99D;
                border-radius: 8px;
                background-color: #00A99D;
            }
        """)
        self.session_type_group.addButton(self.radio_desensitization, 1)
        session_type_layout.addWidget(self.radio_desensitization)
        
        # Opción 2: Instalación de creencia positiva
        self.radio_positive_belief = QRadioButton("Instalación de creencia positiva")
        self.radio_positive_belief.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 13px;
                background: transparent;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #323232;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #00A99D;
                border-radius: 8px;
                background-color: #00A99D;
            }
        """)
        self.session_type_group.addButton(self.radio_positive_belief, 2)
        session_type_layout.addWidget(self.radio_positive_belief)
        
        # Opción 3: Regulación emocional / Ansiedad
        self.radio_emotional_regulation = QRadioButton("Regulación emocional / Ansiedad")
        self.radio_emotional_regulation.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 13px;
                background: transparent;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #323232;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #00A99D;
                border-radius: 8px;
                background-color: #00A99D;
            }
        """)
        self.session_type_group.addButton(self.radio_emotional_regulation, 3)
        session_type_layout.addWidget(self.radio_emotional_regulation)
        
        # Opción 4: Otro (con campo de texto)
        other_layout = QHBoxLayout()
        
        self.radio_other = QRadioButton("Otro:")
        self.radio_other.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 13px;
                background: transparent;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #323232;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #00A99D;
                border-radius: 8px;
                background-color: #00A99D;
            }
        """)
        self.session_type_group.addButton(self.radio_other, 4)
        
        self.other_text = QLineEdit()
        self.other_text.setPlaceholderText("Especifique el tipo de sesión...")
        self.other_text.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 2px solid #555555;
                border-radius: 4px;
                font-size: 12px;
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
        self.other_text.setEnabled(False)  # Inicialmente deshabilitado
        
        # Conectar el radio button "Otro" para habilitar/deshabilitar el campo de texto
        self.radio_other.toggled.connect(self.on_other_toggled)
        
        other_layout.addWidget(self.radio_other)
        other_layout.addWidget(self.other_text)
        
        session_type_layout.addLayout(other_layout)
        
        # Seleccionar la primera opción por defecto
        self.radio_desensitization.setChecked(True)
        
        layout.addWidget(session_type_group)
        
        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón para crear sesión
        create_button = QPushButton("Crear Sesión")
        create_button.setStyleSheet("""
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
        create_button.clicked.connect(self.create_session)
        
        # Botón para cancelar
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
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(create_button)
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
    
    def on_other_toggled(self, checked):
        """Habilita o deshabilita el campo de texto cuando se selecciona 'Otro'"""
        self.other_text.setEnabled(checked)
        if checked:
            self.other_text.setFocus()
        else:
            self.other_text.clear()
    
    def get_selected_session_type(self):
        """Obtiene el tipo de sesión seleccionado"""
        selected_button = self.session_type_group.checkedButton()
        selected_id = self.session_type_group.id(selected_button)
        
        if selected_id == 1:
            return "Desensibilización de recuerdo traumático"
        elif selected_id == 2:
            return "Instalación de creencia positiva"
        elif selected_id == 3:
            return "Regulación emocional / Ansiedad"
        elif selected_id == 4:
            # Opción "Otro"
            other_text = self.other_text.text().strip()
            return other_text if other_text else "Sin especificar"
        else:
            return "Desensibilización de recuerdo traumático"  # Por defecto
    
    def create_session(self):
        """Crea la nueva sesión"""
        try:
            session_type = self.get_selected_session_type()
            
            # Aquí puedes agregar la lógica para crear la sesión en la base de datos
            # Por ahora solo mostraremos un mensaje de confirmación
            
            QMessageBox.information(
                self,
                "Sesión Creada",
                f"Nueva sesión creada exitosamente:\n\n"
                f"Paciente: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}\n"
                f"Fecha: {self.session_datetime.strftime('%d/%m/%Y')}\n"
                f"Hora: {self.session_datetime.strftime('%H:%M')}\n"
                f"Tipo: {session_type}\n\n"
                f"Timestamp completo: {self.session_datetime.isoformat()}"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo crear la sesión:\n{str(e)}"
            )