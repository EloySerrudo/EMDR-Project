from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer, Signal

class MyQtApp:
    """Reemplazo de thorpy.Application para PySide6"""
    
    def __init__(self, app=None, size=(800, 600), caption=None, icon="thorpy", center=True, flags=0):
        # No necesitamos hacer global _SCREEN y _CURRENT_APPLICATION como en thorpy
        # Usar QApplication existente o crear una nueva
        self.app = app if app is not None else QApplication([])  # Inicializa la aplicación Qt
        self.size = tuple(size)
        self.caption = caption
        
        # Crear ventana principal
        self.window = QMainWindow()
        self.window.resize(*self.size)
        
        # Establecer título si se proporciona
        if self.caption:
            self.window.setWindowTitle(caption)
        
        # Centrar ventana si se solicitó
        if center:
            self._center_window()
        
        # Establecer icono
        if icon and icon != "thorpy":  # "thorpy" era el valor predeterminado
            self.set_icon(icon)
        
        # Modo de pantalla completa
        if flags == 1:  # pygame.FULLSCREEN equivale a 1
            self.window.showFullScreen()
        
        # Ruta predeterminada como en la versión original
        self.default_path = "./"
    
    def set_icon(self, icon):
        """Establece el icono de la ventana"""
        if isinstance(icon, str):
            try:
                self.window.setWindowIcon(QIcon(icon))
            except:
                pass  # Ignorar errores si no se puede cargar el icono
    
    def _center_window(self):
        """Centra la ventana en la pantalla"""
        frame_geo = self.window.frameGeometry()
        screen_center = self.app.primaryScreen().availableGeometry().center()
        frame_geo.moveCenter(screen_center)
        self.window.move(frame_geo.topLeft())
    
    def show(self):
        """Muestra la ventana principal"""
        self.window.show()
        
    def exec(self):
        """Ejecuta el bucle principal de la aplicación"""
        return self.app.exec()
    
    def quit(self):
        """Cierra la aplicación"""
        self.app.quit()