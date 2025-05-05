from PySide6.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal

class Selector(QWidget):
    """Selector numérico implementado con QSlider horizontal"""
    
    def __init__(self, x, y, title, values, format_str, btn_plus, btn_minus, updater=None, cyclic=False, show_slider=True, parent=None):
        super().__init__(parent)
        
        # Guardar posición para compatibilidad
        self.pos_x = x
        self.pos_y = y
        
        # Crear layout vertical para organizar componentes
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Etiqueta para mostrar el valor
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        # Layout horizontal para el deslizador
        slider_layout = QHBoxLayout()
        
        # Crear slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFixedWidth(100)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                background: #80c0ff;
                border: 1px solid #5080ff;
                border-radius: 8px;
                margin: -8px 0;
            }
        """)
        
        # Añadir componentes a los layouts según se muestre o no el slider
        main_layout.addWidget(self.title_label)
        
        if show_slider:
            slider_layout.addWidget(self.slider)
            main_layout.addLayout(slider_layout)
        
        main_layout.addWidget(self.value_label)
        
        # Configurar tamaño fijo
        self.setFixedSize(120, 80)
        
        # Almacenar datos
        self.format = format_str
        self.updater = updater
        self.values = values
        self.value = 0
        self.value_index = 0
        self.cyclic = cyclic
        self.show_slider = show_slider
        
        # Configurar slider según los valores
        if values and show_slider:
            self.slider.setMinimum(0)
            self.slider.setMaximum(len(values) - 1)
            self.slider.setValue(0)
            self.slider.setSingleStep(1)
            self.slider.valueChanged.connect(self._slider_changed)
        elif show_slider:
            self.slider.setMinimum(0)
            self.slider.setMaximum(100)
            self.slider.setValue(0)
            self.slider.valueChanged.connect(lambda v: self.set_value(v))
            
        # Guardar referencias a los botones para compatibilidad
        self.btn_plus = btn_plus
        self.btn_minus = btn_minus
        
        # Mostrar valor inicial sin llamar al updater
        self.show_value(initial=True)
    
    def _slider_changed(self, position):
        """Maneja los cambios en el deslizador"""
        self.value_index = position
        self.show_value()
    
    def show_value(self, initial=False):
        """Actualiza la etiqueta de valor"""
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
        if self.updater is not None and not initial:
            self.updater()
    
    def next_value(self):
        """Avanza al siguiente valor (mantiene compatibilidad)"""
        if self.show_slider:
            current = self.slider.value()
            self.slider.setValue(current + 1)
        else:
            if self.values:
                self.value_index = (self.value_index + 1) % len(self.values)
            else:
                self.value += 1
            self.show_value()
    
    def prev_value(self):
        """Retrocede al valor anterior (mantiene compatibilidad)"""
        if self.show_slider:
            current = self.slider.value()
            self.slider.setValue(current - 1)
        else:
            if self.values:
                self.value_index = (self.value_index - 1) % len(self.values)
            else:
                self.value = max(0, self.value - 1)
            self.show_value()
    
    def get_value(self):
        """Devuelve el valor actual"""
        if self.values:
            val = self.values[self.value_index]
        else:
            val = self.value
        return val
    
    def set_value(self, value):
        """Establece un valor específico"""
        if self.values:
            try:
                idx = self.values.index(value)
                self.value_index = idx
                if self.show_slider:
                    self.slider.setValue(idx)
            except ValueError:
                pass
        else:
            self.value = value
            if self.show_slider:
                self.slider.setValue(value)
        self.show_value()