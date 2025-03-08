from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QGridLayout
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QObject, Signal
import os

class Container(QWidget):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._elements = []
        
        if elements:
            self.add_elements(elements)
        
        self.setLayout(self.layout)
    
    def add_elements(self, elements):
        for element in elements:
            self._elements.append(element)
            self.layout.addWidget(element, element.pos_y, element.pos_x)
    
    def get_elements(self):
        return self._elements


class Selector(QWidget):
    def __init__(self, x, y, title, values, format_str, btn_plus, btn_minus, updater=None, cyclic=False, parent=None):
        super().__init__(parent=parent)
        
        # Crear widgets para reemplazar los elementos thorpy
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("background-color: white; font-size: 14px;")
        self.title_label.setFixedSize(120, 30)
        
        self.value_label = QLabel(format_str)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("background-color: white; font-size: 18px;")
        self.value_label.setFixedSize(120, 30)
        
        # Configurar layout para posicionar los labels
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)
        
        # Tamaño del widget
        self.setFixedSize(120, 60)
        # Posición del widget
        self.pos_x = x
        self.pos_y = y
        
        # Almacenar datos
        self.updater = None
        self.values = values
        self.value = 0
        self.format = format_str
        self.value_index = 0
        self.show_value()
        self.updater = updater
        self.cyclic = cyclic
        
        # Conectar botones si se proporcionaron
        if btn_plus:
            btn_plus.clicked.connect(self.next_value)
        if btn_minus:
            btn_minus.clicked.connect(self.prev_value)
    
    def show_value(self):
        if self.values:
            val = self.values[self.value_index]
        else:
            val = self.value
            
        if isinstance(val, tuple):
            text = self.format.format(*val)
        else:
            text = self.format.format(val)
            
        self.value_label.setText(text)
        
        # Opcionalmente llamar al updater
        if self.updater is not None:
            self.updater()
    
    def next_value(self):
        self.value_index += 1
        if self.value_index >= len(self.values):
            if self.cyclic:
                self.value_index = 0
            else:
                self.value_index = len(self.values) - 1
        self.show_value()
    
    def prev_value(self):
        self.value_index -= 1
        if self.value_index < 0:
            if self.cyclic:
                self.value_index = len(self.values) - 1
            else:
                self.value_index = 0
        self.show_value()
    
    def get_value(self):
        if self.values:
            val = self.values[self.value_index]
        else:
            val = self.value
        return val
    
    def set_value(self, value):
        if self.values:
            try:
                idx = self.values.index(value)
                self.value_index = idx
            except ValueError:
                pass
        else:
            self.value = value
        self.show_value()


class CustomButton(QPushButton):
    def __init__(self, x, y, title, callback=None, togglable=False, parent=None):
        """Crea un botón personalizado con imagen"""
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


class EventSystem(QObject):
    """Sistema de eventos para reemplazar los eventos personalizados de pygame"""
    
    # Definir señales que reemplazarán los eventos de pygame
    probe_event = Signal()  # Reemplaza a PROBE_EVENT
    action_event = Signal()  # Reemplaza a ACTION_EVENT
    
    def __init__(self):
        super().__init__()

# Crear instancia global única
event_system = EventSystem()