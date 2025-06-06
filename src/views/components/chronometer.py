from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QTimer
import time

class Chronometer(QLabel):
    """Widget cronómetro basado en QLabel que cuenta tiempo transcurrido"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Variables de control del cronómetro
        self.start_time = 0
        self.elapsed_time = 0
        self.is_running = False
        
        # Timer para actualizar cada segundo
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        
        # Configurar alineación y estilo por defecto
        self.setAlignment(Qt.AlignCenter)
        
        # Aplicar estilo moderno por defecto
        self.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 18px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 rgba(33, 150, 243, 0.3),
                                          stop: 0.5 rgba(63, 169, 245, 0.4),
                                          stop: 1 rgba(33, 150, 243, 0.3));
                border: 2px solid rgba(63, 169, 245, 0.5);
                border-radius: 8px;
                padding: 10px 20px;
                min-width: 60px;
                min-height: 40px;
            }
        """)
        
        # Mostrar tiempo inicial
        self.reset()
    
    def start(self):
        """Inicia el cronómetro"""
        if not self.is_running:
            self.start_time = time.time() - self.elapsed_time
            self.is_running = True
            self.timer.start(100)  # Actualizar cada 100ms para mayor precisión
    
    def stop(self):
        """Detiene el cronómetro pero mantiene el tiempo mostrado"""
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            # El tiempo mostrado se mantiene
    
    def reset(self):
        """Reinicia el cronómetro a 00:00"""
        self.is_running = False
        self.timer.stop()
        self.start_time = 0
        self.elapsed_time = 0
        self.setText("00:00")
    
    def pause(self):
        """Pausa el cronómetro (alias para stop)"""
        self.stop()
    
    def resume(self):
        """Reanuda el cronómetro (alias para start)"""
        self.start()
    
    def update_display(self):
        """Actualiza el texto mostrado con el tiempo transcurrido"""
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
        
        # Convertir segundos a minutos:segundos
        total_seconds = int(self.elapsed_time)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        # Formatear como MM:SS
        time_text = f"{minutes:02d}:{seconds:02d}"
        self.setText(time_text)
    
    def get_elapsed_time(self):
        """Obtiene el tiempo transcurrido en segundos"""
        if self.is_running:
            return time.time() - self.start_time
        return self.elapsed_time
    
    def get_formatted_time(self):
        """Obtiene el tiempo formateado como string MM:SS"""
        return self.text()