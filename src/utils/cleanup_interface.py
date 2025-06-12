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
            print("Ya se está realizando un proceso de cierre")
            return False
        
        print(f"Verificando estado de {len(self.components)} componentes...")
        
        # Verificar si algún componente está ocupado
        busy_components = []
        for component in self.components:
            try:
                if component.is_busy():
                    busy_components.append(component.__class__.__name__)
                    print(f"❌ Componente {component.__class__.__name__} está ocupado")
                else:
                    print(f"✅ Componente {component.__class__.__name__} está listo para cerrar")
            except Exception as e:
                print(f"⚠️  Error verificando {component.__class__.__name__}: {e}")
                busy_components.append(f"{component.__class__.__name__} (error)")
        
        if busy_components:
            print(f"BLOQUEO: Los siguientes componentes están ocupados: {', '.join(busy_components)}")
            self.cleanup_failed.emit(f"Componentes ocupados: {', '.join(busy_components)}")
            return False
        
        print("Todos los componentes están listos. Iniciando limpieza...")
        self.is_closing = True
        
        # Realizar limpieza de todos los componentes
        try:
            for component in self.components:
                try:
                    print(f"Limpiando {component.__class__.__name__}...")
                    component.cleanup()
                    print(f"✅ {component.__class__.__name__} limpiado correctamente")
                except Exception as e:
                    print(f"❌ Error limpiando {component.__class__.__name__}: {e}")
                    raise e
            
            print("✅ Limpieza de todos los componentes completada")
            self.cleanup_completed.emit()
            return True
        except Exception as e:
            error_msg = f"Error durante la limpieza: {str(e)}"
            print(f"❌ {error_msg}")
            self.cleanup_failed.emit(error_msg)
            return False