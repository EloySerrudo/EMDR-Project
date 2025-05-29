import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QTextEdit, QGroupBox, QSplitter,
    QMainWindow, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager


class PatientDetailsDialog(QDialog):
    """Diálogo para mostrar los detalles completos de un paciente"""
    
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.patient_data = None
        
        self.setWindowTitle("Detalles del Paciente")
        self.resize(600, 500)
        self.setModal(True)
        
        self.load_patient_data()
        self.setup_ui()
        
    def load_patient_data(self):
        """Carga los datos completos del paciente desde la base de datos"""
        try:
            self.patient_data = DatabaseManager.get_patient_by_id(self.patient_id)
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
        
        # Título con nombre del paciente
        if self.patient_data:
            title = QLabel(f"Información de {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')}")
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1565C0; padding: 10px;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
        
        # Crear área de scroll para el contenido
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Widget contenedor para el contenido
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # === DATOS PERSONALES ===
        personal_group = QGroupBox("Datos Personales")
        personal_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #E3F2FD;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #1565C0;
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
        
        content_layout.addWidget(personal_group)
        
        # === NOTAS CLÍNICAS ===
        notes_group = QGroupBox("Notas Clínicas")
        notes_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #E8F5E8;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #2E7D32;
            }
        """)
        
        notes_layout = QVBoxLayout(notes_group)
        
        # Campo de texto para las notas (solo lectura)
        self.notes_display = QTextEdit()
        self.notes_display.setReadOnly(True)
        self.notes_display.setMaximumHeight(150)
        self.notes_display.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        if self.patient_data and self.patient_data.get('notas'):
            self.notes_display.setPlainText(self.patient_data.get('notas'))
        else:
            self.notes_display.setPlainText("No hay notas registradas para este paciente.")
        
        notes_layout.addWidget(self.notes_display)
        content_layout.addWidget(notes_group)
        
        # === HISTORIAL DE SESIONES ===
        sessions_group = QGroupBox("Historial de Sesiones")
        sessions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #FFF3E0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #F57C00;
            }
        """)
        
        sessions_layout = QVBoxLayout(sessions_group)
        
        # Cargar historial de sesiones
        self.load_session_history(sessions_layout)
        
        content_layout.addWidget(sessions_group)
        
        # Configurar el scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón para editar paciente
        edit_button = QPushButton("Editar Datos")
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        edit_button.clicked.connect(self.edit_patient)
        
        # Botón para nueva sesión
        new_session_button = QPushButton("Nueva Sesión")
        new_session_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        new_session_button.clicked.connect(self.new_session)
        
        # Botón para cerrar
        close_button = QPushButton("Cerrar")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(edit_button)
        button_layout.addWidget(new_session_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def create_info_field(self, layout, label_text, value_text):
        """Crea un campo de información con etiqueta y valor"""
        value_label = QLabel(str(value_text))
        value_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-weight: normal;
            }
        """)
        value_label.setWordWrap(True)
        layout.addRow(label_text, value_label)
    
    def load_session_history(self, layout):
        """Carga el historial de sesiones del paciente"""
        try:
            sessions = DatabaseManager.get_patient_sessions(self.patient_id)
            
            if not sessions:
                no_sessions_label = QLabel("No hay sesiones registradas para este paciente.")
                no_sessions_label.setStyleSheet("color: #757575; font-style: italic; padding: 10px;")
                layout.addWidget(no_sessions_label)
            else:
                # Crear tabla para mostrar las sesiones
                sessions_table = QTableWidget()
                sessions_table.setColumnCount(4)
                sessions_table.setHorizontalHeaderLabels(["Fecha", "Duración", "Tipo", "Notas"])
                sessions_table.setRowCount(len(sessions))
                
                # Configurar tabla
                sessions_table.setAlternatingRowColors(True)
                sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
                sessions_table.verticalHeader().setVisible(False)
                sessions_table.setMaximumHeight(200)
                
                # Llenar tabla con datos de sesiones
                for i, session in enumerate(sessions):
                    sessions_table.setItem(i, 0, QTableWidgetItem(str(session.get('fecha', ''))))
                    sessions_table.setItem(i, 1, QTableWidgetItem(str(session.get('duracion', ''))))
                    sessions_table.setItem(i, 2, QTableWidgetItem(str(session.get('tipo', 'EMDR'))))
                    sessions_table.setItem(i, 3, QTableWidgetItem(str(session.get('notas', ''))))
                
                # Ajustar columnas
                sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                
                layout.addWidget(sessions_table)
                
        except Exception as e:
            error_label = QLabel(f"Error al cargar sesiones: {str(e)}")
            error_label.setStyleSheet("color: #F44336; padding: 10px;")
            layout.addWidget(error_label)
    
    def edit_patient(self):
        """Abre un diálogo para editar los datos del paciente"""
        QMessageBox.information(self, "Función en desarrollo", 
                               "La función de editar paciente estará disponible pronto.")
    
    def new_session(self):
        """Inicia una nueva sesión para el paciente"""
        QMessageBox.information(self, "Función en desarrollo", 
                               "La función de nueva sesión estará disponible pronto.")


class PatientManagerWidget(QMainWindow):
    """Widget principal para gestionar pacientes"""
    
    # Señal emitida cuando se selecciona un paciente
    patient_selected = Signal(int, str)  # ID del paciente, nombre completo
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.patients_data = []
        
        self.setWindowTitle("EMDR Project - Gestión de Pacientes")
        self.resize(800, 600)
        
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
        header_frame.setStyleSheet("background-color: #1565C0; border-radius: 8px;")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel("GESTIÓN DE PACIENTES")
        title_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        
        if self.username:
            user_label = QLabel(f"Terapeuta: {self.username}")
            user_label.setStyleSheet("color: white; font-size: 14px;")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(user_label)
        else:
            header_layout.addWidget(title_label, 0, Qt.AlignCenter)
        
        main_layout.addWidget(header_frame)
        
        # === BARRA DE BÚSQUEDA ===
        search_frame = QFrame()
        search_frame.setFrameShape(QFrame.StyledPanel)
        search_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 6px;")
        
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 10, 10, 10)
        
        search_label = QLabel("Buscar paciente:")
        search_label.setStyleSheet("font-weight: bold;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escriba el nombre, apellido o ID del paciente...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
        """)
        self.search_input.textChanged.connect(self.filter_patients)
        
        self.search_button = QPushButton("Buscar")
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.search_button.clicked.connect(self.filter_patients)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        
        main_layout.addWidget(search_frame)
        
        # === TABLA DE PACIENTES ===
        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(6)
        self.patients_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Apellido Paterno", "Apellido Materno", "Edad", "Teléfono"
        ])
        
        # Configurar tabla
        self.patients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patients_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patients_table.setAlternatingRowColors(True)
        self.patients_table.verticalHeader().setVisible(False)
        
        # Estilo de la tabla
        self.patients_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                gridline-color: #E0E0E0;
            }
            QHeaderView::section {
                background-color: #E3F2FD;
                padding: 10px;
                font-weight: bold;
                border: 0;
                color: #1565C0;
                border-bottom: 2px solid #2196F3;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E0E0E0;
            }
            QTableWidget::item:selected {
                background-color: #BBDEFB;
                color: #0D47A1;
            }
        """)
        
        # Ajustar columnas
        header = self.patients_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Nombre
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Apellido Paterno
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Apellido Materno
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Edad
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Teléfono
        
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
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.details_button.clicked.connect(self.show_patient_details)
        self.details_button.setEnabled(False)
        
        # Botón para refrescar
        refresh_button = QPushButton("Actualizar Lista")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        refresh_button.clicked.connect(self.load_patients)
        
        # Botón para cerrar
        close_button = QPushButton("Cerrar")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.details_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        main_layout.addWidget(button_frame)
        
        # === BARRA DE ESTADO ===
        self.status_label = QLabel("Cargando pacientes...")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # Conectar selección de tabla
        self.patients_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
    
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
            self.patients_table.setItem(i, 0, QTableWidgetItem(str(patient.get('id', ''))))
            self.patients_table.setItem(i, 1, QTableWidgetItem(patient.get('nombre', '')))
            self.patients_table.setItem(i, 2, QTableWidgetItem(patient.get('apellido_paterno', '')))
            self.patients_table.setItem(i, 3, QTableWidgetItem(patient.get('apellido_materno', '')))
            self.patients_table.setItem(i, 4, QTableWidgetItem(str(patient.get('edad', ''))))
            self.patients_table.setItem(i, 5, QTableWidgetItem(patient.get('celular', '')))
        
        # Resetear selección
        self.patients_table.clearSelection()
        self.details_button.setEnabled(False)
    
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
        self.details_button.setEnabled(len(selected_rows) > 0)
    
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
            QMessageBox.warning(self, "Error", "No se pudo obtener el ID del paciente")
            return
        
        try:
            patient_id = int(patient_id_item.text())
            
            # Abrir diálogo de detalles
            details_dialog = PatientDetailsDialog(patient_id, self)
            details_dialog.exec()
            
        except ValueError:
            QMessageBox.warning(self, "Error", "ID de paciente inválido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mostrar detalles: {str(e)}")


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear ventana principal
    patient_manager = PatientManagerWidget("Dr. Juan Pérez")
    patient_manager.show()
    
    sys.exit(app.exec())