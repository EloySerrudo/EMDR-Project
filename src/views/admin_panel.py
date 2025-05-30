import sys
import os
import winsound
import hashlib
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
    QFormLayout, QGroupBox, QHeaderView, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor, QPixmap
from pathlib import Path

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar el gestor de base de datos
from src.database.database_manager import DatabaseManager


class TherapistDialog(QDialog):
    """Diálogo para añadir o editar un terapeuta"""
    
    def __init__(self, parent=None, therapist_data=None):
        super().__init__(parent)
        self.therapist_data = therapist_data  # None para nuevo, dict para edición
        
        if therapist_data:
            self.setWindowTitle("Editar Terapeuta")
        else:
            self.setWindowTitle("Añadir Nuevo Terapeuta")
            
        self.resize(450, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Grupo de datos personales
        personal_group = QGroupBox("Datos Personales")
        personal_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #424242;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px;
                color: #00A99D;
                left: 15px;
            }
        """)
        personal_layout = QFormLayout(personal_group)
        personal_layout.setLabelAlignment(Qt.AlignRight)
        
        # Estilo para las etiquetas del formulario
        label_style = """
            QLabel {
                color: white;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
            }
        """
        
        self.nombre_input = QLineEdit()
        self.apellido_paterno_input = QLineEdit()
        self.apellido_materno_input = QLineEdit()
        
        # Estilo para inputs
        input_style = """
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #555555;
                border-radius: 6px;
                background-color: #323232;
                font-size: 14px;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #00A99D;
                background-color: #2a2a2a;
            }
        """
        
        self.nombre_input.setStyleSheet(input_style)
        self.apellido_paterno_input.setStyleSheet(input_style)
        self.apellido_materno_input.setStyleSheet(input_style)
        
        # Crear etiquetas personalizadas con estilo
        nombre_label = QLabel("Nombre:")
        nombre_label.setStyleSheet(label_style)
        apellido_paterno_label = QLabel("Apellido Paterno:")
        apellido_paterno_label.setStyleSheet(label_style)
        apellido_materno_label = QLabel("Apellido Materno:")
        apellido_materno_label.setStyleSheet(label_style)
        
        personal_layout.addRow(nombre_label, self.nombre_input)
        personal_layout.addRow(apellido_paterno_label, self.apellido_paterno_input)
        personal_layout.addRow(apellido_materno_label, self.apellido_materno_input)
        
        # Grupo de credenciales
        credentials_group = QGroupBox("Credenciales de Acceso")
        credentials_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #424242;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px;
                color: #00A99D;
                left: 15px;
            }
        """)
        credentials_layout = QFormLayout(credentials_group)
        credentials_layout.setLabelAlignment(Qt.AlignRight)
        
        self.user_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.Password)
        
        self.user_input.setStyleSheet(input_style)
        self.password_input.setStyleSheet(input_style)
        self.password_confirm_input.setStyleSheet(input_style)
        
        # Crear etiquetas personalizadas con estilo para credenciales
        usuario_label = QLabel("Usuario:")
        usuario_label.setStyleSheet(label_style)
        password_label = QLabel("Contraseña:")
        password_label.setStyleSheet(label_style)
        confirm_password_label = QLabel("Confirmar Contraseña:")
        confirm_password_label.setStyleSheet(label_style)
        
        credentials_layout.addRow(usuario_label, self.user_input)
        credentials_layout.addRow(password_label, self.password_input)
        credentials_layout.addRow(confirm_password_label, self.password_confirm_input)
        
        # Si estamos editando, mostrar mensaje sobre contraseña
        if self.therapist_data:
            password_note = QLabel("Deje en blanco para mantener la contraseña actual")
            password_note.setStyleSheet("""
                QLabel {
                    color: #E3F2FD; 
                    font-size: 11px; 
                    font-style: italic;
                    background: transparent;
                }
            """)
            credentials_layout.addRow("", password_note)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.save_therapist)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
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
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        # Añadir todos los elementos al layout principal
        layout.addWidget(personal_group)
        layout.addWidget(credentials_group)
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        
        # Si estamos editando, llenar los campos con los datos existentes
        if self.therapist_data:
            self.nombre_input.setText(self.therapist_data.get('nombre', ''))
            self.apellido_paterno_input.setText(self.therapist_data.get('apellido_paterno', ''))
            self.apellido_materno_input.setText(self.therapist_data.get('apellido_materno', ''))
            self.user_input.setText(self.therapist_data.get('user', ''))
        
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
            QFormLayout QLabel {
                color: #FFFFFF;
                font-weight: bold;
                background: transparent;
            }
        """)
    
    def validate_inputs(self):
        """Valida los inputs antes de guardar"""
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Error", "El nombre no puede estar vacío")
            return False
            
        if not self.apellido_paterno_input.text().strip():
            QMessageBox.warning(self, "Error", "El apellido paterno no puede estar vacío")
            return False
            
        if not self.apellido_materno_input.text().strip():
            QMessageBox.warning(self, "Error", "El apellido materno no puede estar vacío")
            return False
            
        if not self.user_input.text().strip():
            QMessageBox.warning(self, "Error", "El usuario no puede estar vacío")
            return False
            
        # Si es nuevo usuario o se está cambiando la contraseña
        if not self.therapist_data or self.password_input.text():
            if not self.password_input.text():
                QMessageBox.warning(self, "Error", "La contraseña no puede estar vacía")
                return False
                
            if self.password_input.text() != self.password_confirm_input.text():
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
                return False
        
        return True
    
    def save_therapist(self):
        """Guarda los datos del terapeuta"""
        if not self.validate_inputs():
            return
            
        try:
            user = self.user_input.text().strip()
            nombre = self.nombre_input.text().strip()
            apellido_paterno = self.apellido_paterno_input.text().strip()
            apellido_materno = self.apellido_materno_input.text().strip()
            
            # Si hay contraseña, generar hash
            password_hash = None
            if self.password_input.text():
                password_hash = hashlib.sha256(self.password_input.text().encode()).hexdigest()
            
            if self.therapist_data:
                # Actualizar terapeuta existente
                DatabaseManager.update_therapist(
                    self.therapist_data['id'], 
                    user, 
                    password_hash, 
                    apellido_paterno, 
                    apellido_materno, 
                    nombre
                )
                QMessageBox.information(self, "Éxito", "Terapeuta actualizado correctamente")
            else:
                # Añadir nuevo terapeuta
                if password_hash is None:
                    QMessageBox.warning(self, "Error", "La contraseña es obligatoria para nuevos terapeutas")
                    return
                    
                DatabaseManager.add_therapist(
                    user, 
                    password_hash, 
                    apellido_paterno, 
                    apellido_materno, 
                    nombre
                )
                QMessageBox.information(self, "Éxito", "Terapeuta añadido correctamente")
            
            self.accept()  # Cierra el diálogo con éxito
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el terapeuta: {str(e)}")


class AdminPanel(QMainWindow):
    """Panel de administración para gestionar terapeutas"""
    
    # Señal emitida cuando se solicita cerrar sesión
    logout_requested = Signal()
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        
        self.setWindowTitle("EMDR Project - Panel de Administración")
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'icon.png')))
        self.resize(1000, 700)
        
        # Centrar ventana en pantalla
        self.center_on_screen()
        
        self.setup_ui()
        self.load_therapists()
    
    def center_on_screen(self):
        """Centra la ventana en la pantalla"""
        desktop_rect = QApplication.primaryScreen().availableGeometry()
        center = desktop_rect.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center)
        self.move(frame_geometry.topLeft())
    
    def setup_ui(self):
        """Configura la interfaz del panel de administración"""
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
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Logo o título principal
        logo_label = QLabel()
        
        # Intentar cargar logo desde recursos
        logo_path = Path(__file__).parent.parent / 'resources' / 'emdr_logo.png'
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
        
        title_label = QLabel("PANEL DE ADMINISTRACIÓN")
        title_label.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 24px; 
                font-weight: bold;
                background: transparent;
            }
        """)
        
        user_label = QLabel(f"Administrador: {self.username}")
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
        
        main_layout.addWidget(header_frame)
        
        # Sección de terapeutas
        therapist_section = QGroupBox("Gestión de Terapeutas")
        therapist_section.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #00A99D;
                border-radius: 10px;
                margin-top: 15px;
                background-color: #424242;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px;
                color: #00A99D;
                left: 15px;
            }
        """)
        
        therapist_layout = QVBoxLayout(therapist_section)
        therapist_layout.setSpacing(15)
        
        # Botones de acción para terapeutas
        button_layout = QHBoxLayout()
        
        self.add_therapist_btn = QPushButton("Añadir Terapeuta")
        self.add_therapist_btn.clicked.connect(self.add_therapist)
        self.add_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
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
        
        self.edit_therapist_btn = QPushButton("Editar Terapeuta")
        self.edit_therapist_btn.clicked.connect(self.edit_therapist)
        self.edit_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
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
        
        self.delete_therapist_btn = QPushButton("Eliminar Terapeuta")
        self.delete_therapist_btn.clicked.connect(self.delete_therapist)
        self.delete_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #00A99D;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
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
        
        button_layout.addWidget(self.add_therapist_btn)
        button_layout.addWidget(self.edit_therapist_btn)
        button_layout.addWidget(self.delete_therapist_btn)
        button_layout.addStretch()
        
        therapist_layout.addLayout(button_layout)
        
        # Tabla de terapeutas
        self.therapist_table = QTableWidget()
        self.therapist_table.setColumnCount(5)
        self.therapist_table.setHorizontalHeaderLabels([
            "ID", "Usuario", "Apellido Paterno", "Apellido Materno", "Nombre"
        ])
        
        # Configurar la tabla
        self.therapist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.therapist_table.setSelectionMode(QTableWidget.SingleSelection)
        self.therapist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.therapist_table.verticalHeader().setVisible(False)
        self.therapist_table.setAlternatingRowColors(True)
        self.therapist_table.setStyleSheet("""
            QTableWidget {
                background-color: #323232;
                alternate-background-color: #2a2a2a;
                border: 2px solid #555555;
                border-radius: 8px;
                color: white;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #00A99D;
                padding: 8px;
                font-weight: bold;
                border: 1px solid #008C82;
                color: white;
                font-size: 14px;
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
        
        # Doble clic para editar
        self.therapist_table.doubleClicked.connect(self.edit_therapist)
        
        therapist_layout.addWidget(self.therapist_table)
        
        main_layout.addWidget(therapist_section)
        
        # Footer con botones de navegación
        footer_layout = QHBoxLayout()
        
        logout_btn = QPushButton("Cerrar Sesión")
        logout_btn.setFixedSize(134, 43)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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
        logout_btn.clicked.connect(self.logout)
        
        exit_btn = QPushButton("Salir")
        exit_btn.setFixedSize(134, 43)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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
        
        footer_label = QLabel("Sistema de Terapia EMDR - Versión 1.0")
        footer_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                font-style: italic;
                background: transparent;
            }
        """)
        
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        footer_layout.addWidget(logout_btn)
        footer_layout.addWidget(exit_btn)
        
        main_layout.addLayout(footer_layout)
        
        # Estilo global de la ventana
        self.setStyleSheet("""
            QMainWindow {
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
    
    def load_therapists(self):
        """Carga la lista de terapeutas desde la base de datos"""
        try:
            therapists = DatabaseManager.get_all_therapists()
            
            # Limpiar tabla actual
            self.therapist_table.setRowCount(0)
            
            # Añadir filas a la tabla
            for i, therapist in enumerate(therapists):
                self.therapist_table.insertRow(i)
                
                # ID (oculto)
                id_item = QTableWidgetItem(str(therapist['id']))
                id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
                
                # Usuario
                user_item = QTableWidgetItem(therapist['user'])
                user_item.setFlags(user_item.flags() ^ Qt.ItemIsEditable)
                
                # Apellido paterno
                ap_item = QTableWidgetItem(therapist['apellido_paterno'])
                ap_item.setFlags(ap_item.flags() ^ Qt.ItemIsEditable)
                
                # Apellido materno
                am_item = QTableWidgetItem(therapist['apellido_materno'])
                am_item.setFlags(am_item.flags() ^ Qt.ItemIsEditable)
                
                # Nombre
                nombre_item = QTableWidgetItem(therapist['nombre'])
                nombre_item.setFlags(nombre_item.flags() ^ Qt.ItemIsEditable)
                
                self.therapist_table.setItem(i, 0, id_item)
                self.therapist_table.setItem(i, 1, user_item)
                self.therapist_table.setItem(i, 2, ap_item)
                self.therapist_table.setItem(i, 3, am_item)
                self.therapist_table.setItem(i, 4, nombre_item)
            
            self.therapist_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los terapeutas: {str(e)}")
    
    def add_therapist(self):
        """Abre el diálogo para añadir un nuevo terapeuta"""
        dialog = TherapistDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_therapists()
    
    def edit_therapist(self):
        """Abre el diálogo para editar el terapeuta seleccionado"""
        selected_rows = self.therapist_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un terapeuta para editar")
            return
            
        row_index = selected_rows[0].row()
        
        # Obtener datos del terapeuta seleccionado
        therapist_data = {
            'id': int(self.therapist_table.item(row_index, 0).text()),
            'user': self.therapist_table.item(row_index, 1).text(),
            'apellido_paterno': self.therapist_table.item(row_index, 2).text(),
            'apellido_materno': self.therapist_table.item(row_index, 3).text(),
            'nombre': self.therapist_table.item(row_index, 4).text()
        }
        
        dialog = TherapistDialog(self, therapist_data)
        if dialog.exec() == QDialog.Accepted:
            self.load_therapists()
    
    def delete_therapist(self):
        """Elimina el terapeuta seleccionado"""
        selected_rows = self.therapist_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un terapeuta para eliminar")
            return
            
        row_index = selected_rows[0].row()
        therapist_id = int(self.therapist_table.item(row_index, 0).text())
        therapist_name = f"{self.therapist_table.item(row_index, 2).text()} {self.therapist_table.item(row_index, 4).text()}"
        
        # Confirmar eliminación
        reply = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            f"¿Está seguro que desea eliminar al terapeuta {therapist_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                DatabaseManager.delete_therapist(therapist_id)
                self.load_therapists()
                QMessageBox.information(self, "Éxito", "Terapeuta eliminado correctamente")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el terapeuta: {str(e)}")
    
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
            # Emitir señal de logout
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
            # Cerrar aplicación completamente
            QApplication.quit()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear ventana principal
    admin_panel = AdminPanel("eloysc")
    admin_panel.show()
    
    sys.exit(app.exec())