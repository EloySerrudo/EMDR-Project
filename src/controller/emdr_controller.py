import sys
from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QApplication, QStackedLayout, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from numpy import log
import time
import os

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
# Importaciones de componentes de vistas
from src.views.components.containers import Container
from src.views.components.selectors import Selector
from src.views.components.buttons import CustomButton, Switch

# Importaciones de modelos
from src.models.devices import Devices
from src.models.config import Config

# Importaciones de utilidades
from src.utils.hiperf_timer import HighPerfTimer
from src.utils.events import event_system


class MyQtApp:
    """Reemplazo de thorpy.Application para PySide6"""
    
    def __init__(self, app=None, size=(800, 600), title=None, icon=None, center=True, flags=0):
        # No necesitamos hacer global _SCREEN y _CURRENT_APPLICATION como en thorpy
        # Usar QApplication existente o crear una nueva
        self.app = app if app is not None else QApplication([])  # Inicializa la aplicación Qt
        self.size = tuple(size)
        self.title = title
        
        # Crear ventana principal
        self.window = QMainWindow()
        self.window.resize(*self.size)
        
        # Establecer título si se proporciona
        if self.title:
            self.window.setWindowTitle(title)
        
        # Centrar ventana si se solicitó
        if center:
            self._center_window()
        
        # Establecer icono
        if icon is not None:  # "thorpy" era el valor predeterminado
            self._set_icon(icon)
        
        # Modo de pantalla completa
        if flags == 1:  # pygame.FULLSCREEN equivale a 1
            self.window.showFullScreen()
        
        # Ruta predeterminada como en la versión original
        self.default_path = "./"
    
    def _set_icon(self, icon):
        """Establece el icono de la ventana"""
        if isinstance(icon, str):
            try:
                self.window.setWindowIcon(QIcon(icon))
            except:
                pass  # Ignorar errores si no se puede cargar el icono
    
    def _center_window(self):
        """Centra la ventana en la pantalla"""
        frame_geo = self.window.frameGeometry()
        screen_center = self.app.primaryScreen().availableGeometry().center()
        frame_geo.moveCenter(screen_center)
        self.window.move(frame_geo.topLeft())
    
    def show(self):
        """Muestra la ventana principal"""
        self.window.show()
        
    def exec(self):
        """Ejecuta el bucle principal de la aplicación"""
        return self.app.exec()
    
    def quit(self):
        """Cierra la aplicación"""
        self.app.quit()


class EMDRControllerWidget(QWidget):
    """Controlador principal de la aplicación EMDR convertido a widget PySide6"""
    
    def __init__(self, resource_manager=None, parent=None):
        super().__init__(parent)
        self.resource_manager = resource_manager
        self.in_load = False
        self.pausing = False
        self.stopping = False
        
        # Layout Grid
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # Crear QStackedLayout
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        # Diccionario de áreas para el QStackedLayout
        self.areas = {'speed':0, 'lightbar':1, 'buzzer':2, 'headphone':3}
        # Crear contenedor para el QStackedLayout
        stacked_widget = QWidget()
        stacked_widget.setLayout(self.stacked_layout)
        # Añadir el widget al QGridLayout, posición (1,1), abarcando 3 filas y 3 columnas
        self.main_layout.addWidget(stacked_widget, 1, 1, 3, 3)  # From (1,1) to (3,3)
        
        # Agregar botón de escaneo USB en la parte inferior
        self.btn_scan_usb = CustomButton(4, 0, 'Scan USB', self.scan_usb_click)
        self.main_layout.addWidget(self.btn_scan_usb, 4, 0, 1, 4)  # Posición 4,0 ocupando 1 fila y 4 columnas
        
        # Crear botones principales
        self.btn_start = CustomButton(0, 0, 'Play', self.start_click)
        self.btn_start24 = CustomButton(1, 0, 'Play24', self.start24_click)
        self.btn_stop = CustomButton(2, 0, 'Stop', self.stop_click)
        self.btn_pause = CustomButton(3, 0, 'Pause', self.pause_click, togglable=True)
        self.btn_lightbar = CustomButton(0, 1, 'Visual', self.lightbar_click, togglable=True)
        self.btn_lightbar.setActive(False)
        self.btn_buzzer = CustomButton(0, 2, 'Táctil', self.buzzer_click, togglable=True)
        self.btn_buzzer.setActive(False)
        self.btn_headphone = CustomButton(0, 3, 'Auditiva', self.headphone_click, togglable=True)
        
        # Posicionar botones principales: Columna,Fila
        self.main_layout.addWidget(self.btn_start, self.btn_start.pos_y, self.btn_start.pos_x)
        self.main_layout.addWidget(self.btn_start24, self.btn_start24.pos_y, self.btn_start24.pos_x)
        self.main_layout.addWidget(self.btn_stop, self.btn_stop.pos_y, self.btn_stop.pos_x)
        self.main_layout.addWidget(self.btn_pause, self.btn_pause.pos_y, self.btn_pause.pos_x)
        self.main_layout.addWidget(self.btn_lightbar, self.btn_lightbar.pos_y, self.btn_lightbar.pos_x)
        self.main_layout.addWidget(self.btn_buzzer, self.btn_buzzer.pos_y, self.btn_buzzer.pos_x)
        self.main_layout.addWidget(self.btn_headphone, self.btn_headphone.pos_y, self.btn_headphone.pos_x)
        
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
        self.btn_light_on = CustomButton(0, 0, 'On', togglable=True)
        self.btn_light_off = CustomButton(1, 0, 'Off', togglable=True)
        self.switch_light = Switch(self.btn_light_on, self.btn_light_off, self.update_light)
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
        self.btn_buzzer_on = CustomButton(0, 0, 'On', togglable=True)
        self.btn_buzzer_off = CustomButton(1, 0, 'Off', togglable=True)
        self.switch_buzzer = Switch(self.btn_buzzer_on, self.btn_buzzer_off, self.update_buzzer)
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
            self.btn_buzzer_on,
            self.btn_buzzer_off,
            self.btn_buzzer_test,
            self.btn_buzzer_duration_plus,
            self.sel_buzzer_duration,
            self.btn_buzzer_duration_minus
        ], parent=self)
        
        # Área de auriculares
        self.btn_headphone_on = CustomButton(0, 0, 'On', togglable=True)
        self.btn_headphone_off = CustomButton(1, 0, 'Off', togglable=True)
        self.switch_headphone = Switch(self.btn_headphone_on, self.btn_headphone_off, self.update_sound)
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
        
        self.stacked_layout.addWidget(box_speed) # Index 0
        self.stacked_layout.addWidget(box_lightbar) # Index 1
        self.stacked_layout.addWidget(box_buzzer) # Index 2
        self.stacked_layout.addWidget(box_headphone) # Index 3
        
        # Configurar fondo
        self.setStyleSheet("background-color: white;")
        
        # Eliminar la inicialización automática del timer de USB
        self.probe_timer = QTimer(self)
        self.probe_timer.timeout.connect(self.check_usb)
        # self.probe_timer.start(1000)  # Comentar o eliminar esta línea
        
        # Conectar ACTION_EVENT con su manejador
        event_system.action_event.connect(self.action)
        
        # Inicializar pero sin verificar USB
        self.config_mode()
        self.reset_action()
        
        # No se verifican los USB en el arranque
        # self.check_usb() # Eliminar o comentar esta línea
    
    def acquire_devices(self):
        """Solicita acceso exclusivo a los dispositivos"""
        if self.resource_manager:
            return self.resource_manager.acquire_for_emdr()
        return True
    
    def release_devices(self):
        """Libera los dispositivos para otros componentes"""
        if self.resource_manager:
            self.resource_manager.release_devices()
    
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
        # No iniciar el temporizador de sondeo automático
        # self.probe_timer.start(1000)  # Comentar esta línea
        
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
        if not self.acquire_devices():
            print("No se pueden adquirir los dispositivos - otra parte de la aplicación los está usando")
            return
            
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
        
        # Liberar recursos cuando se detiene
        if self.mode == 'action':
            self.release_devices()

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
        if Devices.lightbar_plugged_in():
            if not self.btn_lightbar.active:
                Devices.set_led(Devices.led_num / 2 + 1)
            self.activate(self.btn_lightbar)
        else:
            self.deactivate(self.btn_lightbar)
        if Devices.buzzer_plugged_in():
            self.activate(self.btn_buzzer)
        else:
            self.deactivate(self.btn_buzzer)

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
                # Liberar dispositivos cuando termina la acción
                self.release_devices()
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

    def scan_usb_click(self):
        """Maneja el clic en el botón de escaneo USB y muestra dispositivos conectados"""
        # Cambiar texto del botón durante el escaneo
        old_text = self.btn_scan_usb.text()
        self.btn_scan_usb.setText("Scanning...")
        self.btn_scan_usb.setEnabled(False)
        QApplication.processEvents()  # Forzar actualización de la interfaz
        
        # Realizar el escaneo (la nueva función devuelve los dispositivos encontrados)
        found_devices = Devices.probe()
        
        # Habilitar/deshabilitar botones según dispositivos encontrados
        if "Master Controller" in found_devices:
            # Si encontramos un controlador maestro, verificamos qué dispositivos están conectados
            if "Pulse Sensor" in found_devices:
                # El sensor está conectado, podemos iniciar captura
                self.activate(self.btn_start)
                self.activate(self.btn_start24)
            
            if "Lightbar" in found_devices:
                # La barra de luz está conectada, activar su botón
                self.activate(self.btn_lightbar)
            else:
                self.deactivate(self.btn_lightbar)
            
            # El buzzer es un dispositivo directo, comprobamos si está conectado
            if Devices.buzzer_plugged_in():
                self.activate(self.btn_buzzer)
            else:
                self.deactivate(self.btn_buzzer)
        else:
            # No se encontró controlador maestro, desactivar todo
            self.deactivate(self.btn_lightbar)
            self.deactivate(self.btn_buzzer)
            self.deactivate(self.btn_start)
            self.deactivate(self.btn_start24)
        
        # Mostrar resultados en el botón temporalmente
        self.btn_scan_usb.setEnabled(True)
        
        if found_devices:
            self.btn_scan_usb.setText(f"Found: {', '.join(found_devices[-2:])}")  # Mostrar últimos 2 dispositivos
            
            # Mostrar estado de conexión en la consola
            print("Connected devices:")
            for device in found_devices:
                print(f"- {device}")
            
            # Si hay lightbar, inicializar con LED central
            if "Lightbar" in found_devices:
                Devices.set_led(Devices.led_num // 2 + 1)
        else:
            self.btn_scan_usb.setText("No devices found")
        
        # Restaurar texto original después de 2 segundos
        QTimer.singleShot(2000, lambda: self.btn_scan_usb.setText(old_text))


# Esta sección del código se mantiene para permitir ejecutar el archivo independientemente
if __name__ == "__main__":
    """Función principal que inicializa y ejecuta la aplicación EMDR Controller"""
    # Crear la aplicación Qt
    app = QApplication(sys.argv)
    
    # Analizar argumentos de línea de comandos
    fullscreen = "--fullscreen" in sys.argv
    touchscreen = "--touchscreen" in sys.argv
    
    # Crear ventana principal para modo independiente
    main_window = QMainWindow()
    main_window.setWindowTitle("EMDR Controller")
    main_window.setGeometry(100, 100, 480, 320)
    
    # Crear el widget del controlador
    controller = EMDRControllerWidget(parent=main_window)
    main_window.setCentralWidget(controller)
    
    # Configurar opciones específicas de la ventana
    if fullscreen:
        main_window.showFullScreen()
    if touchscreen:
        main_window.setCursor(Qt.BlankCursor)
    
    # Inicializar controlador
    controller.load_config()
    controller.set_area('speed')
    
    # Mostrar ventana y ejecutar aplicación
    main_window.show()
    
    # Antes de salir, guardar configuración
    app.aboutToQuit.connect(controller.save_config)
    
    sys.exit(app.exec())