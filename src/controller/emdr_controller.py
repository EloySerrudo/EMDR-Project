import sys
from numpy import log
import time
import os

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication, QTabWidget, 
    QPushButton, QLabel, QSpacerItem, QSizePolicy, QFrame, QCheckBox, QScrollArea,
    QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QColor, QBrush, QPen
import qtawesome as qta

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
# Importaciones de componentes de vistas
from src.views.components.containers import Container, SwitchContainer
from src.views.components.selectors import Selector
from src.views.components.counter import Counter
from src.views.components.buttons import CustomButton, Switch
from src.views.components.pyqtSwitch import PyQtSwitch
from src.views.components.chronometer import Chronometer

# Importaciones de modelos
from src.models.devices import Devices, KNOWN_SLAVES
from src.models.config import Config

# Importaciones de utilidades
from src.utils.hiperf_timer import HighPerfTimer
from src.utils.events import event_system


class EMDRPatternVisualizer(QWidget):
    """Widget para visualizar el patrón actual de movimiento EMDR"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.led_count = Devices.led_num
        self.current_led = self.led_count // 2 + 1
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)
        self.dots = []
        
        # Crear los dots (representación de LEDs)
        for i in range(self.led_count):
            self.dots.append(False)  # Todos apagados inicialmente
    
    def update_led_position(self, position):
        """Actualiza la posición del LED activo"""
        # Resetear todos los LEDs
        self.dots = [False] * self.led_count
        
        # Marcar el LED activo
        if 0 < position <= self.led_count:
            self.dots[position-1] = True
        
        # Redibujar
        self.update()
    
    def paintEvent(self, event):
        """Maneja el evento de dibujo"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dibujar el fondo con gradiente
        width = self.width()
        height = self.height()
        
        dot_radius = min(height * 0.25, width / (self.led_count * 2.5))
        center_y = height / 2
        
        # Calcular espaciado entre LEDs
        dot_spacing = (width - (2 * dot_radius * self.led_count)) / (self.led_count + 1)
        
        for i in range(self.led_count):
            center_x = dot_spacing * (i + 1) + dot_radius * (2 * i + 1)
            
            # Dibujar el círculo con efecto de brillo
            if self.dots[i]:
                # LED activo: color brillante con efecto de brillo
                painter.setBrush(QBrush(QColor("#00C2B3")))
                painter.setPen(QPen(QColor("#00FF00"), 2))
                
                # Efecto de brillo exterior
                painter.drawEllipse(center_x - dot_radius - 2, center_y - dot_radius - 2, 
                                  (dot_radius + 2) * 2, (dot_radius + 2) * 2)
                
                # LED principal
                painter.setBrush(QBrush(QColor("#00E6D6")))
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
            else:
                # LED inactivo: color apagado
                painter.setBrush(QBrush(QColor("#424242")))
                painter.setPen(QPen(QColor("#666666"), 1))
            
            painter.drawEllipse(center_x - dot_radius, center_y - dot_radius, 
                              dot_radius * 2, dot_radius * 2)


class EMDRControllerWidget(QWidget):
    """Controlador principal de la aplicación EMDR convertido a widget PySide6"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.in_load = False
        self.pausing = False
        self.stopping = False
        
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #444444;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        # Layout principal vertical
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(0)
        
        # 1. Etiqueta de estado de dispositivos modernizada
        if self.parent():
            self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                            stop: 0 rgba(255, 150, 100, 0.15),
                                            stop: 0.5 rgba(255, 200, 150, 0.2),
                                            stop: 1 rgba(255, 150, 100, 0.15));
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 2px solid rgba(255, 180, 120, 0.3);
                }
            """)
            self.main_layout.addWidget(self.device_status_label)
        
        # 2. Contenedor de botones principales con estilo moderno
        control_container = QFrame()
        control_container.setFrameShape(QFrame.StyledPanel)
        control_container.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 12px;
                border: 2px solid #444444;
                padding: 0px;
            }
        """)
        
        control_layout = QHBoxLayout(control_container)
        control_layout.setContentsMargins(10, 5, 10, 5)
        control_layout.setSpacing(20)
        control_layout.addStretch()
        
        # Layout de reja de botones principales
        button_layout = QGridLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)

        # Crear botones principales con estilo moderno
        self.btn_start = CustomButton('Play', self.start_click)
        self.btn_start24 = CustomButton('Play 24', self.start24_click)
        self.btn_stop = CustomButton('Stop', self.stop_click)
        self.btn_pause = CustomButton('Pause', self.pause_click, togglable=True)
        
        # Aplicar estilos modernos a los botones principales
        main_button_style = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00A99D,
                                          stop: 0.5 #00C2B3,
                                          stop: 1 #00A99D);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #00A99D;
                padding: 10px 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00C2B3,
                                          stop: 0.5 #00D4C6,
                                          stop: 1 #00C2B3);
                border: 2px solid #00C2B3;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #008C82,
                                          stop: 0.5 #009A8F,
                                          stop: 1 #008C82);
                border: 2px solid #008C82;
            }
            QPushButton:disabled {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #555555,
                                          stop: 0.5 #666666,
                                          stop: 1 #555555);
                border: 2px solid #555555;
                color: #888888;
            }
        """
        
        # Estilo especial para botón Stop (rojo)
        stop_button_style = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #D32F2F,
                                          stop: 0.5 #F44336,
                                          stop: 1 #D32F2F);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #D32F2F;
                padding: 10px 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #F44336,
                                          stop: 0.5 #FF5722,
                                          stop: 1 #F44336);
                border: 2px solid #F44336;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #B71C1C,
                                          stop: 0.5 #C62828,
                                          stop: 1 #B71C1C);
                border: 2px solid #B71C1C;
            }
            QPushButton:disabled {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #555555,
                                          stop: 0.5 #666666,
                                          stop: 1 #555555);
                border: 2px solid #555555;
                color: #888888;
            }
        """
        
        # Aplicar estilos a los botones
        self.btn_start.setStyleSheet(main_button_style)
        self.btn_start24.setStyleSheet(main_button_style)
        self.btn_stop.setStyleSheet(stop_button_style)
        self.btn_pause.setStyleSheet(main_button_style)
        
        # Añadir los botones principales al layout de reja
        button_layout.addWidget(self.btn_start, 0, 0)
        button_layout.addWidget(self.btn_start24, 0, 1)
        button_layout.addWidget(self.btn_pause, 1, 0)
        button_layout.addWidget(self.btn_stop, 1, 1)
        
        control_layout.addLayout(button_layout)
        control_layout.addStretch()

        # Botón de escaneo (solo visible si se ejecuta como ventana independiente)
        if self.parent():
            self.btn_scan_usb = CustomButton('Escanear', self.scan_usb_click)
            self.btn_scan_usb.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #424242,
                                              stop: 0.5 #555555,
                                              stop: 1 #424242);
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                    border: 2px solid #424242;
                    padding: 10px 20px;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #555555,
                                              stop: 0.5 #666666,
                                              stop: 1 #555555);
                    border: 2px solid #555555;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #333333,
                                              stop: 0.5 #444444,
                                              stop: 1 #333333);
                    border: 2px solid #333333;
                }
                QPushButton:disabled {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #555555,
                                              stop: 0.5 #666666,
                                              stop: 1 #555555);
                    border: 2px solid #555555;
                    color: #888888;
                }
            """)
            
            control_layout.addWidget(self.btn_scan_usb)
            control_layout.addStretch()
        
        # Checkbox para capturar señales con estilo moderno
        self.chk_capture_signals = QCheckBox("¿Capturar señales?")
        self.chk_capture_signals.setStyleSheet("""
            QCheckBox {
                background: transparent;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
                border-radius: 6px;
            }
            QCheckBox:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 3px;
                border: 2px solid #00A99D;
                background-color: #424242;
            }
            QCheckBox::indicator:checked {
                background-color: #00A99D;
                border: 2px solid #00C2B3;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00C2B3;
            }
        """)
        
        control_layout.addWidget(self.chk_capture_signals)
        control_layout.addStretch()
        
        self.main_layout.addWidget(control_container)
        
        # 3. Contenedor de velocidad y contador con estilo moderno
        speed_counter_container = QFrame()
        speed_counter_container.setFrameShape(QFrame.StyledPanel)
        speed_counter_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 rgba(0, 169, 157, 0.2),
                                          stop: 0.5 rgba(0, 200, 170, 0.25),
                                          stop: 1 rgba(0, 169, 157, 0.2));
                border-radius: 12px;
                border: 2px solid rgba(0, 200, 170, 0.4);
                color: #FFFFFF;
                padding: 0px;
            }
        """)
        
        speed_counter_layout = QHBoxLayout(speed_counter_container)
        speed_counter_layout.setContentsMargins(10, 5, 10, 5)
        speed_counter_layout.setSpacing(20)
        
        label_style = """
            QLabel {
                font-weight: bold;
                font-size: 12px;
                border-radius: 0px;
                border: none;
                background: transparent;
                padding: 0px;
                min-height: 9px;
                max-height: 9px
            }
        """

        # Crear controles de velocidad
        speed_control_box = QVBoxLayout()
        speed_control_box.setSpacing(5)
        
        # Título para velocidad
        speed_title = QLabel("VELOCIDAD")
        speed_title.setAlignment(Qt.AlignCenter)
        speed_title.setStyleSheet(label_style)
        speed_control_box.addWidget(speed_title)
        
        # Layout horizontal para controles de velocidad
        speed_controls_row = QHBoxLayout()
        
        # Botones de velocidad con estilo moderno
        speed_button_style = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00A99D,
                                          stop: 1 #008C82);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #00A99D;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00C2B3,
                                          stop: 1 #00A99D);
                border: 2px solid #00C2B3;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #008C82,
                                          stop: 1 #006B63);
                border: 2px solid #008C82;
            }
        """
        
        self.btn_speed_minus = CustomButton('-', size=(30, 30))
        self.btn_speed_minus.setStyleSheet(speed_button_style)
        self.btn_speed_plus = CustomButton('+', size=(30, 30))
        self.btn_speed_plus.setStyleSheet(speed_button_style)
        
        self.sel_speed = Selector('Velocidad', Config.speeds, '{0:d}/min', 
                                  self.btn_speed_minus, self.btn_speed_plus, 
                                  self.update_speed, ticks=Config.speeds, parent=self)
        
        # Conectar botones de velocidad
        self.btn_speed_plus.clicked.connect(self.sel_speed.next_value)
        self.btn_speed_minus.clicked.connect(self.sel_speed.prev_value)
        
        speed_controls_row.addStretch()
        speed_controls_row.addWidget(self.sel_speed)
        speed_controls_row.addStretch()
        
        speed_control_box.addLayout(speed_controls_row)
        speed_counter_layout.addLayout(speed_control_box)
        
        # Crear contador con estilo moderno
        counter_box = QVBoxLayout()
        counter_box.setSpacing(5)
        
        # Título para contador
        counter_title = QLabel("CONTADOR")
        counter_title.setAlignment(Qt.AlignCenter)
        counter_title.setStyleSheet(label_style)
        counter_box.addWidget(counter_title)
        
        # Selector de contador
        self.sel_counter = Counter(initial_value=0, format_str='{0:d}', parent=self)
        self.sel_counter.set_value(0)
        
        counter_controls_row = QHBoxLayout()
        counter_controls_row.addStretch()
        counter_controls_row.addWidget(self.sel_counter)
        counter_controls_row.addStretch()
        
        counter_box.addLayout(counter_controls_row)
        speed_counter_layout.addLayout(counter_box)
        
        # === CRONÓMETRO (lado derecho) ===
        chronometer_box = QVBoxLayout()
        chronometer_box.setSpacing(5)

        # Título para cronómetro
        chronometer_title = QLabel("TIEMPO")
        chronometer_title.setAlignment(Qt.AlignCenter)
        chronometer_title.setStyleSheet(label_style)
        chronometer_box.addWidget(chronometer_title)

        # Widget cronómetro
        self.chronometer = Chronometer(parent=self)

        chronometer_controls_row = QHBoxLayout()
        chronometer_controls_row.addStretch()
        chronometer_controls_row.addWidget(self.chronometer)
        chronometer_controls_row.addStretch()

        chronometer_box.addLayout(chronometer_controls_row)

        # Añadir al layout principal
        speed_counter_layout.addLayout(chronometer_box)
        
        self.main_layout.addWidget(speed_counter_container)
        
        # Añadir visualizador de patrón EMDR
        self.pattern_visualizer = EMDRPatternVisualizer()
        pattern_visualizer_container = QWidget()
        pattern_visualizer_container.setStyleSheet("""
            QWidget {
                background: #101010;
                border-radius: 15px;
                border: 1px solid #444444;
            }
        """)
        pattern_visualizer_layout = QHBoxLayout(pattern_visualizer_container)
        pattern_visualizer_layout.setContentsMargins(4, 0, 4, 0)
        pattern_visualizer_layout.addWidget(self.pattern_visualizer)
        self.main_layout.addWidget(pattern_visualizer_container)
        
        # 4. Crear el widget de pestañas con estilo moderno
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                background: transparent;
                border: none;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #424242,
                                          stop: 1 #2c2c2c);
                color: #FFFFFF;
                padding: 12px 20px;
                margin-right: 2px;
                border: 2px solid #444444;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00A99D,
                                          stop: 0.5 #00C2B3,
                                          stop: 1 #00A99D);
                color: white;
                border: 2px solid #00A99D;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #555555,
                                          stop: 1 #3c3c3c);
                border: 2px solid #555555;
                border-bottom: none;
            }
            QTabBar::tab:!enabled {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #1a1a1a,
                                          stop: 1 #0a0a0a);
                color: #666666;
                border: 2px solid #222222;
                border-bottom: none;
            }
        """)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setUsesScrollButtons(False)
        
        # Configurar para expandir las pestañas por todo el ancho disponible
        self.tab_widget.tabBar().setExpanding(True)
        
        self.main_layout.addWidget(self.tab_widget)
        
        # 5. Crear contenido de pestañas
        
        # 5.1 Pestaña de Estimulación Auditiva (Auriculares) - Modernizada
        headphone_scroll = QScrollArea()
        headphone_scroll.setWidgetResizable(True)
        headphone_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        headphone_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        headphone_scroll.setFrameShape(QFrame.NoFrame)
        headphone_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #424242;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00A99D;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00C2B3;
            }
        """)

        headphone_container = QWidget()
        headphone_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                color: #FFFFFF;
            }
        """)
        headphone_layout = QVBoxLayout(headphone_container)
        headphone_layout.setContentsMargins(0, 0, 0, 0)
        headphone_layout.setSpacing(0)

        # Contenedor para controles de audio
        audio_controls = QFrame()
        audio_controls.setFrameShape(QFrame.StyledPanel)
        audio_controls.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        audio_controls_layout = QVBoxLayout(audio_controls)
        audio_controls_layout.setSpacing(1)
        audio_controls_layout.setContentsMargins(9, 5, 9, 5)

        # Switch container para auriculares con estilo moderno
        first_headphone_row = QHBoxLayout()
        self.headphone_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.headphone_switch_container.setStyleSheet("""
            QWidget {
                background: transparent;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
            }
        """)
        
        self.switch_headphone = PyQtSwitch()
        self.switch_headphone.setAnimation(True)
        self.switch_headphone.setCircleDiameter(30)
        self.switch_headphone.toggled.connect(self.update_sound)
        self.headphone_switch_container.add_switch(self.switch_headphone)
        self.switch_headphone.get_value = lambda: self.switch_headphone.isChecked()
        self.switch_headphone.set_value = lambda value: self.switch_headphone.setChecked(value)

        # Botón de prueba modernizado
        self.btn_headphone_test = CustomButton('Prueba', self.headphone_test_click)
        self.btn_headphone_test.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #FF9800,
                                          stop: 1 #F57C00);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #FF9800;
                padding: 8px 16px;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #FFB74D,
                                          stop: 1 #FF9800);
                border: 2px solid #FFB74D;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #E65100,
                                          stop: 1 #BF360C);
                border: 2px solid #E65100;
            }
        """)

        first_headphone_row.addWidget(self.headphone_switch_container)
        first_headphone_row.addStretch()
        first_headphone_row.addWidget(self.btn_headphone_test)
        
        audio_controls_layout.addLayout(first_headphone_row)
        
        # Layout para controles de volumen y tono/duración modernizados
        volume_tone_layout = QHBoxLayout()
        volume_tone_layout.setSpacing(20)

        # Controles de volumen modernizados
        volume_controls = QWidget()
        volume_controls.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        volume_layout = QVBoxLayout(volume_controls)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(1)

        # Título para volumen
        volume_title = QLabel("VOLUMEN")
        volume_title.setAlignment(Qt.AlignCenter)
        volume_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        volume_layout.addWidget(volume_title)
        
        # Botones de volumen con estilo moderno
        self.btn_headphone_volume_minus = CustomButton('-', size=(30, 30))
        self.btn_headphone_volume_minus.setStyleSheet(speed_button_style)
        self.btn_headphone_volume_plus = CustomButton('+', size=(30, 30))
        self.btn_headphone_volume_plus.setStyleSheet(speed_button_style)
        
        self.sel_headphone_volume = Selector('Volumen', Config.volumes, '{0:d}%', 
                                             self.btn_headphone_volume_minus, self.btn_headphone_volume_plus, 
                                           self.update_sound, ticks=Config.volumes, parent=self)
        
        # Conectar botones de volumen
        self.btn_headphone_volume_plus.clicked.connect(self.sel_headphone_volume.next_value)
        self.btn_headphone_volume_minus.clicked.connect(self.sel_headphone_volume.prev_value)

        # Controles de volumen con botones
        volume_controls_row = QHBoxLayout()
        volume_controls_row.addStretch()
        volume_controls_row.addWidget(self.sel_headphone_volume)
        volume_controls_row.addStretch()
        
        volume_layout.addLayout(volume_controls_row)
        volume_tone_layout.addWidget(volume_controls)

        # Controles de tono modernizados
        tone_controls = QWidget()
        tone_controls.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        tone_layout = QVBoxLayout(tone_controls)
        tone_layout.setContentsMargins(0, 0, 0, 0)
        tone_layout.setSpacing(1)

        # Título para tono
        tone_title = QLabel("TONO")
        tone_title.setAlignment(Qt.AlignCenter)
        tone_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        tone_layout.addWidget(tone_title)

        self.btn_headphone_tone_minus = CustomButton('◀', size=(30, 30))
        self.btn_headphone_tone_minus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9C27B0,
                                          stop: 1 #7B1FA2);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #9C27B0;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #BA68C8,
                                          stop: 1 #9C27B0);
                border: 2px solid #BA68C8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6A1B9A,
                                          stop: 1 #4A148C);
                border: 2px solid #6A1B9A;
            }
        """)
        self.btn_headphone_tone_plus = CustomButton('▶', size=(30, 30))
        self.btn_headphone_tone_plus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9C27B0,
                                          stop: 1 #7B1FA2);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #9C27B0;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #BA68C8,
                                          stop: 1 #9C27B0);
                border: 2px solid #BA68C8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6A1B9A,
                                          stop: 1 #4A148C);
                border: 2px solid #6A1B9A;
            }
        """)

        self.sel_headphone_tone = Selector('Tono/Duración', Config.tones, '{0}', 
                                           self.btn_headphone_tone_minus, self.btn_headphone_tone_plus, 
                                        self.update_sound, cyclic=True, ticks=range(len(Config.tones)), parent=self)
        
        # Conectar botones de tono
        self.btn_headphone_tone_plus.clicked.connect(self.sel_headphone_tone.next_value)
        self.btn_headphone_tone_minus.clicked.connect(self.sel_headphone_tone.prev_value)

        # Controles de tono con botones modernizados
        tone_controls_row = QHBoxLayout()
        tone_controls_row.addStretch()
        tone_controls_row.addWidget(self.sel_headphone_tone)
        tone_controls_row.addStretch()
        
        tone_layout.addLayout(tone_controls_row)
        volume_tone_layout.addWidget(tone_controls)

        # Añadir controles de volumen y tono al layout principal
        audio_controls_layout.addLayout(volume_tone_layout)

        # Añadir espacio al final
        headphone_layout.addWidget(audio_controls)
        headphone_layout.addStretch()
        headphone_scroll.setWidget(headphone_container)

        # 5.2 Pestaña de Estimulación Visual (Barra de Luz) - Modernizada
        lightbar_scroll = QScrollArea()
        lightbar_scroll.setWidgetResizable(True)
        lightbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lightbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lightbar_scroll.setFrameShape(QFrame.NoFrame)
        lightbar_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #424242;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00A99D;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00C2B3;
            }
        """)

        lightbar_container = QWidget()
        lightbar_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                color: #FFFFFF;
            }
        """)
        lightbar_layout = QVBoxLayout(lightbar_container)
        lightbar_layout.setContentsMargins(0, 0, 0, 0)
        lightbar_layout.setSpacing(0)

        # Título para controles de luz modernizado
        light_title = QLabel("CONTROLES DE LUZ")
        light_title.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 rgba(33, 150, 243, 0.3),
                                          stop: 0.5 rgba(63, 169, 245, 0.4),
                                          stop: 1 rgba(33, 150, 243, 0.3));
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 20px;
                border-radius: 0px;
                border: 2px solid rgba(63, 169, 245, 0.5);
            }
        """)
        light_title.setAlignment(Qt.AlignCenter)
        lightbar_layout.addWidget(light_title)

        # Contenedor para controles de luz
        light_controls = QFrame()
        light_controls.setFrameShape(QFrame.StyledPanel)
        light_controls.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        light_controls_layout = QVBoxLayout(light_controls)
        light_controls_layout.setSpacing(1)
        light_controls_layout.setContentsMargins(9, 5, 9, 5)

        # Switch container para luz con estilo moderno
        first_lightbar_row = QHBoxLayout()
        self.light_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.light_switch_container.setStyleSheet("""
            QWidget {
                background: transparent;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
            }
        """)
        
        self.switch_light = PyQtSwitch()
        self.switch_light.setAnimation(True) 
        self.switch_light.setCircleDiameter(30)
        self.switch_light.toggled.connect(self.update_light)
        self.light_switch_container.add_switch(self.switch_light)
        self.switch_light.get_value = lambda: self.switch_light.isChecked()
        self.switch_light.set_value = lambda value: self.switch_light.setChecked(value)

        # Botón de prueba de luz modernizado
        self.btn_light_test = CustomButton('Prueba', self.light_test_click, togglable=True)
        self.btn_light_test.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2196F3,
                                          stop: 1 #1976D2);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #2196F3;
                padding: 8px 16px;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #42A5F5,
                                          stop: 1 #2196F3);
                border: 2px solid #42A5F5;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #1565C0,
                                          stop: 1 #0D47A1);
                border: 2px solid #1565C0;
            }
            QPushButton:checked {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4CAF50,
                                          stop: 1 #388E3C);
                border: 2px solid #4CAF50;
            }
        """)
        
        # Botón para cambiar entre tiras LED modernizado
        self.btn_light_switch_strip = CustomButton('Cambiar', self.switch_strip_click)
        self.btn_light_switch_strip.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #673AB7,
                                          stop: 1 #512DA8);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #673AB7;
                padding: 8px 16px;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9575CD,
                                          stop: 1 #673AB7);
                border: 2px solid #9575CD;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4527A0,
                                          stop: 1 #311B92);
                border: 2px solid #4527A0;
            }
        """)

        first_lightbar_row.addWidget(self.light_switch_container)
        first_lightbar_row.addStretch()
        first_lightbar_row.addWidget(self.btn_light_test)
        first_lightbar_row.addStretch()
        first_lightbar_row.addWidget(self.btn_light_switch_strip)
        
        light_controls_layout.addLayout(first_lightbar_row)

        # Layout para controles de color e intensidad modernizados
        second_lightbar_row = QHBoxLayout()
        second_lightbar_row.setSpacing(20)

        # Controles de color modernizados
        color_controls = QWidget()
        color_controls.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        color_layout = QVBoxLayout(color_controls)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(1)

        # Título para color
        color_title = QLabel("COLOR")
        color_title.setAlignment(Qt.AlignCenter)
        color_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        color_layout.addWidget(color_title)

        # Controles de color con botones
        color_controls_row = QHBoxLayout()
        
        self.btn_light_color_minus = CustomButton('◀', size=(30, 30))
        self.btn_light_color_minus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #E91E63,
                                          stop: 1 #C2185B);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #E91E63;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #F06292,
                                          stop: 1 #E91E63);
                border: 2px solid #F06292;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #AD1457,
                                          stop: 1 #880E4F);
                border: 2px solid #AD1457;
            }
        """)
        self.btn_light_color_plus = CustomButton('▶', size=(30, 30))
        self.btn_light_color_plus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #E91E63,
                                          stop: 1 #C2185B);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #E91E63;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #F06292,
                                          stop: 1 #E91E63);
                border: 2px solid #F06292;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #AD1457,
                                          stop: 1 #880E4F);
                border: 2px solid #AD1457;
            }
        """)
        
        self.sel_light_color = Selector('Color', Config.colors, '{0}', 
                                        self.btn_light_color_minus, self.btn_light_color_plus,
                                      self.update_light, cyclic=True, ticks=range(len(Config.colors)), parent=self)
        
        # Conectar botones de color
        self.btn_light_color_plus.clicked.connect(self.sel_light_color.next_value)
        self.btn_light_color_minus.clicked.connect(self.sel_light_color.prev_value)

        color_controls_row.addStretch()
        color_controls_row.addWidget(self.sel_light_color)
        color_controls_row.addStretch()
        
        color_layout.addLayout(color_controls_row)
        second_lightbar_row.addWidget(color_controls)

        # Controles de intensidad modernizados
        intensity_controls = QWidget()
        intensity_controls.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        intensity_layout = QVBoxLayout(intensity_controls)
        intensity_layout.setContentsMargins(0, 0, 0, 0)
        intensity_layout.setSpacing(1)

        # Título para intensidad
        intensity_title = QLabel("BRILLO")
        intensity_title.setAlignment(Qt.AlignCenter)
        intensity_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        intensity_layout.addWidget(intensity_title)

        # Controles de intensidad con botones
        intensity_controls_row = QHBoxLayout()
        
        self.btn_light_intens_minus = CustomButton('-', size=(30, 30))
        self.btn_light_intens_minus.setStyleSheet(speed_button_style)
        self.btn_light_intens_plus = CustomButton('+', size=(30, 30))
        self.btn_light_intens_plus.setStyleSheet(speed_button_style)
        
        self.sel_light_intens = Selector('Brillo', Config.intensities, '{0:d}%',
                                       self.btn_light_intens_minus, self.btn_light_intens_plus, 
                                       self.update_light, ticks=Config.intensities, parent=self)
        
        # Conectar botones de intensidad
        self.btn_light_intens_plus.clicked.connect(self.sel_light_intens.next_value)
        self.btn_light_intens_minus.clicked.connect(self.sel_light_intens.prev_value)

        intensity_controls_row.addStretch()
        intensity_controls_row.addWidget(self.sel_light_intens)
        intensity_controls_row.addStretch()
        
        intensity_layout.addLayout(intensity_controls_row)
        second_lightbar_row.addWidget(intensity_controls)

        # Añadir controles de color e intensidad al layout principal
        light_controls_layout.addLayout(second_lightbar_row)
        
        # Añadir espacio al final
        lightbar_layout.addWidget(light_controls)
        lightbar_layout.addStretch()
        lightbar_scroll.setWidget(lightbar_container)
        
        # 5.3 Pestaña de Estimulación Táctil (Buzzer) - Modernizada
        buzzer_scroll = QScrollArea()
        buzzer_scroll.setWidgetResizable(True)
        buzzer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        buzzer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        buzzer_scroll.setFrameShape(QFrame.NoFrame)
        buzzer_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #424242;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00A99D;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00C2B3;
            }
        """)

        buzzer_container = QWidget()
        buzzer_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                color: #FFFFFF;
            }
        """)
        buzzer_layout = QVBoxLayout(buzzer_container)
        buzzer_layout.setContentsMargins(0, 0, 0, 0)
        buzzer_layout.setSpacing(0)

        # Título para controles de vibración modernizado
        buzzer_title = QLabel("CONTROLES DE VIBRACIÓN")
        buzzer_title.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 rgba(156, 39, 176, 0.3),
                                          stop: 0.5 rgba(186, 104, 200, 0.4),
                                          stop: 1 rgba(156, 39, 176, 0.3));
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 20px;
                border-radius: 0px;
                border: 2px solid rgba(186, 104, 200, 0.5);
            }
        """)
        buzzer_title.setAlignment(Qt.AlignCenter)
        buzzer_layout.addWidget(buzzer_title)

        # Contenedor para controles de vibración
        buzzer_controls = QFrame()
        buzzer_controls.setFrameShape(QFrame.StyledPanel)
        buzzer_controls.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        buzzer_controls_layout = QVBoxLayout(buzzer_controls)
        buzzer_controls_layout.setSpacing(1)
        buzzer_controls_layout.setContentsMargins(9, 5, 9, 5)

        # Switch container para buzzer con estilo moderno
        first_buzzer_row = QHBoxLayout()
        self.buzzer_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.buzzer_switch_container.setStyleSheet("""
            QWidget {
                background: transparent;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
            }
        """)
        
        self.switch_buzzer = PyQtSwitch()
        self.switch_buzzer.setAnimation(True)
        self.switch_buzzer.setCircleDiameter(30)
        self.switch_buzzer.toggled.connect(self.update_buzzer)
        self.buzzer_switch_container.add_switch(self.switch_buzzer)
        self.switch_buzzer.get_value = lambda: self.switch_buzzer.isChecked()
        self.switch_buzzer.set_value = lambda value: self.switch_buzzer.setChecked(value)

        # Botón de prueba de buzzer modernizado
        self.btn_buzzer_test = CustomButton('Prueba', self.buzzer_test_click)
        self.btn_buzzer_test.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9C27B0,
                                          stop: 1 #7B1FA2);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #9C27B0;
                padding: 8px 16px;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #BA68C8,
                                          stop: 1 #9C27B0);
                border: 2px solid #BA68C8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6A1B9A,
                                          stop: 1 #4A148C);
                border: 2px solid #6A1B9A;
            }
        """)

        first_buzzer_row.addWidget(self.buzzer_switch_container)
        first_buzzer_row.addStretch()
        first_buzzer_row.addWidget(self.btn_buzzer_test)
        
        buzzer_controls_layout.addLayout(first_buzzer_row)
        
        # Layout para controles de duración modernizados
        second_buzzer_row = QHBoxLayout()
        second_buzzer_row.setSpacing(20)

        # Controles de duración modernizados
        duration_controls = QWidget()
        duration_controls.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        duration_layout = QVBoxLayout(duration_controls)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(1)

        # Título para duración
        duration_title = QLabel("DURACIÓN")
        duration_title.setAlignment(Qt.AlignCenter)
        duration_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        duration_layout.addWidget(duration_title)

        # Controles de duración con botones modernizados
        duration_controls_row = QHBoxLayout()
        
        self.btn_buzzer_duration_minus = CustomButton('-', size=(30, 30))
        self.btn_buzzer_duration_minus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9C27B0,
                                          stop: 1 #7B1FA2);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #9C27B0;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #BA68C8,
                                          stop: 1 #9C27B0);
                border: 2px solid #BA68C8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6A1B9A,
                                          stop: 1 #4A148C);
                border: 2px solid #6A1B9A;
            }
        """)
        self.btn_buzzer_duration_plus = CustomButton('+', size=(30, 30))
        self.btn_buzzer_duration_plus.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9C27B0,
                                          stop: 1 #7B1FA2);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #9C27B0;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #BA68C8,
                                          stop: 1 #9C27B0);
                border: 2px solid #BA68C8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6A1B9A,
                                          stop: 1 #4A148C);
                border: 2px solid #6A1B9A;
            }
        """)
        
        self.sel_buzzer_duration = Selector('Duración', Config.durations, '{0:d} ms', 
                                          self.btn_buzzer_duration_minus, self.btn_buzzer_duration_plus, 
                                          self.update_buzzer, ticks=Config.durations, parent=self)

        # Conectar botones de duración
        self.btn_buzzer_duration_plus.clicked.connect(self.sel_buzzer_duration.next_value)
        self.btn_buzzer_duration_minus.clicked.connect(self.sel_buzzer_duration.prev_value)

        duration_controls_row.addStretch()
        duration_controls_row.addWidget(self.sel_buzzer_duration)
        duration_controls_row.addStretch()
        
        duration_layout.addLayout(duration_controls_row)
        second_buzzer_row.addWidget(duration_controls)

        # Añadir controles de duración al layout principal
        buzzer_controls_layout.addLayout(second_buzzer_row)
        
        # Añadir espacio al final
        buzzer_layout.addWidget(buzzer_controls)
        buzzer_layout.addStretch()
        buzzer_scroll.setWidget(buzzer_container)

        # Añadir las pestañas al TabWidget con iconos sofisticados
        headphone_icon = qta.icon('fa5s.headphones', color='white')
        light_icon = qta.icon('fa6s.eye', color='white')
        buzzer_icon = qta.icon('fa6s.hand', color='white')

        self.tab_widget.addTab(headphone_scroll, headphone_icon, "Estimulación Auditiva")
        self.tab_widget.addTab(lightbar_scroll, light_icon, "Estimulación Visual")
        self.tab_widget.addTab(buzzer_scroll, buzzer_icon, "Estimulación Táctil")
        
        # Deshabilitar pestañas inicialmente hasta verificar conexiones
        # Excepto la auditiva que siempre está disponible
        self.tab_widget.setTabEnabled(0, True)  # Auditiva siempre disponible
        self.tab_widget.setTabEnabled(1, False)  # Visual deshabilitado hasta verificar
        self.tab_widget.setTabEnabled(2, False)  # Táctil deshabilitado hasta verificar
        
        # Para mantener la compatibilidad con el código existente
        self.areas = {'headphone': 0, 'lightbar': 1, 'buzzer': 2}
        
        # Eliminar la inicialización automática del timer de USB
        self.probe_timer = QTimer(self)
        self.probe_timer.timeout.connect(self.scan_usb)
        
        # Conectar ACTION_EVENT con su manejador
        event_system.action_event.connect(self.action)
        event_system.action_event.connect(self.update_visualizer)
        
        # Inicializar pero sin verificar USB
        self.config_mode()
        self.reset_action()
        
        # Verificar dispositivos al iniciar
        # QTimer.singleShot(500, self.scan_usb)
    
    def activate(self, elem):
        """Activa un elemento de la UI"""
        if not elem.active:
            elem.setActive(True)
    
    def deactivate(self, elem):
        """Desactiva un elemento de la UI"""
        if elem.active:
            elem.setActive(False)
    
    def light_test_click(self):
        """Prueba la luz"""
        self.update_light()
    
    def buzzer_test_click(self):
        """Prueba el buzzer"""
        self.update_buzzer()
        Devices.do_buzzer(True)
        time.sleep(1 + self.sel_buzzer_duration.get_value() / 1000)
        Devices.do_buzzer(False)
    
    def headphone_test_click(self):
        """Prueba el sonido de auriculares"""
        self.update_sound()
        Devices.do_sound(True)
        time.sleep(1)
        Devices.do_sound(False)
    
    def update_light(self):
        """Actualiza la configuración de la luz"""
        (color_name, r, g, b) = self.sel_light_color.get_value()
        intensity = self.sel_light_intens.get_value() / 100 * 0.7  # max. 70% intensity
        r = round(r * intensity)
        g = round(g * intensity)
        b = round(b * intensity)
        color = r * 256 * 256 + g * 256 + b
        Devices.set_color(color)
        if self.btn_light_test.isChecked():
            Devices.set_led(-1)
        else:
            Devices.set_led(Devices.led_num / 2 + 1 if self.switch_light.get_value() else 0)
        # self.save_config()
    
    def update_buzzer(self):
        """Actualiza la configuración del buzzer"""
        duration = self.sel_buzzer_duration.get_value()
        Devices.set_buzzer_duration(duration // 10)
        # self.save_config()
    
    def update_sound(self):
        """Actualiza la configuración de sonido"""
        tone_data = self.sel_headphone_tone.get_value()
        volume = self.sel_headphone_volume.get_value() / 100
        Devices.set_tone(tone_data, volume) # El nuevo método maneja tanto WAV como tonos generados
        # El nuevo método set_tone maneja tanto WAV como tonos generados
        Devices.set_tone(tone_data, volume)
        
        print(f"Actualizando sonido: Tono={tone_data[0] if tone_data else 'None'}, "
              f"Volumen={volume}")
        
        # self.save_config()
    
    def update_speed(self):
        """Actualiza la velocidad"""
        if self.mode == 'action':
            self.adjust_action_timer()
        # self.save_config()
    
    def switch_strip_click(self):
        """Cambia a la siguiente tira LED"""
        Devices.switch_to_next_strip()
        # Actualizar LED actual después de cambiar de tira
        if self.switch_light.get_value():
            Devices.set_led(self.led_pos)

    def set_area(self, area):
        """Cambia el área visible"""
        if area != 'speed' and area in self.areas:
            # Cambiar a la pestaña correspondiente
            self.tab_widget.setCurrentIndex(self.areas[area])
        
        # Manejar prueba de luz
        if area != 'lightbar' and self.btn_light_test.isChecked():
            self.btn_light_test.setChecked(False)
            self.light_test_click()
    
    def load_config(self):
        """Carga la configuración desde archivo"""
        try:
            self.in_load = True
            Config.load()
            self.sel_speed.set_value(Config.data.get('general.speed'))
            self.switch_light.set_value(True)
            self.sel_light_color.set_value(Config.data.get('lightbar.color'))
            self.sel_light_intens.set_value(Config.data.get('lightbar.intensity'))
            self.switch_buzzer.set_value(True)
            self.sel_buzzer_duration.set_value(Config.data.get('buzzer.duration'))
            self.switch_headphone.set_value(True)
            
            # Cargar tono guardado o usar el primero disponible
            saved_tone = Config.data.get('headphone.tone')
            if saved_tone and saved_tone in Config.tones:
                self.sel_headphone_tone.set_value(saved_tone)
            elif Config.tones:
                self.sel_headphone_tone.set_value(Config.tones[0])
                Config.data['headphone.tone'] = Config.tones[0]
            
            self.sel_headphone_volume.set_value(Config.data.get('headphone.volume'))
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            # No fallar con archivo de configuración corrupto
            if Config.tones:
                self.sel_headphone_tone.set_value(Config.tones[0])
        
        self.in_load = False
    
    def save_config(self):
        """Guarda la configuración en archivo"""
        if not self.in_load:
            Config.data['general.speed'] = self.sel_speed.get_value()
            Config.data['lightbar.on'] = self.switch_light.get_value()
            Config.data['lightbar.color'] = self.sel_light_color.get_value()
            Config.data['lightbar.intensity'] = self.sel_light_intens.get_value()
            Config.data['buzzer.on'] = self.switch_buzzer.get_value()
            Config.data['buzzer.duration'] = self.sel_buzzer_duration.get_value()
            Config.data['headphone.on'] = self.switch_headphone.get_value()
            Config.data['headphone.tone'] = self.sel_headphone_tone.get_value()
            Config.data['headphone.volume'] = self.sel_headphone_volume.get_value()
            Config.save()
    
    def config_mode(self):
        """Cambia al modo de configuración"""
        self.mode = 'config'
        
        # Habilitar/deshabilitar botones
        if not self.btn_pause.isChecked():
            self.activate(self.btn_start)
            self.activate(self.btn_start24)
            self.deactivate(self.btn_stop)
            self.deactivate(self.btn_pause)
    
    def post_action(self):
        """Publica un evento de acción"""
        if self.mode == 'action':
            timer = HighPerfTimer(self.action_delay + self.action_extra_delay, self.post_action)
            # Reemplazar pygame.event.post con la señal de PySide6
            event_system.action_event.emit()
            timer.start()
    
    def adjust_action_timer(self):
        """Ajusta el temporizador de acción basado en la velocidad"""
        self.action_delay = (Devices.led_num / self.sel_speed.get_value() / Devices.led_num / 2)
        self.action_extra_delay = 0
    
    def action_mode(self):
        """Cambia al modo de acción"""
        # Verificar si podemos adquirir los dispositivos
        if self.mode == 'action':
            return
        self.mode = 'action'
        if not self.pausing:
            self.sel_counter.set_value(0)
            self.chronometer.reset()  # Reiniciar cronómetro
    
        # Iniciar cronómetro
        self.chronometer.start()
        
        self.stopping = False
        self.pausing = False
        
        # Detener temporizador de sondeo
        self.probe_timer.stop()
        
        # Preparar dispositivos
        self.update_light()
        self.update_buzzer()
        self.update_sound()
        
        # Iniciar captura de señales si el checkbox está marcado
        if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
            # Buscar el sensor_monitor a través de la ventana principal
            main_window = self.window()
            if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                if not main_window.sensor_monitor.running:
                    main_window.sensor_monitor.start_acquisition()
        
        # Iniciar temporizador de acción
        self.adjust_action_timer()
        HighPerfTimer(self.action_delay, self.post_action).start()
        
        # Habilitar/deshabilitar botones
        self.deactivate(self.btn_start)
        self.deactivate(self.btn_start24)
        self.activate(self.btn_stop)
        self.activate(self.btn_pause)

    def start_click(self):
        """Maneja clic en el botón Start (Play)"""
        self.max_counter = 0
        self.reset_action()
        self.action_mode()

    def start24_click(self):
        """Maneja clic en el botón Start24 (Play24)"""
        self.max_counter = 24
        self.reset_action()
        self.action_mode()

    def stop_click(self):
        """Maneja clic en el botón Stop"""
        if self.btn_pause.isChecked():
            self.btn_pause.setChecked(False)
        if self.mode == 'action':
            self.stopping = True
            
            # Detener cronómetro
            self.chronometer.stop()
            
            # Detener captura de señales si el checkbox está marcado
            if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
                main_window = self.window()
                if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                    if main_window.sensor_monitor.running:
                        main_window.sensor_monitor.stop_acquisition()
        else:
            self.config_mode()
            self.reset_action()
            # Reiniciar cronómetro cuando se para en modo config
            self.chronometer.reset()

    def pause_click(self):
        """Maneja clic en el botón Pause"""
        if self.btn_pause.isChecked():
            # pause
            self.pausing = True
            
            # Pausar cronómetro
            self.chronometer.pause()
            
            # Detener captura de señales si el checkbox está marcado
            if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
                main_window = self.window()
                if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                    if main_window.sensor_monitor.running:
                        main_window.sensor_monitor.stop_acquisition()
        else:
            # resume
            if self.mode != 'action':
                self.action_mode()
            else:
                self.pausing = False
                self.action_extra_delay = 0
                self.decay = False
                
                # Reanudar cronómetro
                self.chronometer.resume()
                
                # Reanudar captura de señales si el checkbox está marcado y estábamos en pausa
                if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
                    main_window = self.window()
                    if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                        if not main_window.sensor_monitor.running:
                            main_window.sensor_monitor.start_acquisition()

    def reset_action(self):
        """Reinicia la acción EMDR"""
        print('reset_action')
        self.led_pos = int(Devices.led_num / 2) + 1  # start in the middle
        self.direction = -1
        self.decay = False
        Devices.set_led(self.led_pos if self.switch_light.get_value() else 0)
    
    def action(self):
        """Maneja un paso en la secuencia EMDR"""
        if self.mode != 'action':
            return
        
        if self.switch_light.get_value():
            Devices.set_led(self.led_pos)
        
        # Obtener el valor actual del contador
        cntr = self.sel_counter.get_value()
        
        if self.led_pos == 1:
            # left end
            if self.switch_buzzer.get_value():
                Devices.do_buzzer(True)
            if self.switch_headphone.get_value():
                Devices.do_sound(True)
            if self.direction == -1:
                self.direction = 1
        if self.led_pos == Devices.led_num:
            # right end
            if self.switch_buzzer.get_value():
                Devices.do_buzzer(False)
            if self.switch_headphone.get_value():
                Devices.do_sound(False)
            if self.direction == 1:
                self.direction = -1
            if cntr == self.max_counter or self.stopping or self.pausing:
                self.decay = True
        if self.led_pos == int(Devices.led_num / 2) + 1 and self.direction == -1:
            # in the middle
            if self.decay:
                self.config_mode()
                
                # Detener cronómetro al finalizar la sesión
                self.chronometer.stop()
                
                self.reset_action()
                
                # Detener captura de señales si el checkbox está marcado
                if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
                    main_window = self.window()
                    if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                        if main_window.sensor_monitor.running:
                            main_window.sensor_monitor.stop_acquisition()
            
                return
            else:
                cntr += 1
            self.sel_counter.set_value(cntr)
        self.led_pos += self.direction
    
        # Decaimiento: calcular nuevo retraso basado en la posición
        if self.decay:
            middle = int(Devices.led_num / 2) + 1
            n = Devices.led_num - middle
            pos = Devices.led_num - self.led_pos
            alpha = log(1.2) / (log(n) - log(n - 1))
            factor = 1.5 / n ** alpha
            self.action_extra_delay = self.action_delay + factor * pos ** alpha

    def check_slave_connections(self):
        """Método base que contiene la lógica común para verificar conexiones de dispositivos"""
        # Realizar el escaneo y obtener los dispositivos encontrados
        found_devices = Devices.probe()
        
        # Actualizar el estado de las pestañas según los dispositivos encontrados
        if "Master Controller" in found_devices:
            # Verificar lightbar
            lightbar_connected = "Lightbar" in found_devices
            
            # Tab visual (índice 1) debe estar habilitada solo si hay lightbar
            self.tab_widget.setTabEnabled(1, lightbar_connected)
            
            # Verificar buzzer
            buzzer_connected = "Buzzer" in found_devices
            
            # Tab táctil (índice 2) debe estar habilitada solo si hay buzzer
            self.tab_widget.setTabEnabled(2, buzzer_connected)
            
            # La estimulación auditiva siempre está disponible (independientemente de conexiones)
            self.tab_widget.setTabEnabled(0, True)
                
            # Siempre activar los botones de inicio si existe el controlador maestro
            if self.mode == 'config':
                self.activate(self.btn_start)
                self.activate(self.btn_start24)
        else:
            # No hay controlador maestro
            self.deactivate(self.btn_start)
            self.deactivate(self.btn_start24)
            
            # La estimulación auditiva siempre está disponible (incluso sin controlador)
            self.tab_widget.setTabEnabled(0, True)
            
            # Desactivar solo las pestañas específicas que requieren hardware
            self.tab_widget.setTabEnabled(1, False)  # Visual - requiere lightbar
            self.tab_widget.setTabEnabled(2, False)  # Táctil - requiere buzzer
        
        # Actualizar la etiqueta de estado de dispositivos
        self.update_device_status_label(found_devices)
        
        # Asegurar que la pestaña actual está habilitada, o cambiar a Estimulación Auditiva si no
        current_index = self.tab_widget.currentIndex()
        if not self.tab_widget.isTabEnabled(current_index):
            # Si la pestaña actual está deshabilitada, cambiar a Estimulación Auditiva (índice 0)
            self.tab_widget.setCurrentIndex(0)
        
        return found_devices

    def update_device_status_label(self, found_devices):
        """Actualiza la etiqueta de estado de dispositivos con estilo moderno"""
        if not found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                              stop: 0 rgba(244, 67, 54, 0.2),
                                              stop: 0.5 rgba(255, 87, 34, 0.25),
                                              stop: 1 rgba(244, 67, 54, 0.2));
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 2px solid rgba(244, 67, 54, 0.4);
                    margin: 5px;
                }
            """)
            return
            
        if "Master Controller" not in found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                              stop: 0 rgba(244, 67, 54, 0.2),
                                              stop: 0.5 rgba(255, 87, 34, 0.25),
                                              stop: 1 rgba(244, 67, 54, 0.2));
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 2px solid rgba(244, 67, 54, 0.4);
                    margin: 5px;
                }
            """)
            return
        
        # Crear texto de estado para cada tipo de dispositivo conocido
        status_text = "Estado de dispositivos: "
        
        # Comprobar cada tipo de dispositivo en KNOWN_SLAVES
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            # Tratar el sensor como no requerido para esta interfaz
            if name == "Sensor":
                required = False
                
            is_connected = name in found_devices
            status = "✅" if is_connected else "❌"
            status_text += f"{name}: {status} | "
        
        # Añadir también el controlador maestro
        status_text += "Master Controller: ✅"
        
        # Actualizar el texto de la etiqueta
        self.device_status_label.setText(status_text)
        
        # Verificar si todos los dispositivos requeridos están conectados
        required_connected = all(
            name in found_devices
            for slave_id, (name, required) in KNOWN_SLAVES.items()
            if required and name != "Sensor"
        )
        
        # Cambiar el color de fondo según el estado de conexión
        if required_connected:
            self.device_status_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                              stop: 0 rgba(76, 175, 80, 0.2),
                                              stop: 0.5 rgba(129, 199, 132, 0.25),
                                              stop: 1 rgba(76, 175, 80, 0.2));
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 2px solid rgba(76, 175, 80, 0.4);
                    margin: 5px;
                }
            """)
        else:
            self.device_status_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                              stop: 0 rgba(255, 193, 7, 0.2),
                                              stop: 0.5 rgba(255, 213, 79, 0.25),
                                              stop: 1 rgba(255, 193, 7, 0.2));
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 2px solid rgba(255, 193, 7, 0.4);
                    margin: 5px;
                }
            """)

    def scan_usb(self):
        """Verifica los dispositivos USB conectados automáticamente (reemplaza a check_usb)"""
        # No ejecutar durante una acción EMDR
        if self.mode == 'action':
            return
            
        # Usar el método común y actualizar la interfaz
        self.check_slave_connections()

    def scan_usb_click(self):
        """Maneja el clic en el botón de escaneo USB y muestra dispositivos conectados"""
        # Cambiar texto del botón durante el escaneo
        self.btn_scan_usb.setText("Scanning...")
        self.btn_scan_usb.setEnabled(False)
        QApplication.processEvents()  # Forzar actualización de la interfaz
        
        # Realizar el escaneo usando el método común
        found_devices = self.check_slave_connections()
        
        # Re-habilitar el botón (pero NO cambiar su texto)
        self.btn_scan_usb.setEnabled(True)
        self.btn_scan_usb.setText("Escanear")
        
        # Mostrar estado de conexión en la consola
        if found_devices:
            print("Connected devices:")
            for device in found_devices:
                print(f"- {device}")
            
            # Si hay lightbar, inicializar con LED central
            if "Lightbar" in found_devices:
                Devices.set_led(Devices.led_num // 2 + 1)
    
    def closeEvent(self):
        """Maneja el evento de cierre de la ventana"""
        print("Cerrando aplicación y limpiando recursos...")
        
        # Detener cualquier acción EMDR en progreso
        if self.mode == 'action':
            self.stopping = True
            self.config_mode()
        
        # Apagar todos los dispositivos de estimulación
        Devices.set_led(0)  # Apagar todos los LEDs
        
        # Guardar la configuración actual
        self.save_config()

    def update_visualizer(self):
        """Actualiza el visualizador de patrón EMDR"""
        if hasattr(self, 'pattern_visualizer') and hasattr(self, 'led_pos'):
            self.pattern_visualizer.update_led_position(self.led_pos)


# Esta sección del código se mantiene para permitir ejecutar el archivo independientemente
if __name__ == "__main__":
    """Función principal que inicializa y ejecuta la aplicación EMDR Controller"""
    # Crear la aplicación Qt
    app = QApplication([])
    
    # Configurar estilo global de la aplicación
    app.setStyleSheet("""
        QMainWindow {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #323232,
                                          stop: 0.3 #2c2c2c,
                                          stop: 0.6 #252525,
                                          stop: 0.8 #1a1a1a,
                                          stop: 1 #000000);
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    
    # Crear una ventana principal que contendrá el widget
    main_window = QMainWindow()
    main_window.setWindowTitle("Controlador EMDR")
    
    # Crear el widget del controlador para modo independiente
    controller_widget = EMDRControllerWidget(parent=main_window)
    main_window.setCentralWidget(controller_widget)
    
    # Inicializar controlador
    controller_widget.load_config()
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Antes de salir, guardar configuración
    app.aboutToQuit.connect(controller_widget.closeEvent)
    
    sys.exit(app.exec())