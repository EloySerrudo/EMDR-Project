from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                              QFrame, QSlider, QScrollArea)
from PySide6.QtCore import (Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, 
                           QRect, Property)  # Añadimos QRect y Property aquí
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QPixmap

class ModernSwitch(QWidget):
    """
    Switch estilo iOS/Android para la nueva interfaz de EMDR.
    Proporciona un interruptor deslizable con animación y colores modernos.
    """
    toggled = Signal(bool)
    
    def __init__(self, initial_state=False, parent=None):
        super().__init__(parent)
        
        # Configurar propiedades del switch
        self.setFixedSize(60, 30)
        self._checked = initial_state
        self._track_color_on = QColor("#009688")  # Verde teal como en las imágenes
        self._track_color_off = QColor("#777777")  # Gris oscuro para estado apagado
        self._thumb_color = QColor("#FFFFFF")
        
        # Inicializar posición del thumb ANTES de crear la animación
        self._thumb_position = 0
        if initial_state:
            self._thumb_position = 1
            
        # Crear animación después de tener la posición inicial
        self._animation = QPropertyAnimation(self, b"thumb_position")
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(150)
        
    def paintEvent(self, event):
        """Método de dibujado personalizado para el switch"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dibujar pista (track)
        track_color = self._track_color_on if self._checked else self._track_color_off
        painter.setBrush(track_color)
        painter.setPen(Qt.NoPen)
        
        track_height = self.height() - 4
        track_rect = QRect(2, 2, self.width() - 4, track_height)
        painter.drawRoundedRect(track_rect, track_height / 2, track_height / 2)
        
        # Dibujar botón deslizable (thumb)
        painter.setBrush(self._thumb_color)
        thumb_size = track_height - 4
        x_pos = 4 + (self.width() - thumb_size - 8) * self._thumb_position
        thumb_rect = QRect(int(x_pos), 4, thumb_size, thumb_size)
        painter.drawEllipse(thumb_rect)
    
    def mousePressEvent(self, event):
        """Maneja el clic en el switch"""
        self.toggle()
        
    def toggle(self):
        """Cambia el estado del switch con animación"""
        self._checked = not self._checked
        target = 1 if self._checked else 0
        
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(target)
        self._animation.start()
        
        self.toggled.emit(self._checked)
    
    def get_thumb_position(self):
        return self._thumb_position
    
    def set_thumb_position(self, pos):
        self._thumb_position = pos
        self.update()
        
    thumb_position = Property(float, get_thumb_position, set_thumb_position)
    
    def isChecked(self):
        """Devuelve el estado actual del switch"""
        return self._checked
    
    def setChecked(self, checked):
        """Establece el estado del switch sin animación"""
        if self._checked != checked:
            self._checked = checked
            self._thumb_position = 1 if checked else 0
            self.update()
            self.toggled.emit(self._checked)

class ModernSlider(QWidget):
    """
    Control deslizante moderno para ajustar valores como intensidad, velocidad, etc.
    Incluye botones de incremento/decremento y una barra de progreso visual.
    """
    valueChanged = Signal(int)
    
    def __init__(self, min_value=0, max_value=100, initial_value=50, parent=None):
        super().__init__(parent)
        self._min_value = min_value
        self._max_value = max_value
        self._value = initial_value
        
        # Crear layout principal
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)
        
        # Botón de decremento (-)
        self.minus_btn = QPushButton("-")
        self.minus_btn.setFixedSize(40, 40)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #007d71;
            }
        """)
        self.minus_btn.clicked.connect(self.decrease_value)
        
        # Slider central
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_value)
        self.slider.setMaximum(max_value)
        self.slider.setValue(initial_value)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #333333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #009688;
                border: none;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #009688;
                border-radius: 4px;
            }
        """)
        self.slider.valueChanged.connect(self._handle_slider_change)
        
        # Botón de incremento (+)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(40, 40)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #007d71;
            }
        """)
        self.plus_btn.clicked.connect(self.increase_value)
        
        # Añadir widgets al layout
        self.main_layout.addWidget(self.minus_btn)
        self.main_layout.addWidget(self.slider, 1)  # El slider se expandirá para llenar el espacio disponible
        self.main_layout.addWidget(self.plus_btn)
    
    def _handle_slider_change(self, value):
        """Maneja los cambios de valor en el slider"""
        if self._value != value:
            self._value = value
            self.valueChanged.emit(value)
    
    def increase_value(self):
        """Incrementa el valor del slider"""
        new_value = min(self._value + 1, self._max_value)
        self.slider.setValue(new_value)
    
    def decrease_value(self):
        """Decrementa el valor del slider"""
        new_value = max(self._value - 1, self._min_value)
        self.slider.setValue(new_value)
    
    def value(self):
        """Devuelve el valor actual del slider"""
        return self._value
    
    def setValue(self, value):
        """Establece el valor del slider"""
        clamped_value = max(self._min_value, min(value, self._max_value))
        if self._value != clamped_value:
            self.slider.setValue(clamped_value)
            # El cambio de valor en el slider activará _handle_slider_change

class ColorButton(QPushButton):
    """
    Botón de color para la selección de colores en la pantalla Light Tube.
    Muestra un círculo de color y responde a los eventos de clic.
    """
    def __init__(self, color, size=40, parent=None):
        super().__init__(parent)
        self.color = color
        self.selected = False
        self.setFixedSize(size, size)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: {size//2}px;
                border: 2px solid #444444;
            }}
            QPushButton:checked {{
                border: 2px solid white;
            }}
        """)

class HomeButton(QPushButton):
    """
    Botón principal para la pantalla de inicio, con icono y texto descriptivo.
    """
    def __init__(self, title, description, callback=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        
        # Crear layout interno para el botón
        self.inner_layout = QHBoxLayout(self)
        self.inner_layout.setContentsMargins(15, 5, 15, 5)
        
        # Agregar icono (podría ser un QLabel con imagen)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(50, 50)
        self.icon_label.setStyleSheet("background-color: #444; border-radius: 25px;")
        
        # Layout vertical para título y descripción
        self.text_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        
        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet("font-size: 12px; color: #ccc;")
        self.desc_label.setWordWrap(True)
        
        self.text_layout.addWidget(self.title_label)
        self.text_layout.addWidget(self.desc_label)
        
        # Añadir widgets al layout del botón
        self.inner_layout.addWidget(self.icon_label)
        self.inner_layout.addLayout(self.text_layout, 1)  # 1 = stretch factor
        
        # Estilo y comportamiento del botón
        self.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border-radius: 10px;
                border: 1px solid #444444;
                text-align: left;
                padding: 0px;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        
        if callback:
            self.clicked.connect(callback)
    
    def setIcon(self, icon_path):
        """Establece un icono para el botón desde una ruta de archivo"""
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(
                self.icon_label.width(), 
                self.icon_label.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))

class NavigationBar(QWidget):
    """
    Barra de navegación inferior para la aplicación.
    Permite cambiar entre diferentes secciones de la aplicación.
    """
    def __init__(self, navigate_callback, parent=None):
        super().__init__(parent)
        self.navigate_callback = navigate_callback
        self.setFixedHeight(60)
        
        # Crear layout para la barra
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Crear botones de navegación
        self.home_btn = self._create_nav_button("Home", 0)
        self.emdr_btn = self._create_nav_button("EMDR", 1)
        self.sensor_btn = self._create_nav_button("Sensor", 2)
        
        # Añadir botones al layout
        self.layout.addWidget(self.home_btn)
        self.layout.addWidget(self.emdr_btn)
        self.layout.addWidget(self.sensor_btn)
        
        # Estilo para la barra de navegación
        self.setStyleSheet("""
            NavigationBar {
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }
        """)
        
        # Activar el botón Home por defecto
        self.set_active(0)
    
    def _create_nav_button(self, name, index):
        """Crea un botón de navegación"""
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #777777;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:checked {
                color: #009688;
                border-bottom: 2px solid #009688;
            }
        """)
        btn.clicked.connect(lambda: self.navigate_callback(index))
        return btn
    
    def set_active(self, index):
        """Establece qué botón está activo"""
        buttons = [self.home_btn, self.emdr_btn, self.sensor_btn]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)

class SectionHeader(QWidget):
    """
    Encabezado de sección con botón de retroceso y título.
    Usado en las páginas internas para mostrar el título y permitir regresar.
    """
    back_clicked = Signal()
    
    def __init__(self, title, show_back=True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        
        # Crear layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        
        # Botón de retroceso
        if show_back:
            self.back_btn = QPushButton("←")
            self.back_btn.setFixedSize(40, 40)
            self.back_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #009688;
                    font-size: 24px;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:pressed {
                    color: #007d71;
                }
            """)
            self.back_btn.clicked.connect(self.back_clicked.emit)
            self.layout.addWidget(self.back_btn)
        
        # Título de la sección
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label, 1)  # 1 = stretch factor
        
        # Si hay botón de retroceso, añadir un espaciador del mismo tamaño al final
        if show_back:
            spacer = QWidget()
            spacer.setFixedSize(40, 40)
            self.layout.addWidget(spacer)
        
        # Estilo para el encabezado
        self.setStyleSheet("""
            SectionHeader {
                background-color: #000000;
            }
        """)

class SettingRow(QWidget):
    """
    Fila de configuración con etiqueta y control (switch, slider, etc.).
    Utilizado para crear filas consistentes en las pantallas de configuración.
    """
    def __init__(self, label, control, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        
        # Crear layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 5, 15, 5)
        
        # Etiqueta de la configuración
        self.label = QLabel(label)
        self.label.setStyleSheet("font-size: 16px; color: white;")
        
        # Control (switch, slider, etc.)
        self.control = control
        
        # Añadir widgets al layout
        self.layout.addWidget(self.label)
        self.layout.addStretch(1)  # Espaciador flexible
        self.layout.addWidget(self.control)
        
        # Estilo para la fila
        self.setStyleSheet("""
            SettingRow {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333333;
            }
        """)

class SegmentedButton(QWidget):
    """
    Control de botón segmentado para seleccionar entre múltiples opciones mutuamente excluyentes.
    Similar a un radio button group pero con apariencia de botones contiguos.
    """
    selectionChanged = Signal(int, str)  # índice, texto
    
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self.selected_index = 0
        self.buttons = []
        
        # Crear layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Crear botones para cada opción
        for i, option in enumerate(options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setProperty("index", i)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            
            if i == 0:  # Primer botón
                btn.setStyleSheet("""
                    QPushButton {
                        border-top-left-radius: 20px;
                        border-bottom-left-radius: 20px;
                        border-right: none;
                    }
                """)
            elif i == len(options) - 1:  # Último botón
                btn.setStyleSheet("""
                    QPushButton {
                        border-top-right-radius: 20px;
                        border-bottom-right-radius: 20px;
                        border-left: none;
                    }
                """)
            else:  # Botones del medio
                btn.setStyleSheet("""
                    QPushButton {
                        border-radius: 0px;
                        border-left: none;
                        border-right: none;
                    }
                """)
            
            self.buttons.append(btn)
            self.layout.addWidget(btn)
        
        # Estilo común para todos los botones - CORRECCIÓN AQUÍ
        self.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                color: white;
                padding: 8px 12px;
                min-width: 80px;
                font-size: 14px;
            }
            QPushButton:checked {
                background-color: #009688;
                color: white;
            }
        """)
        
        # Seleccionar el primer botón por defecto
        if self.buttons:
            self.set_selected_index(0)
    
    def _on_button_clicked(self, index):
        """Maneja los clics en los botones"""
        if index == self.selected_index:
            return  # No hacer nada si se hace clic en el botón ya seleccionado
        
        self.set_selected_index(index)
    
    def set_selected_index(self, index):
        """Establece qué opción está seleccionada"""
        if 0 <= index < len(self.buttons):
            # Desmarcar todos los botones
            for btn in self.buttons:
                btn.setChecked(False)
            
            # Marcar el botón seleccionado
            self.buttons[index].setChecked(True)
            self.selected_index = index
            
            # Emitir señal
            self.selectionChanged.emit(index, self.options[index])
    
    def get_selected_index(self):
        """Devuelve el índice de la opción seleccionada"""
        return self.selected_index
    
    def get_selected_text(self):
        """Devuelve el texto de la opción seleccionada"""
        return self.options[self.selected_index]