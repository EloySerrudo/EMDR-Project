import sys
from PySide6.QtWidgets import QApplication
from controller_qt import Controller

def main():
    """Función principal que inicializa y ejecuta la aplicación EMDR Controller"""
    # Crear la aplicación Qt
    app = QApplication(sys.argv)
    
    # Analizar argumentos de línea de comandos
    fullscreen = "--fullscreen" in sys.argv
    touchscreen = "--touchscreen" in sys.argv
    
    # Información de uso
    if "--help" in sys.argv or "-h" in sys.argv:
        print("EMDR Controller - PySide6 Version")
        print("Uso: python test_controller.py [opciones]")
        print("Opciones:")
        print("  --fullscreen   : Ejecutar en modo pantalla completa")
        print("  --touchscreen  : Optimizar para pantalla táctil (oculta el cursor)")
        return 0
    
    # Crear y mostrar el controlador
    try:
        controller = Controller(app=app, fullscreen=fullscreen, touchscreen=touchscreen)
        
        # Inicialmente mostrar el área de velocidad
        controller.set_area('speed')
        
        # Cargar configuración guardada
        controller.load_config()
        
        # Mostrar la ventana
        controller.show()
        
        # Ejecutar la aplicación
        return app.exec()
    
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())