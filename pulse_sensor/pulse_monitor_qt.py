import sys
import serial
import numpy as np
import struct
import threading
import time
import argparse
from collections import deque

# PyQtGraph and PySide6 imports
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QTimer, Qt
import pyqtgraph as pg

# Configuración por defecto
DEFAULT_PORT = 'COM6'  # Cambiar según el puerto que use tu ESP32. En la laptop es COM6, en la PC es COM4
DEFAULT_BAUDRATE = 115200
BUFFER_SIZE = 512  # Debe coincidir con el BUFFER_SIZE del Arduino
SAMPLE_RATE = 256  # Hz (debe coincidir con SAMPLE_RATE del Arduino)
DISPLAY_TIME = 5  # Segundos de datos a mostrar en la gráfica

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 12        # Tamaño en bytes de cada paquete

class PulseMonitorQt(QMainWindow):
    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE, display_time=DISPLAY_TIME):
        super().__init__()
        
        # Serial configuration
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.reading_thread = None
        
        # Data storage
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Initialize deques with zeros
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        self.values = deque(initial_values, maxlen=self.display_size)
        
        # Stats tracking
        self.samples_received = 0
        self.packets_received = 0
        self.invalid_packets = 0
        self.duplicate_packets = 0
        self.samples_per_second = 0
        self.last_samples_count = 0
        self.last_rate_update = time.time()
        self.last_packet_id = -1  # Para detectar paquetes duplicados
        
        # Setup UI
        self.setup_ui(display_time)
        
    def setup_ui(self, display_time):
        """Setup the user interface with PyQtGraph plot"""
        self.setWindowTitle("Monitor de Pulso Cardiaco en Tiempo Real")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Valor ADC')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setYRange(-30000, 20000)  # Ajustado para valores ADS1115
        self.plot_widget.setXRange(-display_time, 0)
        
        # Create curve for data
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=1.5))
        
        # Add stats display
        self.stats_label = QLabel("Esperando datos...")
        self.stats_label.setStyleSheet("background-color: rgba(255, 255, 200, 180); padding: 5px;")
        
        # Add plot to layout
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.stats_label)
        
        # Add instructions label
        instructions = QLabel("Controles: Espacio = Iniciar/Detener, Q = Salir")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
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
        if self.serial and not self.running:
            # Reset stats
            self.samples_received = 0
            self.packets_received = 0
            self.invalid_packets = 0
            self.duplicate_packets = 0
            self.last_samples_count = 0
            self.last_rate_update = time.time()
            self.last_packet_id = -1

            # Clear and reset data buffers
            self.times.clear()
            self.values.clear()
            initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
            initial_values = [0] * self.display_size
            self.times.extend(initial_times)
            self.values.extend(initial_values)
            
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
                                
                                # Value (2 bytes)
                                value = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # Add to deques
                                self.times.append(timestamp_s)
                                self.values.append(value)
                                
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
        """Update the plot with new data"""
        if len(self.times) > 0:
            # Convert deques to numpy arrays for plotting
            x_data = np.array(self.times)
            y_data = np.array(self.values)
            
            # Update plot data
            self.curve.setData(x_data, y_data)
            
            # Get current time (last data point)
            current_time = x_data[-1] if len(x_data) > 0 else 0
            
            # Set fixed window of width DISPLAY_TIME that slides with data
            if len(x_data) > 0 and self.running:
                window_start = current_time - DISPLAY_TIME
                window_end = current_time
                self.plot_widget.setXRange(window_start, window_end)
            
            # Update stats label
            stats_str = (f"Paquetes: {self.packets_received} | "
                        f"Muestras/s: {self.samples_per_second} | "
                        f"Inválidos: {self.invalid_packets} | "
                        f"Duplicados: {self.duplicate_packets}")
            self.stats_label.setText(stats_str)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Space:  # Space to start/stop
            if self.running:
                self.stop_acquisition()
            else:
                self.start_acquisition()
        elif event.key() == Qt.Key_Q:  # Q to exit
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.stop_acquisition()
        if self.serial:
            print(f"Puerto {self.port} cerrado")
            self.serial.close()
        super().closeEvent(event)

def main():
    parser = argparse.ArgumentParser(description='Monitor de Pulso Cardiaco (PyQtGraph)')
    parser.add_argument('-p', '--port', default=DEFAULT_PORT,
                        help=f'Puerto serial (default: {DEFAULT_PORT})')
    parser.add_argument('-b', '--baudrate', type=int, default=DEFAULT_BAUDRATE,
                        help=f'Velocidad en baudios (default: {DEFAULT_BAUDRATE})')
    args = parser.parse_args()
    
    app = QApplication([])
    monitor = PulseMonitorQt(port=args.port, baudrate=args.baudrate)
    monitor.show()
    
    # Try to connect to serial port
    if not monitor.connect():
        print("No se pudo conectar al puerto serial. La aplicación continuará sin conexión.")
    
    # Start Qt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
