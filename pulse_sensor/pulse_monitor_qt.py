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
        initial_values = [1700] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        self.values = deque(initial_values, maxlen=self.display_size)
        self.start_time = None
        self.last_timestamp = -self.sample_interval
        
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
        # self.plot_widget.setBackground('w')  # white background
        self.plot_widget.setLabel('left', 'Valor ADC')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setYRange(0, 1500)  # ADC de 12-bits (0-4095)
        self.plot_widget.setXRange(-display_time, 0)
        
        # Create curve for data
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=1))
        
        # Add plot to layout
        layout.addWidget(self.plot_widget)
        
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
            self.serial = serial.Serial(self.port, self.baudrate)
            print(f"Conectado a {self.port} a {self.baudrate} baudios")
            return True
        except serial.SerialException as e:
            print(f"Error al conectar al puerto {self.port}: {e}")
            return False
    
    def start_acquisition(self):
        """Start data acquisition"""
        if self.serial and not self.running:
            # Send command to ESP32 to start capture
            self.serial.write(b'S')
            
            # Start capture
            self.running = True
            self.start_time = time.time()
            
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
            print("Adquisición detenida")

    def _read_data(self):
        """Function that runs in a separate thread to read data"""
        read_event = threading.Event()
        while self.running and not read_event.wait(timeout=0.001):
            # Small pause to not saturate CPU
            available = self.serial.in_waiting
            if available >= 2:  # At least one 16-bit value (2 bytes)
                # Determine how many complete samples we can read
                samples_to_read = min(available // 2, BUFFER_SIZE)
                
                if samples_to_read > 0:
                    # Read complete samples
                    data = self.serial.read(samples_to_read * 2)
                    
                    # Read and process data in a single cycle
                    for i in range(0, len(data), 2):
                        if i + 1 < len(data):
                            # Convert bytes to integer value (uint16)
                            value = struct.unpack('<H', data[i:i+2])[0]
                            
                            # Increment time exactly according to sample rate
                            self.last_timestamp += self.sample_interval
                            self.times.append(self.last_timestamp)
                            self.values.append(value)

    def update_plot(self):
        """Update the plot with new data"""
        if len(self.times) > 0:
            # Convert deques to numpy arrays for plotting
            x_data = np.array(self.times)
            y_data = np.array(self.values) - 1500
            
            # Update plot data
            self.curve.setData(x_data, y_data)
            
            # Get current time (last data point)
            current_time = x_data[-1]
            
            # Set fixed window of width DISPLAY_TIME that slides with data
            window_start = current_time - DISPLAY_TIME
            window_end = current_time
            self.plot_widget.setXRange(window_start, window_end)
    
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
