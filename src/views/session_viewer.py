import sys
import os
from pathlib import Path
import numpy as np
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QGridLayout, QGroupBox, QApplication,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon
import pyqtgraph as pg

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.database_manager import DatabaseManager
from src.analysis.session_analyzer import SessionAnalyzer

class SessionViewerWindow(QMainWindow):
    """Ventana para visualizar análisis detallado de sesiones individuales"""
    
    # Señal emitida cuando la ventana se cierra
    window_closed = Signal()
    
    def __init__(self, session_id: int = None, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.session_data = None
        self.session_metrics = None
        self.analyzer = SessionAnalyzer()
        
        # Configurar ventana
        self.setWindowTitle("EMDR Project - Visor de Sesión")
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'resources' / 'emdr_icon.png')))
        
        # Configurar UI
        self.setup_ui()
        
        # Cargar datos si se proporciona session_id
        if session_id:
            self.load_session(session_id)
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === HEADER CON CONTROLES ===
        header_frame = self.create_header()
        main_layout.addWidget(header_frame)
        
        # === ÁREA PRINCIPAL CON TABS ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #424242;
                border-radius: 8px;
                background-color: #F8F9FA;
            }
            QTabBar::tab {
                background: #E0E0E0;
                color: #424242;
                border: 2px solid #424242;
                border-bottom: none;
                border-radius: 8px 8px 0px 0px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #00A99D;
                color: white;
            }
            QTabBar::tab:hover {
                background: #B0BEC5;
            }
        """)
        
        # Tab 1: Visualización de señales
        self.signals_tab = self.create_signals_tab()
        self.tab_widget.addTab(self.signals_tab, "📊 Señales")
        
        # Tab 2: Métricas y análisis
        self.metrics_tab = self.create_metrics_tab()
        self.tab_widget.addTab(self.metrics_tab, "📈 Métricas")
        
        # Tab 3: Análisis temporal
        self.temporal_tab = self.create_temporal_tab()
        self.tab_widget.addTab(self.temporal_tab, "⏱️ Análisis Temporal")
        
        main_layout.addWidget(self.tab_widget)
        
        # === FOOTER CON INFO ===
        footer_frame = self.create_footer()
        main_layout.addWidget(footer_frame)
    
    def create_header(self) -> QFrame:
        """Crea el header con controles de sesión"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(0, 169, 157, 0.9),
                                           stop: 1 rgba(0, 140, 130, 0.8));
                border-radius: 8px;
                border: 2px solid #00A99D;
                padding: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Título y selector de sesión
        title_label = QLabel("VISOR DE SESIÓN EMDR")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Selector de sesión
        session_label = QLabel("Sesión:")
        session_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        header_layout.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("""
            QComboBox {
                background: white;
                border: 2px solid #424242;
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: bold;
                min-width: 200px;
            }
        """)
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        header_layout.addWidget(self.session_combo)
        
        # Botón de actualizar
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #424242;
                border: 2px solid #424242;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E0E0E0;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_session_list)
        header_layout.addWidget(refresh_btn)
        
        return header_frame
    
    def create_signals_tab(self) -> QWidget:
        """Crea el tab de visualización de señales"""
        signals_widget = QWidget()
        layout = QVBoxLayout(signals_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === CONTROLES DE VISUALIZACIÓN ===
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.StyledPanel)
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        controls_layout = QHBoxLayout(controls_frame)
        
        # Control de zoom temporal
        zoom_label = QLabel("Zoom Temporal:")
        controls_layout.addWidget(zoom_label)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self.update_time_range)
        controls_layout.addWidget(self.time_slider)
        
        # Control de ventana de tiempo
        window_label = QLabel("Ventana (min):")
        controls_layout.addWidget(window_label)
        
        self.window_spin = QSpinBox()
        self.window_spin.setMinimum(1)
        self.window_spin.setMaximum(60)
        self.window_spin.setValue(10)
        self.window_spin.valueChanged.connect(self.update_time_range)
        controls_layout.addWidget(self.window_spin)
        
        # Checkboxes para mostrar/ocultar señales
        self.show_eog_check = QCheckBox("Mostrar EOG")
        self.show_eog_check.setChecked(True)
        self.show_eog_check.toggled.connect(self.update_signal_visibility)
        controls_layout.addWidget(self.show_eog_check)
        
        self.show_ppg_check = QCheckBox("Mostrar PPG")
        self.show_ppg_check.setChecked(True)
        self.show_ppg_check.toggled.connect(self.update_signal_visibility)
        controls_layout.addWidget(self.show_ppg_check)
        
        self.show_bpm_check = QCheckBox("Mostrar BPM")
        self.show_bpm_check.setChecked(True)
        self.show_bpm_check.toggled.connect(self.update_signal_visibility)
        controls_layout.addWidget(self.show_bpm_check)
        
        layout.addWidget(controls_frame)
        
        # === ÁREA DE GRÁFICAS ===
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('w')
        
        # Crear plots individuales
        self.eog_plot = self.plot_widget.addPlot(row=0, col=0, title="Señal EOG - Movimientos Oculares")
        self.eog_plot.setLabel('left', 'Amplitud (µV)')
        self.eog_plot.setLabel('bottom', 'Tiempo (min)')
        self.eog_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.bpm_plot = self.plot_widget.addPlot(row=1, col=0, title="Frecuencia Cardíaca (BPM)")
        self.bpm_plot.setLabel('left', 'BPM')
        self.bpm_plot.setLabel('bottom', 'Tiempo (min)')
        self.bpm_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.ppg_plot = self.plot_widget.addPlot(row=2, col=0, title="Señal PPG - Fotopletismografía")
        self.ppg_plot.setLabel('left', 'Amplitud (ADU)')
        self.ppg_plot.setLabel('bottom', 'Tiempo (min)')
        self.ppg_plot.showGrid(x=True, y=True, alpha=0.3)
        
        layout.addWidget(self.plot_widget)
        
        return signals_widget
    
    def create_metrics_tab(self) -> QWidget:
        """Crea el tab de métricas y análisis"""
        metrics_widget = QWidget()
        layout = QHBoxLayout(metrics_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === PANEL IZQUIERDO: MÉTRICAS PRINCIPALES ===
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.StyledPanel)
        
        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        
        # Grupo de métricas HRV
        self.hrv_group = self.create_metrics_group("💓 Variabilidad del Ritmo Cardíaco (HRV)")
        left_layout.addWidget(self.hrv_group)
        
        # Grupo de métricas de estrés
        self.stress_group = self.create_metrics_group("😰 Respuesta al Estrés")
        left_layout.addWidget(self.stress_group)
        
        # Grupo de métricas de relajación
        self.relaxation_group = self.create_metrics_group("😌 Tendencias de Relajación")
        left_layout.addWidget(self.relaxation_group)
        
        left_layout.addStretch()
        left_scroll.setWidget(left_content)
        layout.addWidget(left_scroll, 1)
        
        # === PANEL DERECHO: MÉTRICAS EOG Y VISUALIZACIONES ===
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.StyledPanel)
        
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        
        # Grupo de métricas EOG
        self.eog_group = self.create_metrics_group("👁️ Patrones de Movimientos Oculares")
        right_layout.addWidget(self.eog_group)
        
        # Grupo de información de sesión
        self.session_info_group = self.create_metrics_group("ℹ️ Información de Sesión")
        right_layout.addWidget(self.session_info_group)
        
        right_layout.addStretch()
        right_scroll.setWidget(right_content)
        layout.addWidget(right_scroll, 1)
        
        return metrics_widget
    
    def create_temporal_tab(self) -> QWidget:
        """Crea el tab de análisis temporal"""
        temporal_widget = QWidget()
        layout = QVBoxLayout(temporal_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === TABLA DE ANÁLISIS POR SEGMENTOS ===
        segments_group = QGroupBox("📊 Análisis por Segmentos Temporales")
        segments_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #F8F9FA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
        """)
        
        segments_layout = QVBoxLayout(segments_group)
        
        self.segments_table = QTableWidget()
        self.segments_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #CCCCCC;
                background-color: white;
                alternate-background-color: #F5F5F5;
            }
            QHeaderView::section {
                background-color: #00A99D;
                color: white;
                font-weight: bold;
                border: 1px solid #008A80;
                padding: 8px;
            }
        """)
        self.segments_table.setAlternatingRowColors(True)
        segments_layout.addWidget(self.segments_table)
        
        layout.addWidget(segments_group)
        
        # === GRÁFICA DE PROGRESIÓN ===
        progression_group = QGroupBox("📈 Progresión Durante la Sesión")
        progression_group.setStyleSheet(segments_group.styleSheet())
        
        progression_layout = QVBoxLayout(progression_group)
        
        self.progression_plot = pg.PlotWidget()
        self.progression_plot.setBackground('w')
        self.progression_plot.setLabel('left', 'BPM Promedio')
        self.progression_plot.setLabel('bottom', 'Segmento de Tiempo')
        self.progression_plot.showGrid(x=True, y=True, alpha=0.3)
        progression_layout.addWidget(self.progression_plot)
        
        layout.addWidget(progression_group)
        
        return temporal_widget
    
    def create_metrics_group(self, title: str) -> QGroupBox:
        """Crea un grupo de métricas con estilo consistente"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #F8F9FA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00A99D;
            }
        """)
        
        layout = QGridLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)
        
        return group
    
    def load_session(self, session_id: int):
        """Carga y analiza una sesión específica"""
        try:
            # Cargar datos de la sesión
            self.session_data = self.analyzer.load_session_data(session_id)
            
            if not self.session_data:
                self.show_error("No se pudieron cargar los datos de la sesión")
                return
            
            # Calcular métricas
            self.session_metrics = self.analyzer.calculate_comprehensive_metrics(self.session_data)
            
            # Actualizar visualizaciones
            self.update_signals_plot()
            self.update_metrics_display()
            self.update_temporal_analysis()
            
            # Actualizar título de ventana
            patient_name = self.get_patient_name(self.session_data['patient_id'])
            session_date = self.session_data['fecha']
            self.setWindowTitle(f"EMDR Project - Sesión: {patient_name} ({session_date})")
            
        except Exception as e:
            self.show_error(f"Error cargando sesión: {str(e)}")
    
    def update_signals_plot(self):
        """Actualiza las gráficas de señales"""
        if not self.session_data:
            return
        
        # Convertir timestamps a minutos
        timestamps = self.session_data['timestamps']
        time_minutes = (timestamps - timestamps[0]) / (1000 * 60)  # ms a minutos
        
        # Limpiar plots
        self.eog_plot.clear()
        self.bpm_plot.clear()
        self.ppg_plot.clear()
        
        # Plotear señales
        if self.show_eog_check.isChecked():
            self.eog_plot.plot(time_minutes, self.session_data['eog_data'], 
                              pen=pg.mkPen('#2196F3', width=1), name='EOG')
        
        if self.show_bpm_check.isChecked():
            # Filtrar BPM válidos para mejor visualización
            bpm_data = self.session_data['bpm_data']
            valid_bpm = np.where((bpm_data >= 40) & (bpm_data <= 200), bpm_data, np.nan)
            self.bpm_plot.plot(time_minutes, valid_bpm, 
                              pen=pg.mkPen('#FF9800', width=2), name='BPM')
            
            # Añadir líneas de referencia
            self.bpm_plot.addLine(y=60, pen=pg.mkPen('#4CAF50', style=Qt.DashLine))
            self.bpm_plot.addLine(y=100, pen=pg.mkPen('#FFC107', style=Qt.DashLine))
        
        if self.show_ppg_check.isChecked():
            self.ppg_plot.plot(time_minutes, self.session_data['ppg_data'], 
                              pen=pg.mkPen('#00A99D', width=1), name='PPG')
        
        # Aplicar zoom si es necesario
        self.update_time_range()
    
    def update_metrics_display(self):
        """Actualiza la visualización de métricas"""
        if not self.session_metrics:
            return
        
        # === MÉTRICAS HRV ===
        hrv_metrics = self.session_metrics.get('hrv_metrics', {})
        if 'error' not in hrv_metrics:
            self.populate_metrics_group(self.hrv_group, {
                'BPM Promedio': f"{hrv_metrics.get('mean_bpm', 0):.1f}",
                'Desviación Estándar': f"{hrv_metrics.get('std_bpm', 0):.1f}",
                'BPM Mínimo': f"{hrv_metrics.get('min_bpm', 0):.1f}",
                'BPM Máximo': f"{hrv_metrics.get('max_bpm', 0):.1f}",
                'Coeficiente de Variación': f"{hrv_metrics.get('cv_bpm', 0):.1f}%",
                'RMSSD': f"{hrv_metrics.get('rmssd', 0):.1f} ms",
                'SDNN': f"{hrv_metrics.get('sdnn', 0):.1f} ms",
                'Ratio LF/HF': f"{hrv_metrics.get('lf_hf_ratio', 0):.2f}"
            })
        
        # === MÉTRICAS DE ESTRÉS ===
        stress_metrics = self.session_metrics.get('stress_metrics', {})
        self.populate_metrics_group(self.stress_group, {
            'Tendencia BPM': f"{stress_metrics.get('bpm_trend_slope', 0):.3f} BPM/min",
            'BPM Inicial': f"{stress_metrics.get('inicio_mean_bpm', 0):.1f}",
            'BPM Final': f"{stress_metrics.get('final_mean_bpm', 0):.1f}",
            'Cambio %': f"{stress_metrics.get('bpm_change_percent', 0):.1f}%",
            'Picos de Estrés': f"{stress_metrics.get('stress_peaks_count', 0)}",
            'Amplitud PPG': f"{stress_metrics.get('ppg_amplitude', 0):.0f} ADU"
        })
        
        # === MÉTRICAS DE RELAJACIÓN ===
        relaxation_metrics = self.session_metrics.get('relaxation_metrics', {})
        if 'error' not in relaxation_metrics:
            self.populate_metrics_group(self.relaxation_group, {
                'Tiempo de Relajación': f"{relaxation_metrics.get('total_relaxation_time_minutes', 0):.1f} min",
                'Porcentaje de Relajación': f"{relaxation_metrics.get('relaxation_percentage', 0):.1f}%",
                'BPM Basal': f"{relaxation_metrics.get('baseline_bpm', 0):.1f}",
                'Tasa de Recuperación': f"{relaxation_metrics.get('recovery_rate', float('inf')):.1f} seg"
            })
        
        # === MÉTRICAS EOG ===
        eog_metrics = self.session_metrics.get('eog_metrics', {})
        if 'error' not in eog_metrics:
            self.populate_metrics_group(self.eog_group, {
                'Amplitud EOG': f"{eog_metrics.get('amplitude', 0):.0f} µV",
                'RMS': f"{eog_metrics.get('rms', 0):.1f}",
                'Movimientos/seg': f"{eog_metrics.get('movement_rate_per_second', 0):.2f}",
                'Total Movimientos': f"{eog_metrics.get('total_movements', 0)}",
                'Índice de Simetría': f"{eog_metrics.get('bilateral_symmetry_index', 0):.3f}",
                'Asimetría': f"{eog_metrics.get('skewness', 0):.3f}"
            })
        
        # === INFORMACIÓN DE SESIÓN ===
        session_info = self.session_metrics.get('session_info', {})
        self.populate_metrics_group(self.session_info_group, {
            'Duración': f"{session_info.get('duration_minutes', 0):.1f} min",
            'Total Muestras': f"{session_info.get('total_samples', 0):,}",
            'Tasa de Muestreo': f"{session_info.get('sample_rate_actual', 0):.1f} Hz",
            'Fecha de Sesión': self.session_data.get('fecha', 'N/A'),
            'ID de Paciente': str(self.session_data.get('patient_id', 'N/A'))
        })
    
    def populate_metrics_group(self, group: QGroupBox, metrics: Dict[str, str]):
        """Llena un grupo de métricas con datos"""
        # Limpiar layout anterior
        layout = group.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)
        
        # Añadir nuevas métricas
        row = 0
        for key, value in metrics.items():
            # Label del nombre
            name_label = QLabel(f"{key}:")
            name_label.setStyleSheet("""
                QLabel {
                    color: #424242;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            layout.addWidget(name_label, row, 0)
            
            # Label del valor
            value_label = QLabel(str(value))
            value_label.setStyleSheet("""
                QLabel {
                    color: #00A99D;
                    font-weight: bold;
                    font-size: 12px;
                    background-color: #E8F5E8;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
            """)
            layout.addWidget(value_label, row, 1)
            
            row += 1
    
    def update_temporal_analysis(self):
        """Actualiza el análisis temporal"""
        if not self.session_metrics:
            return
        
        temporal_analysis = self.session_metrics.get('temporal_analysis', {})
        segments = temporal_analysis.get('segments', [])
        
        if not segments:
            return
        
        # === ACTUALIZAR TABLA DE SEGMENTOS ===
        self.segments_table.setRowCount(len(segments))
        self.segments_table.setColumnCount(6)
        self.segments_table.setHorizontalHeaderLabels([
            'Segmento', 'Tiempo (min)', 'BPM Promedio', 'Desv. Estándar', 
            'Amplitud PPG', 'Actividad EOG'
        ])
        
        for i, segment in enumerate(segments):
            self.segments_table.setItem(i, 0, QTableWidgetItem(str(segment['segment'])))
            self.segments_table.setItem(i, 1, QTableWidgetItem(
                f"{segment['time_start_minutes']:.1f} - {segment['time_end_minutes']:.1f}"
            ))
            self.segments_table.setItem(i, 2, QTableWidgetItem(f"{segment['mean_bpm']:.1f}"))
            self.segments_table.setItem(i, 3, QTableWidgetItem(f"{segment['std_bpm']:.1f}"))
            self.segments_table.setItem(i, 4, QTableWidgetItem(f"{segment['ppg_amplitude']:.0f}"))
            self.segments_table.setItem(i, 5, QTableWidgetItem(f"{segment['eog_activity']:.1f}"))
        
        # Ajustar tamaño de columnas
        self.segments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # === ACTUALIZAR GRÁFICA DE PROGRESIÓN ===
        self.progression_plot.clear()
        
        segment_numbers = [s['segment'] for s in segments]
        bpm_progression = [s['mean_bpm'] for s in segments]
        std_progression = [s['std_bpm'] for s in segments]
        
        # Plotear BPM promedio
        self.progression_plot.plot(segment_numbers, bpm_progression, 
                                 pen=pg.mkPen('#FF9800', width=3), 
                                 symbol='o', symbolBrush='#FF9800', symbolSize=8,
                                 name='BPM Promedio')
        
        # Añadir barras de error para desviación estándar
        error_bars = pg.ErrorBarItem(
            x=np.array(segment_numbers), y=np.array(bpm_progression),
            top=np.array(std_progression), bottom=np.array(std_progression),
            pen=pg.mkPen('#FF9800', width=2)
        )
        self.progression_plot.addItem(error_bars)
        
        # Añadir línea de tendencia si hay suficientes puntos
        if len(segments) >= 3:
            z = np.polyfit(segment_numbers, bpm_progression, 1)
            p = np.poly1d(z)
            trend_line = p(segment_numbers)
            self.progression_plot.plot(segment_numbers, trend_line, 
                                     pen=pg.mkPen('#2196F3', style=Qt.DashLine, width=2),
                                     name='Tendencia')
    
    def update_time_range(self):
        """Actualiza el rango de tiempo visible en las gráficas"""
        if not self.session_data:
            return
        
        timestamps = self.session_data['timestamps']
        total_duration = (timestamps[-1] - timestamps[0]) / (1000 * 60)  # minutos
        
        window_minutes = self.window_spin.value()
        slider_position = self.time_slider.value() / 100.0
        
        start_time = slider_position * max(0, total_duration - window_minutes)
        end_time = start_time + window_minutes
        
        # Aplicar zoom a todas las gráficas
        self.eog_plot.setXRange(start_time, end_time)
        self.bpm_plot.setXRange(start_time, end_time)
        self.ppg_plot.setXRange(start_time, end_time)
    
    def update_signal_visibility(self):
        """Actualiza la visibilidad de las señales"""
        self.update_signals_plot()
    
    def refresh_session_list(self):
        """Actualiza la lista de sesiones disponibles"""
        try:
            sessions = DatabaseManager.get_all_sessions()
            self.session_combo.clear()
            
            for session in sessions:
                patient_name = self.get_patient_name(session['id_paciente'])
                display_text = f"Sesión {session['id']} - {patient_name} ({session['fecha']})"
                self.session_combo.addItem(display_text, session['id'])
                
        except Exception as e:
            self.show_error(f"Error cargando lista de sesiones: {str(e)}")
    
    def on_session_changed(self):
        """Maneja el cambio de sesión seleccionada"""
        current_data = self.session_combo.currentData()
        if current_data:
            self.load_session(current_data)
    
    def get_patient_name(self, patient_id: int) -> str:
        """Obtiene el nombre completo del paciente"""
        try:
            patient = DatabaseManager.get_patient(patient_id)
            if patient:
                return f"{patient['nombre']} {patient['apellido_paterno']} {patient['apellido_materno']}"
            return f"Paciente {patient_id}"
        except:
            return f"Paciente {patient_id}"
    
    def create_footer(self) -> QFrame:
        """Crea el footer con información adicional"""
        footer_frame = QFrame()
        footer_frame.setFrameShape(QFrame.StyledPanel)
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("Listo para cargar sesión")
        self.status_label.setStyleSheet("color: #424242; font-size: 11px;")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Botón para cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #F44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #D32F2F;
            }
        """)
        close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)
        
        return footer_frame
    
    def show_error(self, message: str):
        """Muestra un mensaje de error"""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold;")
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana"""
        self.window_closed.emit()
        event.accept()


# Para pruebas independientes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear ventana con una sesión específica (ajustar ID según tu BD)
    viewer = SessionViewerWindow(session_id=1)
    viewer.show()
    
    sys.exit(app.exec())