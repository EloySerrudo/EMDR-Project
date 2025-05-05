from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtGui import QPixmap, QIcon
import os

class CustomButton(QPushButton):
    def __init__(self, x, y, title, callback=None, togglable=False, parent=None):
        """Crea un botón personalizado con imagen"""
        super().__init__(parent)
        self.title = title
        self.active = True
        
        # Cargar imágenes
        self.pixmap_normal = self._load_image(f'./src/imgs/{title.lower()}_normal.png', './src/imgs/default_normal.png')
        self.pixmap_pressed = self._load_image(f'./src/imgs/{title.lower()}_pressed.png', './src/imgs/default_pressed.png')
        self.pixmap_inactive = self._load_image(f'./src/imgs/{title.lower()}_inactive.png', './src/imgs/default_inactive.png')
        
        # Configurar apariencia
        self.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        self.setFixedSize(100, 60)  # Ajusta según el tamaño de tus imágenes
        self.pos_x = x
        self.pos_y = y
        
        # Configurar comportamiento
        self.setCheckable(togglable)
        if callback:
            self.clicked.connect(callback)
        
        # Inicializar el estado visual
        self.update_icon()
    
    def _load_image(self, primary_path, fallback_path):
        """Intenta cargar una imagen, usando la alternativa si falla"""
        try:
            if os.path.exists(primary_path):
                return QPixmap(primary_path)
            else:
                return QPixmap(fallback_path)
        except:
            try:
                return QPixmap(fallback_path)
            except:
                # Crear un pixmap en blanco si ambos fallan
                return QPixmap(100, 60)
    
    def update_icon(self):
        """Actualiza el icono basado en el estado actual"""
        if not self.active:
            self.setIcon(QIcon(self.pixmap_inactive))
        elif self.isChecked():
            self.setIcon(QIcon(self.pixmap_pressed))
        else:
            self.setIcon(QIcon(self.pixmap_normal))
        
        self.setIconSize(self.size())
    
    def setActive(self, active):
        """Establece si el botón está activo o no"""
        self.active = active
        self.setEnabled(active)
        self.update_icon()
    
    # Override de los eventos para manejar estados visuales
    def checkStateSet(self):
        super().checkStateSet()
        self.update_icon()
    
    def nextCheckState(self):
        super().nextCheckState()
        self.update_icon()


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