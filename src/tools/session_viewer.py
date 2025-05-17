import os
import sys
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QSplitter, QFrame, QSlider,
    QGroupBox, QGridLayout, QScrollBar
)
from PySide6.QtCore import Qt, QTimer

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar DatabaseManager
from src.database.database_manager import DatabaseManager

class SessionViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Datos de Sesiones EMDR")
        self.resize(1000, 700)

        # Variables para los datos
        self.patients = []
        self.sessions = []
        self.current_data = None
        self.time_window = 10  # Segundos a mostrar en la vista
        self.display_position = 0  # Posición actual en los datos
        
        # Configurar la interfaz de usuario
        self.setup_ui()
        
        # Cargar datos iniciales
        self.load_patients()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Panel superior para selección
        selection_panel = QGroupBox("Selección de Datos")
        selection_layout = QGridLayout(selection_panel)
        
        # Selector de paciente
        selection_layout.addWidget(QLabel("Paciente:"), 0, 0)
        self.patient_combo = QComboBox()
        self.patient_combo.currentIndexChanged.connect(self.on_patient_changed)
        selection_layout.addWidget(self.patient_combo, 0, 1)
        
        # Selector de sesión
        selection_layout.addWidget(QLabel("Sesión:"), 0, 2)
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)
        selection_layout.addWidget(self.session_combo, 0, 3)
        
        # Botón de carga
        load_btn = QPushButton("Cargar Datos")
        load_btn.clicked.connect(self.load_session_data)
        selection_layout.addWidget(load_btn, 0, 4)
        
        main_layout.addWidget(selection_panel)
        
        # Contenedor para gráficos
        plots_container = QWidget()
        plots_layout = QVBoxLayout(plots_container)
        plots_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear los tres gráficos
        # 1. Gráfico PPG
        self.ppg_plot = pg.PlotWidget()
        self.ppg_plot.setLabel('left', 'Señal PPG')
        self.ppg_plot.setBackground('w')
        self.ppg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ppg_curve = self.ppg_plot.plot(pen=pg.mkPen('#E91E63', width=2))
        plots_layout.addWidget(self.ppg_plot)
        
        # 2. Gráfico BPM
        self.bpm_plot = pg.PlotWidget()
        self.bpm_plot.setLabel('left', 'BPM')
        self.bpm_plot.setBackground('w')
        self.bpm_plot.showGrid(x=True, y=True, alpha=0.3)
        self.bpm_plot.setYRange(40, 180)  # Rango típico para BPM humano
        self.bpm_curve = self.bpm_plot.plot(pen=pg.mkPen('#FF9800', width=2))
        plots_layout.addWidget(self.bpm_plot)
        
        # 3. Gráfico EOG
        self.eog_plot = pg.PlotWidget()
        self.eog_plot.setLabel('left', 'Señal EOG')
        self.eog_plot.setLabel('bottom', 'Tiempo (s)')
        self.eog_plot.setBackground('w')
        self.eog_plot.showGrid(x=True, y=True, alpha=0.3)
        self.eog_curve = self.eog_plot.plot(pen=pg.mkPen('#2196F3', width=2))
        plots_layout.addWidget(self.eog_plot)
        
        main_layout.addWidget(plots_container)
        
        # Panel de control para navegación
        navigation_panel = QGroupBox("Navegación y Controles")
        navigation_layout = QVBoxLayout(navigation_panel)
        
        # Control deslizante para cambiar la posición
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Posición:"))
        self.position_slider = QScrollBar(Qt.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(100)
        self.position_slider.valueChanged.connect(self.on_position_changed)
        slider_layout.addWidget(self.position_slider)
        navigation_layout.addLayout(slider_layout)
        
        # Controles de ventana de tiempo
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Ventana de tiempo (s):"))
        
        window_btn_layout = QHBoxLayout()
        for window in [5, 10, 30, 60]:
            btn = QPushButton(str(window))
            btn.clicked.connect(lambda _, w=window: self.set_time_window(w))
            window_btn_layout.addWidget(btn)
        
        window_layout.addLayout(window_btn_layout)
        navigation_layout.addLayout(window_layout)
        
        main_layout.addWidget(navigation_panel)
        
        # Barra de estado
        self.statusBar().showMessage("Listo para cargar datos de sesión")

    def load_patients(self):
        """Cargar lista de pacientes"""
        self.patients = DatabaseManager.get_all_patients()
        self.patient_combo.clear()
        
        for patient in self.patients:
            full_name = f"{patient['apellido_paterno']} {patient['apellido_materno']}, {patient['nombre']}"
            self.patient_combo.addItem(full_name, patient['id'])

    def on_patient_changed(self, index):
        """Cuando cambia la selección de paciente"""
        if index < 0:
            return
            
        patient_id = self.patient_combo.itemData(index)
        self.load_sessions(patient_id)

    def load_sessions(self, patient_id):
        """Cargar sesiones del paciente seleccionado"""
        self.sessions = DatabaseManager.get_sessions_for_patient(patient_id)
        self.session_combo.clear()
        
        for session in self.sessions:
            self.session_combo.addItem(
                f"Sesión #{session['id']} - {session['fecha']}", 
                session['id']
            )

    def on_session_changed(self, index):
        """Cuando cambia la selección de sesión"""
        pass  # Solo se cargará al hacer clic en el botón de carga

    def load_session_data(self):
        """Cargar datos de la sesión seleccionada"""
        if self.session_combo.count() == 0:
            self.statusBar().showMessage("No hay sesiones disponibles")
            return
            
        session_id = self.session_combo.currentData()
        self.statusBar().showMessage(f"Cargando datos de sesión #{session_id}...")
        
        # Obtener datos de la sesión
        self.current_data = DatabaseManager.get_session_data(session_id)
        
        if not self.current_data:
            self.statusBar().showMessage("No se pudieron cargar los datos de la sesión")
            return
            
        # Actualizar el slider según la cantidad de datos
        data_length = 0
        if self.current_data.get("ppg_data") is not None:
            data_length = len(self.current_data["ppg_data"])
        elif self.current_data.get("eog_data") is not None:
            data_length = len(self.current_data["eog_data"])
        elif self.current_data.get("bpm_data") is not None:
            data_length = len(self.current_data["bpm_data"])
            
        if data_length == 0:
            self.statusBar().showMessage("La sesión no contiene datos")
            return
            
        # Configurar slider
        self.position_slider.setMaximum(max(0, data_length - 1))
        self.position_slider.setValue(0)
        self.display_position = 0
        
        # Mostrar los datos
        self.update_plots()
        
        self.statusBar().showMessage(f"Datos cargados: {data_length} muestras")

    def on_position_changed(self, value):
        """Cuando se mueve el slider de posición"""
        self.display_position = value
        self.update_plots()

    def set_time_window(self, seconds):
        """Cambiar el tamaño de la ventana de tiempo"""
        self.time_window = seconds
        self.update_plots()

    def update_plots(self):
        """Actualizar todas las gráficas"""
        if not self.current_data:
            return
            
        # Crear vector de tiempo basado en frecuencia de muestreo (asumimos 125 Hz)
        sample_rate = 125  # Hz
        
        # Determinar cuántas muestras mostrar
        samples_to_show = self.time_window * sample_rate
        
        # Datos PPG
        if self.current_data.get("ppg_data") is not None:
            ppg_data = self.current_data["ppg_data"]
            
            # Calcular índices de inicio y fin
            end_idx = min(self.display_position + samples_to_show, len(ppg_data))
            start_idx = max(0, end_idx - samples_to_show)
            
            # Extraer segmento de datos
            segment = ppg_data[start_idx:end_idx]
            
            # Crear vector de tiempo para este segmento
            time_vector = np.arange(len(segment)) / sample_rate
            
            # Actualizar gráfica
            self.ppg_curve.setData(time_vector, segment)
            self.ppg_plot.setXRange(0, self.time_window)
        
        # Datos BPM
        if self.current_data.get("bpm_data") is not None:
            bpm_data = self.current_data["bpm_data"]
            
            # Calcular índices
            end_idx = min(self.display_position + samples_to_show, len(bpm_data))
            start_idx = max(0, end_idx - samples_to_show)
            
            # Extraer segmento
            segment = bpm_data[start_idx:end_idx]
            
            # Crear vector de tiempo
            time_vector = np.arange(len(segment)) / sample_rate
            
            # Actualizar gráfica
            self.bpm_curve.setData(time_vector, segment)
            self.bpm_plot.setXRange(0, self.time_window)
        
        # Datos EOG
        if self.current_data.get("eog_data") is not None:
            eog_data = self.current_data["eog_data"]
            
            # Calcular índices
            end_idx = min(self.display_position + samples_to_show, len(eog_data))
            start_idx = max(0, end_idx - samples_to_show)
            
            # Extraer segmento
            segment = eog_data[start_idx:end_idx]
            
            # Crear vector de tiempo
            time_vector = np.arange(len(segment)) / sample_rate
            
            # Actualizar gráfica
            self.eog_curve.setData(time_vector, segment)
            self.eog_plot.setXRange(0, self.time_window)


def main():
    app = QApplication(sys.argv)
    viewer = SessionViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()