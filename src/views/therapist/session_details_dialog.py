import sys
import os
import json
import pickle
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QMessageBox, QFrame, QGroupBox, QDialog, QFormLayout,
    QSlider, QScrollArea, QGridLayout, QSpinBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg

# Importar la clase DatabaseManager
from database.database_manager import DatabaseManager
# Importar el filtro PPG offline y calculador BPM
from utils.signal_processing import OfflinePPGFilter, BPMOfflineCalculation


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
        self.ppg_filtered = None  # Señal PPG filtrada
        self.ms_data = None
        self.window_size_seconds = 300  # Ventana de 5 minutos (300 segundos)
        self.current_position = 0  # Posición actual en la gráfica
        
        # Variables para el filtro PPG
        self.ppg_filter = None
        self.filter_result = None
        
        # Variables para BPM
        self.bpm_data = None
        self.bpm_times = None
        self.bpm_confidence = None
        self.bpm_calculator = None
        
        # Variables para campos clínicos editables
        self.sud_inicial_field = None
        self.sud_intermedio_field = None
        self.sud_final_field = None
        self.voc_field = None
        self.comentarios_field = None
        
        # Variables para botones de edición
        self.edit_button = None
        self.save_button = None
        self.edit_session_type_button = None
        
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
            
            # Procesar y filtrar datos PPG si están disponibles
            if self.ppg_data is not None and self.ms_data is not None:
                self.process_and_filter_ppg()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos de la sesión: {str(e)}")
            self.reject()
    
    def process_and_filter_ppg(self):
        """Procesa y filtra los datos PPG usando OfflinePPGFilter"""
        try:
            # Verificar que los datos sean válidos
            if self.ppg_data is None or self.ms_data is None:
                print("Datos PPG o MS no disponibles")
                return
            
            # Convertir a arrays numpy si es necesario
            if not isinstance(self.ppg_data, np.ndarray):
                self.ppg_data = np.array(self.ppg_data)
            
            if not isinstance(self.ms_data, np.ndarray):
                self.ms_data = np.array(self.ms_data)
            
            # Verificar que tenemos suficientes datos
            if len(self.ppg_data) < 500:  # Mínimo ~4 segundos a 125 Hz
                print(f"Insuficientes datos PPG: {len(self.ppg_data)} muestras")
                return
            
            print(f"Procesando señal PPG: {len(self.ppg_data)} muestras")
            
            # Calcular frecuencia de muestreo estimada
            if len(self.ms_data) > 1:
                time_span_sec = (max(self.ms_data) - min(self.ms_data)) / 1000.0
                estimated_fs = len(self.ms_data) / time_span_sec
                print(f"Frecuencia de muestreo estimada: {estimated_fs:.1f} Hz")
            else:
                estimated_fs = 125  # Valor por defecto
            
            # Crear filtro PPG offline con parámetros optimizados
            self.ppg_filter = OfflinePPGFilter(
                fs=estimated_fs,
                hp_cutoff=0.5,      # Eliminar deriva DC, preservar HRV
                lp_cutoff=5.0,      # Rango cardíaco hasta 300 BPM
                notch_freq=50,      # Eliminar ruido de red eléctrica
                notch_q=30,         # Factor de calidad del notch
                smoothing=True      # Suavizado adicional
            )
            
            # Aplicar filtro offline
            self.filter_result = self.ppg_filter.filter_signal(self.ppg_data)
            
            # Obtener señal filtrada
            self.ppg_filtered = self.filter_result['filtered']
            
            # Calcular evolución de BPM
            try:
                print("Calculando evolución de BPM...")
                self.bpm_calculator = BPMOfflineCalculation(fs=estimated_fs)
                bpm_result = self.bpm_calculator.calculate_bpm_evolution(
                    self.ppg_filtered, 
                    self.ms_data
                )
                
                # Extraer datos de BPM
                self.bpm_data = bpm_result['bpm_values']
                self.bpm_times = bpm_result['times_sec']
                self.bpm_confidence = bpm_result['confidence_values']
                
                metadata_bpm = bpm_result['metadata']
                print(f"✅ BPM calculado: {metadata_bpm['total_points']} puntos")
                if metadata_bpm.get('mean_bpm'):
                    print(f"  - BPM promedio: {metadata_bpm['mean_bpm']:.1f} ± {metadata_bpm['std_bpm']:.1f}")
                    
            except Exception as e:
                print(f"Error calculando BPM: {e}")
                self.bpm_data = None
                self.bpm_times = None
                self.bpm_confidence = None
            
            # Mostrar información del filtrado
            quality = self.filter_result['quality']
            metadata = self.filter_result['metadata']
            
            print(f"✅ Filtrado PPG completado:")
            print(f"  - Calidad general: {quality['overall']}")
            print(f"  - SNR mejorado: {metadata['snr_improvement_db']:.1f} dB")
            print(f"  - Picos detectados: {quality['peaks_detected']}")
            
            if quality.get('estimated_hr'):
                print(f"  - Frecuencia cardíaca estimada: {quality['estimated_hr']:.1f} BPM")
            
            # Calcular límites fijos del eje Y
            self.calculate_fixed_y_limits()
            
            # Detectar artefactos si los hay
            artifacts = self.filter_result.get('artifacts', [])
            if artifacts:
                print(f"  - Artefactos de movimiento detectados: {len(artifacts)}")
                for i, (start, end, duration) in enumerate(artifacts):
                    print(f"    Artefacto {i+1}: {duration:.0f}ms")
            
        except Exception as e:
            print(f"Error procesando datos PPG: {e}")
            QMessageBox.warning(
                self, 
                "Advertencia", 
                f"Error al filtrar señal PPG: {str(e)}\n\nSe mostrará la señal sin filtrar."
            )
            # Usar señal original si falla el filtrado
            self.ppg_filtered = self.ppg_data.copy() if self.ppg_data is not None else None
    
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
                font-size: 16px; 
                font-weight: bold; 
                color: #00A99D; 
                padding: 0px;
                background: transparent;
                border: none;
            }
        """)
        
        # Layout principal vertical para las dos filas
        title_layout = QVBoxLayout(title)
        title_layout.setContentsMargins(5, 10, 5, 10)
        title_layout.setSpacing(10)

        # PRIMERA FILA - Información básica
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(15)

        patient_name_text = f"Paciente: {self.patient_data.get('nombre', '')} {self.patient_data.get('apellido_paterno', '')} {self.patient_data.get('apellido_materno', '')}"
        patient_name = QLabel(patient_name_text)
        patient_name.setAlignment(Qt.AlignCenter)
        first_row_layout.addWidget(patient_name)
        
        # Separador visual
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #555555; font-size: 16px;")
        first_row_layout.addWidget(separator1)
        
        sesion = QLabel(f"Sesión #{self.session_id}")
        sesion.setAlignment(Qt.AlignCenter)
        first_row_layout.addWidget(sesion)
        
        # Separador visual
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #555555; font-size: 16px;")
        first_row_layout.addWidget(separator2)
        
        fecha, hora = self.format_datetime_string(self.session_data.get('fecha'))
        fecha_label = QLabel(f"Fecha: {fecha}")
        fecha_label.setAlignment(Qt.AlignCenter)
        first_row_layout.addWidget(fecha_label)
        
        # Separador visual
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #555555; font-size: 16px;")
        first_row_layout.addWidget(separator3)

        hora_label = QLabel(f"Hora: {hora}")
        hora_label.setAlignment(Qt.AlignCenter)
        first_row_layout.addWidget(hora_label)
        
        # Añadir primera fila al layout principal
        title_layout.addLayout(first_row_layout)
        
        # SEGUNDA FILA - Objetivo de la sesión
        second_row_layout = QHBoxLayout()
        second_row_layout.setSpacing(10)
        
        objetivo_text = self.session_data.get('objetivo', '')
        if not objetivo_text or objetivo_text.strip() == '':
            objetivo_text = "Sin objetivo registrado"
            objetivo_style = """
                QLabel {
                    font-size: 14px; 
                    font-weight: normal; 
                    color: #AAAAAA; 
                    padding: 0px;
                    background: transparent;
                    border: none;
                    font-style: italic;
                }
            """
        else:
            objetivo_style = """
                QLabel {
                    font-size: 14px; 
                    font-weight: bold; 
                    color: #00A99D; 
                    padding: 0px;
                    background: transparent;
                    border: none;
                }
            """
        
        objetivo_label = QLabel(f"Objetivo: {objetivo_text}")
        objetivo_label.setAlignment(Qt.AlignCenter)
        objetivo_label.setStyleSheet(objetivo_style)
        objetivo_label.setWordWrap(True)  # Permitir salto de línea si es muy largo
        second_row_layout.addWidget(objetivo_label)
        
        # Añadir segunda fila al layout principal
        title_layout.addLayout(second_row_layout)
        
        main_layout.addWidget(title)

        # === DATOS CLÍNICOS ===
        clinical_group = QGroupBox("Datos Clínicos")
        clinical_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 0px;
                padding-top: 0px;
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
        
        # Crear layout vertical principal para los campos clínicos
        clinical_main_layout = QVBoxLayout(clinical_group)
        clinical_main_layout.setSpacing(10)
        
        # Layout horizontal para SUD y VOC
        clinical_horizontal_layout = QHBoxLayout()
        clinical_horizontal_layout.setSpacing(15)
        
        # Crear campos de datos clínicos en disposición horizontal
        if self.session_data:
            self.sud_inicial_field = self.create_clinical_field(clinical_horizontal_layout, "SUD Inicial:", 
                                                 self.session_data.get('sud_inicial'))
            self.sud_intermedio_field = self.create_clinical_field(clinical_horizontal_layout, "SUD Intermedio:", 
                                                 self.session_data.get('sud_interm'))
            self.sud_final_field = self.create_clinical_field(clinical_horizontal_layout, "SUD Final:", 
                                                 self.session_data.get('sud_final'))
            self.voc_field = self.create_clinical_field(clinical_horizontal_layout, "VOC:", 
                                                 self.session_data.get('voc'))

        clinical_main_layout.addLayout(clinical_horizontal_layout)
        
        # Campo de comentarios en una segunda fila
        comentarios_layout = QHBoxLayout()
        comentarios_layout.setSpacing(10)
        
        # Label de comentarios
        comentarios_label = QLabel("Comentarios:")
        comentarios_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
                text-align: center;
            }
        """)
        comentarios_label.setAlignment(Qt.AlignCenter)
        comentarios_label.setFixedWidth(100)  # Ancho fijo similar a otros labels
        
        # Campo de texto para comentarios
        self.comentarios_field = QLineEdit()
        self.comentarios_field.setReadOnly(True)
        
        # Establecer valor inicial
        comentarios_value = self.session_data.get('comentarios') if self.session_data else None
        if comentarios_value:
            self.comentarios_field.setText(str(comentarios_value))
        else:
            self.comentarios_field.setText("Sin comentarios")
            
        # Estilo inicial para modo solo lectura
        self.comentarios_field.setStyleSheet("""
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
        
        comentarios_layout.addWidget(comentarios_label)
        comentarios_layout.addWidget(self.comentarios_field)
        
        clinical_main_layout.addLayout(comentarios_layout)

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
        if self.ppg_filtered is not None and self.ms_data is not None:
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
        
        # Botón para editar tipo de sesión (inicialmente deshabilitado)
        self.edit_session_type_button = QPushButton("Editar Tipo de Sesión")
        self.edit_session_type_button.setStyleSheet("""
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
        self.edit_session_type_button.clicked.connect(self.open_session_type_editor)
        self.edit_session_type_button.setEnabled(False)  # Inicialmente deshabilitado
        
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
        button_layout.addWidget(self.edit_session_type_button)
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
        self.plot_widget = pg.PlotWidget()
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
        self.plot_widget.setLabel('bottom', 'Tiempo (MM:SS)', color='white', size='12pt')
        
        # Título dinámico basado en si hay filtrado
        if self.filter_result:
            quality = self.filter_result['quality']['overall']
            hr_est = self.filter_result['quality'].get('estimated_hr')
            if hr_est:
                title_text = f'Datos de Pulso (PPG) - Filtrado | Calidad: {quality} | HR: {hr_est:.0f} BPM'
            else:
                title_text = f'Datos de Pulso (PPG) - Filtrado | Calidad: {quality}'
        else:
            title_text = 'Datos de Pulso (PPG) - Sin filtrar'
            
        self.plot_widget.setTitle(title_text, color='#00A99D', size='14pt')
        
        # Configurar la grilla
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Configurar los ejes
        self.plot_widget.getAxis('left').setPen(color='white', width=1)
        self.plot_widget.getAxis('bottom').setPen(color='white', width=1)
        self.plot_widget.getAxis('left').setTextPen(color='white')
        self.plot_widget.getAxis('bottom').setTextPen(color='white')
        
        # Configurar límites Y fijos si están disponibles
        if hasattr(self, 'y_min') and hasattr(self, 'y_max') and self.y_min is not None and self.y_max is not None:
            self.plot_widget.setYRange(self.y_min, self.y_max, padding=0)
        
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
                    background-color: transparent;
                    border: 1px solid #444444;
                    padding: 0px;
                }
            """)
            nav_layout = QHBoxLayout(nav_frame)
            nav_layout.setContentsMargins(15, 0, 15, 0)
            
            # Control de ventana de tiempo
            window_label = QLabel("Ventana:")
            window_label.setStyleSheet("color: #FFFFFF; font-size: 12px;")
            
            self.window_spinbox = QSpinBox()
            self.window_spinbox.setRange(5, 20)  # 5-20 minutos
            self.window_spinbox.setValue(int(self.window_size_seconds / 60))  # Convertir a minutos
            self.window_spinbox.setSuffix(" minutos")
            self.window_spinbox.valueChanged.connect(self.update_window_duration_minutes)
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
            total_time_mmss = self.format_time_mmss(total_time_seconds)
            self.position_label = QLabel(f"Posición: 00:00 / {total_time_mmss}")
            self.position_label.setStyleSheet("color: #00A99D; font-weight: bold; font-size: 12px;")
            
            nav_layout.addWidget(window_label)
            nav_layout.addWidget(self.window_spinbox)
            nav_layout.addWidget(QLabel("   "))  # Espaciador
            nav_layout.addWidget(nav_label)
            nav_layout.addWidget(self.time_slider)
            nav_layout.addWidget(self.position_label)
            
            parent_layout.addWidget(nav_frame)
    
    def format_time_mmss(self, time_seconds):
        """Convierte tiempo en segundos a formato MM:SS"""
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def generate_time_ticks(self, start_time_ms, end_time_ms):
        """Genera ticks personalizados para el eje X en formato MM:SS"""
        ticks = []
        
        # Convertir a segundos desde el inicio de la grabación
        base_time_ms = min(self.ms_data) if self.ms_data is not None else 0
        start_sec = (start_time_ms - base_time_ms) / 1000.0
        end_sec = (end_time_ms - base_time_ms) / 1000.0
        
        # Determinar intervalo de ticks basado en la duración de la ventana
        window_duration = end_sec - start_sec
        if window_duration <= 60:  # <= 1 minuto
            tick_interval = 10  # cada 10 segundos
        elif window_duration <= 300:  # <= 5 minutos
            tick_interval = 30  # cada 30 segundos
        else:
            tick_interval = 60  # cada minuto
        
        # Generar ticks
        current_sec = int(start_sec // tick_interval) * tick_interval
        while current_sec <= end_sec:
            tick_time_ms = base_time_ms + (current_sec * 1000)
            if start_time_ms <= tick_time_ms <= end_time_ms:
                tick_label = self.format_time_mmss(current_sec)
                ticks.append((tick_time_ms, tick_label))
            current_sec += tick_interval
            
        return ticks
    
    def generate_time_ticks_seconds(self, start_time_sec, end_time_sec):
        """Genera ticks personalizados para el eje X en formato MM:SS (entrada en segundos)"""
        ticks = []
        
        # Determinar intervalo de ticks basado en la duración de la ventana
        window_duration = end_time_sec - start_time_sec
        if window_duration <= 60:  # <= 1 minuto
            tick_interval = 10  # cada 10 segundos
        elif window_duration <= 300:  # <= 5 minutos
            tick_interval = 30  # cada 30 segundos
        else:
            tick_interval = 60  # cada minuto
        
        # Generar ticks
        current_sec = int(start_time_sec // tick_interval) * tick_interval
        while current_sec <= end_time_sec:
            if start_time_sec <= current_sec <= end_time_sec:
                tick_label = self.format_time_mmss(current_sec)
                ticks.append((current_sec, tick_label))
            current_sec += tick_interval
            
        return ticks
    
    def calculate_fixed_y_limits(self):
        """Calcula los límites fijos del eje Y basándose en toda la señal"""
        self.y_min = None
        self.y_max = None
        
        # Priorizar datos de BPM si están disponibles
        if self.bpm_data is not None and len(self.bpm_data) > 0:
            # Para BPM, usar límites más amplios para mejor visualización
            data_min = np.min(self.bpm_data)
            data_max = np.max(self.bpm_data)
            
            # Agregar margen del 10% para mejor visualización
            margin = (data_max - data_min) * 0.1
            self.y_min = max(0, data_min - margin)  # BPM no puede ser negativo
            self.y_max = data_max + margin
            
            print(f"📊 Límites Y fijos para BPM: {self.y_min:.1f} - {self.y_max:.1f}")
            
        else:
            # Fallback a señal PPG (filtrada o original)
            ppg_to_analyze = self.ppg_filtered if self.ppg_filtered is not None else self.ppg_data
            
            if ppg_to_analyze is not None and len(ppg_to_analyze) > 0:
                data_min = np.min(ppg_to_analyze)
                data_max = np.max(ppg_to_analyze)
                
                # Agregar margen del 5% para señal PPG
                margin = (data_max - data_min) * 0.05
                self.y_min = data_min - margin
                self.y_max = data_max + margin
                
                print(f"📊 Límites Y fijos para PPG: {self.y_min:.1f} - {self.y_max:.1f}")
    
    def update_window_duration_minutes(self, value_minutes):
        """Actualizar duración de ventana de visualización (entrada en minutos)"""
        self.window_size_seconds = value_minutes * 60  # Convertir minutos a segundos
        
        if self.ms_data is not None and len(self.ms_data) > 0:
            # Reconfigurar slider
            total_time_ms = max(self.ms_data) - min(self.ms_data)
            total_time_seconds = total_time_ms / 1000.0
            max_time = max(0, total_time_seconds - self.window_size_seconds)
            self.time_slider.setMaximum(int(max_time * 10))
            
            # Actualizar gráficas
            self.update_chart()

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
        
        # Formatear tiempos en MM:SS
        current_time_mmss = self.format_time_mmss(self.current_position)
        total_time_mmss = self.format_time_mmss(total_time_seconds)
        self.position_label.setText(f"Posición: {current_time_mmss} / {total_time_mmss}")
    
    def update_chart(self):
        """Actualiza la gráfica con la evolución de BPM usando PyQtGraph"""
        # Usar datos de BPM si están disponibles, sino mostrar señal PPG
        if self.bpm_data is not None and self.bpm_times is not None:
            data_to_plot = self.bpm_data
            times_to_plot_ms = self.bpm_times * 1000  # Ya está en segundos, convertir a ms
            data_label = 'Evolución BPM'
            data_unit = 'BPM'
        else:
            # Fallback a PPG filtrada o original
            ppg_to_plot = self.ppg_filtered if self.ppg_filtered is not None else self.ppg_data
            if ppg_to_plot is None or self.ms_data is None:
                return
            data_to_plot = ppg_to_plot
            times_to_plot_ms = self.ms_data
            data_label = 'PPG Filtrada' if self.ppg_filtered is not None else 'PPG Original'
            data_unit = 'Amplitud'
        
        try:
            # Calcular ventana de tiempo
            start_time_ms = min(times_to_plot_ms) + (self.current_position * 1000)
            end_time_ms = start_time_ms + (self.window_size_seconds * 1000)
            
            # Filtrar datos dentro de la ventana
            mask = (times_to_plot_ms >= start_time_ms) & (times_to_plot_ms <= end_time_ms)
            windowed_times_ms = times_to_plot_ms[mask]
            windowed_data = data_to_plot[mask]
            
            # CONVERSIÓN A SEGUNDOS para evitar notación científica
            windowed_times_sec = windowed_times_ms / 1000.0
            start_time_sec = start_time_ms / 1000.0
            end_time_sec = end_time_ms / 1000.0
            
            # Limpiar la gráfica
            self.plot_widget.clear()
            
            if len(windowed_times_sec) > 0 and len(windowed_data) > 0:
                # Graficar datos con color verde esmeralda (USANDO SEGUNDOS)
                pen = pg.mkPen(color='#00A99D', width=2)
                self.plot_widget.plot(windowed_times_sec, windowed_data, pen=pen, name=data_label)
                
                # Si es BPM, agregar líneas de referencia
                if self.bpm_data is not None:
                    # Línea de BPM promedio durante esta ventana
                    if len(windowed_data) > 0:
                        mean_bpm = np.mean(windowed_data)
                        ref_line = pg.InfiniteLine(
                            pos=mean_bpm, 
                            angle=0, 
                            pen=pg.mkPen('#CCCCCC', width=1, style=Qt.DashLine),
                            label=f'Promedio: {mean_bpm:.1f} BPM'
                        )
                        self.plot_widget.addItem(ref_line)
                    
                    # Mostrar confianza si está disponible
                    if (self.bpm_confidence is not None and 
                        hasattr(self, 'show_confidence') and self.show_confidence):
                        windowed_confidence = self.bpm_confidence[mask]
                        confidence_pen = pg.mkPen(color='#FFA500', width=1, style=Qt.DotLine)
                        # Normalizar confianza para visualización
                        conf_normalized = windowed_confidence * np.max(windowed_data)
                        self.plot_widget.plot(windowed_times_sec, conf_normalized, 
                                            pen=confidence_pen, name='Confianza')
                
                # Configurar los límites del eje X (EN SEGUNDOS)
                self.plot_widget.setXRange(start_time_sec, end_time_sec, padding=0)
                
                # Configurar límites fijos del eje Y
                if hasattr(self, 'y_min') and hasattr(self, 'y_max') and self.y_min is not None and self.y_max is not None:
                    self.plot_widget.setYRange(self.y_min, self.y_max, padding=0)
                
                # Título con información específica del tipo de datos
                if self.bpm_data is not None:
                    if len(windowed_data) > 0:
                        min_bpm = np.min(windowed_data)
                        max_bpm = np.max(windowed_data)
                        min_time = self.format_time_mmss(self.current_position)
                        max_time = self.format_time_mmss(self.current_position + self.window_size_seconds)
                        title_text = f'Evolución BPM (Rango: {min_bpm:.1f}-{max_bpm:.1f}) - Ventana: {min_time} a {max_time}'
                    else:
                        title_text = f'Evolución BPM - Ventana: {self.current_position:.1f}s a {self.current_position + self.window_size_seconds:.1f}s'
                else:
                    # Título para PPG
                    if self.filter_result:
                        quality = self.filter_result['quality']['overall']
                        title_text = f'PPG Filtrada (Calidad: {quality}) - Ventana: {self.current_position:.1f}s a {self.current_position + self.window_size_seconds:.1f}s'
                    else:
                        title_text = f'PPG Original - Ventana: {self.current_position:.1f}s a {self.current_position + self.window_size_seconds:.1f}s'
                
                self.plot_widget.setTitle(title_text, color='#00A99D', size='14pt')
                
                # Configurar etiquetas de ejes
                self.plot_widget.setLabel('left', data_unit, color='#00A99D')
                self.plot_widget.setLabel('bottom', 'Tiempo (MM:SS)', color='#00A99D')
                
                # Configurar formato personalizado del eje X para mostrar MM:SS (USANDO SEGUNDOS)
                axis = self.plot_widget.getAxis('bottom')
                axis.setTicks([self.generate_time_ticks_seconds(start_time_sec, end_time_sec)])
                
                # Marcar artefactos si existen y estamos viendo PPG
                if (self.bpm_data is None and 
                    self.filter_result and 
                    self.filter_result.get('artifacts') and 
                    len(self.filter_result['artifacts']) > 0):
                    self.mark_artifacts_in_window(start_time_ms, end_time_ms)
                    
            else:
                # Mostrar mensaje si no hay datos en esta ventana
                text_item = pg.TextItem(
                    'No hay datos en esta ventana',
                    color='#AAAAAA',
                    anchor=(0.5, 0.5)
                )
                text_item.setPos(start_time_ms + (end_time_ms - start_time_ms) / 2, 0)
                self.plot_widget.addItem(text_item)
                
                # Configurar límites X y Y fijos incluso sin datos
                self.plot_widget.setXRange(start_time_ms, end_time_ms, padding=0)
                if hasattr(self, 'y_min') and hasattr(self, 'y_max') and self.y_min is not None and self.y_max is not None:
                    self.plot_widget.setYRange(self.y_min, self.y_max, padding=0)
                
                if self.bpm_data is not None:
                    self.plot_widget.setTitle('Evolución BPM - Sin datos', color='#AAAAAA', size='14pt')
                else:
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
    
    def mark_artifacts_in_window(self, start_time_ms, end_time_ms):
        """Marcar artefactos de movimiento que estén visible en la ventana actual"""
        if not self.filter_result or not self.filter_result.get('artifacts'):
            return
        
        try:
            # Calcular frecuencia de muestreo estimada para convertir índices a tiempo
            if len(self.ms_data) > 1:
                time_span_sec = (max(self.ms_data) - min(self.ms_data)) / 1000.0
                estimated_fs = len(self.ms_data) / time_span_sec
            else:
                estimated_fs = 125
            
            # Tiempo base de la grabación
            base_time_ms = min(self.ms_data)
            
            for artifact_idx_start, artifact_idx_end, duration_ms in self.filter_result['artifacts']:
                # Convertir índices de muestra a tiempo absoluto
                artifact_start_ms = base_time_ms + (artifact_idx_start / estimated_fs) * 1000
                artifact_end_ms = base_time_ms + (artifact_idx_end / estimated_fs) * 1000
                
                # Verificar si el artefacto está visible en la ventana actual
                if (artifact_start_ms < end_time_ms and artifact_end_ms > start_time_ms):
                    # Crear región de resaltado para el artefacto
                    region = pg.LinearRegionItem(
                        [max(artifact_start_ms, start_time_ms), 
                         min(artifact_end_ms, end_time_ms)],
                        brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                        pen=pg.mkPen(255, 0, 0, 100),     # Borde rojo
                        movable=False
                    )
                    self.plot_widget.addItem(region)
                    
                    # Agregar etiqueta del artefacto
                    artifact_label = pg.TextItem(
                        f'Artefacto ({duration_ms:.0f}ms)',
                        color='red',
                        anchor=(0.5, 1.0)
                    )
                    artifact_label.setPos(
                        (artifact_start_ms + artifact_end_ms) / 2,
                        self.plot_widget.getViewBox().viewRange()[1][1] * 0.9
                    )
                    self.plot_widget.addItem(artifact_label)
                    
        except Exception as e:
            print(f"Error marcando artefactos: {e}")

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
        
        # Habilitar campo de comentarios
        if self.comentarios_field:
            self.comentarios_field.setReadOnly(False)
            # Limpiar "Sin comentarios" cuando se entra en modo edición
            if self.comentarios_field.text() == "Sin comentarios":
                self.comentarios_field.setText("")
            self.comentarios_field.setStyleSheet("""
                QLineEdit {
                    background-color: #424242;
                    border: 2px solid #00A99D;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    background-color: #4a4a4a;
                    border: 2px solid #00C2B3;
                }
            """)
        
        # Cambiar estado de botones
        self.edit_button.setEnabled(False)
        self.save_button.setEnabled(True)
        self.edit_session_type_button.setEnabled(True)
    
    def save_changes(self):
        """Guarda los cambios en la base de datos"""
        try:
            # Obtener valores de los campos
            sud_inicial = self.get_field_value(self.sud_inicial_field)
            sud_intermedio = self.get_field_value(self.sud_intermedio_field)
            sud_final = self.get_field_value(self.sud_final_field)
            voc = self.get_field_value(self.voc_field)
            
            # Obtener comentarios
            comentarios_text = ""
            if self.comentarios_field:
                comentarios_text = self.comentarios_field.text().strip()
                # Si está vacío o es "Sin comentarios", guardar como None
                if comentarios_text == "" or comentarios_text == "Sin comentarios":
                    comentarios_text = None
            else:
                comentarios_text = None
            
            # Actualizar datos clínicos en la base de datos
            success_clinical = DatabaseManager.update_session_clinical_data(
                session_id=self.session_id,
                sud_inicial=sud_inicial,
                sud_intermedio=sud_intermedio,
                sud_final=sud_final,
                voc=voc
            )
            
            # Actualizar comentarios en la base de datos
            success_comments = DatabaseManager.update_session_comments(
                session_id=self.session_id,
                comentarios=comentarios_text
            )
            
            if success_clinical and success_comments:
                QMessageBox.information(self, "Éxito", "Los datos clínicos y comentarios han sido actualizados correctamente.")
                
                # Actualizar datos locales
                self.session_data['sud_inicial'] = sud_inicial
                self.session_data['sud_interm'] = sud_intermedio
                self.session_data['sud_final'] = sud_final
                self.session_data['voc'] = voc
                self.session_data['comentarios'] = comentarios_text
                
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
        
        # Restaurar campo de comentarios
        if self.comentarios_field:
            self.comentarios_field.setReadOnly(True)
            # Si el campo está vacío, mostrar "Sin comentarios"
            if self.comentarios_field.text().strip() == "":
                self.comentarios_field.setText("Sin comentarios")
            
            readonly_style_comments = """
                QLineEdit {
                    background-color: #323232;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: normal;
                    color: white;
                    font-size: 13px;
                }
            """
            self.comentarios_field.setStyleSheet(readonly_style_comments)
        
        # Cambiar estado de botones
        self.edit_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.edit_session_type_button.setEnabled(False)

    def open_session_type_editor(self):
        """Abre el diálogo para editar el tipo de sesión (objetivo)"""
        current_objetivo = self.session_data.get('objetivo', '')
        
        # Crear y abrir el diálogo
        dialog = SessionTypeEditorDialog(current_objetivo, self)
        if dialog.exec() == QDialog.Accepted:
            # Obtener el nuevo objetivo
            new_objetivo = dialog.get_selected_session_type()
            
            # Actualizar en la base de datos
            success = DatabaseManager.update_session_objective(self.session_id, new_objetivo)
            
            if success:
                # Actualizar datos locales
                self.session_data['objetivo'] = new_objetivo
                
                # Actualizar la interfaz - recargar la ventana con los nuevos datos
                self.refresh_objective_display()
                
                QMessageBox.information(self, "Éxito", "El tipo de sesión ha sido actualizado correctamente.")
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar el tipo de sesión en la base de datos.")
    
    def refresh_objective_display(self):
        """Actualiza la visualización del objetivo en la interfaz"""
        # Buscar y actualizar el label del objetivo en la segunda fila
        objetivo_text = self.session_data.get('objetivo', '')
        if not objetivo_text or objetivo_text.strip() == '':
            objetivo_text = "Sin objetivo registrado"

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


class SessionTypeEditorDialog(QDialog):
    """Diálogo para editar el tipo de sesión (objetivo)"""
    
    def __init__(self, current_objetivo, parent=None):
        super().__init__(parent)
        self.current_objetivo = current_objetivo
        
        self.setWindowTitle("Editar Tipo de Sesión")
        self.resize(500, 350)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
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
        
        # Seleccionar la opción actual
        self.set_current_selection()
        
        layout.addWidget(session_type_group)
        
        # === BOTONES DE ACCIÓN ===
        button_layout = QHBoxLayout()
        
        # Botón para guardar
        save_button = QPushButton("Guardar")
        save_button.setStyleSheet("""
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
        save_button.clicked.connect(self.accept)
        
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
        
        button_layout.addWidget(save_button)
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
    
    def set_current_selection(self):
        """Establece la selección actual basada en el objetivo existente"""
        if not self.current_objetivo:
            self.radio_desensitization.setChecked(True)
            return
            
        objetivo_lower = self.current_objetivo.lower()
        
        if "desensibilización" in objetivo_lower or "traumático" in objetivo_lower:
            self.radio_desensitization.setChecked(True)
        elif "instalación" in objetivo_lower or "positiva" in objetivo_lower or "creencia" in objetivo_lower:
            self.radio_positive_belief.setChecked(True)
        elif "regulación" in objetivo_lower or "emocional" in objetivo_lower or "ansiedad" in objetivo_lower:
            self.radio_emotional_regulation.setChecked(True)
        else:
            # Es un tipo personalizado
            self.radio_other.setChecked(True)
            self.other_text.setText(self.current_objetivo)
            self.other_text.setEnabled(True)
    
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
    
    
if __name__ == "__main__":
    # Ejemplo de uso para pruebas
    app = QApplication(sys.argv)
    
    # Crear diálogo de ejemplo (necesitarías un session_id válido)
    # dialog = SessionDetailsDialog(session_id=1)
    # dialog.exec()
    
    app.quit()
