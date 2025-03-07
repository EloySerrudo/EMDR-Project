from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QSize, Qt
import os

class CustomButton(QPushButton):
    def __init__(self, title, callback=None, togglable=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.active = True
        
        # Cargar imágenes
        self.pixmap_normal = self._load_image(f'imgs/{title.lower()}_normal.png', 'imgs/default_normal.png')
        self.pixmap_pressed = self._load_image(f'imgs/{title.lower()}_pressed.png', 'imgs/default_pressed.png')
        self.pixmap_inactive = self._load_image(f'imgs/{title.lower()}_inactive.png', 'imgs/default_inactive.png')
        
        # Configurar apariencia
        self.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        self.setFixedSize(100, 60)  # Ajusta según el tamaño de tus imágenes
        
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