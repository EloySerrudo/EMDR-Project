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
from src.views.therapist_dashboard import TherapistDashboard

# Modificar la función main() para manejar diferentes tipos de login
def main():
    """Función principal que inicia la aplicación con autenticación"""
    # Inicializar la aplicación Qt
    app = QApplication(sys.argv)
    
    # Asegurar que la base de datos esté inicializada
    init_db()
    
    # Variables para las ventanas principales
    login_window = None
    main_window = None
    admin_window = None
    
    def show_login():
        """Muestra la ventana de login"""
        nonlocal login_window
        # Crear nueva ventana de login
        login_window = LoginWidget()
        
        # Conectar señales
        login_window.login_successful.connect(on_login_success)
        
        # Mostrar ventana de login
        login_window.show()
    
    def on_login_success(username, user_type):
        """Maneja el login exitoso"""
        nonlocal main_window, admin_window
        
        # Cerrar ventana de login
        if login_window:
            login_window.close()
        
        # Abrir la ventana correspondiente según el tipo de usuario
        if user_type == "terapeutas":
            # Crear y mostrar dashboard terapéutico
            main_window = TherapistDashboard(username)
            
            # Conectar señal de logout del dashboard
            main_window.logout_requested.connect(on_logout_requested)
            
            main_window.show()
        else:  # administradores
            # Crear y mostrar panel de administración
            admin_window = AdminPanel(username)
            
            # Si AdminPanel tiene señal de logout, conectarla también
            if hasattr(admin_window, 'logout_requested'):
                admin_window.logout_requested.connect(on_logout_requested)
            
            admin_window.showMaximized()
    
    def on_logout_requested():
        """Maneja la solicitud de logout"""
        nonlocal main_window, admin_window
        
        # Cerrar ventanas principales si existen
        if main_window:
            main_window.close()
            main_window = None
        
        if admin_window:
            admin_window.close()
            admin_window = None
        
        # Mostrar nuevamente la ventana de login
        show_login()
    
    # Mostrar la ventana de login inicial
    show_login()
    
    # Ejecutar el bucle de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()