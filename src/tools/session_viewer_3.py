import os
import sys
import numpy as np
import pandas as pd
import pickle
import zlib
from datetime import datetime, timedelta
from collections import deque

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSplitter, QTabWidget, QGridLayout, QGroupBox,
    QSpinBox, QCheckBox, QDateEdit, QMessageBox, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize, QDate, Slot
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QKeySequence
import pyqtgraph as pg

# Importar herramientas de análisis y base de datos
from database.database_manager import DatabaseManager
from scipy import signal

class SessionViewer(QMainWindow):
    """Visor de sesiones EMDR con visualización de señales"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visualizador de Sesiones EMDR")
        self.resize(1200, 800)
        
        # Variables de estado
        self.current_patient = None
        self.current_session_id = None
        self.session_data = None
        self.eog_data = None
        self.ppg_data = None
        self.bpm_data = None
        self.time_data = None
        self.session_roi = None  # Región de interés seleccionada
        
        # Configurar la interfaz
        self.setup_ui()
        
        # Cargar pacientes
        self.load_patients()
        
        # Configurar estilo
        self.setup_style()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Panel superior: Selector de paciente y sesión
        top_panel = QGroupBox("Selección de Paciente y Sesión")
        top_layout = QHBoxLayout(top_panel)
        
        # Selector de paciente
        patient_layout = QVBoxLayout()
        patient_label = QLabel("Paciente:")
        self.patient_selector = QComboBox()
        self.patient_selector.setMinimumWidth(250)
        self.patient_selector.currentIndexChanged.connect(self.on_patient_changed)
        patient_layout.addWidget(patient_label)
        patient_layout.addWidget(self.patient_selector)
        top_layout.addLayout(patient_layout)
        
        # Selector de sesión
        session_layout = QVBoxLayout()
        session_label = QLabel("Sesión:")
        self.session_selector = QComboBox()
        self.session_selector.setMinimumWidth(250)
        self.session_selector.currentIndexChanged.connect(self.on_session_changed)
        session_layout.addWidget(session_label)
        session_layout.addWidget(self.session_selector)
        top_layout.addLayout(session_layout)
        
        # Filtro de fechas
        date_layout = QVBoxLayout()
        date_label = QLabel("Filtrar por fecha:")
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.dateChanged.connect(self.filter_sessions_by_date)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_filter)
        top_layout.addLayout(date_layout)
        
        # Botones de acción
        action_layout = QVBoxLayout()
        action_label = QLabel("Acciones:")
        self.load_btn = QPushButton("Cargar Sesión")
        self.load_btn.clicked.connect(self.load_session_data)
        action_layout.addWidget(action_label)
        action_layout.addWidget(self.load_btn)
        top_layout.addLayout(action_layout)
        
        # Añadir el panel superior al layout principal
        main_layout.addWidget(top_panel)
        
        # Panel central: Visualización de datos
        overview_layout = QVBoxLayout()
        
        # Dividir la vista en varias gráficas
        self.signals_splitter = QSplitter(Qt.Vertical)
        
        # Gráfica para EOG
        self.eog_plot_widget = pg.PlotWidget()
        self.eog_plot_widget.setLabel('left', 'EOG')
        self.eog_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.eog_plot_widget.setBackground('w')
        
        # Gráfica para PPG
        self.ppg_plot_widget = pg.PlotWidget()
        self.ppg_plot_widget.setLabel('left', 'PPG')
        self.ppg_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.ppg_plot_widget.setBackground('w')
        
        # Gráfica para BPM
        self.bpm_plot_widget = pg.PlotWidget()
        self.bpm_plot_widget.setLabel('left', 'BPM')
        self.bpm_plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.bpm_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.bpm_plot_widget.setBackground('w')
        
        # Añadir gráficas al splitter
        self.signals_splitter.addWidget(self.eog_plot_widget)
        self.signals_splitter.addWidget(self.ppg_plot_widget)
        self.signals_splitter.addWidget(self.bpm_plot_widget)
        
        # Configurar curvas para datos
        self.eog_curve = self.eog_plot_widget.plot(pen=pg.mkPen('#2196F3', width=2))
        self.ppg_curve = self.ppg_plot_widget.plot(pen=pg.mkPen('#E91E63', width=2))
        self.bpm_curve = self.bpm_plot_widget.plot(pen=pg.mkPen('#FF9800', width=2))
        
        # Añadir etiquetas y leyendas
        eog_label = pg.TextItem(text="EOG - Movimiento Ocular", color=(0,0,0), anchor=(0,0))
        eog_label.setPos(10, 10)
        self.eog_plot_widget.addItem(eog_label)
        
        ppg_label = pg.TextItem(text="PPG - Señal Cardíaca", color=(0,0,0), anchor=(0,0))
        ppg_label.setPos(10, 10)
        self.ppg_plot_widget.addItem(ppg_label)
        
        bpm_label = pg.TextItem(text="BPM - Frecuencia Cardíaca", color=(0,0,0), anchor=(0,0))
        bpm_label.setPos(10, 10)
        self.bpm_plot_widget.addItem(bpm_label)
        
        # Enlazar ejes X para sincronización
        self.eog_plot_widget.setXLink(self.bpm_plot_widget)
        self.ppg_plot_widget.setXLink(self.bpm_plot_widget)
        
        # Panel de información de sesión
        session_info_box = QGroupBox("Información de Sesión")
        session_info_layout = QGridLayout(session_info_box)
        
        # Etiquetas para información
        self.session_date_label = QLabel("Fecha: --")
        self.session_duration_label = QLabel("Duración: --")
        self.sample_count_label = QLabel("Muestras: --")
        self.avg_bpm_label = QLabel("BPM Promedio: --")
        
        # Añadir etiquetas al layout
        session_info_layout.addWidget(self.session_date_label, 0, 0)
        session_info_layout.addWidget(self.session_duration_label, 0, 1)
        session_info_layout.addWidget(self.sample_count_label, 1, 0)
        session_info_layout.addWidget(self.avg_bpm_label, 1, 1)
        
        # Controles de visualización
        viz_controls_box = QGroupBox("Controles de Visualización")
        viz_controls_layout = QHBoxLayout(viz_controls_box)
        
        # Botón para seleccionar región
        self.roi_btn = QPushButton("Seleccionar Región")
        self.roi_btn.clicked.connect(self.toggle_roi_selection)
        
        # Botón para resetear zoom
        self.reset_zoom_btn = QPushButton("Resetear Zoom")
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        # Botón para exportar datos
        self.export_btn = QPushButton("Exportar Datos")
        self.export_btn.clicked.connect(self.export_session_data)
        
        # Añadir botones al layout
        viz_controls_layout.addWidget(self.roi_btn)
        viz_controls_layout.addWidget(self.reset_zoom_btn)
        viz_controls_layout.addWidget(self.export_btn)
        
        # Añadir controles a la vista general
        overview_layout.addWidget(self.signals_splitter)
        overview_layout.addWidget(session_info_box)
        overview_layout.addWidget(viz_controls_box)
        
        # Añadir layout al principal
        main_layout.addLayout(overview_layout, 1)
        
        # Barra de estado para mensajes
        self.statusBar().showMessage("Listo para visualizar sesiones")
    
    def setup_style(self):
        """Configurar estilo visual de la aplicación"""
        # Estilo para toda la aplicación
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #2196F3;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px;
                min-height: 25px;
            }
        """)
        
    def load_patients(self):
        """Cargar lista de pacientes desde la base de datos"""
        try:
            patients = DatabaseManager.get_all_patients()
            self.patient_selector.clear()
            self.patient_selector.addItem("-- Seleccione un paciente --", None)
            
            for patient in patients:
                full_name = f"{patient['apellido_paterno']} {patient['apellido_materno']}, {patient['nombre']}"
                self.patient_selector.addItem(full_name, patient['id'])
                
            self.statusBar().showMessage(f"Se cargaron {len(patients)} pacientes")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar la lista de pacientes: {str(e)}")
    
    def on_patient_changed(self, index):
        """Manejar cambio de paciente seleccionado"""
        patient_id = self.patient_selector.currentData()
        if patient_id is None:
            self.session_selector.clear()
            self.current_patient = None
            return
            
        try:
            # Obtener datos del paciente
            self.current_patient = DatabaseManager.get_patient(patient_id)
            
            # Cargar sesiones del paciente
            self.load_patient_sessions(patient_id)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el paciente: {str(e)}")
    
    def load_patient_sessions(self, patient_id):
        """Cargar sesiones para el paciente seleccionado"""
        try:
            sessions = DatabaseManager.get_sessions_for_patient(patient_id)
            
            self.session_selector.clear()
            self.session_selector.addItem("-- Seleccione una sesión --", None)
            
            for session in sessions:
                # Formatear fecha para mejor visualización
                date_str = session['fecha']
                if isinstance(date_str, str):
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                    except:
                        formatted_date = date_str
                else:
                    formatted_date = str(date_str)
                
                # Añadir sesión al selector
                self.session_selector.addItem(f"Sesión #{session['id']} - {formatted_date}", session['id'])
            
            self.statusBar().showMessage(f"Se cargaron {len(sessions)} sesiones para el paciente")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las sesiones: {str(e)}")
    
    def filter_sessions_by_date(self, date):
        """Filtrar sesiones por fecha"""
        if not self.current_patient:
            return
        
        # Implementación básica del filtro por fecha
        QMessageBox.information(self, "Filtro", "Función de filtrado por fecha pendiente de implementar")
    
    def on_session_changed(self, index):
        """Manejar cambio de sesión seleccionada"""
        session_id = self.session_selector.currentData()
        self.current_session_id = session_id
        
        # No cargar datos automáticamente, esperar a que el usuario presione el botón
        if session_id:
            self.load_btn.setEnabled(True)
            self.statusBar().showMessage(f"Sesión #{session_id} seleccionada. Presione 'Cargar Sesión' para visualizar.")
        else:
            self.load_btn.setEnabled(False)
    
    def load_session_data(self):
        """Cargar y visualizar los datos de la sesión seleccionada"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Error", "No hay sesión seleccionada")
            return
            
        try:
            # Mostrar mensaje de carga
            self.statusBar().showMessage(f"Cargando datos de sesión #{self.current_session_id}...")
            QApplication.processEvents()
            
            # Cargar datos desde la base de datos
            self.session_data = DatabaseManager.get_session(self.current_session_id, signal_data=True)

            if not self.session_data:
                QMessageBox.warning(self, "Error", "No se encontraron datos para esta sesión")
                return
             
            # Extraer y descomprimir datos si es necesario
            try:
                # Intentar extraer directamente (si ya están descomprimidos)
                self.eog_data = self.session_data.get('datos_eog')
                self.ppg_data = self.session_data.get('datos_ppg')
                self.bpm_data = self.session_data.get('datos_bpm')
                
                # Verificar si los datos son bytes comprimidos
                if isinstance(self.eog_data, bytes):
                    self.eog_data = pickle.loads(zlib.decompress(self.eog_data))
                if isinstance(self.ppg_data, bytes):
                    self.ppg_data = pickle.loads(zlib.decompress(self.ppg_data))
                if isinstance(self.bpm_data, bytes):
                    self.bpm_data = pickle.loads(zlib.decompress(self.bpm_data))
                    
                # Convertir a numpy arrays para mejor manipulación
                self.eog_data = np.array(self.eog_data)
                self.ppg_data = np.array(self.ppg_data)
                if self.bpm_data is not None:
                    self.bpm_data = np.array(self.bpm_data)
                    
                # Imprimir información para depuración
                print(f"EOG shape: {self.eog_data.shape}, type: {type(self.eog_data)}")
                print(f"PPG shape: {self.ppg_data.shape}, type: {type(self.ppg_data)}")
                if self.bpm_data is not None:
                    print(f"BPM shape: {self.bpm_data.shape}, type: {type(self.bpm_data)}")
                else:
                    print("No hay datos BPM disponibles")
                
            except Exception as e:
                print(f"Error al procesar datos: {str(e)}")
                import traceback
                traceback.print_exc()
                QMessageBox.warning(self, "Error de formato", 
                                 "Los datos no tienen el formato esperado. Detalles: " + str(e))
                return
            
            if self.eog_data is None or self.ppg_data is None:
                QMessageBox.warning(self, "Datos incompletos", 
                                   "Esta sesión no tiene datos completos de EOG o PPG")
                return
                
            # Crear array de tiempo basado en frecuencia de muestreo
            sample_count = len(self.eog_data)
            self.time_data = np.arange(sample_count) / 125.0  # 125 Hz es la frecuencia de muestreo
            
            # Agregar después de crear self.time_data
            if not self.validate_data():
                QMessageBox.warning(self, "Error de datos", 
                                   "Los datos tienen un formato incorrecto o valores extremos")
                return
            
            # Actualizar gráficos
            self.update_plots()
            
            # Actualizar información de la sesión
            self.update_session_info()
            
            self.statusBar().showMessage(f"Datos de sesión #{self.current_session_id} cargados correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los datos: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_plots(self):
        """Actualizar los gráficos con los datos cargados"""
        if self.eog_data is None or self.time_data is None:
            return
        
        try:
            # Verificar que los datos tienen forma adecuada
            if len(self.eog_data) != len(self.time_data):
                print(f"Error: Dimensiones no coinciden. Tiempo: {len(self.time_data)}, EOG: {len(self.eog_data)}")
                return
                
            # Limpiar gráficos anteriores
            self.eog_curve.clear()
            self.ppg_curve.clear()
            self.bpm_curve.clear()  # Siempre limpiar la curva BPM
                
            # Actualizar gráficos con nuevos datos
            self.eog_curve.setData(self.time_data, self.eog_data)
            self.ppg_curve.setData(self.time_data, self.ppg_data)
            
            # Procesar datos BPM con manejo especial
            if self.bpm_data is not None:
                # Verificar longitud de BPM
                if len(self.bpm_data) == len(self.time_data):
                    # Caso ideal: misma longitud
                    bpm_time = self.time_data
                    bpm_values = self.bpm_data
                else:
                    # Caso diferente longitud: crear nueva escala de tiempo
                    print(f"Advertencia: BPM tiene diferente longitud ({len(self.bpm_data)}) que tiempo ({len(self.time_data)})")
                    bpm_time = np.linspace(self.time_data[0], self.time_data[-1], len(self.bpm_data))
                    bpm_values = self.bpm_data
            
                # Filtrar valores extremos o inválidos
                valid_indices = (bpm_values > 30) & (bpm_values < 200)
                if np.any(valid_indices):
                    filtered_time = bpm_time[valid_indices]
                    filtered_values = bpm_values[valid_indices]
                    
                    # Establecer datos en la curva BPM
                    self.bpm_curve.setData(filtered_time, filtered_values)
                    
                    # Ajustar rango Y para BPM
                    bpm_min, bpm_max = np.min(filtered_values), np.max(filtered_values)
                    bpm_margin = (bpm_max - bpm_min) * 0.2
                    self.bpm_plot_widget.setYRange(max(40, bpm_min - bpm_margin), 
                                                min(180, bpm_max + bpm_margin))
                else:
                    # No hay valores válidos
                    self.bpm_plot_widget.setYRange(40, 120)  # Rango por defecto
                    print("Advertencia: No hay valores BPM válidos para mostrar")
            else:
                # No hay datos BPM
                self.bpm_plot_widget.setYRange(40, 120)  # Rango por defecto
            
            eog_min, eog_max = np.min(self.eog_data), np.max(self.eog_data)
            ppg_min, ppg_max = np.min(self.ppg_data), np.max(self.ppg_data)
            
            # Ajustar rangos con margen
            eog_margin = (eog_max - eog_min) * 0.1
            ppg_margin = (ppg_max - ppg_min) * 0.1
            
            self.eog_plot_widget.setYRange(eog_min - eog_margin, eog_max + eog_margin)
            self.ppg_plot_widget.setYRange(ppg_min - ppg_margin, ppg_max + ppg_margin)
            
            # Ajustar rango de tiempo
            self.eog_plot_widget.setXRange(self.time_data[0], self.time_data[-1])
            
            print("Gráficos actualizados correctamente")
            
        except Exception as e:
            print(f"Error al actualizar gráficos: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_session_info(self):
        """Actualizar información de la sesión"""
        if not self.session_data or not self.time_data.size:
            return
            
        # Obtener información de la fecha de la sesión
        date_str = self.session_data['fecha']
        
        # Formatear fecha
        if isinstance(date_str, str):
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                formatted_date = date_str
        else:
            formatted_date = str(date_str)
        
        # Calcular duración
        duration_sec = self.time_data[-1]
        minutes, seconds = divmod(duration_sec, 60)
        duration_str = f"{int(minutes)}m {int(seconds)}s"
        
        # Calcular BPM promedio
        if self.bpm_data is not None and len(self.bpm_data) > 0:
            # Filtrar valores cero que pueden ser inicio de la medición
            valid_bpm = [x for x in self.bpm_data if x > 30]
            avg_bpm = np.mean(valid_bpm) if valid_bpm else 0
            avg_bpm_str = f"{avg_bpm:.1f}"
        else:
            avg_bpm_str = "N/A"
        
        # Actualizar etiquetas
        self.session_date_label.setText(f"Fecha: {formatted_date}")
        self.session_duration_label.setText(f"Duración: {duration_str}")
        self.sample_count_label.setText(f"Muestras: {len(self.time_data)}")
        self.avg_bpm_label.setText(f"BPM Promedio: {avg_bpm_str}")
    
    def toggle_roi_selection(self):
        """Activar/desactivar selección de región de interés"""
        if self.session_roi is None:
            # Crear ROI en el gráfico de BPM (inferior)
            self.session_roi = pg.LinearRegionItem()
            self.session_roi.setZValue(10)
            self.session_roi.setRegion([self.time_data[0], self.time_data[-1]])
            self.bpm_plot_widget.addItem(self.session_roi)
            self.roi_btn.setText("Aplicar Selección")
            
            # Cambiar color del botón para indicar estado activo
            self.roi_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5722;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E64A19;
                }
            """)
        else:
            # Obtener región seleccionada
            region_min, region_max = self.session_roi.getRegion()
            
            # Aplicar zoom a la región seleccionada
            self.eog_plot_widget.setXRange(region_min, region_max)
            self.ppg_plot_widget.setXRange(region_min, region_max)
            self.bpm_plot_widget.setXRange(region_min, region_max)
            
            # Eliminar ROI
            self.bpm_plot_widget.removeItem(self.session_roi)
            self.session_roi = None
            self.roi_btn.setText("Seleccionar Región")
            
            # Restaurar estilo del botón
            self.roi_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
    
    def reset_zoom(self):
        """Resetear zoom a vista completa"""
        if self.time_data is not None and len(self.time_data) > 0:
            self.eog_plot_widget.setXRange(self.time_data[0], self.time_data[-1])
            self.ppg_plot_widget.setXRange(self.time_data[0], self.time_data[-1])
            self.bpm_plot_widget.setXRange(self.time_data[0], self.time_data[-1])
    
    def export_session_data(self):
        """Exportar datos de la sesión actual a archivo CSV"""
        if not self.current_session_id or self.eog_data is None:
            QMessageBox.warning(self, "Error", "No hay datos de sesión para exportar")
            return
            
        try:
            # Pedir ubicación para guardar archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar datos de sesión", "", "CSV (*.csv);;Excel (*.xlsx)"
            )
            
            if not file_path:
                return  # Usuario canceló
                
            # Crear DataFrame con los datos
            data = {
                'Tiempo_s': self.time_data,
                'EOG': self.eog_data,
                'PPG': self.ppg_data
            }
            
            if self.bpm_data is not None:
                data['BPM'] = self.bpm_data
                
            df = pd.DataFrame(data)
            
            # Guardar según extensión
            if file_path.lower().endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                if not file_path.lower().endswith('.csv'):
                    file_path += '.csv'
                df.to_csv(file_path, index=False)
                
            # Mostrar mensaje de éxito
            QMessageBox.information(
                self, "Exportación exitosa", 
                f"Datos exportados correctamente a:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron exportar los datos: {str(e)}")
    
    def validate_data(self):
        """Validar que los datos tengan formato numérico adecuado"""
        try:
            # Verificar tipos de datos
            if not isinstance(self.eog_data, (list, np.ndarray)) or not isinstance(self.ppg_data, (list, np.ndarray)):
                print("Error: Datos de EOG o PPG no son listas o arrays")
                return False
                
            # Verificar que los datos sean numéricos
            if not np.issubdtype(np.array(self.eog_data).dtype, np.number):
                print(f"Error: Datos EOG no son numéricos. Tipo: {np.array(self.eog_data).dtype}")
                return False
                
            if not np.issubdtype(np.array(self.ppg_data).dtype, np.number):
                print(f"Error: Datos PPG no son numéricos. Tipo: {np.array(self.ppg_data).dtype}")
                return False
                
            # Verificar que no haya valores extremos que puedan afectar la visualización
            eog_max = np.max(np.abs(self.eog_data))
            ppg_max = np.max(np.abs(self.ppg_data))
            
            if eog_max > 1e6:
                print(f"Advertencia: Valores EOG muy grandes: {eog_max}")
                
            if ppg_max > 1e6:
                print(f"Advertencia: Valores PPG muy grandes: {ppg_max}")
                
            return True
            
        except Exception as e:
            print(f"Error al validar datos: {str(e)}")
            return False

if __name__ == "__main__":
    """Función principal para ejecutar el visor de sesiones como aplicación independiente"""
    app = QApplication([])
    viewer = SessionViewer()
    viewer.show()
    sys.exit(app.exec())