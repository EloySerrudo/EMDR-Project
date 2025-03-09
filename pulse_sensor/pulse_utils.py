import matplotlib.pyplot as plt
import numpy as np
import serial.tools.list_ports
import time
import os
from datetime import datetime

def list_available_ports():
    """Lista todos los puertos seriales disponibles"""
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    print("\nPuertos disponibles:")
    for port, desc, hwid in sorted(ports):
        available_ports.append(port)
        print(f"- {port}: {desc} [{hwid}]")
    
    return available_ports

def test_serial_connection(port, baudrate=115200, timeout=2):
    """Prueba la conexión serial con el dispositivo"""
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Conectado a {port} a {baudrate} baudios")
        
        # Enviar comando de prueba (parar adquisición y luego iniciar brevemente)
        ser.write(b'P')  # Detener primero por si estaba ejecutándose
        time.sleep(0.2)
        ser.write(b'S')  # Iniciar adquisición
        
        # Esperar datos por un corto tiempo
        time.sleep(0.5)
        data_received = ser.in_waiting > 0
        
        # Detener adquisición
        ser.write(b'P')
        ser.close()
        
        if data_received:
            print("Conexión exitosa: datos recibidos del sensor")
            return True
        else:
            print("Conexión establecida pero no se recibieron datos")
            return False
            
    except serial.SerialException as e:
        print(f"Error al conectar: {e}")
        return False

def save_session(times, values, filename=None):
    """Guarda los datos de una sesión en un archivo CSV"""
    if filename is None:
        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pulse_data_{timestamp}.csv"
    
    # Crear directorio si no existe
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", filename)
    
    # Guardar datos
    with open(filepath, 'w') as f:
        f.write("Time,Value\n")
        for t, v in zip(times, values):
            f.write(f"{t:.6f},{v}\n")
    
    print(f"Datos guardados en {filepath}")
    return filepath

def visualize_fft(values, sample_rate=1000, title="Análisis de Frecuencia"):
    """Visualiza el espectro de frecuencia de la señal usando FFT"""
    # Calcular FFT
    n = len(values)
    fft_values = np.fft.rfft(values)
    fft_freq = np.fft.rfftfreq(n, d=1.0/sample_rate)
    
    # Calcular magnitud y normalizar
    magnitude = np.abs(fft_values) / n
    
    # Encontrar la frecuencia dominante (excluyendo DC)
    mask = fft_freq > 0.5  # Filtrar frecuencias muy bajas
    peak_freq = fft_freq[mask][np.argmax(magnitude[mask])]
    bpm_estimate = peak_freq * 60  # Convertir Hz a BPM
    
    # Crear gráfico
    plt.figure(figsize=(10, 6))
    plt.plot(fft_freq, magnitude)
    plt.xlabel('Frecuencia (Hz)')
    plt.ylabel('Magnitud')
    plt.title(f'{title} - Frecuencia dominante: {peak_freq:.2f}Hz ({bpm_estimate:.1f} BPM)')
    plt.grid(True)
    plt.axvline(x=peak_freq, color='r', linestyle='--')
    
    # Limitar el eje X a frecuencias relevantes para pulso cardíaco (0.5-5Hz)
    plt.xlim(0.5, 5)
    
    plt.tight_layout()
    plt.show()
    
    return peak_freq, bpm_estimate
