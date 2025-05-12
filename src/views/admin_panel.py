from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
    QFormLayout, QGroupBox, QHeaderView, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor

import sys
import os
import hashlib

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
            
        self.resize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Grupo de datos personales
        personal_group = QGroupBox("Datos Personales")
        personal_layout = QFormLayout(personal_group)
        
        self.nombre_input = QLineEdit()
        self.apellido_paterno_input = QLineEdit()
        self.apellido_materno_input = QLineEdit()
        
        personal_layout.addRow("Nombre:", self.nombre_input)
        personal_layout.addRow("Apellido Paterno:", self.apellido_paterno_input)
        personal_layout.addRow("Apellido Materno:", self.apellido_materno_input)
        
        # Grupo de credenciales
        credentials_group = QGroupBox("Credenciales de Acceso")
        credentials_layout = QFormLayout(credentials_group)
        
        self.user_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.Password)
        
        credentials_layout.addRow("Usuario:", self.user_input)
        credentials_layout.addRow("Contraseña:", self.password_input)
        credentials_layout.addRow("Confirmar Contraseña:", self.password_confirm_input)
        
        # Si estamos editando, mostrar mensaje sobre contraseña
        if self.therapist_data:
            password_note = QLabel("Deje en blanco para mantener la contraseña actual")
            password_note.setStyleSheet("color: gray; font-size: 11px; font-style: italic;")
            credentials_layout.addRow("", password_note)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.save_therapist)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
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
            
            # Las contraseñas siempre se dejan vacías para edición
    
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
    
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        
        self.setWindowTitle("EMDR Project - Panel de Administración")
        self.resize(900, 600)
        
        self.setup_ui()
        self.load_therapists()
    
    def setup_ui(self):
        """Configura la interfaz del panel de administración"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("background-color: #1565C0; border-radius: 4px;")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel("PANEL DE ADMINISTRACIÓN")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        
        user_label = QLabel(f"Administrador: {self.username}")
        user_label.setStyleSheet("color: white; font-size: 14px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(user_label)
        
        main_layout.addWidget(header_frame)
        
        # Sección de terapeutas
        therapist_section = QGroupBox("Gestión de Terapeutas")
        therapist_section.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #1565C0;
            }
        """)
        
        therapist_layout = QVBoxLayout(therapist_section)
        
        # Botones de acción para terapeutas
        button_layout = QHBoxLayout()
        
        self.add_therapist_btn = QPushButton("Añadir Terapeuta")
        self.add_therapist_btn.clicked.connect(self.add_therapist)
        self.add_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.edit_therapist_btn = QPushButton("Editar Terapeuta")
        self.edit_therapist_btn.clicked.connect(self.edit_therapist)
        self.edit_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        self.delete_therapist_btn = QPushButton("Eliminar Terapeuta")
        self.delete_therapist_btn.clicked.connect(self.delete_therapist)
        self.delete_therapist_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
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
                background-color: white;
                alternate-background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
            QHeaderView::section {
                background-color: #E3F2FD;
                padding: 6px;
                font-weight: bold;
                border: 0;
                color: #1565C0;
            }
        """)
        
        # Doble clic para editar
        self.therapist_table.doubleClicked.connect(self.edit_therapist)
        
        therapist_layout.addWidget(self.therapist_table)
        
        main_layout.addWidget(therapist_section)
        
        # Footer con botón de salida
        footer_layout = QHBoxLayout()
        
        exit_btn = QPushButton("Cerrar Sesión")
        exit_btn.clicked.connect(self.close)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        footer_layout.addStretch()
        footer_layout.addWidget(exit_btn)
        
        main_layout.addLayout(footer_layout)
    
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