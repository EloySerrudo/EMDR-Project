from abc import ABC, abstractmethod
from PySide6.QtCore import QObject, Signal

class CleanupInterface(ABC):
    """Interfaz para componentes que requieren limpieza al cerrar"""
    
    @abstractmethod
    def cleanup(self):
        """Realizar limpieza de recursos"""
        pass
    
    @abstractmethod
    def is_busy(self) -> bool:
        """Verificar si el componente está ocupado y no debe cerrarse"""
        pass

class CleanupManager(QObject):
    """Manager centralizado para coordinar el cierre de componentes"""
    cleanup_completed = Signal()
    cleanup_failed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.components = []
        self.is_closing = False
    
    def register_component(self, component):
        """Registrar un componente para limpieza"""
        # Verificar que el componente tenga los métodos necesarios
        if hasattr(component, 'cleanup') and hasattr(component, 'is_busy'):
            if component not in self.components:
                self.components.append(component)
        else:
            print(f"Advertencia: {component.__class__.__name__} no implementa cleanup() o is_busy()")
    
    def unregister_component(self, component: CleanupInterface):
        """Desregistrar un componente"""
        if component in self.components:
            self.components.remove(component)
    
    def request_close(self) -> bool:
        """Solicitar cierre de todos los componentes"""
        if self.is_closing:
            return False
        
        # Verificar si algún componente está ocupado
        for component in self.components:
            if component.is_busy():
                print(f"Componente {component.__class__.__name__} está ocupado, no se puede cerrar")
                return False
        
        self.is_closing = True
        
        # Realizar limpieza de todos los componentes
        try:
            for component in self.components:
                component.cleanup()
            self.cleanup_completed.emit()
            return True
        except Exception as e:
            self.cleanup_failed.emit(str(e))
            return False