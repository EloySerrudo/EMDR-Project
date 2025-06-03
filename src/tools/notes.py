import pygame
import numpy as np
import time

# Diccionario de notas y frecuencias (escala temperada)
notas = {
    'C4': 261.63,   # Do
    'D4': 293.66,   # Re
    'E4': 329.63,   # Mi
    'F4': 349.23,   # Fa
    'G4': 392.00,   # Sol
    'A4': 440.00,   # La
    'B4': 493.88,   # Si
    'C5': 523.25,   # Do (octava superior)
}

fs = 44100        # Frecuencia de muestreo
duration = 0.1    # Duración de cada nota (segundos)
fade_duration = 0.025  # Duración del fade in/out (segundos)

def create_envelope(samples, fade_samples):
    """Crea un envelope ADSR simple con fade in/out"""
    envelope = np.ones(samples)
    
    # Fade in (Attack)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    
    # Fade out (Release)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    return envelope

pygame.mixer.init(frequency=fs, size=-16, channels=1)

fade_samples = int(fs * fade_duration)

for nombre, freq in notas.items():
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    
    # Generar la onda sinusoidal
    sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)
    
    # Aplicar envelope para suavizar inicio y final
    envelope = create_envelope(len(sine_wave), fade_samples)
    note = (sine_wave * envelope * 32767).astype(np.int16)
    
    sound = pygame.sndarray.make_sound(note)
    print(f"Reproduciendo nota: {nombre} ({freq:.2f} Hz)")
    sound.play()
    pygame.time.delay(int(duration * 1000))
    time.sleep(0.1)  # Pausa más corta entre notas

pygame.mixer.quit()
