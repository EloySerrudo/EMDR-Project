import sys
from numpy import log
import time
import os

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QApplication, QStackedLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

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


class EMDRControllerWidget(QWidget):
    """Controlador principal de la aplicación EMDR convertido a widget PySide6"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.in_load = False
        self.pausing = False
        self.stopping = False
        
        # Layout Grid - Reorganizado para asegurar que la etiqueta de estado esté arriba
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Primero: Añadir etiqueta de estado de dispositivos en la parte superior (fila 0)
        self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
        self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
        self.main_layout.addWidget(self.device_status_label, 0, 0, 1, 5)  # Posición 0,0 ocupando 1 fila y 5 columnas
        
        # Segundo: Crear botones principales (ahora en la fila 1, dejando espacio para la etiqueta)
        self.btn_start = CustomButton(0, 0, 'Play', self.start_click)
        self.btn_start24 = CustomButton(1, 0, 'Play24', self.start24_click)
        self.btn_stop = CustomButton(2, 0, 'Stop', self.stop_click)
        self.btn_pause = CustomButton(3, 0, 'Pause', self.pause_click, togglable=True)
        self.btn_lightbar = CustomButton(0, 1, 'Visual', self.lightbar_click, togglable=True)
        self.btn_lightbar.setActive(False)
        self.btn_buzzer = CustomButton(0, 2, 'Táctil', self.buzzer_click, togglable=True)
        self.btn_buzzer.setActive(False)
        self.btn_headphone = CustomButton(0, 3, 'Auditiva', self.headphone_click, togglable=True)
        
        # Tercero: Crear QStackedLayout
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        self.areas = {'speed':0, 'lightbar':1, 'buzzer':2, 'headphone':3}
        stacked_widget = QWidget()
        stacked_widget.setLayout(self.stacked_layout)
        
        # Cuarto: Añadir botón de escaneo USB en la parte inferior
        self.btn_scan_usb = CustomButton(4, 0, 'Escanear', self.scan_usb_click)
        
        # Quinto: Posicionar todos los widgets en la cuadrícula con los desplazamientos correctos
        
        # Los botones principales se desplazan una fila hacia abajo (fila+1)
        self.main_layout.addWidget(self.btn_start, self.btn_start.pos_y + 1, self.btn_start.pos_x)
        self.main_layout.addWidget(self.btn_start24, self.btn_start24.pos_y + 1, self.btn_start24.pos_x)
        self.main_layout.addWidget(self.btn_stop, self.btn_stop.pos_y + 1, self.btn_stop.pos_x)
        self.main_layout.addWidget(self.btn_pause, self.btn_pause.pos_y + 1, self.btn_pause.pos_x)
        self.main_layout.addWidget(self.btn_lightbar, self.btn_lightbar.pos_y + 1, self.btn_lightbar.pos_x)
        self.main_layout.addWidget(self.btn_buzzer, self.btn_buzzer.pos_y + 1, self.btn_buzzer.pos_x)
        self.main_layout.addWidget(self.btn_headphone, self.btn_headphone.pos_y + 1, self.btn_headphone.pos_x)
        
        # El widget apilado también se desplaza una fila hacia abajo
        self.main_layout.addWidget(stacked_widget, 2, 1, 3, 3)  # Ahora en la fila 2
        
        # El botón de escaneo se desplaza una fila hacia abajo
        self.main_layout.addWidget(self.btn_scan_usb, self.btn_scan_usb.pos_y + 1, self.btn_scan_usb.pos_x, 1, 4)
        
        # Área de velocidad - Modificado para ocultar slider del contador
        self.sel_counter = Selector(1, 0, 'Contador', None, '{0:d}', None, None, show_slider=False, parent=self)
        self.sel_counter.set_value(0)

        # Botones más pequeños y cuadrados (75x75 píxeles)
        self.btn_speed_plus = CustomButton(2, 1, '+', size=(75, 75))
        self.btn_speed_minus = CustomButton(0, 1, '-', size=(75, 75))

        self.sel_speed = Selector(1, 1, 'Velocidad', Config.speeds, '{0:d}/min', 
                                  self.btn_speed_plus, self.btn_speed_minus, 
                                  self.update_speed, parent=self)

        # Conectar botones de velocidad
        self.btn_speed_plus.clicked.connect(self.sel_speed.next_value)
        self.btn_speed_minus.clicked.connect(self.sel_speed.prev_value)

        box_speed = Container(elements=[
            self.sel_counter,
            self.btn_speed_plus,
            self.sel_speed,
            self.btn_speed_minus
        ], parent=self)
        
        # Área de barra de luz - Botones más pequeños y cuadrados
        # Crear un layout para contener la etiqueta y el switch
        self.light_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_light = PyQtSwitch()
        self.switch_light.setAnimation(True) 
        self.switch_light.setCircleDiameter(30)
        self.switch_light.toggled.connect(self.update_light)
        self.light_switch_container.add_switch(self.switch_light)
        self.switch_light.get_value = lambda: self.switch_light.isChecked()
        self.switch_light.set_value = lambda value: self.switch_light.setChecked(value)

        self.btn_light_test = CustomButton(2, 0, 'Prueba', self.light_test_click, togglable=True)

        self.btn_light_color_plus = CustomButton(2, 1, '>>', size=(75, 75))
        self.btn_light_color_minus = CustomButton(0, 1, '<<', size=(75, 75))
        self.sel_light_color = Selector(1, 1, 'Color', Config.colors, '{0}',
                                        self.btn_light_color_plus, self.btn_light_color_minus,
                                        self.update_light, cyclic=True, parent=self)

        # Conectar botones de color
        self.btn_light_color_plus.clicked.connect(self.sel_light_color.next_value)
        self.btn_light_color_minus.clicked.connect(self.sel_light_color.prev_value)

        self.btn_light_intens_plus = CustomButton(2, 2, '+', size=(75, 75))
        self.btn_light_intens_minus = CustomButton(0, 2, '-', size=(75, 75))
        self.sel_light_intens = Selector(1, 2, 'Brillo', Config.intensities, '{0:d}%',
                                         self.btn_light_intens_plus, self.btn_light_intens_minus,
                                         self.update_light, parent=self)

        # Conectar botones de intensidad
        self.btn_light_intens_plus.clicked.connect(self.sel_light_intens.next_value)
        self.btn_light_intens_minus.clicked.connect(self.sel_light_intens.prev_value)

        box_lightbar = Container(elements=[
            self.light_switch_container,  # Reemplaza los botones ON/OFF
            self.btn_light_test,
            self.btn_light_color_plus,
            self.sel_light_color,
            self.btn_light_color_minus,
            self.btn_light_intens_plus,
            self.sel_light_intens,
            self.btn_light_intens_minus
        ], parent=self)
        
        # Área de buzzer - Continuar con el resto de la interfaz
        self.buzzer_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_buzzer = PyQtSwitch()
        self.switch_buzzer.setAnimation(True)
        self.switch_buzzer.toggled.connect(self.update_buzzer)
        self.buzzer_switch_container.add_switch(self.switch_buzzer)
        self.switch_buzzer.get_value = lambda: self.switch_buzzer.isChecked()
        self.switch_buzzer.set_value = lambda value: self.switch_buzzer.setChecked(value)
        
        self.btn_buzzer_test = CustomButton(2, 0, 'Prueba', self.buzzer_test_click)
        
        self.btn_buzzer_duration_plus = CustomButton(2, 1, '+', size=(75, 75))
        self.btn_buzzer_duration_minus = CustomButton(0, 1, '-', size=(75, 75))
        self.sel_buzzer_duration = Selector(1, 1, 'Duración', Config.durations, '{0:d} ms', 
                                            self.btn_buzzer_duration_plus, self.btn_buzzer_duration_minus, 
                                            self.update_buzzer, parent=self)

        # Conectar botones de duración del buzzer
        self.btn_buzzer_duration_plus.clicked.connect(self.sel_buzzer_duration.next_value)
        self.btn_buzzer_duration_minus.clicked.connect(self.sel_buzzer_duration.prev_value)

        box_buzzer = Container(elements=[
            self.buzzer_switch_container,  # Reemplaza los botones ON/OFF
            self.btn_buzzer_test,
            self.btn_buzzer_duration_plus,
            self.sel_buzzer_duration,
            self.btn_buzzer_duration_minus
        ], parent=self)
        
        # Área de auriculares
        self.headphone_switch_container = SwitchContainer("On/Off:", 0, 0)
        self.switch_headphone = PyQtSwitch()
        self.switch_headphone.setAnimation(True)
        self.switch_headphone.setCircleDiameter(30)
        self.switch_headphone.toggled.connect(self.update_sound)
        self.headphone_switch_container.add_switch(self.switch_headphone)
        self.switch_headphone.get_value = lambda: self.switch_headphone.isChecked()
        self.switch_headphone.set_value = lambda value: self.switch_headphone.setChecked(value)

        self.btn_headphone_test = CustomButton(2, 0, 'Prueba', self.headphone_test_click)
        
        self.btn_headphone_volume_plus = CustomButton(2, 1, '+', size=(75, 75))
        self.btn_headphone_volume_minus = CustomButton(0, 1, '-', size=(75, 75))
        self.sel_headphone_volume = Selector(1, 1, 'Volumen', Config.volumes, '{0:d}%',
                                             self.btn_headphone_volume_plus, self.btn_headphone_volume_minus, 
                                             self.update_sound, parent=self)

        # Conectar botones de volumen
        self.btn_headphone_volume_plus.clicked.connect(self.sel_headphone_volume.next_value)
        self.btn_headphone_volume_minus.clicked.connect(self.sel_headphone_volume.prev_value)

        self.btn_headphone_tone_plus = CustomButton(2, 2, '>>', size=(75, 75))
        self.btn_headphone_tone_minus = CustomButton(0, 2, '<<', size=(75, 75))
        self.sel_headphone_tone = Selector(1, 2, 'Tono/Duración', Config.tones, '{0}',
                                           self.btn_headphone_tone_plus, self.btn_headphone_tone_minus, 
                                           self.update_sound, cyclic=True, parent=self)

        # Conectar botones de tono
        self.btn_headphone_tone_plus.clicked.connect(self.sel_headphone_tone.next_value)
        self.btn_headphone_tone_minus.clicked.connect(self.sel_headphone_tone.prev_value)

        box_headphone = Container(elements=[
            self.headphone_switch_container,  # Reemplaza los botones ON/OFF
            self.btn_headphone_test,
            self.btn_headphone_volume_plus,
            self.sel_headphone_volume,
            self.btn_headphone_volume_minus,
            self.btn_headphone_tone_plus,
            self.sel_headphone_tone,
            self.btn_headphone_tone_minus
        ], parent=self)
        
        self.stacked_layout.addWidget(box_speed) # Index 0
        self.stacked_layout.addWidget(box_lightbar) # Index 1
        self.stacked_layout.addWidget(box_buzzer) # Index 2
        self.stacked_layout.addWidget(box_headphone) # Index 3
        
        # Configurar fondo
        self.setStyleSheet("background-color: white;")
        
        # Eliminar la inicialización automática del timer de USB
        self.probe_timer = QTimer(self)
        self.probe_timer.timeout.connect(self.scan_usb)
        # self.probe_timer.start(1000)  # Comentar o eliminar esta línea
        
        # Conectar ACTION_EVENT con su manejador
        event_system.action_event.connect(self.action)
        
        # Inicializar pero sin verificar USB
        self.config_mode()
        self.reset_action()
    
    def activate(self, elem):
        """Activa un elemento de la UI"""
        if not elem.active:
            elem.setActive(True)
    
    def deactivate(self, elem):
        """Desactiva un elemento de la UI"""
        if elem.active:
            elem.setActive(False)
    
    def lightbar_click(self):
        """Maneja el clic en el botón de la barra de luz"""
        if self.btn_lightbar.isChecked():
            self.set_area('lightbar')
        else:
            self.set_area('speed')
    
    def buzzer_click(self):
        """Maneja el clic en el botón de buzzer"""
        if self.btn_buzzer.isChecked():
            self.set_area('buzzer')
        else:
            self.set_area('speed')
    
    def headphone_click(self):
        """Maneja el clic en el botón de auriculares"""
        if self.btn_headphone.isChecked():
            self.set_area('headphone')
        else:
            self.set_area('speed')
    
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
        self.stacked_layout.setCurrentIndex(self.areas[area])
        
        # Gestionar botones togglables
        if self.btn_lightbar.isChecked() and area != 'lightbar':
            self.btn_lightbar.setChecked(False)
        if self.btn_buzzer.isChecked() and area != 'buzzer':
            self.btn_buzzer.setChecked(False)
        if self.btn_headphone.isChecked() and area != 'headphone':
            self.btn_headphone.setChecked(False)
        
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
            # self.switch_light.set_value(Config.data.get('lightbar.on'))
            self.switch_light.set_value(True)
            self.sel_light_color.set_value(Config.data.get('lightbar.color'))
            self.sel_light_intens.set_value(Config.data.get('lightbar.intensity'))
            # self.switch_buzzer.set_value(Config.data.get('buzzer.on'))
            self.switch_buzzer.set_value(True)
            self.sel_buzzer_duration.set_value(Config.data.get('buzzer.duration'))
            # self.switch_headphone.set_value(Config.data.get('headphone.on'))
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
        # No iniciar el temporizador de sondeo automático
        # self.probe_timer.start(1000)  # Mantener comentado
        
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
        self.action_delay = (60 / self.sel_speed.get_value() / Devices.led_num / 2)
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
        self.set_area('speed')
        self.max_counter = 0
        self.reset_action()
        self.action_mode()

    def start24_click(self):
        """Maneja clic en el botón Start24 (Play24)"""
        self.set_area('speed')
        self.max_counter = 24
        self.reset_action()
        self.action_mode()

    def stop_click(self):
        """Maneja clic en el botón Stop"""
        if self.btn_pause.isChecked():
            self.btn_pause.setChecked(False)
        if self.mode == 'action':
            self.stopping = True
        else:
            self.config_mode()
            self.reset_action()

    def pause_click(self):
        """Maneja clic en el botón Pause"""
        if self.btn_pause.isChecked():
            # pause
            self.pausing = True
        else:
            # resume
            if self.mode != 'action':
                self.action_mode()
            else:
                self.pausing = False
                self.action_extra_delay = 0
                self.decay = False

    def reset_action(self):
        """Reinicia la acción EMDR"""
        print('reset_action')
        self.led_pos = int(Devices.led_num / 2) + 1  # start in the middle
        self.direction = -1
        self.decay = False
        Devices.set_led(self.led_pos if self.switch_light.get_value() else 0)
    
    def action(self):
        """Maneja un paso en la secuencia EMDR"""
        # Eliminamos el parámetro event ya que usamos signals
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
        
        # Actualizar el estado de los botones según los dispositivos encontrados
        if "Master Controller" in found_devices:
            # Verificar lightbar
            if "Lightbar" in found_devices:
                self.activate(self.btn_lightbar)
            else:
                self.deactivate(self.btn_lightbar)
            
            # Verificar buzzer
            if "Buzzer" in found_devices:
                self.activate(self.btn_buzzer)
            else:
                self.deactivate(self.btn_buzzer)
                
            # Siempre activar los botones de inicio si existe el controlador maestro
            if self.mode == 'config':
                self.activate(self.btn_start)
                self.activate(self.btn_start24)
        else:
            # No hay controlador maestro, desactivar todos los controles
            self.deactivate(self.btn_lightbar)
            self.deactivate(self.btn_buzzer)
            self.deactivate(self.btn_start)
            self.deactivate(self.btn_start24)
        
        # Actualizar la etiqueta de estado de dispositivos
        self.update_device_status_label(found_devices)
        
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
    controller.set_area('speed')
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Antes de salir, guardar configuración
    app.aboutToQuit.connect(controller.closeEvent)
    
    sys.exit(app.exec())