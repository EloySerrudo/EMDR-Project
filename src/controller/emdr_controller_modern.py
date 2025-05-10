import sys
import os
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QStackedWidget, QPushButton, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar componentes compartidos
from src.common.components import (ModernSwitch, ModernSlider, ColorButton, 
                                  SectionHeader, SettingRow, SegmentedButton)
from src.common.stylesheets import get_combined_style, get_primary_color

# Importaciones de modelos y utilidades
from src.models.devices import Devices
from src.models.config import Config
from src.utils.hiperf_timer import HighPerfTimer
from src.utils.events import event_system


class DeviceStatusBar(QWidget):
    """Barra de estado para mostrar la conexión de dispositivos"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("device-status-bar")
        self.setFixedHeight(40)
        
        # Layout horizontal
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        
        # Etiqueta de estado
        self.status_label = QLabel("Dispositivos: No conectados")
        self.status_label.setStyleSheet("color: #aaaaaa;")
        
        # Botón de escaneo
        self.scan_button = QPushButton("Escanear")
        self.scan_button.setFixedSize(80, 30)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #aaaaaa;
                color: #aaaaaa;
                border-radius: 5px;
            }
        """)
        
        # Añadir widgets al layout
        self.layout.addWidget(self.status_label)
        self.layout.addStretch()
        self.layout.addWidget(self.scan_button)
        
        # Estilo del widget
        self.setStyleSheet("""
            DeviceStatusBar {
                background-color: #262626;
                border-bottom: 1px solid #333333;
            }
        """)
    
    def update_status(self, device_status, all_required_connected=False):
        """Actualiza la visualización del estado de dispositivos"""
        if not device_status:
            self.status_label.setText("Dispositivos: No conectados")
            self.status_label.setStyleSheet("color: #f44336;")
            return
            
        master_connected = "Master Controller" in device_status
        if not master_connected:
            self.status_label.setText("Dispositivos: Controlador no encontrado")
            self.status_label.setStyleSheet("color: #f44336;")
            return
        
        # Mostrar estado compacto
        if all_required_connected:
            self.status_label.setText("Dispositivos: Conectados")
            self.status_label.setStyleSheet("color: #4caf50;")
        else:
            self.status_label.setText("Dispositivos: Algunos faltan")
            self.status_label.setStyleSheet("color: #ff9800;")


class ControlFooter(QWidget):
    """Pie de página con controles comunes (velocidad y botón de inicio)"""
    
    def __init__(self, start_callback=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 5, 15, 5)
        
        # Control de velocidad
        self.speed_label = QLabel("Speed 15 / 25")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setStyleSheet("font-size: 16px; color: white;")
        
        # Slider de velocidad
        self.speed_slider = ModernSlider(1, 25, initial_value=15)
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        
        # Contenedor con botón de timer y botón de inicio
        self.button_layout = QHBoxLayout()
        
        # Botón de timer
        self.timer_button = QPushButton()
        self.timer_button.setIcon(QIcon("src/assets/icons/timer.png"))
        self.timer_button.setFixedSize(50, 50)
        self.timer_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #009688;
                border-radius: 25px;
            }
        """)
        
        # Botón de inicio
        self.start_button = QPushButton("Start")
        self.start_button.setFixedHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        if start_callback:
            self.start_button.clicked.connect(start_callback)
        
        # Añadir botones al layout
        self.button_layout.addWidget(self.timer_button)
        self.button_layout.addSpacing(10)
        self.button_layout.addWidget(self.start_button, 1)
        
        # Añadir elementos al layout principal
        self.main_layout.addWidget(self.speed_label)
        self.main_layout.addWidget(self.speed_slider)
        self.main_layout.addLayout(self.button_layout)
        
        # Estilo del widget
        self.setStyleSheet("""
            ControlFooter {
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }
        """)
    
    def _update_speed_label(self, value):
        """Actualiza la etiqueta de velocidad con el valor actual"""
        self.speed_label.setText(f"Speed {value} / 25")
    
    def get_speed(self):
        """Obtiene el valor actual de velocidad"""
        return self.speed_slider.value()
    
    def set_speed(self, value):
        """Establece el valor de velocidad"""
        self.speed_slider.setValue(value)
    
    def set_start_text(self, text):
        """Cambia el texto del botón de inicio"""
        self.start_button.setText(text)
    
    def set_start_enabled(self, enabled):
        """Habilita o deshabilita el botón de inicio"""
        self.start_button.setEnabled(enabled)


class HomeScreen(QWidget):
    """Pantalla principal con selección de dispositivos EMDR"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(20)
        
        # Imagen ilustrativa central
        self.image_label = QLabel()
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #262626;
                border-radius: 10px;
            }
        """)
        self.image_label.setFixedHeight(300)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Imagen placeholder - se reemplazaría con un icono real
        self.image_label.setText("EMDRKIT")
        self.image_label.setFont(QFont("Arial", 28, QFont.Bold))
        
        # Botones de dispositivos
        self.create_device_buttons()
        
        # Añadir widgets al layout
        self.layout.addStretch(1)
        self.layout.addWidget(self.image_label)
        self.layout.addLayout(self.devices_layout)
        self.layout.addStretch(1)
    
    def create_device_buttons(self):
        """Crea los botones para cada dispositivo EMDR"""
        self.devices_layout = QHBoxLayout()
        self.devices_layout.setContentsMargins(20, 10, 20, 10)
        self.devices_layout.setSpacing(15)
        
        # Botón Light Tube
        self.light_button = self.create_device_button("Light Tube")
        
        # Botón Pulsators
        self.pulsator_button = self.create_device_button("Pulsators")
        
        # Botón Headphone
        self.headphone_button = self.create_device_button("Headphone")
        
        # Añadir botones al layout
        self.devices_layout.addWidget(self.light_button)
        self.devices_layout.addWidget(self.pulsator_button)
        self.devices_layout.addWidget(self.headphone_button)
    
    def create_device_button(self, name):
        """Crea un botón de dispositivo individual"""
        button = QPushButton(name)
        button.setFixedSize(100, 100)
        button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 10px;
                border: 1px solid #444444;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #009688;
            }
        """)
        return button


class LightScreen(QWidget):
    """Pantalla para controlar la barra de luz (Light Tube)"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Cabecera de sección
        self.header = SectionHeader("Light Tube")
        self.header.back_clicked.connect(self._go_back)
        
        # Contenido principal
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 20, 15, 20)
        self.content_layout.setSpacing(20)
        
        # Fila de Activación
        self.active_switch = ModernSwitch()
        self.active_switch.toggled.connect(self._on_active_toggled)
        self.active_row = SettingRow("Active", self.active_switch)
        self.active_status = QLabel("Light Tube is off")
        self.active_status.setStyleSheet("color: #aaaaaa; margin-left: 15px;")
        
        # Fila de Brillo
        self.brightness_slider = ModernSlider(0, 100, initial_value=75)
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        self.brightness_row = SettingRow("Brightness", self.brightness_slider)
        
        # Fila de Modo (Sweep/Blink)
        self.mode_buttons = SegmentedButton(["Sweep", "Blink"])
        self.mode_buttons.selectionChanged.connect(self._on_mode_changed)
        self.mode_row = SettingRow("Mode", self.mode_buttons)
        
        # Sección de Color
        self.color_label = QLabel("Color")
        self.color_label.setStyleSheet("font-size: 16px; color: white;")
        self.color_status = QLabel("Light Tube color is green")
        self.color_status.setStyleSheet("color: #aaaaaa;")
        
        # Paleta de colores
        self.create_color_palette()
        
        # Separador
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("background-color: #333333;")

        separator2 = QFrame() 
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("background-color: #333333;")

        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        separator3.setStyleSheet("background-color: #333333;")

        # Modificar esta parte del código
        self.content_layout.addWidget(self.active_row)
        self.content_layout.addWidget(self.active_status)
        self.content_layout.addWidget(separator1)  # Primer separador
        self.content_layout.addWidget(self.brightness_row)
        self.content_layout.addWidget(separator2)  # Segundo separador
        self.content_layout.addWidget(self.mode_row)
        self.content_layout.addWidget(separator3)  # Tercer separador
        self.content_layout.addWidget(self.color_label)
        self.content_layout.addWidget(self.color_status)
        self.content_layout.addLayout(self.color_palette_layout)
        self.content_layout.addStretch(1)
        
        # Añadir cabecera y contenido al layout principal
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.content)
    
    def create_color_palette(self):
        """Crea la paleta de selección de colores"""
        self.color_palette_layout = QHBoxLayout()
        self.color_buttons = []
        
        # Colores del modelo Config
        colors = [
            ("#FF0000", "Rojo"),
            ("#FFFF00", "Amarillo"),
            ("#FF8000", "Naranja"),
            ("#00FF00", "Verde"),
            ("#00FFFF", "Cian"),
            ("#0000FF", "Azul"),
            ("#FF00FF", "Magenta"),
            ("#FFFFFF", "Blanco"),
        ]
        
        # Crear botón para cada color
        for color_hex, color_name in colors:
            btn = ColorButton(color_hex)
            btn.clicked.connect(lambda checked, c=color_name: self._on_color_selected(c))
            self.color_buttons.append(btn)
            self.color_palette_layout.addWidget(btn)
        
        # Botón para colores personalizados
        custom_btn = QPushButton()
        custom_btn.setFixedSize(40, 40)
        custom_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #555555;
                border-radius: 20px;
            }
        """)
        self.color_palette_layout.addWidget(custom_btn)
        
        # Seleccionar el color verde por defecto (índice 3)
        self.color_buttons[3].setChecked(True)
    
    def _go_back(self):
        """Volver a la pantalla anterior"""
        if self.controller:
            self.controller.show_home_screen()
    
    def _on_active_toggled(self, is_active):
        """Maneja el cambio en el interruptor de activación"""
        status_text = "Light Tube is on" if is_active else "Light Tube is off"
        self.active_status.setText(status_text)
        if self.controller:
            self.controller.update_light()
    
    def _on_brightness_changed(self, value):
        """Maneja el cambio de brillo"""
        if self.controller:
            self.controller.update_light()
    
    def _on_mode_changed(self, index, text):
        """Maneja el cambio de modo (Sweep/Blink)"""
        if self.controller:
            self.controller.update_light()
    
    def _on_color_selected(self, color_name):
        """Maneja la selección de color"""
        self.color_status.setText(f"Light Tube color is {color_name.lower()}")
        if self.controller:
            self.controller.update_light()


class PulsatorScreen(QWidget):
    """Pantalla para controlar los pulsadores (vibradores)"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Cabecera de sección
        self.header = SectionHeader("Pulsators")
        self.header.back_clicked.connect(self._go_back)
        
        # Contenido principal
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 20, 15, 20)
        self.content_layout.setSpacing(20)
        
        # Fila de Activación
        self.active_switch = ModernSwitch()
        self.active_switch.toggled.connect(self._on_active_toggled)
        self.active_row = SettingRow("Active", self.active_switch)
        self.active_status = QLabel("Pulsators are off")
        self.active_status.setStyleSheet("color: #aaaaaa; margin-left: 15px;")
        
        # Fila de Intensidad
        self.intensity_slider = ModernSlider(0, 100, initial_value=50)
        self.intensity_slider.valueChanged.connect(self._on_intensity_changed)
        self.intensity_row = SettingRow("Intensity", self.intensity_slider)
        
        # Opción para usar velocidad diferente
        self.use_different_speed = ModernSwitch()
        self.use_different_speed.toggled.connect(self._on_different_speed_toggled)
        self.different_speed_row = SettingRow("Use different speed", self.use_different_speed)
        
        # Separadores
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setStyleSheet("background-color: #333333;")
        
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: #333333;")
        
        # Añadir elementos al contenido
        self.content_layout.addWidget(self.active_row)
        self.content_layout.addWidget(self.active_status)
        self.content_layout.addWidget(separator1)
        self.content_layout.addWidget(self.intensity_row)
        self.content_layout.addWidget(separator2)
        self.content_layout.addWidget(self.different_speed_row)
        self.content_layout.addStretch(1)
        
        # Añadir cabecera y contenido al layout principal
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.content)
    
    def _go_back(self):
        """Volver a la pantalla anterior"""
        if self.controller:
            self.controller.show_home_screen()
    
    def _on_active_toggled(self, is_active):
        """Maneja el cambio en el interruptor de activación"""
        status_text = "Pulsators are on" if is_active else "Pulsators are off"
        self.active_status.setText(status_text)
        if self.controller:
            self.controller.update_buzzer()
    
    def _on_intensity_changed(self, value):
        """Maneja el cambio de intensidad"""
        if self.controller:
            self.controller.update_buzzer()
    
    def _on_different_speed_toggled(self, use_different):
        """Maneja el cambio en la opción de usar velocidad diferente"""
        if self.controller:
            self.controller.update_buzzer()


class HeadphoneScreen(QWidget):
    """Pantalla para controlar los auriculares"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Cabecera de sección
        self.header = SectionHeader("Headphone")
        self.header.back_clicked.connect(self._go_back)
        
        # Contenido principal
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 20, 15, 20)
        self.content_layout.setSpacing(20)
        
        # Fila de Activación
        self.active_switch = ModernSwitch()
        self.active_switch.toggled.connect(self._on_active_toggled)
        self.active_row = SettingRow("Active", self.active_switch)
        self.active_status = QLabel("Headphone is off")
        self.active_status.setStyleSheet("color: #aaaaaa; margin-left: 15px;")
        
        # Fila de Volumen
        self.volume_slider = ModernSlider(0, 100, initial_value=100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_row = SettingRow("Volume", self.volume_slider)
        
        # Separador
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setStyleSheet("background-color: #333333;")
        
        # Sincronización de sonido
        self.sync_label = QLabel("Sound synced to")
        self.sync_label.setStyleSheet("font-size: 16px; color: white;")
        
        # Botones de sincronización
        self.sync_buttons = SegmentedButton(["Light Tube", "Pulsators", "Random"])
        self.sync_buttons.selectionChanged.connect(self._on_sync_changed)
        
        # Tipos de sonido
        self.sound_label = QLabel("Sound")
        self.sound_label.setStyleSheet("font-size: 16px; color: white;")
        
        # Botones de tipo de sonido
        self.sound_buttons = SegmentedButton(["Click 1", "Click 2", "Beep 1", "Beep 2"])
        self.sound_buttons.selectionChanged.connect(self._on_sound_type_changed)
        
        # Botones de música personalizada
        self.custom_music_layout = QHBoxLayout()
        self.custom_music_btn = QPushButton("Custom music")
        self.custom_sound_btn = QPushButton("Custom sound file")
        
        self.custom_music_btn.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        self.custom_sound_btn.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        self.custom_music_layout.addWidget(self.custom_music_btn)
        self.custom_music_layout.addWidget(self.custom_sound_btn)
        
        # Opción para usar velocidad diferente
        self.use_different_speed = ModernSwitch()
        self.use_different_speed.toggled.connect(self._on_different_speed_toggled)
        self.different_speed_row = SettingRow("Use different speed", self.use_different_speed)
        
        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: #333333;")
        
        # Añadir elementos al contenido
        self.content_layout.addWidget(self.active_row)
        self.content_layout.addWidget(self.active_status)
        self.content_layout.addWidget(separator1)
        self.content_layout.addWidget(self.volume_row)
        self.content_layout.addWidget(self.sync_label)
        self.content_layout.addWidget(self.sync_buttons)
        self.content_layout.addWidget(self.sound_label)
        self.content_layout.addWidget(self.sound_buttons)
        self.content_layout.addLayout(self.custom_music_layout)
        self.content_layout.addWidget(separator2)
        self.content_layout.addWidget(self.different_speed_row)
        self.content_layout.addStretch(1)
        
        # Añadir cabecera y contenido al layout principal
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.content)
    
    def _go_back(self):
        """Volver a la pantalla anterior"""
        if self.controller:
            self.controller.show_home_screen()
    
    def _on_active_toggled(self, is_active):
        """Maneja el cambio en el interruptor de activación"""
        status_text = "Headphone is on" if is_active else "Headphone is off"
        self.active_status.setText(status_text)
        if self.controller:
            self.controller.update_sound()
    
    def _on_volume_changed(self, value):
        """Maneja el cambio de volumen"""
        if self.controller:
            self.controller.update_sound()
    
    def _on_sync_changed(self, index, text):
        """Maneja el cambio de sincronización"""
        if self.controller:
            self.controller.update_sound()
    
    def _on_sound_type_changed(self, index, text):
        """Maneja el cambio de tipo de sonido"""
        if self.controller:
            self.controller.update_sound()
    
    def _on_different_speed_toggled(self, use_different):
        """Maneja el cambio en la opción de usar velocidad diferente"""
        if self.controller:
            self.controller.update_sound()


class EMDRModernController(QWidget):
    """
    Controlador EMDR con interfaz moderna.
    Implementa la funcionalidad del controlador original con un diseño moderno.
    """
    
    def __init__(self, device_manager=None):
        super().__init__()
        self.device_manager = device_manager
        
        # Variables de estado
        self.mode = 'config'
        self.pausing = False
        self.stopping = False
        self.in_load = False
        self.max_counter = 0
        self.counter_value = 0
        self.led_pos = int(Devices.led_num / 2) + 1  # start in the middle
        self.direction = -1
        self.decay = False
        
        # Configurar UI
        self.setup_ui()
        
        # Cargar configuración
        self.load_config()
        
        # Conectar eventos
        if device_manager:
            device_manager.device_status_changed.connect(self.update_device_status)
        
        # Conectar ACTION_EVENT con su manejador
        event_system.action_event.connect(self.action)
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Layout principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Barra de estado de dispositivos
        self.device_status_bar = DeviceStatusBar()
        if self.device_manager:
            self.device_status_bar.scan_button.clicked.connect(self.device_manager.scan_devices)
        
        # Widget de contenido apilado para cambiar entre pantallas
        self.content_stack = QStackedWidget()
        
        # Crear pantallas
        self.home_screen = HomeScreen()
        self.light_screen = LightScreen(self)
        self.pulsator_screen = PulsatorScreen(self)
        self.headphone_screen = HeadphoneScreen(self)
        
        # Añadir pantallas al stack
        self.content_stack.addWidget(self.home_screen)
        self.content_stack.addWidget(self.light_screen)
        self.content_stack.addWidget(self.pulsator_screen)
        self.content_stack.addWidget(self.headphone_screen)
        
        # Conectar botones de la pantalla principal
        self.home_screen.light_button.clicked.connect(lambda: self.content_stack.setCurrentWidget(self.light_screen))
        self.home_screen.pulsator_button.clicked.connect(lambda: self.content_stack.setCurrentWidget(self.pulsator_screen))
        self.home_screen.headphone_button.clicked.connect(lambda: self.content_stack.setCurrentWidget(self.headphone_screen))
        
        # Pie de página con controles comunes
        self.footer = ControlFooter(self.start_click)
        
        # Añadir widgets al layout principal
        self.layout.addWidget(self.device_status_bar)
        self.layout.addWidget(self.content_stack, 1)  # 1 = stretch factor
        self.layout.addWidget(self.footer)
        
        # Aplicar estilo
        self.setStyleSheet(get_combined_style('light'))  # Tema inicial
    
    def show_home_screen(self):
        """Muestra la pantalla principal"""
        self.content_stack.setCurrentWidget(self.home_screen)
    
    def start_click(self):
        """Maneja clic en el botón Start (Play)"""
        if self.mode == 'config':
            # Iniciar sesión EMDR
            self.max_counter = 0
            self.reset_action()
            self.action_mode()
            self.footer.set_start_text("Stop")
        else:
            # Detener sesión EMDR
            self.stop_click()
            self.footer.set_start_text("Start")
    
    def stop_click(self):
        """Maneja clic en el botón Stop"""
        if self.mode == 'action':
            self.stopping = True
        else:
            self.config_mode()
            self.reset_action()
    
    def reset_action(self):
        """Reinicia la acción EMDR"""
        self.led_pos = int(Devices.led_num / 2) + 1  # start in the middle
        self.direction = -1
        self.decay = False
        self.counter_value = 0
        
        # Actualizar la posición del LED basado en el estado del Light Tube
        is_light_active = self.light_screen.active_switch.isChecked()
        Devices.set_led(self.led_pos if is_light_active else 0)
    
    def action_mode(self):
        """Cambia al modo de acción"""
        # Verificar si podemos adquirir los dispositivos
        if self.mode == 'action':
            return
        self.mode = 'action'
        if not self.pausing:
            self.counter_value = 0
        self.stopping = False
        self.pausing = False
        
        # Preparar dispositivos
        self.update_light()
        self.update_buzzer()
        self.update_sound()
        
        # Iniciar temporizador de acción
        self.adjust_action_timer()
        HighPerfTimer(self.action_delay, self.post_action).start()
    
    def config_mode(self):
        """Cambia al modo de configuración"""
        self.mode = 'config'
    
    def post_action(self):
        """Publica un evento de acción"""
        if self.mode == 'action':
            timer = HighPerfTimer(self.action_delay + self.action_extra_delay, self.post_action)
            event_system.action_event.emit()
            timer.start()
    
    def adjust_action_timer(self):
        """Ajusta el temporizador de acción basado en la velocidad"""
        speed = self.footer.get_speed()
        self.action_delay = (60 / speed / Devices.led_num / 2)
        self.action_extra_delay = 0
    
    def action(self):
        """Maneja un paso en la secuencia EMDR"""
        if self.mode != 'action':
            return
        
        # Actualizar luz si está activa
        is_light_active = self.light_screen.active_switch.isChecked()
        if is_light_active:
            Devices.set_led(self.led_pos)
        
        # Control de los estímulos en los extremos
        if self.led_pos == 1:
            # left end
            is_buzzer_active = self.pulsator_screen.active_switch.isChecked()
            if is_buzzer_active:
                Devices.do_buzzer(True)
            
            is_headphone_active = self.headphone_screen.active_switch.isChecked()
            if is_headphone_active:
                Devices.do_sound(True)
                
            if self.direction == -1:
                self.direction = 1
                
        if self.led_pos == Devices.led_num:
            # right end
            is_buzzer_active = self.pulsator_screen.active_switch.isChecked()
            if is_buzzer_active:
                Devices.do_buzzer(False)
            
            is_headphone_active = self.headphone_screen.active_switch.isChecked()
            if is_headphone_active:
                Devices.do_sound(False)
                
            if self.direction == 1:
                self.direction = -1
                
            if self.counter_value == self.max_counter or self.stopping or self.pausing:
                self.decay = True
                
        if self.led_pos == int(Devices.led_num / 2) + 1 and self.direction == -1:
            # in the middle
            if self.decay:
                self.config_mode()
                self.reset_action()
                self.footer.set_start_text("Start")
                return
            else:
                self.counter_value += 1
                
        self.led_pos += self.direction
        
        if self.decay:
            from numpy import log
            middle = int(Devices.led_num / 2) + 1
            n = Devices.led_num - middle
            pos = Devices.led_num - self.led_pos
            alpha = log(1.2) / (log(n) - log(n - 1))
            factor = 1.5 / n ** alpha
            self.action_extra_delay = self.action_delay + factor * pos ** alpha
    
    def update_light(self):
        """Actualiza la configuración de la luz"""
        # Obtener estado de activación
        is_active = self.light_screen.active_switch.isChecked()
        
        # Obtener brillo
        brightness = self.light_screen.brightness_slider.value() / 100 * 0.7  # max. 70% intensity
        
        # Obtener color seleccionado
        color_index = -1
        for i, btn in enumerate(self.light_screen.color_buttons):
            if btn.isChecked():
                color_index = i
                break
        
        # Colores disponibles (RGB)
        colors = [
            (255, 0, 0),    # Rojo
            (255, 255, 0),  # Amarillo
            (255, 128, 0),  # Naranja
            (0, 255, 0),    # Verde
            (0, 255, 255),  # Cian
            (0, 0, 255),    # Azul
            (255, 0, 255),  # Magenta
            (255, 255, 255) # Blanco
        ]
        
        # Usar verde como predeterminado si no hay selección
        if color_index == -1:
            color_index = 3  # Verde
        
        # Aplicar brillo al color
        r, g, b = colors[color_index]
        r = round(r * brightness)
        g = round(g * brightness)
        b = round(b * brightness)
        
        # Convertir a formato único para el dispositivo
        color = r * 256 * 256 + g * 256 + b
        Devices.set_color(color)
        
        # Actualizar estado del LED
        if self.mode == 'config':
            # En modo configuración, responder al botón de test
            if is_active:
                Devices.set_led(int(Devices.led_num / 2) + 1)
            else:
                Devices.set_led(0)
    
    def update_buzzer(self):
        """Actualiza la configuración del buzzer"""
        # Obtener intensidad
        intensity = self.pulsator_screen.intensity_slider.value()
        
        # Mapear la intensidad a una duración de vibración (100-500ms)
        duration = int(100 + (intensity / 100) * 400)
        
        # Actualizar duración del buzzer
        Devices.set_buzzer_duration(duration // 10)
    
    def update_sound(self):
        """Actualiza la configuración de sonido"""
        # Obtener volumen
        volume = self.headphone_screen.volume_slider.value() / 100
        
        # Obtener tipo de sonido seleccionado
        sound_index = self.headphone_screen.sound_buttons.get_selected_index()
        
        # Tipos de tonos disponibles (frecuencia, duración)
        tones = [
            (440, 50),   # Click 1: Medio/Corto
            (440, 100),  # Click 2: Medio/Largo
            (880, 100),  # Beep 1: Alto/Corto
            (220, 50),   # Beep 2: Bajo/Corto
        ]
        
        # Usar el primer tono como predeterminado
        if sound_index < 0 or sound_index >= len(tones):
            sound_index = 0
            
        # Aplicar configuración de sonido
        frequency, duration = tones[sound_index]
        Devices.set_tone(frequency, duration, volume)
    
    def load_config(self):
        """Carga la configuración desde archivo"""
        try:
            self.in_load = True
            Config.load()
            
            # Actualizar velocidad
            self.footer.set_speed(Config.data.get('general.speed', 15))
            
            # Actualizar Light Tube
            self.light_screen.active_switch.setChecked(Config.data.get('lightbar.on', True))
            
            # La conversión de color es más compleja y depende de tu implementación
            
            self.light_screen.brightness_slider.setValue(Config.data.get('lightbar.intensity', 75))
            
            # Actualizar Pulsators
            self.pulsator_screen.active_switch.setChecked(Config.data.get('buzzer.on', True))
            
            # Mapear duración a intensidad
            duration = Config.data.get('buzzer.duration', 100)
            intensity = int(((duration - 100) / 400) * 100)
            self.pulsator_screen.intensity_slider.setValue(intensity)
            
            # Actualizar Headphone
            self.headphone_screen.active_switch.setChecked(Config.data.get('headphone.on', True))
            self.headphone_screen.volume_slider.setValue(int(Config.data.get('headphone.volume', 0.5) * 100))
            
            # Configuración de tono requiere mapeo específico según tu implementación
            
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
        finally:
            self.in_load = False
            
            # Actualizar dispositivos después de cargar
            self.update_light()
            self.update_buzzer()
            self.update_sound()
    
    def save_config(self):
        """Guarda la configuración en archivo"""
        if self.in_load:
            return
            
        try:
            # Velocidad
            Config.data['general.speed'] = self.footer.get_speed()
            
            # Light Tube
            Config.data['lightbar.on'] = self.light_screen.active_switch.isChecked()
            Config.data['lightbar.intensity'] = self.light_screen.brightness_slider.value()
            
            # TODO: Guardar color seleccionado
            
            # Pulsators
            Config.data['buzzer.on'] = self.pulsator_screen.active_switch.isChecked()
            
            # Convertir intensidad a duración
            intensity = self.pulsator_screen.intensity_slider.value()
            duration = int(100 + (intensity / 100) * 400)
            Config.data['buzzer.duration'] = duration
            
            # Headphone
            Config.data['headphone.on'] = self.headphone_screen.active_switch.isChecked()
            Config.data['headphone.volume'] = self.headphone_screen.volume_slider.value() / 100
            
            # TODO: Guardar configuración de tono
            
            # Guardar a archivo
            Config.save()
            
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
    
    def update_device_status(self, device_status, all_required_connected):
        """Actualiza la visualización del estado de los dispositivos"""
        self.device_status_bar.update_status(device_status, all_required_connected)
        
        # Habilitar/deshabilitar funciones según los dispositivos conectados
        lightbar_connected = "Lightbar" in device_status
        buzzer_connected = "Buzzer" in device_status
        
        # Actualizar botones en la pantalla principal
        self.home_screen.light_button.setEnabled(lightbar_connected)
        self.home_screen.pulsator_button.setEnabled(buzzer_connected)
        
        # El botón de inicio solo está activo si hay algún dispositivo conectado
        self.footer.set_start_enabled(all_required_connected)
    
    def cleanup(self):
        """Limpia recursos antes de cerrar"""
        # Detener cualquier acción en progreso
        if self.mode == 'action':
            self.stopping = True
            self.config_mode()
        
        # Apagar todos los dispositivos
        Devices.set_led(0)  # Apagar LEDs
        
        # Guardar configuración
        self.save_config()


# Punto de entrada para pruebas independientes
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = EMDRModernController()
    controller.show()
    sys.exit(app.exec())