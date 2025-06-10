from PySide6.QtWidgets import QPushButton, QSlider, QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

class CustomButton(QPushButton):
    """Botón normal que mantiene compatibilidad con el botón personalizado original"""
    
    def __init__(self, title, callback=None, togglable=False, size=(100, 60), parent=None):
        super().__init__(title, parent)
        self.active = True
        self.title = title
        
        # Configurar comportamiento
        self.setCheckable(togglable)
        if callback:
            self.clicked.connect(callback)
        
        # Estilo básico
        self.setFixedSize(*size)
        self.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0; 
                border: 2px solid #c0c0c0;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { 
                background-color: #e0e0e0; 
            }
            QPushButton:pressed, QPushButton:checked { 
                background-color: #c0e0ff;
                border: 2px solid #80c0ff; 
            }
            QPushButton:disabled { 
                background-color: #e0e0e0; 
                color: #a0a0a0; 
                border: 2px solid #d0d0d0;
            }
        """)
    
    def setActive(self, active):
        """Mantiene compatibilidad con la interfaz anterior"""
        self.active = active
        self.setEnabled(active)


class Switch(QWidget):
    """Implementación de interruptor deslizante On/Off"""
    
    def __init__(self, btn_on, btn_off, updater=None, parent=None):
        super().__init__(parent)
        
        # Crear un layout horizontal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear etiquetas para "Off" y "On"
        self.label_off = QLabel("Off")
        self.label_on = QLabel("On")
        
        # Crear deslizador
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1)
        self.slider.setFixedSize(60, 30)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 30px;
                background: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-radius: 15px;
            }
            QSlider::handle:horizontal {
                width: 28px;
                background: #80c0ff;
                border: 1px solid #5080ff;
                border-radius: 14px;
                margin: 1px;
            }
            QSlider::handle:horizontal:checked {
                background: #5080ff;
            }
        """)
        
        # Añadir widgets al layout
        layout.addWidget(self.label_off)
        layout.addWidget(self.slider)
        layout.addWidget(self.label_on)
        
        # Guardar referencias a los botones originales (para compatibilidad)
        self.btn_on = btn_on
        self.btn_off = btn_off
        
        # Guardar el actualizador y conectar
        self.updater = updater
        self.slider.valueChanged.connect(self._on_slider_changed)
        
        # Estado inicial
        self.set_value(False)
    
    def _on_slider_changed(self):
        """Maneja cambios en el deslizador"""
        value = self.slider.value() == 1
        # Actualizar botones originales para mantener compatibilidad
        self.btn_on.setChecked(value)
        self.btn_off.setChecked(not value)
        
        # Actualizar colores según estado
        self._update_colors()
        
        # Llamar al actualizador si existe
        if self.updater:
            self.updater()
    
    def _update_colors(self):
        """Actualiza los colores según el estado"""
        if self.get_value():
            self.label_on.setStyleSheet("font-weight: bold; color: #0066cc;")
            self.label_off.setStyleSheet("color: #808080;")
        else:
            self.label_on.setStyleSheet("color: #808080;")
            self.label_off.setStyleSheet("font-weight: bold; color: #0066cc;")
    
    def get_value(self):
        """Devuelve True si está activado"""
        return self.slider.value() == 1
    
    def set_value(self, value):
        """Establece el valor del interruptor"""
        self.slider.setValue(1 if value else 0)
        self._update_colors()