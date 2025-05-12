import sys
import os
from PySide6.QtWidgets import QApplication

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importaciones para componentes específicos
from src.views.login import LoginWidget
from src.database.db_connection import init_db
# Añadir import para el panel de administración
from src.views.admin_panel import AdminPanel
# Añadir import para el panel de control de EMDR
from src.views.control_panel import EMDRControlPanel

# Modificar la función main() para manejar diferentes tipos de login
def main():
    """Función principal que inicia la aplicación con autenticación"""
    # Inicializar la aplicación Qt
    app = QApplication(sys.argv)
    
    # Asegurar que la base de datos esté inicializada
    init_db()
    
    # Crear y mostrar la ventana de login
    login_window = LoginWidget()
    
    # Variables para las ventanas principales
    main_window = None
    admin_window = None
    
    # Función para manejar el login exitoso
    def on_login_success(username, user_type):
        nonlocal main_window, admin_window
        # Cerrar ventana de login
        login_window.close()
        
        # Abrir la ventana correspondiente según el tipo de usuario
        if user_type == "terapeutas":
            # Crear y mostrar ventana principal de terapia
            main_window = EMDRControlPanel(username)
            main_window.showMaximized()
        else:  # administradores
            # Crear y mostrar panel de administración
            admin_window = AdminPanel(username)
            admin_window.showMaximized()
    
    # Conectar señal de login exitoso
    login_window.login_successful.connect(on_login_success)
    
    # Mostrar ventana de login
    login_window.show()
    
    # Ejecutar el bucle de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()