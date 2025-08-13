import sys
import os
import json
import pickle
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QGroupBox, QDialog, QFormLayout,
    QSlider, QScrollArea, QGridLayout, QSpinBox
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg
from pyqtgraph import PlotWidget

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
        
        # Variables para campos clínicos editables
        self.sud_inicial_field = None
        self.sud_intermedio_field = None
        self.sud_final_field = None
        self.voc_field = None
        
        # Variables para botones de edición
        self.edit_button = None
        self.save_button = None
        
        self.setWindowTitle("Detalles de la Sesión")
        self.resize(900, 600)
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
                border: none;
            }
        """)
        
        title_layout = QVBoxLayout(title)
        title_layout.setContentsMargins(5, 0, 5, 0)
        title_layout.setSpacing(5)

        patient_name_text = f"Paciente: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')} {self.patient_data.get('apellido_materno', '')}"
        patient_name = QLabel(patient_name_text)
        patient_name.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(patient_name)
        
        sesion = QLabel(f"Detalles de la Sesión #{self.session_id}")
        sesion.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(sesion)
        
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
            self.sud_inicial_field = self.create_clinical_field(clinical_layout, "SUD Inicial:", 
                                                 self.session_data.get('sud_inicial'))
            self.sud_intermedio_field = self.create_clinical_field(clinical_layout, "SUD Intermedio:", 
                                                 self.session_data.get('sud_interm'))
            self.sud_final_field = self.create_clinical_field(clinical_layout, "SUD Final:", 
                                                 self.session_data.get('sud_final'))
            self.voc_field = self.create_clinical_field(clinical_layout, "VOC:", 
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
        
        # Botón para editar
        self.edit_button = QPushButton("Editar")
        self.edit_button.setStyleSheet("""
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
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        
        # Botón para guardar (inicialmente deshabilitado)
        self.save_button = QPushButton("Guardar")
        self.save_button.setStyleSheet("""
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
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setEnabled(False)  # Inicialmente deshabilitado
        
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
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.save_button)
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
    
    def create_clinical_field(self, layout, label_text, value):
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
        
        # Retornar el campo para poder mantener referencia
        return field
    
    def setup_chart(self, parent_layout):
        """Configura la gráfica de datos PPG usando PyQtGraph"""
        # Configurar el tema oscuro de PyQtGraph
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#323232')
        pg.setConfigOption('foreground', 'w')
        
        # Crear el widget de gráfica
        self.plot_widget = PlotWidget()
        self.plot_widget.setFixedHeight(300)
        
        # Configurar el estilo del plot widget
        self.plot_widget.setStyleSheet("""
            PlotWidget {
                background-color: #323232;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        
        # Configurar el plot
        self.plot_widget.setBackground('#2a2a2a')
        self.plot_widget.setLabel('left', 'Señal PPG', color='white', size='12pt')
        self.plot_widget.setLabel('bottom', 'Tiempo (ms)', color='white', size='12pt')
        self.plot_widget.setTitle('Datos de Pulso (PPG)', color='#00A99D', size='14pt')
        
        # Configurar la grilla
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Configurar los ejes
        self.plot_widget.getAxis('left').setPen(color='white', width=1)
        self.plot_widget.getAxis('bottom').setPen(color='white', width=1)
        self.plot_widget.getAxis('left').setTextPen(color='white')
        self.plot_widget.getAxis('bottom').setTextPen(color='white')
        
        # Añadir el widget al layout
        parent_layout.addWidget(self.plot_widget)
        
        # Crear scroll bar para navegar por los datos
        if len(self.ms_data) > 0:
            self.setup_navigation_panel(parent_layout)
            self.update_chart()
    
    def setup_navigation_panel(self, parent_layout):
        """Crear panel de navegación temporal basado en offline_analysis_window"""
        # Calcular el rango total de tiempo en segundos
        total_time_ms = max(self.ms_data) - min(self.ms_data) if len(self.ms_data) > 0 else 0
        total_time_seconds = total_time_ms / 1000.0
        
        # Solo crear panel si hay más datos que la ventana
        if total_time_seconds > self.window_size_seconds:
            nav_frame = QFrame()
            nav_frame.setStyleSheet("""
                QFrame {
                    background-color: #2A2A2A;
                    border: 1px solid #444444;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)
            nav_layout = QHBoxLayout(nav_frame)
            nav_layout.setContentsMargins(15, 10, 15, 10)
            
            # Control de ventana de tiempo
            window_label = QLabel("Ventana:")
            window_label.setStyleSheet("color: #FFFFFF; font-size: 12px;")
            
            self.window_spinbox = QSpinBox()
            self.window_spinbox.setRange(2, 60)
            self.window_spinbox.setValue(self.window_size_seconds)
            self.window_spinbox.setSuffix(" segundos")
            self.window_spinbox.valueChanged.connect(self.update_window_duration)
            self.window_spinbox.setStyleSheet("""
                QSpinBox {
                    background-color: #3A3A3A;
                    border: 2px solid #555555;
                    border-radius: 5px;
                    padding: 5px;
                    color: #FFFFFF;
                }
            """)
            
            # Slider de navegación
            nav_label = QLabel("Navegación:")
            nav_label.setStyleSheet("color: #FFFFFF; font-size: 12px;")
            
            self.time_slider = QSlider(Qt.Horizontal)
            self.time_slider.setMinimum(0)
            max_time = max(0, total_time_seconds - self.window_size_seconds)
            self.time_slider.setMaximum(int(max_time * 10))  # Mayor resolución
            self.time_slider.setValue(0)
            self.time_slider.valueChanged.connect(self.update_time_position)
            self.time_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: #3A3A3A;
                    height: 8px;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #00A99D;
                    border: 2px solid #00A99D;
                    width: 20px;
                    margin: -6px 0;
                    border-radius: 10px;
                }
                QSlider::handle:horizontal:hover {
                    background: #00C2B3;
                    border: 2px solid #00C2B3;
                }
            """)
            
            # Label posición actual
            self.position_label = QLabel(f"Posición: 0.0 / {total_time_seconds:.1f} s")
            self.position_label.setStyleSheet("color: #00A99D; font-weight: bold; font-size: 12px;")
            
            nav_layout.addWidget(window_label)
            nav_layout.addWidget(self.window_spinbox)
            nav_layout.addWidget(QLabel("   "))  # Espaciador
            nav_layout.addWidget(nav_label)
            nav_layout.addWidget(self.time_slider)
            nav_layout.addWidget(self.position_label)
            
            parent_layout.addWidget(nav_frame)
    
    def update_window_duration(self, value):
        """Actualizar duración de ventana de visualización"""
        self.window_size_seconds = value
        
        if self.ms_data is not None and len(self.ms_data) > 0:
            # Reconfigurar slider
            total_time_ms = max(self.ms_data) - min(self.ms_data)
            total_time_seconds = total_time_ms / 1000.0
            max_time = max(0, total_time_seconds - self.window_size_seconds)
            self.time_slider.setMaximum(int(max_time * 10))
            
            # Actualizar gráficas
            self.update_chart()
    
    def update_time_position(self, value):
        """Actualizar posición temporal desde el slider"""
        if self.ms_data is None or len(self.ms_data) == 0:
            return
            
        total_time_ms = max(self.ms_data) - min(self.ms_data)
        total_time_seconds = total_time_ms / 1000.0
        
        self.current_position = value / 10.0  # Convertir de resolución alta
        self.update_chart()
        
        self.position_label.setText(f"Posición: {self.current_position:.1f} / {total_time_seconds:.1f} s")
    
    def update_chart(self):
        """Actualiza la gráfica con la ventana de datos actual usando PyQtGraph"""
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
            
            # Limpiar la gráfica
            self.plot_widget.clear()
            
            if len(windowed_ms) > 0 and len(windowed_ppg) > 0:
                # Graficar datos con color verde esmeralda
                pen = pg.mkPen(color='#00A99D', width=2)
                self.plot_widget.plot(windowed_ms, windowed_ppg, pen=pen, name='PPG')
                
                # Configurar los límites del eje X
                self.plot_widget.setXRange(start_time_ms, end_time_ms, padding=0)
                
                # Actualizar el título con información de la ventana
                self.plot_widget.setTitle(
                    f'Datos de Pulso (PPG) - Ventana: {self.current_position}s a {self.current_position + self.window_size_seconds}s',
                    color='#00A99D', 
                    size='14pt'
                )
            else:
                # Mostrar mensaje si no hay datos en esta ventana
                text_item = pg.TextItem(
                    'No hay datos en esta ventana',
                    color='#AAAAAA',
                    anchor=(0.5, 0.5)
                )
                text_item.setPos(start_time_ms + (end_time_ms - start_time_ms) / 2, 0)
                self.plot_widget.addItem(text_item)
                self.plot_widget.setTitle('Datos de Pulso (PPG) - Sin datos', color='#AAAAAA', size='14pt')
            
        except Exception as e:
            print(f"Error actualizando gráfica: {e}")
            # Limpiar y mostrar mensaje de error
            self.plot_widget.clear()
            error_text = pg.TextItem(
                f'Error mostrando datos: {str(e)}',
                color='red',
                anchor=(0.5, 0.5)
            )
            error_text.setPos(0, 0)
            self.plot_widget.addItem(error_text)

    def toggle_edit_mode(self):
        """Activa/desactiva el modo de edición para los campos clínicos"""
        # Habilitar campos para edición
        if self.sud_inicial_field:
            self.sud_inicial_field.setReadOnly(False)
            self.sud_inicial_field.setStyleSheet("""
                QLineEdit {
                    background-color: #424242;
                    border: 2px solid #00A99D;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                    text-align: center;
                }
                QLineEdit:focus {
                    background-color: #4a4a4a;
                    border: 2px solid #00C2B3;
                }
            """)
        
        if self.sud_intermedio_field:
            self.sud_intermedio_field.setReadOnly(False)
            self.sud_intermedio_field.setStyleSheet("""
                QLineEdit {
                    background-color: #424242;
                    border: 2px solid #00A99D;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                    text-align: center;
                }
                QLineEdit:focus {
                    background-color: #4a4a4a;
                    border: 2px solid #00C2B3;
                }
            """)
        
        if self.sud_final_field:
            self.sud_final_field.setReadOnly(False)
            self.sud_final_field.setStyleSheet("""
                QLineEdit {
                    background-color: #424242;
                    border: 2px solid #00A99D;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                    text-align: center;
                }
                QLineEdit:focus {
                    background-color: #4a4a4a;
                    border: 2px solid #00C2B3;
                }
            """)
        
        if self.voc_field:
            self.voc_field.setReadOnly(False)
            self.voc_field.setStyleSheet("""
                QLineEdit {
                    background-color: #424242;
                    border: 2px solid #00A99D;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                    text-align: center;
                }
                QLineEdit:focus {
                    background-color: #4a4a4a;
                    border: 2px solid #00C2B3;
                }
            """)
        
        # Cambiar estado de botones
        self.edit_button.setEnabled(False)
        self.save_button.setEnabled(True)
    
    def save_changes(self):
        """Guarda los cambios en la base de datos"""
        try:
            # Obtener valores de los campos
            sud_inicial = self.get_field_value(self.sud_inicial_field)
            sud_intermedio = self.get_field_value(self.sud_intermedio_field)
            sud_final = self.get_field_value(self.sud_final_field)
            voc = self.get_field_value(self.voc_field)
            
            # Actualizar en la base de datos
            success = DatabaseManager.update_session_clinical_data(
                session_id=self.session_id,
                sud_inicial=sud_inicial,
                sud_intermedio=sud_intermedio,
                sud_final=sud_final,
                voc=voc
            )
            
            if success:
                QMessageBox.information(self, "Éxito", "Los datos clínicos han sido actualizados correctamente.")
                
                # Actualizar datos locales
                self.session_data['sud_inicial'] = sud_inicial
                self.session_data['sud_interm'] = sud_intermedio
                self.session_data['sud_final'] = sud_final
                self.session_data['voc'] = voc
                
                # Restaurar modo de solo lectura
                self.restore_readonly_mode()
                
                # Notificar al padre para actualizar la vista si es necesario
                if hasattr(self.parent, 'refresh_session_history'):
                    self.parent.refresh_session_history()
                    
            else:
                QMessageBox.critical(self, "Error", "No se pudieron guardar los cambios en la base de datos.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar los cambios: {str(e)}")
    
    def get_field_value(self, field):
        """Obtiene el valor de un campo, retornando None si está vacío o contiene 'No registrado'"""
        if field is None:
            return None
        
        value = field.text().strip()
        if value == "" or value == "No registrado":
            return None
        
        try:
            # Intentar convertir a número
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None
    
    def restore_readonly_mode(self):
        """Restaura el modo de solo lectura para los campos"""
        readonly_style = """
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
        """
        
        if self.sud_inicial_field:
            self.sud_inicial_field.setReadOnly(True)
            self.sud_inicial_field.setStyleSheet(readonly_style)
        
        if self.sud_intermedio_field:
            self.sud_intermedio_field.setReadOnly(True)
            self.sud_intermedio_field.setStyleSheet(readonly_style)
        
        if self.sud_final_field:
            self.sud_final_field.setReadOnly(True)
            self.sud_final_field.setStyleSheet(readonly_style)
        
        if self.voc_field:
            self.voc_field.setReadOnly(True)
            self.voc_field.setStyleSheet(readonly_style)
        
        # Cambiar estado de botones
        self.edit_button.setEnabled(True)
        self.save_button.setEnabled(False)

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
