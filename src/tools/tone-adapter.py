import numpy as np
import wave
import os
from pathlib import Path

class EMDRWavProcessor:
    """Procesador de archivos WAV mono para convertirlos a formato EMDR bilateral"""
    
    def __init__(self, input_dir=None, output_dir=None):
        self.fs = 44100  # Frecuencia de muestreo estándar
        self.target_duration = 0.15  # Duración objetivo para EMDR (150ms)
        self.fade_duration = 0.02  # Fade suave (20ms)
        self.amplitude = 0.6  # Amplitud moderada para evitar distorsión
        
        # Determinar la ruta del directorio de entrada
        if input_dir is None:
            current_dir = Path(__file__).parent
            project_root = current_dir.parent
            input_dir = project_root / "resources" / "tones"
        else:
            input_dir = Path(input_dir)
        
        # Determinar la ruta del directorio de salida (mismo que entrada por defecto)
        if output_dir is None:
            output_dir = input_dir
        else:
            output_dir = Path(output_dir)
        
        self.input_path = input_dir
        self.output_path = output_dir
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def load_wav_file(self, filename):
        """Carga un archivo WAV y extrae sus datos"""
        filepath = self.input_path / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {filepath}")
        
        with wave.open(str(filepath), 'r') as wav_file:
            # Obtener parámetros del archivo
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            frames = wav_file.getnframes()
            
            print(f"Archivo original:")
            print(f"  - Canales: {channels}")
            print(f"  - Bits: {sample_width * 8}")
            print(f"  - Frecuencia: {framerate} Hz")
            print(f"  - Duración: {frames / framerate:.3f} segundos")
            
            # Leer datos de audio
            audio_data = wav_file.readframes(frames)
            
            # Convertir a numpy array
            if sample_width == 1:
                audio_array = np.frombuffer(audio_data, dtype=np.uint8)
                # Convertir de unsigned a signed
                audio_array = audio_array.astype(np.float32) - 128
                audio_array = audio_array / 128.0
            elif sample_width == 2:
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif sample_width == 3:
                # 24-bit audio
                audio_array = np.frombuffer(audio_data, dtype=np.uint8)
                audio_array = audio_array.reshape(-1, 3)
                audio_array = ((audio_array[:, 2].astype(np.int32) << 16) |
                              (audio_array[:, 1].astype(np.int32) << 8) |
                              audio_array[:, 0].astype(np.int32))
                # Convertir a signed 24-bit
                audio_array = np.where(audio_array >= 2**23, 
                                     audio_array - 2**24, audio_array)
                audio_array = audio_array.astype(np.float32) / (2**23)
            elif sample_width == 4:
                audio_array = np.frombuffer(audio_data, dtype=np.int32)
                audio_array = audio_array.astype(np.float32) / (2**31)
            else:
                raise ValueError(f"Formato de bits no soportado: {sample_width * 8}")
            
            # Si es estéreo, convertir a mono promediando los canales
            if channels == 2:
                audio_array = audio_array.reshape(-1, 2)
                audio_array = np.mean(audio_array, axis=1)
                print(f"  - Convertido de estéreo a mono")
            
            return audio_array, framerate
    
    def resample_audio(self, audio_data, original_fs):
        """Remuestrea el audio a la frecuencia objetivo si es necesario"""
        if original_fs != self.fs:
            print(f"  - Remuestreando de {original_fs}Hz a {self.fs}Hz")
            # Interpolación simple para remuestreo
            original_length = len(audio_data)
            new_length = int(original_length * self.fs / original_fs)
            
            # Crear índices para interpolación
            old_indices = np.linspace(0, original_length - 1, original_length)
            new_indices = np.linspace(0, original_length - 1, new_length)
            
            # Interpolar
            resampled_audio = np.interp(new_indices, old_indices, audio_data)
            return resampled_audio
        
        return audio_data
    
    def adjust_duration(self, audio_data):
        """Ajusta la duración del audio al objetivo EMDR"""
        current_duration = len(audio_data) / self.fs
        target_samples = int(self.fs * self.target_duration)
        
        print(f"  - Duración original: {current_duration:.3f}s")
        print(f"  - Duración objetivo: {self.target_duration:.3f}s")
        
        if len(audio_data) > target_samples:
            # Truncar al centro del audio
            start = (len(audio_data) - target_samples) // 2
            audio_data = audio_data[start:start + target_samples]
            print(f"  - Audio truncado al centro")
        elif len(audio_data) < target_samples:
            # Repetir el audio hasta alcanzar la duración objetivo
            repeats = target_samples // len(audio_data) + 1
            audio_data = np.tile(audio_data, repeats)[:target_samples]
            print(f"  - Audio repetido para alcanzar duración objetivo")
        
        return audio_data
    
    def create_envelope(self, samples):
        """Crea un envelope ADSR para suavizar inicio y final"""
        envelope = np.ones(samples)
        fade_samples = int(self.fs * self.fade_duration)
        
        if fade_samples > 0 and fade_samples < samples // 2:
            # Attack - Fade in suave
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            
            # Release - Fade out suave
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        
        return envelope
    
    def normalize_audio(self, audio_data):
        """Normaliza el audio para evitar distorsión"""
        # Encontrar el pico máximo
        max_amplitude = np.max(np.abs(audio_data))
        
        if max_amplitude > 0:
            # Normalizar al nivel de amplitud objetivo
            normalized_audio = audio_data * (self.amplitude / max_amplitude)
            print(f"  - Audio normalizado (pico: {max_amplitude:.3f} -> {self.amplitude:.3f})")
            return normalized_audio
        
        return audio_data
    
    def create_stereo_files(self, processed_audio, base_name):
        """Crea archivos estéreo LEFT y RIGHT a partir del audio procesado"""
        samples = len(processed_audio)
        
        # Convertir a formato de 16 bits
        audio_data = (processed_audio * 32767).astype(np.int16)
        
        # Crear versión estéreo - canal izquierdo activo
        stereo_left = np.zeros((samples, 2), dtype=np.int16)
        stereo_left[:, 0] = audio_data  # Canal izquierdo
        stereo_left[:, 1] = 0           # Canal derecho silencioso
        
        # Crear versión estéreo - canal derecho activo  
        stereo_right = np.zeros((samples, 2), dtype=np.int16)
        stereo_right[:, 0] = 0          # Canal izquierdo silencioso
        stereo_right[:, 1] = audio_data # Canal derecho
        
        # Generar nombres de archivo
        left_filename = self.output_path / f"{base_name}_LEFT.wav"
        right_filename = self.output_path / f"{base_name}_RIGHT.wav"
        
        # Guardar archivos
        self.save_wav_file(left_filename, stereo_left)
        self.save_wav_file(right_filename, stereo_right)
        
        print(f"  ✓ {left_filename.name}")
        print(f"  ✓ {right_filename.name}")
        
        return left_filename, right_filename
    
    def save_wav_file(self, filename, stereo_data):
        """Guarda datos de audio en formato WAV"""
        with wave.open(str(filename), 'w') as wav_file:
            wav_file.setnchannels(2)  # Estéreo
            wav_file.setsampwidth(2)  # 16 bits
            wav_file.setframerate(self.fs)  # 44.1 kHz
            wav_file.writeframes(stereo_data.tobytes())
    
    def process_wav_file(self, input_filename, output_base_name=None):
        """Procesa un archivo WAV mono y lo convierte al formato EMDR bilateral"""
        print(f"=== Procesando archivo: {input_filename} ===")
        
        try:
            # Cargar archivo original
            audio_data, original_fs = self.load_wav_file(input_filename)
            
            # Remuestrear si es necesario
            audio_data = self.resample_audio(audio_data, original_fs)
            
            # Ajustar duración
            audio_data = self.adjust_duration(audio_data)
            
            # Normalizar audio
            audio_data = self.normalize_audio(audio_data)
            
            # Aplicar envelope
            envelope = self.create_envelope(len(audio_data))
            audio_data = audio_data * envelope
            
            # Generar nombre base si no se proporciona
            if output_base_name is None:
                input_stem = Path(input_filename).stem
                output_base_name = f"tone_00_{input_stem}_custom"
            
            # Crear archivos estéreo
            left_file, right_file = self.create_stereo_files(audio_data, output_base_name)
            
            print(f"✅ Procesamiento completado exitosamente")
            print(f"📁 Archivos guardados en: {self.output_path.absolute()}")
            
            return left_file, right_file
            
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            return None, None


def main():
    """Función principal para procesar el archivo audio-emdr-1.wav"""
    print("=== Procesador de Audio WAV para EMDR ===")
    print("Procesando archivo mono a formato EMDR bilateral...")
    print()
    
    # Crear el procesador
    processor = EMDRWavProcessor()
    
    # Procesar el archivo específico
    input_file = "audio-emdr-1.wav"
    output_name = "tone_00_audio_emdr_1_custom"
    
    left_file, right_file = processor.process_wav_file(input_file, output_name)
    
    if left_file and right_file:
        print()
        print("🎵 Archivos creados:")
        print(f"  - Canal izquierdo: {left_file.name}")
        print(f"  - Canal derecho: {right_file.name}")
        print()
        print("📋 Especificaciones finales:")
        print(f"  - Formato: WAV estéreo, 44.1kHz, 16-bit")
        print(f"  - Duración: {processor.target_duration*1000:.0f}ms")
        print(f"  - Canales: Izquierdo/Derecho separados")
        print(f"  - Optimizado para estimulación EMDR bilateral")
        print()
        print("✨ ¡Listo para usar en tu aplicación EMDR!")
    else:
        print("❌ No se pudo procesar el archivo")


if __name__ == "__main__":
    main()