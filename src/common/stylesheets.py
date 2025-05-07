"""
Hojas de estilo centralizadas para mantener una apariencia coherente en toda la aplicación.
Define el tema principal (oscuro) y variaciones para componentes específicos.
"""

# Tema oscuro principal utilizado en toda la aplicación
DARK_THEME = """
    /* Estilos generales para toda la aplicación */
    QMainWindow, QWidget {
        background-color: #1a1a1a;
        color: white;
        font-family: Arial, Helvetica, sans-serif;
    }
    
    /* Bordes y separadores */
    QFrame[frameShape="4"],  /* QFrame::HLine */
    QFrame[frameShape="5"] { /* QFrame::VLine */
        background-color: #333333;
        max-width: 1px;
        max-height: 1px;
    }
    
    /* Botones estándar */
    QPushButton {
        background-color: #333333;
        color: white;
        border: 1px solid #444444;
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 14px;
    }
    
    QPushButton:hover {
        background-color: #404040;
    }
    
    QPushButton:pressed {
        background-color: #2a2a2a;
    }
    
    QPushButton:disabled {
        background-color: #2a2a2a;
        color: #666666;
        border: 1px solid #333333;
    }
    
    /* Botones de acción principal, como Start */
    QPushButton.primary {
        background-color: #009688;
        color: white;
        border: none;
    }
    
    QPushButton.primary:hover {
        background-color: #00a697;
    }
    
    QPushButton.primary:pressed {
        background-color: #007d71;
    }
    
    /* Etiquetas */
    QLabel {
        color: white;
        font-size: 14px;
    }
    
    QLabel.title {
        font-size: 20px;
        font-weight: bold;
    }
    
    QLabel.subtitle {
        font-size: 16px;
        color: #aaaaaa;
    }
    
    QLabel.value {
        font-size: 16px;
        font-weight: bold;
        color: #009688;
    }
    
    /* Sliders */
    QSlider::groove:horizontal {
        height: 8px;
        background: #333333;
        border-radius: 4px;
    }
    
    QSlider::handle:horizontal {
        background: #009688;
        width: 20px;
        margin-top: -6px; 
        margin-bottom: -6px;
        border-radius: 10px;
    }
    
    QSlider::sub-page:horizontal {
        background: #009688;
        height: 8px;
        border-radius: 4px;
    }
    
    QSlider::handle:horizontal:hover {
        background: #00a697;
    }
    
    /* ScrollArea y ScrollBar */
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    
    QScrollBar:vertical {
        background: #262626;
        width: 12px;
        margin: 0px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background: #555555;
        min-height: 30px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #666666;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, 
    QScrollBar::sub-page:vertical {
        background: none;
        height: 0px;
        width: 0px;
    }
    
    /* Contenedores de configuración */
    QGroupBox {
        border: 1px solid #333333;
        border-radius: 10px;
        margin-top: 16px;
        padding-top: 16px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
        color: #009688;
    }
"""

# Estilos específicos para la pantalla Light Tube
LIGHT_TUBE_STYLE = """
    /* Estilos específicos para la pantalla Light Tube */
    QPushButton.color-button {
        border-radius: 20px;
        min-width: 40px;
        min-height: 40px;
        max-width: 40px;
        max-height: 40px;
        padding: 0;
        border: 2px solid #444444;
    }
    
    QPushButton.color-button:checked {
        border: 2px solid white;
    }
    
    /* Estilos para los botones de modo (Sweep/Blink) */
    QPushButton.mode-button {
        border-radius: 0;
        background-color: #333333;
        min-height: 40px;
        font-size: 15px;
    }
    
    QPushButton.mode-button:checked {
        background-color: #009688;
    }
    
    QPushButton.mode-button:first {
        border-top-left-radius: 20px;
        border-bottom-left-radius: 20px;
    }
    
    QPushButton.mode-button:last {
        border-top-right-radius: 20px;
        border-bottom-right-radius: 20px;
    }
"""

# Estilos específicos para la pantalla Pulsators
PULSATOR_STYLE = """
    /* Estilos específicos para la pantalla Pulsators */
    QLabel.pulsator-status {
        color: #777777;
        font-size: 14px;
    }
"""

# Estilos específicos para la pantalla Headphone
HEADPHONE_STYLE = """
    /* Estilos específicos para la pantalla Headphone */
    QPushButton.sound-button {
        background-color: #333333;
        min-height: 40px;
        border-radius: 20px;
        font-size: 15px;
    }
    
    QPushButton.sound-button:checked {
        background-color: #009688;
    }
    
    QPushButton.custom-audio {
        background-color: #009688;
        min-height: 50px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
    }
"""

# Estilo para la barra de navegación
NAVIGATION_BAR_STYLE = """
    QWidget#navigation-bar {
        background-color: #1a1a1a;
        border-top: 1px solid #333333;
    }
    
    QPushButton.nav-button {
        background-color: transparent;
        border: none;
        color: #777777;
        font-size: 14px;
        min-height: 40px;
        padding: 10px;
    }
    
    QPushButton.nav-button:checked {
        color: #009688;
        border-bottom: 2px solid #009688;
    }
"""

# Estilo para la barra de estado (información de dispositivos)
DEVICE_STATUS_BAR_STYLE = """
    QWidget#device-status-bar {
        background-color: #262626;
        border-bottom: 1px solid #333333;
    }
    
    QLabel.status-label {
        font-size: 12px;
        color: #aaaaaa;
    }
    
    QLabel.status-ok {
        color: #4caf50;  /* Verde para dispositivos conectados */
    }
    
    QLabel.status-error {
        color: #f44336;  /* Rojo para dispositivos no conectados */
    }
    
    QPushButton.scan-button {
        background-color: transparent;
        border: 1px solid #aaaaaa;
        color: #aaaaaa;
        border-radius: 5px;
        padding: 2px 8px;
        font-size: 12px;
    }
    
    QPushButton.scan-button:hover {
        border-color: #009688;
        color: #009688;
    }
"""

# Estilo para pantallas del monitor de sensores
SENSOR_MONITOR_STYLE = """
    /* Estilo para gráficas */
    PlotWidget {
        background-color: #262626;
        border: 1px solid #333333;
        border-radius: 5px;
    }
    
    /* Controles para ajustes de gráfica */
    QPushButton.sensor-control {
        background-color: #333333;
        min-width: 30px;
        max-width: 30px;
        min-height: 30px;
        max-height: 30px;
        border-radius: 15px;
        font-size: 14px;
        padding: 0;
    }
    
    QPushButton.recording {
        background-color: #f44336;  /* Rojo para grabación activa */
    }
    
    QLabel.sensor-value {
        font-size: 18px;
        font-weight: bold;
        color: #00b0ff;  /* Azul para valores de sensores */
    }
    
    QLabel.heart-rate {
        font-size: 24px;
        font-weight: bold;
        color: #f44336;  /* Rojo para ritmo cardíaco */
    }
"""

# Combinar todos los estilos según sea necesario
def get_combined_style(module_name):
    """
    Obtiene el estilo combinado para un módulo específico.
    
    Args:
        module_name: Nombre del módulo ('light', 'pulsator', 'headphone', 'sensor')
        
    Returns:
        str: Estilo combinado para ese módulo
    """
    combined_style = DARK_THEME
    
    if module_name == 'light':
        combined_style += LIGHT_TUBE_STYLE
    elif module_name == 'pulsator':
        combined_style += PULSATOR_STYLE
    elif module_name == 'headphone':
        combined_style += HEADPHONE_STYLE
    elif module_name == 'sensor':
        combined_style += SENSOR_MONITOR_STYLE
    
    # La barra de navegación y estado de dispositivos se usa en todos los módulos
    combined_style += NAVIGATION_BAR_STYLE
    combined_style += DEVICE_STATUS_BAR_STYLE
    
    return combined_style

# Función para obtener color primario (para uso programático)
def get_primary_color():
    """Devuelve el color primario usado en la aplicación"""
    return "#009688"  # Verde teal