from threading import Lock
import pickle

class Config():
    colors = [
        ('Blanco', 255, 255, 255),
        ('Rojo', 255, 0, 0),
        ('Verde', 0, 255, 0),
        ('Azul', 0, 0, 255),
        ('Amarillo', 255, 255, 0),
    ]
    intensities = [
        20, 40, 60, 80, 100
    ]
    speeds = [
        10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 140
    ]
    durations = [
        100, 200, 300, 400, 500, 600, 800, 1000
    ]
    volumes = [
        20, 40, 60, 80, 100
    ]
    tones = [
        ('Medio/Corto', 440, 50),
        ('Medio/Largo', 440, 100),
        ('Alto/Corto', 880, 100),
        ('Alto/Largo', 880, 200),
        ('Bajo/Corto', 220, 25),
        ('Bajo/Largo', 220, 50),
    ]
    data = {
        'general.speed': 10,
        'lightbar.on': True,
        'lightbar.intensity': 20,
        'lightbar.color': colors[0],
        'buzzer.on': True,
        'buzzer.duration': 100,
        'headphone.on': True,
        'headphone.volume': 0.5,
        'headphone.tone': tones[0],
    }

    @classmethod
    def load(cls):
        try:
            with open('emdr.config', 'rb') as f:
                cls.data = pickle.load(f)
        except:
            pass

    @classmethod
    def save(cls):
        with open('emdr.config', 'wb') as f:
            pickle.dump(cls.data, f)