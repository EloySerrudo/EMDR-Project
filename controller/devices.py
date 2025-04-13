from serial import Serial
from serial.tools.list_ports import comports
from time import sleep
import pygame
from array import array
from device_config import DEVICE_CONFIG

class Note(pygame.mixer.Sound):
    def __init__(self, frequency, volume=.33):
        self.frequency = frequency
        super().__init__(buffer=self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        period = int(round(pygame.mixer.get_init()[0] / self.frequency))
        samples = array("h", [0] * period)
        amplitude = 2 ** (abs(pygame.mixer.get_init()[1]) - 1) - 1
        for time in range(period):
            if time < period / 2:
                samples[time] = amplitude
            else:
                samples[time] = -amplitude
        return samples

class Devices():
    led_num = 60
    _buzzer_duration = 100
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    _channel_left = pygame.mixer.Channel(0)
    _channel_left.set_volume(1, 0)
    _channel_right = pygame.mixer.Channel(1)
    _channel_right.set_volume(0, 1)
    _beep = Note(440)
    _sound_duration = 50
    _lightbar = (None, None)
    _buzzer = (None, None)

    @classmethod
    def probe(cls):
        _, ser = cls._lightbar
        if ser:
            ser.close()
        cls._lightbar = (None, None)
        _, ser = cls._buzzer
        if ser:
            ser.close()
        cls._buzzer = (None, None)
        
        for p in comports():
            for d in DEVICE_CONFIG.values():
                if (p.vid, p.pid) == (d['vid'], d['pid']):
                    ser = None
                    try:
                        ser = Serial(p.device, baudrate=d['baud'], timeout=0.5)  # Timeout aumentado
                        sleep(2)
                        # Enviar 4 bytes: comando 'i' + 3 bytes a cero
                        ser.write(bytes([ord('i'), 0, 0, 0]))
                        ser.flush()
                        id_str = ser.read_until().strip()
                        print(f"Device ID: {id_str}")
                        if id_str.find(b'EMDR Lightbar') == 0:
                            cls._lightbar = (d, ser)
                        # elif id_str.find(b'EMDR Master Controller') == 0:  # Identificador del coordinador
                        elif b'EMDR Master Controller' in id_str:
                            cls._lightbar = (d, ser)  # Tratar al coordinador como si fuera un lightbar
                        elif id_str.find(b'EMDR Buzzer') == 0:
                            cls._buzzer = (d, ser)
                        else:
                            ser.close()
                    except Exception as e:
                        print(f"Error probing device: {e}")
                        if ser:
                            ser.close()
                        pass

    @classmethod
    def lightbar_plugged_in(cls):
        return cls._lightbar != (None, None)

    @classmethod
    def buzzer_plugged_in(cls):
        return cls._buzzer != (None, None)

    @classmethod
    def write(cls, devser, cmd):
        (dev, ser) = devser
        if dev and ser:
            ser.write(cmd)
            ser.flush()


    @classmethod
    def set_led(cls, num):
        if num >= 0:
            # Enviar 4 bytes: comando 'l' + posición del LED + 2 bytes a cero
            cls.write(cls._lightbar, bytes([ord('l'), int(num), 0, 0]))
        else:
            # Enviar 4 bytes: comando 't' + 3 bytes a cero
            cls.write(cls._lightbar, bytes([ord('t'), 0, 0, 0]))

    @classmethod
    def set_color(cls, col):
        r = (col >> 16) & 0xFF
        g = (col >> 8) & 0xFF
        b = col & 0xFF
        # Enviar 4 bytes: comando 'c' + r + g + b
        cls.write(cls._lightbar, bytes([ord('c'), r, g, b]))

    @classmethod
    def set_buzzer_duration(cls, duration):
        cls._buzzer_duration = duration

    @classmethod
    def do_buzzer(cls, left):
        cls.write(cls._buzzer, (b'l' if left else b'r') + b' %d\r\n' % cls._buzzer_duration)

    @classmethod
    def do_sound(cls, left):
        if left:
            cls._channel_left.play(cls._beep, cls._sound_duration)
        else:
            cls._channel_right.play(cls._beep, cls._sound_duration)

    @classmethod
    def set_tone(cls, frequency, duration, volume):
        cls._beep = Note(frequency)
        cls._sound_duration = duration
        cls._channel_left.set_volume(1 * volume, 0)
        cls._channel_right.set_volume(0, 1 * volume)
        