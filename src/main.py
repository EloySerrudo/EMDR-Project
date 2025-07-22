import sys
import os
from PySide6.QtWidgets import QApplication

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importaciones para componentes específicos
from views.auth.login import LoginWidget
from views.admin.admin_dashboard import AdminDashboard
from views.therapist.therapist_dashboard import TherapistDashboard

# Importar e inicializar la base de datos
from src.database.db_connection import init_db

def main():
    """Función principal que inicia la aplicación con autenticación"""
    # Inicializar la aplicación Qt
    app = QApplication(sys.argv)
    
    # Inicializar base de datos al arrancar
    print("🔧 Inicializando base de datos...")
    init_db()
    
    # Variables para las ventanas principales
    login_window = None
    user_dashboard_window = None
    admin_dashboard_window = None
    
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
        nonlocal user_dashboard_window, admin_dashboard_window
        
        # Cerrar ventana de login
        if login_window:
            login_window.close()
        
        # Abrir la ventana correspondiente según el tipo de usuario
        if user_type == "terapeutas":
            # Crear y mostrar dashboard terapéutico
            user_dashboard_window = TherapistDashboard(username)
            
            # Conectar señal de logout del dashboard
            user_dashboard_window.logout_requested.connect(on_logout_requested)
            
            user_dashboard_window.show()
        else:  # administradores
            # Crear y mostrar dashboard administrativo
            admin_dashboard_window = AdminDashboard(username)
            
            # Conectar señal de logout del dashboard
            admin_dashboard_window.logout_requested.connect(on_logout_requested)
            
            admin_dashboard_window.show()
    
    def on_logout_requested():
        """Maneja la solicitud de logout"""
        nonlocal user_dashboard_window, admin_dashboard_window
        
        # Cerrar ventanas principales si existen
        if user_dashboard_window:
            user_dashboard_window.close()
            user_dashboard_window = None
        
        if admin_dashboard_window:
            admin_dashboard_window.close()
            admin_dashboard_window = None
        
        # Mostrar nuevamente la ventana de login
        show_login()
    
    # Mostrar la ventana de login inicial
    show_login()
    
    # Ejecutar el bucle de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()