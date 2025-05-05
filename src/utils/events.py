from PySide6.QtCore import QObject, Signal

class EventSystem(QObject):
    """Sistema de eventos para reemplazar los eventos personalizados de pygame"""
    
    # Definir señales que reemplazarán los eventos de pygame
    probe_event = Signal()  # Reemplaza a PROBE_EVENT
    action_event = Signal()  # Reemplaza a ACTION_EVENT
    
    def __init__(self):
        super().__init__()

# Crear instancia global única
event_system = EventSystem()