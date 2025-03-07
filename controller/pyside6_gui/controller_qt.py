from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QApplication
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon
import os
import sys
from math import log
import time

# Importar componentes convertidos a Qt
from app_qt import MyQtApp
from custom_button import CustomButton
from container_qt import Container
from selector_qt import Selector
from switch_qt import Switch
from events_qt import event_system
from devices import Devices  # Podemos seguir usando esta clase
from config import Config    # Podemos seguir usando esta clase
from hiperf_timer import HighPerfTimer  # Podemos seguir usando esta clase o reemplazarla con QTimer

class Controller(QMainWindow):
    """Controlador principal de la aplicación EMDR convertido a PySide6"""
    
    def __init__(self, app=None, fullscreen=False, touchscreen=False):
        self.in_load = False
        self.pausing = False
        self.stopping = False
        
        # Crear aplicación Qt usando la app existente si se proporciona
        self.app = MyQtApp(app=app, size=(480, 320), caption="EMDR Controller", icon='imgs/icon.png', 
                          flags=1 if fullscreen else 0)  # 1 = pantalla completa
        
        # Configurar ventana principal
        super().__init__()
        self.app.window = self  # La ventana principal es este controlador
        self.resize(*self.app.size)
        self.setWindowTitle(self.app.caption)
        
        # Widget central
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        if touchscreen:
            # No hay cursor de ratón en modo táctil (equivalente a ocultar cursor en pygame)
            self.setCursor(Qt.BlankCursor)
        
        # Crear botones principales
        self.btn_start = self.button(0, 0, 'Play', self.start_click)
        self.btn_start24 = self.button(1, 0, 'Play24', self.start24_click)
        self.btn_stop = self.button(2, 0, 'Stop', self.stop_click)
        self.btn_pause = self.button(3, 0, 'Pause', self.pause_click, togglable=True)
        self.btn_lightbar = self.button(0, 1, 'Light', self.lightbar_click, togglable=True)
        self.btn_lightbar.setActive(False)
        self.btn_buzzer = self.button(0, 2, 'Buzzer', self.buzzer_click, togglable=True)
        self.btn_buzzer.setActive(False)
        self.btn_headphone = self.button(0, 3, 'Sound', self.headphone_click, togglable=True)
        
        # Área de velocidad
        self.sel_counter = Selector(2, 1, 'Counter', None, '{0:d}', None, None, parent=self)
        self.sel_counter.set_value(0)
        self.btn_speed_plus = self.button(3, 2, '+')
        self.btn_speed_minus = self.button(1, 2, '-')
        self.sel_speed = Selector(2, 2, 'Speed.', Config.speeds, '{0:d}/min', 
                                 self.btn_speed_plus, self.btn_speed_minus, 
                                 self.update_speed, parent=self)
        
        self.box_speed = Container(elements=[
            self.sel_counter,
            self.btn_speed_plus,
            self.sel_speed,
            self.btn_speed_minus
        ], parent=self)
        
        # Área de barra de luz
        self.btn_light_on = self.button(1, 1, 'On', togglable=True)
        self.btn_light_off = self.button(2, 1, 'Off', togglable=True)
        self.switch_light = Switch(self.btn_light_on, self.btn_light_off, self.update_light)
        self.btn_light_test = self.button(3, 1, 'Test', self.light_test_click, togglable=True)
        
        self.btn_light_color_plus = self.button(3, 2, '+')
        self.btn_light_color_minus = self.button(1, 2, '-')
        self.sel_light_color = Selector(2, 2, 'Colour', Config.colors, '{0}', 
                                      self.btn_light_color_plus, self.btn_light_color_minus, 
                                      self.update_light, cyclic=True, parent=self)
        
        self.btn_light_intens_plus = self.button(3, 3, '+')
        self.btn_light_intens_minus = self.button(1, 3, '-')
        self.sel_light_intens = Selector(2, 3, 'Brightness', Config.intensities, '{0:d}%', 
                                       self.btn_light_intens_plus, self.btn_light_intens_minus, 
                                       self.update_light, parent=self)
        
        self.box_lightbar = Container(elements=[
            self.btn_light_on,
            self.btn_light_off,
            self.btn_light_test,
            self.btn_light_color_plus,
            self.sel_light_color,
            self.btn_light_color_minus,
            self.btn_light_intens_plus,
            self.sel_light_intens,
            self.btn_light_intens_minus
        ], parent=self)
        
        # Área de buzzer - Continuar con el resto de la interfaz
        self.btn_buzzer_on = self.button(1, 1, 'On', togglable=True)
        self.btn_buzzer_off = self.button(2, 1, 'Off', togglable=True)
        self.switch_buzzer = Switch(self.btn_buzzer_on, self.btn_buzzer_off, self.update_buzzer)
        self.btn_buzzer_test = self.button(3, 1, 'Test', self.buzzer_test_click)
        
        self.btn_buzzer_duration_plus = self.button(3, 2, '+')
        self.btn_buzzer_duration_minus = self.button(1, 2, '-')
        self.sel_buzzer_duration = Selector(2, 2, 'Duration', Config.durations, '{0:d} ms', 
                                          self.btn_buzzer_duration_plus, self.btn_buzzer_duration_minus, 
                                          self.update_buzzer, parent=self)
        
        self.box_buzzer = Container(elements=[
            self.btn_buzzer_on,
            self.btn_buzzer_off,
            self.btn_buzzer_test,
            self.btn_buzzer_duration_plus,
            self.sel_buzzer_duration,
            self.btn_buzzer_duration_minus
        ], parent=self)
        
        # Área de auriculares
        self.btn_headphone_on = self.button(1, 1, 'On', togglable=True)
        self.btn_headphone_off = self.button(2, 1, 'Off', togglable=True)
        self.switch_headphone = Switch(self.btn_headphone_on, self.btn_headphone_off, self.update_sound)
        self.btn_headphone_test = self.button(3, 1, 'Test', self.headphone_test_click)
        
        self.btn_headphone_volume_plus = self.button(3, 2, '+')
        self.btn_headphone_volume_minus = self.button(1, 2, '-')
        self.sel_headphone_volume = Selector(2, 2, 'Volume', Config.volumes, '{0:d}%', 
                                           self.btn_headphone_volume_plus, self.btn_headphone_volume_minus, 
                                           self.update_sound, parent=self)
        
        self.btn_headphone_tone_plus = self.button(3, 3, '+')
        self.btn_headphone_tone_minus = self.button(1, 3, '-')
        self.sel_headphone_tone = Selector(2, 3, 'Sound', Config.tones, '{0}', 
                                         self.btn_headphone_tone_plus, self.btn_headphone_tone_minus, 
                                         self.update_sound, cyclic=True, parent=self)
        
        self.box_headphone = Container(elements=[
            self.btn_headphone_on,
            self.btn_headphone_off,
            self.btn_headphone_test,
            self.btn_headphone_volume_plus,
            self.sel_headphone_volume,
            self.btn_headphone_volume_minus,
            self.btn_headphone_tone_plus,
            self.sel_headphone_tone,
            self.btn_headphone_tone_minus
        ], parent=self)
        
        # Configurar fondo
        self.central_widget.setStyleSheet("background-color: white;")
        
        # Conectar eventos
        self.probe_timer = QTimer(self)
        self.probe_timer.timeout.connect(self.check_usb)
        
        # Conectar ACTION_EVENT con su manejador
        event_system.action_event.connect(self.action)
        
        # Inicializar
        self.config_mode()
        self.reset_action()
        self.activate(self.btn_lightbar)
        self.deactivate(self.btn_lightbar)
        self.activate(self.btn_buzzer)
        self.deactivate(self.btn_buzzer)
        self.check_usb()
    
    def button(self, x, y, title, callback=None, togglable=False):
        """Crea un botón personalizado con imagen"""
        btn = CustomButton(title, callback, togglable, self)
        
        # Calcular posición
        pos_x = 60 + 120 * x
        pos_y = 40 + 80 * y
        
        btn.move(pos_x - btn.width()//2, pos_y - btn.height()//2)
        return btn
    
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
    
    # Añadir a la clase Controller existente:

    def update_buzzer(self):
        """Actualiza la configuración del buzzer"""
        duration = self.sel_buzzer_duration.get_value()
        Devices.set_buzzer_duration(duration)
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
        self.box_speed.set_visible(area == 'speed')
        self.box_lightbar.set_visible(area == 'lightbar')
        self.box_buzzer.set_visible(area == 'buzzer')
        self.box_headphone.set_visible(area == 'headphone')
        
        
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
            self.switch_light.set_value(Config.data.get('lightbar.on'))
            self.sel_light_color.set_value(Config.data.get('lightbar.color'))
            self.sel_light_intens.set_value(Config.data.get('lightbar.intensity'))
            self.switch_buzzer.set_value(Config.data.get('buzzer.on'))
            self.sel_buzzer_duration.set_value(Config.data.get('buzzer.duration'))
            self.switch_headphone.set_value(Config.data.get('headphone.on'))
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
        # Iniciar temporizador de sondeo (reemplaza pygame.time.set_timer)
        # self.probe_timer.start(1000)  # cada 1000ms = 1s <-------- EDITADO
        
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
    
    def run(self):
        """Ejecuta la aplicación - inicialización y bucle principal"""
        self.load_config()
        self.set_area('speed')
        # Las líneas self.menu.play() y app.quit() se manejan ahora en test_controller.py
        # La aplicación se ejecuta al llamar a app.exec()
        return self.app.exec()

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

    def check_usb(self):
        """Verifica los dispositivos USB conectados"""
        # Eliminamos el parámetro event que no se usa
        if self.mode == 'action':
            return
        Devices.probe()
        if Devices.buzzer_plugged_in():
            self.activate(self.btn_buzzer)
        else:
            self.deactivate(self.btn_buzzer)
        if Devices.lightbar_plugged_in():
            if not self.btn_lightbar.active:
                Devices.set_led(Devices.led_num / 2 + 1)
            self.activate(self.btn_lightbar)
        else:
            self.deactivate(self.btn_lightbar)

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

    # Añadir este método para manejar el cierre de la ventana
    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        self.save_config()
        # Opcional: apagar todos los dispositivos al salir
        Devices.set_led(0)
        event.accept()  # Acepta el cierre