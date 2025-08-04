import sys
import os
import json
import pickle
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QGroupBox, QDialog, QFormLayout,
    QScrollBar, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal
import matplotlib
matplotlib.use('Qt5Agg')  # Configurar backend antes de importar pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Importar la clase DatabaseManager
from src.database.database_manager import DatabaseManager


class SessionDetailsDialog(QDialog):
    """Diálogo para mostrar los detalles y gráfica de una sesión específica"""
    
    def __init__(self, session_id, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.parent = parent
        self.session_data = None
        self.patient_data = None  # Inicializar datos del paciente
        
        # Variables para la gráfica
        self.ppg_data = None
        self.ms_data = None
        self.window_size_seconds = 8  # Ventana de 8 segundos
        self.current_position = 0  # Posición actual en la gráfica
        
        self.setWindowTitle("Detalles de la Sesión")
        self.resize(900, 700)
        self.setModal(True)
        
        self.load_session_data()
        self.setup_ui()
        
    def load_session_data(self):
        """Carga los datos completos de la sesión desde la base de datos"""
        try:
            self.session_data = DatabaseManager.get_session(self.session_id, signal_data=True)
            if not self.session_data:
                QMessageBox.critical(self, "Error", f"No se pudo encontrar la sesión con ID: {self.session_id}")
                self.reject()
                return
            
            # Obtener datos del paciente
            patient_id = self.session_data.get('id_paciente')
            if patient_id:
                self.patient_data = DatabaseManager.get_patient(patient_id)
            else:
                self.patient_data = None
                
            # Recuperar datos de PPG y milisegundos
            self.ppg_data = self.session_data.get('datos_ppg')
            self.ms_data = self.session_data.get('datos_ms')

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos de la sesión: {str(e)}")
            self.reject()
    
    def process_sensor_data(self):
        """Procesa los datos de sensores desde la base de datos"""
        try:
            # Intentar deserializar datos_ppg
            if self.session_data.get('datos_ppg'):
                ppg_blob = self.session_data['datos_ppg']
                # Intentar diferentes métodos de deserialización
                try:
                    # Método 1: JSON
                    self.ppg_data = json.loads(ppg_blob.decode('utf-8'))
                except:
                    try:
                        # Método 2: Pickle
                        self.ppg_data = pickle.loads(ppg_blob)
                    except:
                        try:
                            # Método 3: NumPy array
                            self.ppg_data = np.frombuffer(ppg_blob, dtype=np.float64)
                        except:
                            print("No se pudo deserializar datos_ppg")
                            self.ppg_data = None
            
            # Intentar deserializar datos_ms
            if self.session_data.get('datos_ms'):
                ms_blob = self.session_data['datos_ms']
                try:
                    # Método 1: JSON
                    self.ms_data = json.loads(ms_blob.decode('utf-8'))
                except:
                    try:
                        # Método 2: Pickle
                        self.ms_data = pickle.loads(ms_blob)
                    except:
                        try:
                            # Método 3: NumPy array
                            self.ms_data = np.frombuffer(ms_blob, dtype=np.float64)
                        except:
                            print("No se pudo deserializar datos_ms")
                            self.ms_data = None
                            
        except Exception as e:
            print(f"Error procesando datos de sensores: {e}")
            self.ppg_data = None
            self.ms_data = None
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # === INFORMACIÓN DEL PACIENTE Y SESIÓN ===
        title = QFrame()
        title.setFrameShape(QFrame.StyledPanel)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px; 
                font-weight: bold; 
                color: #00A99D; 
                padding: 0px;
                background: transparent;
            }
        """)
        
        title_layout = QVBoxLayout(title)
        title_layout.setContentsMargins(5, 0, 5, 0)
        title_layout.setSpacing(5)

        sesion = QLabel(f"Detalles de la Sesión #{self.session_id}")
        sesion.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(sesion)
        
        patient_name_text = f"Paciente: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')} {self.patient_data.get('apellido_materno', '')}"
        patient_name = QLabel(patient_name_text)
        patient_name.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(patient_name)
        
        fecha, hora = self.format_datetime_string(self.session_data.get('fecha'))
        fecha_label = QLabel(f"Fecha: {fecha}")
        hora_label = QLabel(f"Hora: {hora}")
        fecha_label.setAlignment(Qt.AlignCenter)
        hora_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(fecha_label)
        title_layout.addWidget(hora_label)
        
        main_layout.addWidget(title)

        # === DATOS CLÍNICOS ===
        clinical_group = QGroupBox("Datos Clínicos")
        clinical_group.setStyleSheet("""
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
        
        # Crear layout horizontal para los campos clínicos
        clinical_layout = QHBoxLayout(clinical_group)
        clinical_layout.setSpacing(15)
        
        # Crear campos de datos clínicos en disposición horizontal
        if self.session_data:
            self.create_clinical_field_horizontal(clinical_layout, "SUD Inicial:", 
                                                 self.session_data.get('sud_inicial'))
            self.create_clinical_field_horizontal(clinical_layout, "SUD Intermedio:", 
                                                 self.session_data.get('sud_interm'))
            self.create_clinical_field_horizontal(clinical_layout, "SUD Final:", 
                                                 self.session_data.get('sud_final'))
            self.create_clinical_field_horizontal(clinical_layout, "VOC:", 
                                                 self.session_data.get('voc'))

        main_layout.addWidget(clinical_group)

        # === GRÁFICA DE DATOS PPG ===
        chart_group = QGroupBox("Datos de Pulso (PPG)")
        chart_group.setStyleSheet("""
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
        
        chart_layout = QVBoxLayout(chart_group)
        
        # Verificar si hay datos de PPG disponibles
        if self.ppg_data is not None and self.ms_data is not None:
            self.setup_chart(chart_layout)
        else:
            # Mostrar mensaje de datos no disponibles
            no_data_label = QLabel("Datos de pulso no registrados")
            no_data_label.setStyleSheet("""
                QLabel {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 20px;
                    font-size: 14px;
                    color: #AAAAAA;
                    text-align: center;
                }
            """)
            no_data_label.setAlignment(Qt.AlignCenter)
            chart_layout.addWidget(no_data_label)

        main_layout.addWidget(chart_group)

        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón para cerrar
        close_button = QPushButton("Cerrar")
        close_button.setStyleSheet("""
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
        close_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

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
    
    def create_clinical_field_horizontal(self, layout, label_text, value):
        """Crea un campo clínico con etiqueta y valor en disposición vertical dentro del layout horizontal"""
        # Contenedor vertical para cada campo
        field_container = QHBoxLayout()
        field_container.setSpacing(5)
        
        # Etiqueta
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
                text-align: center;
            }
        """)
        label.setAlignment(Qt.AlignCenter)
        
        # Campo de texto
        field = QLineEdit()
        field.setReadOnly(True)
        field.setFixedWidth(100)  # Ancho fijo para consistencia
        field.setStyleSheet("""
            QLineEdit {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-weight: normal;
                color: white;
                font-size: 13px;
                text-align: center;
            }
        """)
        
        # Establecer el valor o mensaje por defecto
        if value is not None:
            field.setText(str(value))
        else:
            field.setText("No registrado")
            field.setStyleSheet("""
                QLineEdit {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: #AAAAAA;
                    font-size: 13px;
                    font-style: italic;
                    text-align: center;
                }
            """)
        
        # Agregar al contenedor horizontal
        field_container.addWidget(label)
        field_container.addWidget(field)
        
        # Crear widget contenedor y agregarlo al layout horizontal
        container_widget = QWidget()
        container_widget.setLayout(field_container)
        layout.addWidget(container_widget)
    
    def create_clinical_field(self, layout, label_text, value):
        """Crea un campo clínico con etiqueta y valor (método original para compatibilidad)"""
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
            }
        """)
        
        # Crear QLineEdit de solo lectura
        field = QLineEdit()
        field.setReadOnly(True)
        field.setStyleSheet("""
            QLineEdit {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-weight: normal;
                color: white;
                font-size: 13px;
            }
        """)
        
        # Establecer el valor o mensaje por defecto
        if value is not None:
            field.setText(str(value))
        else:
            field.setText("No registrado")
            field.setStyleSheet("""
                QLineEdit {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: #AAAAAA;
                    font-size: 13px;
                    font-style: italic;
                }
            """)
        
        layout.addRow(label, field)
    
    def setup_chart(self, parent_layout):
        """Configura la gráfica de datos PPG"""
        # Crear la figura de matplotlib
        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #323232;")
        
        # Configurar el eje
        self.ax = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor('#323232')
        self.ax.set_facecolor('#2a2a2a')
        
        # Estilo de la gráfica
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.set_xlabel('Tiempo (ms)', color='white')
        self.ax.set_ylabel('Señal PPG', color='white')
        self.ax.set_title('Datos de Pulso (PPG)', color='#00A99D', fontweight='bold')
        
        parent_layout.addWidget(self.canvas)
        
        # Crear scroll bar para navegar por los datos
        if len(self.ms_data) > 0:
            self.setup_scrollbar(parent_layout)
            self.update_chart()
    
    def setup_scrollbar(self, parent_layout):
        """Configura la barra de desplazamiento para navegar por los datos"""
        # Calcular el rango total de tiempo en segundos
        total_time_ms = max(self.ms_data) - min(self.ms_data) if len(self.ms_data) > 0 else 0
        total_time_seconds = total_time_ms / 1000.0
        
        # Solo crear scrollbar si hay más datos que la ventana
        if total_time_seconds > self.window_size_seconds:
            scroll_container = QHBoxLayout()
            
            # Etiqueta de información
            info_label = QLabel(f"Ventana: {self.window_size_seconds}s | Total: {total_time_seconds:.1f}s")
            info_label.setStyleSheet("""
                QLabel {
                    color: #AAAAAA;
                    font-size: 12px;
                    background: transparent;
                }
            """)
            
            # Scroll bar
            self.scroll_bar = QScrollBar(Qt.Horizontal)
            self.scroll_bar.setMinimum(0)
            self.scroll_bar.setMaximum(int(total_time_seconds - self.window_size_seconds))
            self.scroll_bar.setValue(0)
            self.scroll_bar.setStyleSheet("""
                QScrollBar:horizontal {
                    background-color: #424242;
                    height: 20px;
                    border-radius: 10px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #00A99D;
                    border-radius: 8px;
                    min-width: 20px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #00C2B3;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
            """)
            self.scroll_bar.valueChanged.connect(self.on_scroll)
            
            scroll_container.addWidget(QLabel("Inicio"))
            scroll_container.addWidget(self.scroll_bar)
            scroll_container.addWidget(QLabel("Fin"))
            scroll_container.addWidget(info_label)
            
            parent_layout.addLayout(scroll_container)
    
    def on_scroll(self, value):
        """Maneja el cambio en la posición del scroll bar"""
        self.current_position = value
        self.update_chart()
    
    def update_chart(self):
        """Actualiza la gráfica con la ventana de datos actual"""
        if self.ppg_data is None or self.ms_data is None:
            return
        
        try:
            # Calcular ventana de tiempo
            start_time_ms = min(self.ms_data) + (self.current_position * 1000)
            end_time_ms = start_time_ms + (self.window_size_seconds * 1000)
            
            # Filtrar datos dentro de la ventana
            mask = (self.ms_data >= start_time_ms) & (self.ms_data <= end_time_ms)
            windowed_ms = self.ms_data[mask]
            windowed_ppg = self.ppg_data[mask]
            
            # Limpiar y redibujar
            self.ax.clear()
            
            if len(windowed_ms) > 0 and len(windowed_ppg) > 0:
                # Graficar datos
                self.ax.plot(windowed_ms, windowed_ppg, color='#00A99D', linewidth=1.5)
                
                # Configurar ejes
                self.ax.set_xlim(start_time_ms, end_time_ms)
                self.ax.set_xlabel('Tiempo (ms)', color='white')
                self.ax.set_ylabel('Señal PPG', color='white')
                self.ax.set_title(f'Datos de Pulso (PPG) - Ventana: {self.current_position}s a {self.current_position + self.window_size_seconds}s', 
                                color='#00A99D', fontweight='bold')
            else:
                # Mostrar mensaje si no hay datos en esta ventana
                self.ax.text(0.5, 0.5, 'No hay datos en esta ventana', 
                           transform=self.ax.transAxes, ha='center', va='center',
                           color='#AAAAAA', fontsize=14)
                self.ax.set_title('Datos de Pulso (PPG) - Sin datos', color='#AAAAAA')
            
            # Aplicar estilo
            self.ax.set_facecolor('#2a2a2a')
            self.ax.tick_params(colors='white')
            self.ax.spines['bottom'].set_color('white')
            self.ax.spines['top'].set_color('white')
            self.ax.spines['right'].set_color('white')
            self.ax.spines['left'].set_color('white')
            
            # Actualizar canvas
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error actualizando gráfica: {e}")
            self.ax.clear()
            self.ax.text(0.5, 0.5, f'Error mostrando datos: {str(e)}', 
                       transform=self.ax.transAxes, ha='center', va='center',
                       color='red', fontsize=12)
            self.canvas.draw()

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
    
    
if __name__ == "__main__":
    # Ejemplo de uso para pruebas
    app = QApplication(sys.argv)
    
    # Crear diálogo de ejemplo (necesitarías un session_id válido)
    # dialog = SessionDetailsDialog(session_id=1)
    # dialog.exec()
    
    app.quit()
