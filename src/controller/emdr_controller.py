import sys
from numpy import log
import time
import os

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication, QTabWidget, 
    QPushButton, QLabel, QSpacerItem, QSizePolicy, QFrame, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QColor, QBrush, QPen

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
# Importaciones de componentes de vistas
from src.views.components.containers import Container, SwitchContainer
from src.views.components.selectors import Selector
from src.views.components.buttons import CustomButton, Switch
from src.views.components.pyqtSwitch import PyQtSwitch

# Importaciones de modelos
from src.models.devices import Devices, KNOWN_SLAVES
from src.models.config import Config

# Importaciones de utilidades
from src.utils.hiperf_timer import HighPerfTimer
from src.utils.events import event_system


class CollapsibleSection(QWidget):
    """Sección colapsable para agrupar controles relacionados"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #C0C0C0;
                border-radius: 4px;
                background-color: #F8F9FA;
            }
            QPushButton {
                text-align: left;
                padding: 5px;
                background-color: #E3F2FD;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
            QPushButton:pressed {
                background-color: #90CAF9;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Botón de título (header)
        self.title = title
        self.toggle_button = QPushButton(f" ▼  {self.title}")
        self.toggle_button.clicked.connect(self.toggle_content)
        self.main_layout.addWidget(self.toggle_button)
        
        # Contenedor para el contenido
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.content_frame)
        
        self.is_collapsed = False
    
    def toggle_content(self):
        """Alterna entre mostrar/ocultar el contenido"""
        self.is_collapsed = not self.is_collapsed
        self.content_frame.setVisible(not self.is_collapsed)
        
        # Actualizar el ícono
        icon = "▶" if self.is_collapsed else "▼"

        title = self.title #self.toggle_button.text().split(" ", 1)[1]
        self.toggle_button.setText(f" {icon}  {title}")
    
    def add_widget(self, widget):
        """Añade un widget al contenido"""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Añade un layout al contenido"""
        self.content_layout.addLayout(layout)


# Agregar esta clase antes de EMDRControllerWidget

class EMDRPatternVisualizer(QWidget):
    """Widget para visualizar el patrón actual de movimiento EMDR"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.led_count = Devices.led_num
        self.current_led = self.led_count // 2 + 1
        self.setMinimumHeight(50)
        self.setMaximumHeight(50)
        self.dots = []
        
        # Crear los dots (representación de LEDs)
        for i in range(self.led_count):
            self.dots.append(False)  # Todos apagados inicialmente
        
        # Establecer el estilo
        self.setStyleSheet("""
            background-color: #282828;
            border-radius: 10px;
            margin: 5px;
        """)
    
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
        
        # Dibujar el fondo
        painter.fillRect(self.rect(), QColor("#282828"))
        
        # Dibujar los LEDs
        width = self.width()
        height = self.height()
        
        dot_radius = min(height * 0.3, width / (self.led_count * 2))
        center_y = height / 2
        
        # Calcular espaciado entre LEDs
        dot_spacing = (width - (2 * dot_radius * self.led_count)) / (self.led_count + 1)
        
        for i in range(self.led_count):
            center_x = dot_spacing * (i + 1) + dot_radius * (2 * i + 1)
            
            # Dibujar el círculo
            if self.dots[i]:
                # LED activo: color brillante
                painter.setBrush(QBrush(QColor("#00FF00")))
            else:
                # LED inactivo: color apagado
                painter.setBrush(QBrush(QColor("#303030")))
            
            painter.setPen(QPen(QColor("#505050"), 1))
            painter.drawEllipse(center_x - dot_radius, center_y - dot_radius, 
                              dot_radius * 2, dot_radius * 2)


class EMDRControllerWidget(QWidget):
    """Controlador principal de la aplicación EMDR convertido a widget PySide6"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.in_load = False
        self.pausing = False
        self.stopping = False
        
        # Layout principal vertical
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        
        # 1. Etiqueta de estado de dispositivos en la parte superior
        self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
        self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
        self.main_layout.addWidget(self.device_status_label)
        
        # 2. Layout para botones principales (reemplazando QGridLayout)
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.setSpacing(2)
        
        # Crear botones principales
        self.btn_start = CustomButton(0, 0, 'Play', self.start_click)
        self.btn_start24 = CustomButton(1, 0, 'Play24', self.start24_click)
        self.btn_stop = CustomButton(2, 0, 'Stop', self.stop_click)
        self.btn_pause = CustomButton(3, 0, 'Pause', self.pause_click, togglable=True)
        
        # Crear layout horizontal para la primera fila de botones
        top_button_row = QHBoxLayout()
        top_button_row.addWidget(self.btn_start)
        top_button_row.addWidget(self.btn_start24)
        top_button_row.addWidget(self.btn_stop)
        top_button_row.addWidget(self.btn_pause)
        
        # Añadir checkbox para capturar señales
        self.chk_capture_signals = QCheckBox("¿Capturar señales?")
        self.chk_capture_signals.setStyleSheet("""
            QCheckBox {
                margin-top: 5px;
                font-weight: bold;
                color: #1565C0;
            }
        """)
        capture_checkbox_row = QHBoxLayout()
        capture_checkbox_row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        capture_checkbox_row.addWidget(self.chk_capture_signals)
        capture_checkbox_row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Crear el botón Escanear en su propia fila
        self.btn_scan_usb = CustomButton(4, 0, 'Escanear', self.scan_usb_click)
        scan_button_row = QHBoxLayout()
        scan_button_row.addWidget(self.btn_scan_usb)
        
        # Añadir todas las filas al layout de botones
        button_layout.addLayout(top_button_row)
        button_layout.addLayout(capture_checkbox_row)
        button_layout.addLayout(scan_button_row)
        
        # Añadir el contenedor de botones al layout principal
        self.main_layout.addWidget(button_container)
        
        # 3. Crear widget de velocidad (siempre visible)
        speed_container = QWidget()
        speed_layout = QVBoxLayout(speed_container)
        
        # Crear el selector de contador
        self.sel_counter = Selector(1, 0, 'Contador', None, '{0:d}', None, None, show_slider=False, parent=self)
        self.sel_counter.set_value(0)
        
        # Layout para el contador
        counter_row = QHBoxLayout()
        counter_row.addStretch()
        counter_row.addWidget(self.sel_counter)
        counter_row.addStretch()
        speed_layout.addLayout(counter_row)
        
        # Crear layout para controles de velocidad
        speed_control_row = QHBoxLayout()
        
        # Botones de velocidad
        self.btn_speed_minus = CustomButton(0, 1, '-', size=(30, 30))
        self.sel_speed = Selector(1, 1, 'Velocidad', Config.speeds, '{0:d}/min', None, None, self.update_speed, parent=self)
        self.btn_speed_plus = CustomButton(2, 1, '+', size=(30, 30))
        
        # Conectar botones de velocidad
        self.btn_speed_plus.clicked.connect(self.sel_speed.next_value)
        self.btn_speed_minus.clicked.connect(self.sel_speed.prev_value)
        
        # Añadir controles de velocidad al layout
        speed_control_row.addStretch()
        speed_control_row.addWidget(self.btn_speed_minus)
        speed_control_row.addWidget(self.sel_speed)
        speed_control_row.addWidget(self.btn_speed_plus)
        speed_control_row.addStretch()
        
        speed_layout.addLayout(speed_control_row)

        # Añadir visualizador de patrón EMDR
        self.pattern_visualizer = EMDRPatternVisualizer()
        speed_layout.addWidget(self.pattern_visualizer)

        self.main_layout.addWidget(speed_container)
        
        # 4. Crear el widget de pestañas
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                background-color: white; 
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px;
                /* Eliminar min-width para permitir que el ancho sea flexible */
            }
            QTabBar::tab:selected {
                background-color: white;
                font-weight: bold;
            }
            QTabBar::tab:!enabled {
                color: #a0a0a0;
                background-color: #f0f0f0;
            }
        """)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setUsesScrollButtons(False)  # No mostrar botones de scroll
        
        # Configurar para expandir las pestañas por todo el ancho disponible
        self.tab_widget.tabBar().setExpanding(True)  # Esta es la línea clave
        
        self.main_layout.addWidget(self.tab_widget)
        
        # 5. Crear contenido de pestañas
        
        # 5.1 Pestaña de Estimulación Auditiva (Auriculares)
        headphone_scroll = QScrollArea()
        headphone_scroll.setWidgetResizable(True)
        headphone_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        headphone_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        headphone_scroll.setFrameShape(QFrame.NoFrame)

        headphone_container = QWidget()
        headphone_layout = QVBoxLayout(headphone_container)
        headphone_layout.setContentsMargins(5, 5, 5, 5)

        # Sección colapsable para controles principales
        audio_main_section = CollapsibleSection("CONTROLES DE AUDIO")

        # Layout para los controles de audio
        audio_controls = QWidget()
        audio_controls_layout = QVBoxLayout(audio_controls)

        # Switch container para auriculares
        control_row = QHBoxLayout()
        self.headphone_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_headphone = PyQtSwitch()
        self.switch_headphone.setAnimation(True)
        self.switch_headphone.setCircleDiameter(30)
        self.switch_headphone.toggled.connect(self.update_sound)
        self.headphone_switch_container.add_switch(self.switch_headphone)
        self.switch_headphone.get_value = lambda: self.switch_headphone.isChecked()
        self.switch_headphone.set_value = lambda value: self.switch_headphone.setChecked(value)
        # self.switch_headphone.set_value(True)

        # Botón de prueba
        self.btn_headphone_test = CustomButton(2, 0, 'Prueba', self.headphone_test_click)

        control_row.addWidget(self.headphone_switch_container)
        control_row.addStretch()
        control_row.addWidget(self.btn_headphone_test)
        audio_controls_layout.addLayout(control_row)

        # Añadir controles a la sección
        audio_main_section.add_widget(audio_controls)

        # Sección colapsable para volumen
        audio_volume_section = CollapsibleSection("VOLUMEN")

        # Controles de volumen
        volume_controls = QWidget()
        volume_layout = QHBoxLayout(volume_controls)
        volume_layout.setContentsMargins(5, 5, 5, 5)

        self.btn_headphone_volume_minus = CustomButton(0, 1, '-', size=(75, 75))
        self.sel_headphone_volume = Selector(1, 1, 'Volumen', Config.volumes, '{0:d}%', None, None, self.update_sound, parent=self)
        self.btn_headphone_volume_plus = CustomButton(2, 1, '+', size=(75, 75))

        # Conectar botones de volumen
        self.btn_headphone_volume_plus.clicked.connect(self.sel_headphone_volume.next_value)
        self.btn_headphone_volume_minus.clicked.connect(self.sel_headphone_volume.prev_value)

        volume_layout.addStretch()
        volume_layout.addWidget(self.btn_headphone_volume_minus)
        volume_layout.addWidget(self.sel_headphone_volume)
        volume_layout.addWidget(self.btn_headphone_volume_plus)
        volume_layout.addStretch()

        audio_volume_section.add_widget(volume_controls)

        # Sección colapsable para tono
        audio_tone_section = CollapsibleSection("TONO/DURACIÓN")

        # Controles de tono
        tone_controls = QWidget()
        tone_layout = QHBoxLayout(tone_controls)
        tone_layout.setContentsMargins(5, 5, 5, 5)

        self.btn_headphone_tone_minus = CustomButton(0, 2, '<<', size=(75, 75))
        self.sel_headphone_tone = Selector(1, 2, 'Tono/Duración', Config.tones, '{0}', None, None, 
                                        self.update_sound, cyclic=True, parent=self)
        self.btn_headphone_tone_plus = CustomButton(2, 2, '>>', size=(75, 75))

        # Conectar botones de tono
        self.btn_headphone_tone_plus.clicked.connect(self.sel_headphone_tone.next_value)
        self.btn_headphone_tone_minus.clicked.connect(self.sel_headphone_tone.prev_value)

        tone_layout.addStretch()
        tone_layout.addWidget(self.btn_headphone_tone_minus)
        tone_layout.addWidget(self.sel_headphone_tone)
        tone_layout.addWidget(self.btn_headphone_tone_plus)
        tone_layout.addStretch()

        audio_tone_section.add_widget(tone_controls)

        # Añadir todas las secciones al layout principal
        headphone_layout.addWidget(audio_main_section)
        headphone_layout.addWidget(audio_volume_section)
        headphone_layout.addWidget(audio_tone_section)
        headphone_layout.addStretch()
        
        headphone_scroll.setWidget(headphone_container)

        # 5.2 Pestaña de Estimulación Visual (Barra de Luz)
        lightbar_scroll = QScrollArea()
        lightbar_scroll.setWidgetResizable(True)
        lightbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lightbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lightbar_scroll.setFrameShape(QFrame.NoFrame)

        lightbar_container = QWidget()
        lightbar_layout = QVBoxLayout(lightbar_container)
        lightbar_layout.setContentsMargins(5, 5, 5, 5)

        # Switch para la barra de luz
        self.light_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_light = PyQtSwitch()
        self.switch_light.setAnimation(True) 
        self.switch_light.setCircleDiameter(30)
        self.switch_light.toggled.connect(self.update_light)
        self.light_switch_container.add_switch(self.switch_light)
        self.switch_light.get_value = lambda: self.switch_light.isChecked()
        self.switch_light.set_value = lambda value: self.switch_light.setChecked(value)

        # Botón de prueba de luz
        self.btn_light_test = CustomButton(2, 0, 'Prueba', self.light_test_click, togglable=True)
        
        # Primera fila: Switch y botón prueba
        lightbar_row1 = QHBoxLayout()
        lightbar_row1.addWidget(self.light_switch_container)
        lightbar_row1.addStretch()
        lightbar_row1.addWidget(self.btn_light_test)

        # Controles de color
        self.btn_light_color_minus = CustomButton(0, 1, '<<', size=(75, 75))
        self.sel_light_color = Selector(1, 1, 'Color', Config.colors, '{0}', None, None,
                                      self.update_light, cyclic=True, parent=self)
        self.btn_light_color_plus = CustomButton(2, 1, '>>', size=(75, 75))

        # Conectar botones de color
        self.btn_light_color_plus.clicked.connect(self.sel_light_color.next_value)
        self.btn_light_color_minus.clicked.connect(self.sel_light_color.prev_value)
        
        # Segunda fila: Controles de color
        lightbar_row2 = QHBoxLayout()
        lightbar_row2.addStretch()
        lightbar_row2.addWidget(self.btn_light_color_minus)
        lightbar_row2.addWidget(self.sel_light_color)
        lightbar_row2.addWidget(self.btn_light_color_plus)
        lightbar_row2.addStretch()

        # Controles de intensidad
        self.btn_light_intens_minus = CustomButton(0, 2, '-', size=(75, 75))
        self.sel_light_intens = Selector(1, 2, 'Brillo', Config.intensities, '{0:d}%',
                                       None, None, self.update_light, parent=self)
        self.btn_light_intens_plus = CustomButton(2, 2, '+', size=(75, 75))

        # Conectar botones de intensidad
        self.btn_light_intens_plus.clicked.connect(self.sel_light_intens.next_value)
        self.btn_light_intens_minus.clicked.connect(self.sel_light_intens.prev_value)
        
        # Tercera fila: Controles de intensidad
        lightbar_row3 = QHBoxLayout()
        lightbar_row3.addStretch()
        lightbar_row3.addWidget(self.btn_light_intens_minus)
        lightbar_row3.addWidget(self.sel_light_intens)
        lightbar_row3.addWidget(self.btn_light_intens_plus)
        lightbar_row3.addStretch()
        
        # Añadir todas las filas al layout de la barra de luz
        lightbar_layout.addLayout(lightbar_row1)
        lightbar_layout.addLayout(lightbar_row2)
        lightbar_layout.addLayout(lightbar_row3)
        lightbar_layout.addStretch()
        
        lightbar_scroll.setWidget(lightbar_container)

        # 5.3 Pestaña de Estimulación Táctil (Buzzer)
        buzzer_scroll = QScrollArea()
        buzzer_scroll.setWidgetResizable(True)
        buzzer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        buzzer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        buzzer_scroll.setFrameShape(QFrame.NoFrame)

        buzzer_container = QWidget()
        buzzer_layout = QVBoxLayout(buzzer_container)
        buzzer_layout.setContentsMargins(5, 5, 5, 5)

        # Switch para el buzzer
        self.buzzer_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_buzzer = PyQtSwitch()
        self.switch_buzzer.setAnimation(True)
        self.switch_buzzer.toggled.connect(self.update_buzzer)
        self.buzzer_switch_container.add_switch(self.switch_buzzer)
        self.switch_buzzer.get_value = lambda: self.switch_buzzer.isChecked()
        self.switch_buzzer.set_value = lambda value: self.switch_buzzer.setChecked(value)
        
        # Botón de prueba de buzzer
        self.btn_buzzer_test = CustomButton(2, 0, 'Prueba', self.buzzer_test_click)
        
        # Primera fila: Switch y botón prueba
        buzzer_row1 = QHBoxLayout()
        buzzer_row1.addWidget(self.buzzer_switch_container)
        buzzer_row1.addStretch()
        buzzer_row1.addWidget(self.btn_buzzer_test)
        
        # Controles de duración
        self.btn_buzzer_duration_minus = CustomButton(0, 1, '-', size=(75, 75))
        self.sel_buzzer_duration = Selector(1, 1, 'Duración', Config.durations, '{0:d} ms', 
                                          None, None, self.update_buzzer, parent=self)
        self.btn_buzzer_duration_plus = CustomButton(2, 1, '+', size=(75, 75))
        
        # Conectar botones de duración
        self.btn_buzzer_duration_plus.clicked.connect(self.sel_buzzer_duration.next_value)
        self.btn_buzzer_duration_minus.clicked.connect(self.sel_buzzer_duration.prev_value)
        
        # Segunda fila: Controles de duración
        buzzer_row2 = QHBoxLayout()
        buzzer_row2.addStretch()
        buzzer_row2.addWidget(self.btn_buzzer_duration_minus)
        buzzer_row2.addWidget(self.sel_buzzer_duration)
        buzzer_row2.addWidget(self.btn_buzzer_duration_plus)
        buzzer_row2.addStretch()
        
        # Añadir todas las filas al layout del buzzer
        buzzer_layout.addLayout(buzzer_row1)
        buzzer_layout.addLayout(buzzer_row2)
        buzzer_layout.addStretch()  # Añadir espacio al final
        
        buzzer_scroll.setWidget(buzzer_container)

        # Añadir las pestañas al TabWidget
        self.tab_widget.addTab(headphone_scroll, "Estimulación Auditiva")
        self.tab_widget.addTab(lightbar_scroll, "Estimulación Visual")
        self.tab_widget.addTab(buzzer_scroll, "Estimulación Táctil")
        
        # Deshabilitar pestañas inicialmente hasta verificar conexiones
        # Excepto la auditiva que siempre está disponible
        self.tab_widget.setTabEnabled(0, True)  # Auditiva siempre disponible
        self.tab_widget.setTabEnabled(1, False)  # Visual deshabilitado hasta verificar
        self.tab_widget.setTabEnabled(2, False)  # Táctil deshabilitado hasta verificar
        
        # Para mantener la compatibilidad con el código existente
        self.areas = {'headphone': 0, 'lightbar': 1, 'buzzer': 2}
        
        # Configurar fondo
        self.setStyleSheet("background-color: rgba(230, 230, 230, 100);")
        
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
        self.save_config()
    
    def update_buzzer(self):
        """Actualiza la configuración del buzzer"""
        duration = self.sel_buzzer_duration.get_value()
        Devices.set_buzzer_duration(duration // 10)
        self.save_config()
    
    def update_sound(self):
        """Actualiza la configuración de sonido"""
        (tone_name, frequency, duration) = self.sel_headphone_tone.get_value()
        volume = self.sel_headphone_volume.get_value() / 100
        Devices.set_tone(frequency, duration, volume)
        self.save_config()
    
    def update_speed(self):
        """Actualiza la velocidad"""
        self.save_config()
        if self.mode == 'action':
            self.adjust_action_timer()
    
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
            self.sel_headphone_tone.set_value(Config.data.get('headphone.tone'))
            self.sel_headphone_volume.set_value(Config.data.get('headphone.volume'))
        except:
            # No fallar con archivo de configuración corrupto
            pass
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
            
            # Detener captura de señales si el checkbox está marcado
            if hasattr(self, 'chk_capture_signals') and self.chk_capture_signals.isChecked():
                main_window = self.window()
                if hasattr(main_window, 'sensor_monitor') and main_window.sensor_monitor:
                    if main_window.sensor_monitor.running:
                        main_window.sensor_monitor.stop_acquisition()
        else:
            self.config_mode()
            self.reset_action()

    def pause_click(self):
        """Maneja clic en el botón Pause"""
        if self.btn_pause.isChecked():
            # pause
            self.pausing = True
            
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
                self.reset_action()
                return
            else:
                cntr += 1
            self.sel_counter.set_value(cntr)
        self.led_pos += self.direction
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
        """Actualiza la etiqueta de estado de dispositivos"""
        if not found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
            return
            
        if "Master Controller" not in found_devices:
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
            return
        
        # Crear texto de estado para cada tipo de dispositivo conocido
        status_text = "Estado de dispositivos: "
        
        # Comprobar cada tipo de dispositivo en KNOWN_SLAVES
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            # Tratar el sensor como no requerido para esta interfaz
            if name == "Sensor":
                required = False
                
            is_connected = name in found_devices
            status = "CONECTADO" if is_connected else "DESCONECTADO"
            req = " (Requerido)" if required else ""
            status_text += f"{name}{req}: {status} | "
        
        # Añadir también el controlador maestro
        status_text += "Master Controller: CONECTADO"
        
        # Actualizar el texto de la etiqueta
        self.device_status_label.setText(status_text)
        
        # Verificar si todos los dispositivos requeridos (excepto el Sensor) están conectados
        required_connected = all(
            name in found_devices
            for slave_id, (name, required) in KNOWN_SLAVES.items()
            if required and name != "Sensor"
        )
        
        # Cambiar el color de fondo según el estado de conexión
        if required_connected:
            self.device_status_label.setStyleSheet("background-color: rgba(200, 255, 200, 180); padding: 5px;")
        else:
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")

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
    
    # Crear ventana principal para modo independiente
    main_window = QMainWindow()
    main_window.setWindowTitle("EMDR Controller")
    main_window.setGeometry(100, 100, 480, 320)
    
    # Crear el widget del controlador
    controller = EMDRControllerWidget(parent=main_window)
    main_window.setCentralWidget(controller)
    
    # Inicializar controlador
    controller.load_config()
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Antes de salir, guardar configuración
    app.aboutToQuit.connect(controller.closeEvent)
    
    sys.exit(app.exec())