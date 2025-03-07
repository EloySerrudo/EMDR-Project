from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

class Switch(QWidget):
    def __init__(self, btn_on, btn_off, updater=None, parent=None):
        super().__init__(parent)
        
        # Almacenar referencias a los botones y el actualizador
        self.btn_on = btn_on
        self.btn_off = btn_off
        self.updater = updater
        
        # Configurar conexiones
        self.btn_on.clicked.connect(self.on_click)
        self.btn_off.clicked.connect(self.off_click)
        
        # Configuración inicial (apagado por defecto)
        self.set_value(False)
        
    def set_value(self, value):
        """Establece el estado del interruptor"""
        self.btn_on.setChecked(value)
        self.btn_off.setChecked(not value)
        
        # Aplicar estilo para resaltar el botón activo
        if value:
            self.btn_on.setProperty("active", True)
            self.btn_off.setProperty("active", False)
        else:
            self.btn_on.setProperty("active", False)
            self.btn_off.setProperty("active", True)
        
        # Forzar actualización de estilos
        self.btn_on.style().unpolish(self.btn_on)
        self.btn_on.style().polish(self.btn_on)
        self.btn_off.style().unpolish(self.btn_off)
        self.btn_off.style().polish(self.btn_off)
    
    def get_value(self):
        """Retorna True si el botón ON está activado"""
        return self.btn_on.isChecked()
    
    def on_click(self):
        """Maneja el clic en el botón ON"""
        if not self.btn_on.isChecked():  # Si el botón se estaba desactivando
            self.btn_on.setChecked(True)  # Mantenerlo activado
            return
            
        # Desactivar el botón OFF
        self.btn_off.setChecked(False)
        
        # Actualizar estilos
        self.set_value(True)
        
        # Llamar al callback si existe
        if self.updater is not None:
            self.updater()
    
    def off_click(self):
        """Maneja el clic en el botón OFF"""
        if not self.btn_off.isChecked():  # Si el botón se estaba desactivando
            self.btn_off.setChecked(True)  # Mantenerlo activado
            return
            
        # Desactivar el botón ON
        self.btn_on.setChecked(False)
        
        # Actualizar estilos
        self.set_value(False)
        
        # Llamar al callback si existe
        if self.updater is not None:
            self.updater()