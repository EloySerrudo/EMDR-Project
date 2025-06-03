import numpy as np
import wave
import os
from pathlib import Path

class EMDRAudioGenerator:
    """Generador de archivos de audio WAV para estimulación EMDR bilateral"""
    
    def __init__(self, output_dir=None):
        self.fs = 44100  # Frecuencia de muestreo estándar
        self.duration = 0.15  # Duración óptima para EMDR (150ms)
        self.fade_duration = 0.02  # Fade suave (20ms)
        self.amplitude = 0.6  # Amplitud moderada para evitar distorsión
        
        # Determinar la ruta del directorio de salida
        if output_dir is None:
            # Obtener la ruta del directorio actual del script
            current_dir = Path(__file__).parent
            # Navegar hasta el directorio raíz del proyecto y crear la ruta de recursos
            project_root = current_dir.parent
            output_dir = project_root / "resources" / "tones"
        else:
            output_dir = Path(output_dir)
        
        # Crear directorio de salida (crear toda la estructura si no existe)
        self.output_path = output_dir
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Definir 8 tonos diferentes para EMDR
        # Frecuencias seleccionadas para ser agradables y distinguibles
        self.tones = {
            'tone_01_pure_440Hz': {
                'frequency': 440.0,
                'wave_type': 'sine',
                'description': 'La natural - Tono puro suave'
            },
            'tone_02_warm_330Hz': {
                'frequency': 329.63,
                'wave_type': 'sine',
                'description': 'Mi - Tono cálido medio'
            },
            'tone_03_deep_261Hz': {
                'frequency': 261.63,
                'wave_type': 'sine',
                'description': 'Do medio - Tono profundo'
            },
            'tone_04_bright_523Hz': {
                'frequency': 523.25,
                'wave_type': 'sine',
                'description': 'Do alto - Tono brillante'
            },
            'tone_05_soft_392Hz': {
                'frequency': 392.00,
                'wave_type': 'sine_soft',
                'description': 'Sol - Tono suave con armónicos'
            },
            'tone_06_mellow_293Hz': {
                'frequency': 293.66,
                'wave_type': 'sine_soft',
                'description': 'Re - Tono meloso'
            },
            'tone_07_gentle_349Hz': {
                'frequency': 349.23,
                'wave_type': 'triangle',
                'description': 'Fa - Onda triangular suave'
            },
            'tone_08_calm_493Hz': {
                'frequency': 493.88,
                'wave_type': 'triangle',
                'description': 'Si - Onda triangular calmante'
            }
        }
    
    def create_envelope(self, samples):
        """Crea un envelope ADSR para suavizar inicio y final"""
        envelope = np.ones(samples)
        fade_samples = int(self.fs * self.fade_duration)
        
        # Attack - Fade in suave
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        
        # Release - Fade out suave
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        
        return envelope
    
    def generate_wave(self, frequency, wave_type='sine'):
        """Genera diferentes tipos de ondas según el tipo especificado"""
        samples = int(self.fs * self.duration)
        t = np.linspace(0, self.duration, samples, endpoint=False)
        
        if wave_type == 'sine':
            # Onda sinusoidal pura
            wave = np.sin(2 * np.pi * frequency * t)
            
        elif wave_type == 'sine_soft':
            # Onda sinusoidal con ligeros armónicos para suavidad
            wave = (np.sin(2 * np.pi * frequency * t) + 
                   0.1 * np.sin(2 * np.pi * frequency * 2 * t) +
                   0.05 * np.sin(2 * np.pi * frequency * 3 * t))
            wave = wave / np.max(np.abs(wave))  # Normalizar
            
        elif wave_type == 'triangle':
            # Onda triangular suave
            wave = 2 * np.arcsin(np.sin(2 * np.pi * frequency * t)) / np.pi
            
        else:
            # Por defecto, onda sinusoidal
            wave = np.sin(2 * np.pi * frequency * t)
        
        return wave
    
    def create_stereo_files(self, tone_name, tone_config):
        """Crea archivos estéreo para estimulación bilateral"""
        frequency = tone_config['frequency']
        wave_type = tone_config['wave_type']
        description = tone_config['description']
        
        print(f"Generando: {tone_name} - {description}")
        
        # Generar la forma de onda base
        mono_wave = self.generate_wave(frequency, wave_type)
        
        # Aplicar envelope
        samples = len(mono_wave)
        envelope = self.create_envelope(samples)
        shaped_wave = mono_wave * envelope * self.amplitude
        
        # Convertir a formato de 16 bits
        audio_data = (shaped_wave * 32767).astype(np.int16)
        
        # Crear versión estéreo - canal izquierdo activo
        stereo_left = np.zeros((samples, 2), dtype=np.int16)
        stereo_left[:, 0] = audio_data  # Canal izquierdo
        stereo_left[:, 1] = 0           # Canal derecho silencioso
        
        # Crear versión estéreo - canal derecho activo  
        stereo_right = np.zeros((samples, 2), dtype=np.int16)
        stereo_right[:, 0] = 0          # Canal izquierdo silencioso
        stereo_right[:, 1] = audio_data # Canal derecho
        
        # Guardar archivos WAV
        left_filename = self.output_path / f"{tone_name}_LEFT.wav"
        right_filename = self.output_path / f"{tone_name}_RIGHT.wav"
        
        self.save_wav_file(left_filename, stereo_left)
        self.save_wav_file(right_filename, stereo_right)
        
        return left_filename, right_filename
    
    def save_wav_file(self, filename, stereo_data):
        """Guarda datos de audio en formato WAV"""
        with wave.open(str(filename), 'w') as wav_file:
            wav_file.setnchannels(2)  # Estéreo
            wav_file.setsampwidth(2)  # 16 bits
            wav_file.setframerate(self.fs)  # 44.1 kHz
            wav_file.writeframes(stereo_data.tobytes())
    
    def generate_all_tones(self):
        """Genera todos los archivos de audio EMDR"""
        print("Generando archivos de audio WAV para estimulación EMDR...")
        print(f"Configuración: {self.fs}Hz, {self.duration*1000:.0f}ms duración")
        print(f"Directorio de salida: {self.output_path.absolute()}")
        print("-" * 60)
        
        generated_files = []
        
        for tone_name, tone_config in self.tones.items():
            try:
                left_file, right_file = self.create_stereo_files(tone_name, tone_config)
                generated_files.extend([left_file, right_file])
                print(f"  ✓ {left_file.name}")
                print(f"  ✓ {right_file.name}")
                
            except Exception as e:
                print(f"  ✗ Error generando {tone_name}: {e}")
        
        print("-" * 60)
        print(f"Generación completada: {len(generated_files)} archivos creados")
        print(f"Archivos guardados en: {self.output_path.absolute()}")
        
        return generated_files
    
    def create_tone_mapping(self):
        """Crea un diccionario para mapear tonos con sus archivos"""
        tone_mapping = {}
        
        for i, (tone_name, tone_config) in enumerate(self.tones.items()):
            tone_mapping[i] = {
                'name': tone_name,
                'description': tone_config['description'],
                'frequency': tone_config['frequency'],
                'left_file': f"{tone_name}_LEFT.wav",
                'right_file': f"{tone_name}_RIGHT.wav",
                'full_path_left': str(self.output_path / f"{tone_name}_LEFT.wav"),
                'full_path_right': str(self.output_path / f"{tone_name}_RIGHT.wav")
            }
        
        return tone_mapping


def main():
    """Función principal para generar los archivos de audio"""
    print("=== Generador de Tonos EMDR ===")
    print("Generando archivos WAV en directorio de recursos del proyecto...")
    print()
    
    # Crear el generador (automáticamente usará src/resources/tones/)
    generator = EMDRAudioGenerator()
    
    # Generar todos los tonos
    files = generator.generate_all_tones()
    
    # Crear mapeo de tonos
    tone_mapping = generator.create_tone_mapping()
    
    print("\nMapeo de tonos generado:")
    for idx, info in tone_mapping.items():
        print(f"  {idx}: {info['description']} ({info['frequency']:.1f}Hz)")
    
    print(f"\nEstructura de directorios creada:")
    print(f"  📁 src/")
    print(f"    📁 resources/")
    print(f"      📁 tones/")
    print(f"        🎵 {len(files)} archivos .wav")
    
    print(f"\nUso recomendado:")
    print(f"- Cargar archivos desde: src/resources/tones/")
    print(f"- Alternar reproducción: izquierdo → derecho → izquierdo...")
    print(f"- Cada archivo tiene {generator.duration*1000:.0f}ms de duración")
    print(f"- Optimizado para estimulación EMDR bilateral")


if __name__ == "__main__":
    main()