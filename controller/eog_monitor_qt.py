import sys
import serial
import numpy as np
import struct
import threading
import time
import argparse
import os
from collections import deque
import pandas as pd
from datetime import datetime

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import QTimer, Qt, Signal, QObject
import pyqtgraph as pg

# Importación del filtro en tiempo real
from signal_processing import RealTimeFilter

# Configuración por defecto
DEFAULT_PORT = 'COM6'  # Cambiar según el puerto que use tu ESP32
DEFAULT_BAUDRATE = 115200
BUFFER_SIZE = 512  # Debe coincidir con el BUFFER_SIZE del Arduino
SAMPLE_RATE = 125  # Hz (tasa efectiva: 250 SPS ÷ 2 canales)
DISPLAY_TIME = 5  # Segundos de datos a mostrar en la gráfica

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 15        # Tamaño en bytes de cada paquete (actualizado para incluir ambos canales y el ID del dispositivo)

# Diccionario de esclavos: {ID: (nombre, requerido_para_captura)}
KNOWN_SLAVES = {
    1: ("Sensor EOG", True),  # ID 1: Sensor de EOG (requerido para captura)
    # Aquí se pueden añadir más esclavos en el futuro
}

class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)
    
class EOGMonitorQt(QMainWindow):
    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE, display_time=DISPLAY_TIME):
        super().__init__()
        
        # Serial configuration
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.reading_thread = None
        
        # Data storage for display
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Initialize deques with zeros
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        self.values = deque(initial_values, maxlen=self.display_size)
        self.filtered_values = deque(initial_values, maxlen=self.display_size)
        
        # For unlimited data storage (for saving to CSV)
        self.idx = []
        self.tiempos = []
        self.valores = []
        self.valores_filtrados = []
        
        # Filter for real-time signal processing
        self.eog_filter = RealTimeFilter(
            filter_type='bandpass', fs=SAMPLE_RATE, lowcut=0.1, highcut=30.0, order=4
        )
        
        # Stats tracking
        self.samples_received = 0
        self.packets_received = 0
        self.invalid_packets = 0
        self.duplicate_packets = 0
        self.samples_per_second = 0
        self.last_samples_count = 0
        self.last_rate_update = time.time()
        self.last_packet_id = -1  # Para detectar paquetes duplicados
        
        # Slave device tracking
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        self.slave_count = 0
        self.connection_thread = None
        self.signals = SignalsObject()
        self.signals.device_status_updated.connect(self.update_device_status)
        
        # Setup UI
        self.setup_ui(display_time)
        
    def setup_ui(self, display_time):
        """Setup the user interface with PyQtGraph plots"""
        self.setWindowTitle("Monitor de EOG en Tiempo Real")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Device status section
        self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
        self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
        main_layout.addWidget(self.device_status_label)
        
        # Create two plot widgets
        # Raw signal plot
        self.raw_plot_widget = pg.PlotWidget()
        self.raw_plot_widget.setLabel('left', 'Señal EOG cruda')
        self.raw_plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.raw_plot_widget.showGrid(x=True, y=True)
        self.raw_plot_widget.setYRange(-25000, 20000)  # Ajustado para valores EOG (-30000, 30000)
        self.raw_plot_widget.setXRange(-display_time, 0)
        
        # Filtered signal plot
        self.filtered_plot_widget = pg.PlotWidget()
        self.filtered_plot_widget.setLabel('left', 'Señal EOG filtrada')
        self.filtered_plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.filtered_plot_widget.showGrid(x=True, y=True)
        self.filtered_plot_widget.setYRange(-25000, 20000)  # Ajustado para valores filtrados (-30000, 30000)
        self.filtered_plot_widget.setXRange(-display_time, 0)
        
        # Create curves for data
        self.raw_curve = self.raw_plot_widget.plot(pen=pg.mkPen('r', width=1.5))
        self.filtered_curve = self.filtered_plot_widget.plot(pen=pg.mkPen('g', width=1.5))
        
        # Add plots to layout
        main_layout.addWidget(self.raw_plot_widget)
        main_layout.addWidget(self.filtered_plot_widget)
        
        # Stats display
        self.stats_label = QLabel("Esperando datos...")
        self.stats_label.setStyleSheet("background-color: rgba(255, 255, 200, 180); padding: 5px;")
        main_layout.addWidget(self.stats_label)
        
        # Add instructions label
        instructions = QLabel("Controles: Espacio = Iniciar/Detener, C = Verificar Conexiones, S = Guardar datos, Q = Salir")
        instructions.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instructions)
        
        self.setCentralWidget(central_widget)
        
        # Setup timer for updating plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # 50ms refresh rate (20 FPS)
        
    def connect(self):
        """Connect to serial port"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Conectado a {self.port} a {self.baudrate} baudios")
            self.serial.reset_input_buffer()  # Clear any pending data
            return True
        except serial.SerialException as e:
            print(f"Error al conectar al puerto {self.port}: {e}")
            return False
    
    def start_acquisition(self):
        """Start data acquisition"""
        if not self.serial or self.running:
            return
            
        if not self.required_devices_connected:
            print("\nNo se puede iniciar la adquisición: dispositivos requeridos no conectados.")
            print("Use la tecla 'C' para verificar conexiones.\n")
            return
        
        # Reset stats and filter
        self.samples_received = 0
        self.packets_received = 0
        self.invalid_packets = 0
        self.duplicate_packets = 0
        self.last_samples_count = 0
        self.last_rate_update = time.time()
        self.last_packet_id = -1
        self.eog_filter.reset()

        # Clear and reset data buffers
        self.times.clear()
        self.values.clear()
        self.filtered_values.clear()
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        self.times.extend(initial_times)
        self.values.extend(initial_values)
        self.filtered_values.extend(initial_values)
        
        # Clear lists for CSV data storage
        self.idx = []
        self.tiempos = []
        self.valores = []
        self.valores_filtrados = []
        
        # Send command to ESP32 to start capture
        self.serial.write(b'S')
        
        # Start capture
        self.running = True
        
        # Start reading thread
        self.reading_thread = threading.Thread(target=self._read_data)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        print("Adquisición iniciada")

    def stop_acquisition(self):
        """Stop data acquisition"""
        if self.serial and self.running:
            # Send command to ESP32 to stop capture
            self.serial.write(b'P')
            
            # Stop capture
            self.running = False
            if self.reading_thread:
                self.reading_thread.join(timeout=1.0)
            print(f"Adquisición detenida. Total paquetes: {self.packets_received}")

    def _find_packet_start(self, buffer):
        """Find the start of a packet in the buffer"""
        if len(buffer) < 2:
            return -1
            
        for i in range(len(buffer) - 1):
            # Look for the header byte sequence (Little Endian: 0x55, 0xAA)
            if buffer[i] == (PACKET_HEADER & 0xFF) and buffer[i + 1] == (PACKET_HEADER >> 8) & 0xFF:
                return i
                
        return -1

    def check_slave_connections(self):
        """Send command to check for connected slaves"""
        if not self.serial:
            print("No hay conexión serial establecida")
            return
            
        print("Verificando dispositivos conectados...")
        self.serial.write(b'C')  # Send command to check connections
        
        # Reset connection status
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        
        # Read response in a separate thread to avoid blocking the UI
        if self.connection_thread is None or not self.connection_thread.is_alive():
            self.connection_thread = threading.Thread(target=self._read_connection_data)
            self.connection_thread.daemon = True
            self.connection_thread.start()
    
    def _read_connection_data(self):
        """Read connection data in a separate thread"""
        # Clear buffer before reading
        message_buffer = bytearray()
        timeout = time.time() + 2.0  # 2 seconds timeout
        
        # Clear serial buffer
        self.serial.reset_input_buffer()
        
        while time.time() < timeout:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    message_buffer.extend(data)
                    
                    # Check if we have enough bytes to process
                    if len(message_buffer) >= 3:  # At least '!', 'C' and slave_count
                        marker = chr(message_buffer[0])
                        command = chr(message_buffer[1])
                        
                        if marker == '!' and command == 'C':
                            slave_count = message_buffer[2]
                            # Check if we have all bytes needed
                            if len(message_buffer) >= 3 + (slave_count * 2):
                                self.slave_count = slave_count
                                
                                # Process connection information
                                status_dict = {}
                                for i in range(slave_count):
                                    device_id = message_buffer[3 + (i * 2)]
                                    status = message_buffer[4 + (i * 2)] == 1
                                    
                                    if device_id in self.slave_status:
                                        self.slave_status[device_id] = status
                                        status_dict[device_id] = status
                                
                                # Check for required devices
                                required_connected = all(
                                    self.slave_status.get(slave_id, False) 
                                    for slave_id, (_, required) in KNOWN_SLAVES.items() 
                                    if required
                                )
                                
                                # Update UI from main thread
                                self.signals.device_status_updated.emit(status_dict, required_connected)
                                self._print_connection_status()
                                break
                    
                time.sleep(0.05)
            except Exception as e:
                print(f"Error al leer datos de conexión: {e}")
                break
    
    def update_device_status(self, status_dict, required_connected):
        """Update the device status UI - called from main thread"""
        self.required_devices_connected = required_connected
        
        # Update status label
        status_text = "Estado de dispositivos: "
        for slave_id, connected in status_dict.items():
            name, required = KNOWN_SLAVES.get(slave_id, ("Desconocido", False))
            status = "CONECTADO" if connected else "DESCONECTADO"
            req = " (Requerido)" if required else ""
            status_text += f"{name}{req}: {status} | "
        
        self.device_status_label.setText(status_text.rstrip(" | "))
        
        # Change background color based on connection status
        if required_connected:
            self.device_status_label.setStyleSheet("background-color: rgba(200, 255, 200, 180); padding: 5px;")
        else:
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
    
    def _print_connection_status(self):
        """Print connection status to terminal"""
        print("\n--- Estado de conexión de esclavos ---")
        
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            connected = self.slave_status.get(slave_id, False)
            status = "CONECTADO" if connected else "DESCONECTADO"
            req_text = "(Requerido)" if required else "(Opcional)"
            print(f"Esclavo ID:{slave_id} - {name} {req_text}: {status}")
        
        print("-------------------------------------\n")
        
        if self.required_devices_connected:
            print("Todos los dispositivos requeridos están conectados.\n")
        else:
            print("ADVERTENCIA: Uno o más dispositivos requeridos no están conectados.")
            print("La adquisición de datos está deshabilitada hasta que todos los dispositivos requeridos estén conectados.\n")

    def _read_data(self):
        """Function that runs in a separate thread to read binary data"""
        data_buffer = bytearray()
        
        while self.running:
            try:
                # Read available data
                available = self.serial.in_waiting
                
                if available > 0:
                    # Read available data
                    new_data = self.serial.read(min(available, BUFFER_SIZE * PACKET_SIZE))
                    data_buffer.extend(new_data)
                    
                    # Process while we have enough data for a complete packet
                    while len(data_buffer) >= PACKET_SIZE:
                        # Look for packet start
                        packet_start = self._find_packet_start(data_buffer)
                        
                        if packet_start < 0:
                            # No valid header found, keep only the last byte
                            if len(data_buffer) > 1:
                                data_buffer = data_buffer[-1:]
                            break
                            
                        # If packet doesn't start at buffer beginning, discard preceding bytes
                        if packet_start > 0:
                            data_buffer = data_buffer[packet_start:]
                            
                        # Check if we have a complete packet
                        if len(data_buffer) < PACKET_SIZE:
                            break
                            
                        # Extract packet data
                        try:
                            # Header (2 bytes)
                            header = struct.unpack('<H', data_buffer[0:2])[0]
                            
                            if header == PACKET_HEADER:
                                # ID (4 bytes)
                                packet_id = struct.unpack('<I', data_buffer[2:6])[0]
                                
                                # Check for duplicate packets
                                if packet_id <= self.last_packet_id:
                                    self.duplicate_packets += 1
                                    # Remove processed packet from buffer and continue
                                    data_buffer = data_buffer[PACKET_SIZE:]
                                    continue
                                
                                # Update last processed ID
                                self.last_packet_id = packet_id
                                
                                # Timestamp (4 bytes)
                                timestamp_ms = struct.unpack('<I', data_buffer[6:10])[0]
                                timestamp_s = timestamp_ms / 1000.0  # Convert to seconds
                                
                                # Skip value_0, we only care about EOG value
                                
                                # EOG value (2 bytes)
                                value = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # Device ID (1 byte) is at position 14
                                device_id = data_buffer[14]
                                
                                # Apply real-time filter
                                filtered_value = self.eog_filter.filter(value)
                                
                                # Add to deques for display
                                self.times.append(timestamp_s)
                                self.values.append(value)
                                self.filtered_values.append(filtered_value)
                                
                                # Add to lists for CSV storage
                                self.idx.append(packet_id)
                                self.tiempos.append(timestamp_ms)
                                self.valores.append(value)
                                self.valores_filtrados.append(filtered_value)
                                
                                # Update counters
                                self.samples_received += 1
                                self.packets_received += 1
                            else:
                                # Invalid header, discard initial byte and continue
                                self.invalid_packets += 1
                                data_buffer = data_buffer[1:]
                                continue
                                
                            # Remove processed packet from buffer
                            data_buffer = data_buffer[PACKET_SIZE:]
                        except Exception as e:
                            print(f"Error processing packet: {e}")
                            # On error, discard initial byte and continue
                            data_buffer = data_buffer[1:]
                
                # Update stats every second
                current_time = time.time()
                if current_time - self.last_rate_update >= 1.0:
                    elapsed = current_time - self.last_rate_update
                    new_samples = self.samples_received - self.last_samples_count
                    self.samples_per_second = int(new_samples / elapsed)
                    
                    self.last_samples_count = self.samples_received
                    self.last_rate_update = current_time
                
                # Small pause to not saturate CPU
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error reading data: {e}")
                time.sleep(0.1)  # Longer pause on error

    def update_plot(self):
        """Update the plots with new data"""
        if len(self.times) > 0:
            # Convert deques to numpy arrays for plotting
            x_data = np.array(self.times)
            y_data = np.array(self.values)
            y_filtered = np.array(self.filtered_values)
            
            # Update plot data
            self.raw_curve.setData(x_data, y_data)
            self.filtered_curve.setData(x_data, y_filtered)
            
            # Get current time (last data point)
            current_time = x_data[-1] if len(x_data) > 0 else 0
            
            # Set fixed window of width DISPLAY_TIME that slides with data
            if len(x_data) > 0 and self.running:
                window_start = current_time - DISPLAY_TIME
                window_end = current_time
                self.raw_plot_widget.setXRange(window_start, window_end)
                self.filtered_plot_widget.setXRange(window_start, window_end)
            
            # Update stats label
            stats_str = (f"Paquetes: {self.packets_received} | "
                        f"Muestras/s: {self.samples_per_second} | "
                        f"Inválidos: {self.invalid_packets} | "
                        f"Duplicados: {self.duplicate_packets}")
            self.stats_label.setText(stats_str)
    
    def save_data_to_csv(self):
        """Save collected data to CSV file"""
        try:
            if len(self.idx) == 0:
                print("No hay datos para guardar")
                return
                
            # Create DataFrame with data
            data = {
                'ID': self.idx,
                'Timestamp_ms': self.tiempos,
                'EOG_raw': self.valores,
                'EOG_filtrado': self.valores_filtrados
            }
            df = pd.DataFrame(data)
            
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate filename with date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"eog_data_{timestamp}.csv")
            
            # Save data
            df.to_csv(filename, index=False)
            print(f"\nDatos guardados en: {filename}")
            print(f"Total de muestras guardadas: {len(self.idx)}")
            
        except Exception as e:
            print(f"Error al guardar datos: {e}")
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Space:  # Space to start/stop
            if self.running:
                self.stop_acquisition()
            else:
                self.start_acquisition()
        elif event.key() == Qt.Key_C:  # C to check connections
            if not self.running:  # Only check if not capturing
                self.check_slave_connections()
        elif event.key() == Qt.Key_S:  # S to save data
            self.save_data_to_csv()
        elif event.key() == Qt.Key_Q:  # Q to exit
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.stop_acquisition()
        
        # Save data before closing if we have any
        if len(self.idx) > 0:
            print("\nGuardando datos antes de salir...")
            self.save_data_to_csv()
            
        if self.serial:
            print(f"Puerto {self.port} cerrado")
            self.serial.close()
        super().closeEvent(event)

def main():
    parser = argparse.ArgumentParser(description='Monitor de EOG (PyQtGraph)')
    parser.add_argument('-p', '--port', default=DEFAULT_PORT,
                        help=f'Puerto serial (default: {DEFAULT_PORT})')
    parser.add_argument('-b', '--baudrate', type=int, default=DEFAULT_BAUDRATE,
                        help=f'Velocidad en baudios (default: {DEFAULT_BAUDRATE})')
    args = parser.parse_args()
    
    app = QApplication([])
    monitor = EOGMonitorQt(port=args.port, baudrate=args.baudrate)
    monitor.show()
    
    # Try to connect to serial port
    if not monitor.connect():
        print("No se pudo conectar al puerto serial. La aplicación continuará sin conexión.")
    
    # Start Qt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
