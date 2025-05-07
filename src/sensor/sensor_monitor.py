import sys
import numpy as np
import struct
import threading
import time
import os
from collections import deque
import pandas as pd
from datetime import datetime

# PyQtGraph y PySide6 imports
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import QTimer, Qt, Signal, QObject
import pyqtgraph as pg

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importaciones para gestión de dispositivos
from src.models.devices import Devices, KNOWN_SLAVES

# Importación del filtro en tiempo real
from src.utils.signal_processing import RealTimeFilter

# Configuración constantes
SAMPLE_RATE = 125  # Hz (tasa efectiva: 250 SPS ÷ 2 canales)
DISPLAY_TIME = 5   # Segundos de datos a mostrar en la gráfica
BUFFER_SIZE = 512  # Tamaño máximo de buffer

# Constantes para el protocolo binario
PACKET_HEADER = 0xAA55  # Debe coincidir con el header en el código Arduino
PACKET_SIZE = 15        # Tamaño en bytes de cada paquete

class SignalsObject(QObject):
    device_status_updated = Signal(dict, bool)
    
class SensorMonitor(QWidget):
    def __init__(self, display_time=DISPLAY_TIME, parent=None):
        super().__init__(parent)
        
        # Ya no necesitamos configuración de puerto y baudrate
        self.running = False
        self.reading_thread = None
        
        # Data storage for display
        self.display_size = display_time * SAMPLE_RATE
        self.sample_interval = 1.0 / SAMPLE_RATE
        
        # Initialize deques with zeros
        initial_times = [-display_time + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        
        self.times = deque(initial_times, maxlen=self.display_size)
        
        # Buffers para EOG
        self.eog_values = deque(initial_values, maxlen=self.display_size)
        self.filtered_eog_values = deque(initial_values, maxlen=self.display_size)
        
        # Buffers para PPG
        self.ppg_values = deque(initial_values, maxlen=self.display_size)
        self.filtered_ppg_values = deque(initial_values, maxlen=self.display_size)
        
        # For unlimited data storage (for saving to CSV)
        self.idx = []
        self.tiempos = []
        
        # Para EOG
        self.eog_datos = []
        self.eog_datos_filtrados = []
        
        # Para PPG
        self.ppg_datos = []
        self.ppg_datos_filtrados = []
        
        # Filtros para ambas señales
        self.eog_filter = RealTimeFilter(
            filter_type='bandpass', fs=SAMPLE_RATE, lowcut=0.1, highcut=30.0, order=4
        )
        self.ppg_filter = RealTimeFilter(
            filter_type='bandpass', fs=SAMPLE_RATE, lowcut=0.5, highcut=8.0, order=4
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
        # Layout principal (ahora se aplica directamente al QWidget)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Device status section
        self.device_status_label = QLabel("Estado de dispositivos: Desconocido")
        self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
        main_layout.addWidget(self.device_status_label)
        
        # Create two plot widgets
        # PPG signal plot (superior)
        self.ppg_plot_widget = pg.PlotWidget()
        self.ppg_plot_widget.setLabel('left', 'Señal PPG filtrada')
        self.ppg_plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.ppg_plot_widget.setYRange(-25000, 25000)
        self.ppg_plot_widget.setXRange(-display_time-0.02, 0.01, padding=0)
        
        # Primero configurar el espaciado de ticks y luego la cuadrícula
        x_axis_ppg = self.ppg_plot_widget.getAxis('bottom')
        x_axis_ppg.setTickSpacing(major=1, minor=0.5)  # Marcas principales cada 1 segundo, menores cada 0.5
        self.ppg_plot_widget.showGrid(x=True, y=True)
        
        # EOG signal plot (inferior)
        self.eog_plot_widget = pg.PlotWidget()
        self.eog_plot_widget.setLabel('left', 'Señal EOG filtrada')
        self.eog_plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.eog_plot_widget.setYRange(-25000, 25000)
        self.eog_plot_widget.setXRange(-display_time-0.02, 0.01, padding=0)
        
        # Primero configurar el espaciado de ticks y luego la cuadrícula
        x_axis_eog = self.eog_plot_widget.getAxis('bottom')
        x_axis_eog.setTickSpacing(major=1, minor=0.5)  # Marcas principales cada 1 segundo, menores cada 0.5
        self.eog_plot_widget.showGrid(x=True, y=True)
        
        # Create curves for data
        self.ppg_curve = self.ppg_plot_widget.plot(pen=pg.mkPen('r', width=1.5))
        self.eog_curve = self.eog_plot_widget.plot(pen=pg.mkPen('g', width=1.5))
        
        # Add plots to layout
        main_layout.addWidget(self.ppg_plot_widget)
        main_layout.addWidget(self.eog_plot_widget)
        
        # Stats display
        self.stats_label = QLabel("Esperando datos...")
        self.stats_label.setStyleSheet("background-color: rgba(255, 255, 200, 180); padding: 5px;")
        main_layout.addWidget(self.stats_label)
        
        # Crear un layout horizontal para los botones
        button_layout = QHBoxLayout()
        
        # Botón de Iniciar/Detener
        self.btn_start_stop = QPushButton("Iniciar Adquisición")
        self.btn_start_stop.clicked.connect(self.toggle_acquisition)
        button_layout.addWidget(self.btn_start_stop)
        
        # Botón de Escanear Dispositivos
        self.btn_scan_usb = QPushButton("Escanear")
        self.btn_scan_usb.clicked.connect(self.check_slave_connections)
        button_layout.addWidget(self.btn_scan_usb)
        
        # Botón de Guardar Datos
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.save_data_to_csv)
        button_layout.addWidget(self.btn_save)
        
        # Botón de Salir (solo visible si se ejecuta como ventana independiente)
        if not self.parent():
            self.btn_exit = QPushButton("Salir")
            self.btn_exit.clicked.connect(self.close)
            button_layout.addWidget(self.btn_exit)
        
        # Añadir el layout de botones al layout principal
        main_layout.addLayout(button_layout)
        
        # Setup timer for updating plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # 50ms refresh rate (20 FPS)
    
    def toggle_acquisition(self):
        """Toggle between start and stop acquisition"""
        if self.running:
            self.stop_acquisition()
            self.btn_start_stop.setText("Iniciar Adquisición")
        else:
            self.start_acquisition()
            self.btn_start_stop.setText("Detener Adquisición")
        
    def start_acquisition(self):
        """Start data acquisition"""
        # Verificar que el controlador maestro esté conectado
        if not Devices.master_plugged_in() or self.running:
            print("No hay conexión con el controlador maestro o ya está adquiriendo datos")
            return
            
        if not self.required_devices_connected:
            print("\nNo se puede iniciar la adquisición: dispositivos requeridos no conectados.")
            print("Use el botón 'Escanear Dispositivos' para verificar conexiones.\n")
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
        self.ppg_filter.reset()

        # Clear and reset data buffers
        self.times.clear()
        self.eog_values.clear()
        self.filtered_eog_values.clear()
        self.ppg_values.clear()
        self.filtered_ppg_values.clear()
        
        initial_times = [-DISPLAY_TIME + i * self.sample_interval for i in range(self.display_size)]
        initial_values = [0] * self.display_size
        self.times.extend(initial_times)
        self.eog_values.extend(initial_values)
        self.filtered_eog_values.extend(initial_values)
        self.ppg_values.extend(initial_values)
        self.filtered_ppg_values.extend(initial_values)
        
        # Clear lists for CSV data storage
        self.idx = []
        self.tiempos = []
        self.eog_datos = []
        self.eog_datos_filtrados = []
        self.ppg_datos = []
        self.ppg_datos_filtrados = []
        
        # Send command to ESP32 to start capture usando Devices
        Devices.start_sensor()
        
        # Start capture
        self.running = True
        
        # Start reading thread
        self.reading_thread = threading.Thread(target=self._read_data)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        print("Adquisición iniciada")

    def stop_acquisition(self):
        """Stop data acquisition"""
        if Devices.master_plugged_in() and self.running:
            # Send command to ESP32 to stop capture
            Devices.stop_sensor()
            
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
        # Escanear dispositivos usando Devices
        found_devices = Devices.probe()
        
        if not found_devices:
            print("No se encontraron dispositivos")
            self.device_status_label.setText("Estado de dispositivos: No se encontraron dispositivos")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
            return
            
        if "Master Controller" not in found_devices:
            print("No se encontró el controlador maestro")
            self.device_status_label.setText("Estado de dispositivos: No se encontró el controlador maestro")
            self.device_status_label.setStyleSheet("background-color: rgba(255, 200, 200, 180); padding: 5px;")
            return
            
        print("Verificando dispositivos conectados...")
        
        # Reset connection status
        self.slave_status = {slave_id: False for slave_id in KNOWN_SLAVES}
        self.required_devices_connected = False
        
        # Update status from found devices
        status_dict = {}
        for slave_id, (name, required) in KNOWN_SLAVES.items():
            is_connected = name in found_devices
            self.slave_status[slave_id] = is_connected
            status_dict[slave_id] = is_connected
            
        # Check for required devices
        required_connected = all(
            self.slave_status.get(slave_id, False) 
            for slave_id, (_, required) in KNOWN_SLAVES.items() 
            if required
        )
        
        self.required_devices_connected = required_connected
        self.signals.device_status_updated.emit(status_dict, required_connected)
        self._print_connection_status()
    
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
        serial_conn = Devices.get_master_connection()  # Obtener la conexión serial del controlador maestro
        
        if not serial_conn:
            print("No hay conexión serial disponible")
            self.running = False
            return
        
        while self.running:
            try:
                # Read available data
                available = serial_conn.in_waiting
                
                if available > 0:
                    # Read available data
                    new_data = serial_conn.read(min(available, BUFFER_SIZE * PACKET_SIZE))
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
                                
                                # PPG value (2 bytes) en data_buffer[10:12]
                                ppg_value = struct.unpack('<h', data_buffer[10:12])[0]
                                
                                # EOG value (2 bytes) en data_buffer[12:14]
                                eog_value = struct.unpack('<h', data_buffer[12:14])[0]
                                
                                # Device ID (1 byte) is at position 14
                                device_id = data_buffer[14]
                                
                                # Apply real-time filters
                                filtered_ppg_value = self.ppg_filter.filter(ppg_value)
                                filtered_eog_value = self.eog_filter.filter(eog_value)
                                
                                # Add to deques for display
                                self.times.append(timestamp_s)
                                
                                # PPG data
                                self.ppg_values.append(ppg_value)
                                self.filtered_ppg_values.append(filtered_ppg_value)
                                
                                # EOG data
                                self.eog_values.append(eog_value)
                                self.filtered_eog_values.append(filtered_eog_value)
                                
                                # Add to lists for CSV storage
                                self.idx.append(packet_id)
                                self.tiempos.append(timestamp_ms)
                                
                                # PPG data for storage
                                self.ppg_datos.append(ppg_value)
                                self.ppg_datos_filtrados.append(filtered_ppg_value)
                                
                                # EOG data for storage
                                self.eog_datos.append(eog_value)
                                self.eog_datos_filtrados.append(filtered_eog_value)
                                
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
            
            # Datos filtrados para mostrar
            filtered_ppg_data = np.array(self.filtered_ppg_values)
            filtered_eog_data = np.array(self.filtered_eog_values)
            
            if self.running:
                # Normalizar los tiempos para que siempre estén entre -5 y 0
                current_time = x_data[-1]
                normalized_x = x_data - current_time  # El tiempo actual será 0, los anteriores negativos
            else:
                # Si está detenido, mantener la última normalización
                normalized_x = x_data
                
            # Update plot data con los tiempos normalizados
            self.ppg_curve.setData(normalized_x, filtered_ppg_data)
            self.eog_curve.setData(normalized_x, filtered_eog_data)
            
            # Fijar siempre el rango X entre -5 y 0
            self.ppg_plot_widget.setXRange(-DISPLAY_TIME-0.02, 0.01, padding=0)
            self.eog_plot_widget.setXRange(-DISPLAY_TIME-0.02, 0.01, padding=0)
            
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
                
            # Create DataFrame with data including both PPG and EOG
            data = {
                'ID': self.idx,
                'Timestamp_ms': self.tiempos,
                'PPG_raw': self.ppg_datos,
                'PPG_filtrado': self.ppg_datos_filtrados,
                'EOG_raw': self.eog_datos,
                'EOG_filtrado': self.eog_datos_filtrados
            }
            df = pd.DataFrame(data)
            
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate filename with date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"sensor_data_{timestamp}.csv")
            
            # Save data
            df.to_csv(filename, index=False)
            print(f"\nDatos guardados en: {filename}")
            print(f"Total de muestras guardadas: {len(self.idx)}")
            
        except Exception as e:
            print(f"Error al guardar datos: {e}")
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.stop_acquisition()
        
        # Save data before closing if we have any
        if len(self.idx) > 0:
            print("\nGuardando datos antes de salir...")
            self.save_data_to_csv()
            
        # Si es parte de otra ventana, permitir el comportamiento por defecto
        if self.parent():
            event.accept()
        else:
            super().closeEvent(event)
            
    # Método para permitir integración con otras ventanas
    def cleanup(self):
        """Método para limpiar recursos cuando el widget es parte de otra ventana"""
        self.stop_acquisition()
        if self.timer:
            self.timer.stop()
        if len(self.idx) > 0:
            self.save_data_to_csv()


# Solo cuando se ejecuta como aplicación independiente
if __name__ == "__main__":
    """Función principal para ejecutar el monitor como aplicación independiente"""
    app = QApplication([])
    
    # Crear una ventana principal que contendrá el widget
    main_window = QMainWindow()
    main_window.setWindowTitle("Monitor de PPG y EOG en Tiempo Real")
    main_window.setGeometry(100, 100, 800, 600)
    
    # Crear la instancia del monitor como widget
    monitor_widget = SensorMonitor(parent=main_window)
    main_window.setCentralWidget(monitor_widget)
    
    # Maximizar ventana para mejor visualización
    main_window.showMaximized()
    
    # Cuando se cierra la ventana principal, asegurar la limpieza
    app.aboutToQuit.connect(monitor_widget.cleanup)
    
    # Start Qt event loop
    sys.exit(app.exec())