#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
# Importaciones de componentes de vistas
from src.views.components.selectors import Selector
from src.views.components.buttons import CustomButton

# Simular Config.speeds para la prueba
class Config:
    speeds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

class SimpleSelectorTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prueba Simple - Widget Selector con Contorno Rojo")
        self.setGeometry(200, 200, 400, 300)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # Título
        title = QLabel("Selector con Contorno Rojo")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #333; margin-bottom: 20px;")
        main_layout.addWidget(title)
        
        # Crear botones para el selector
        self.btn_minus = CustomButton('-', size=(30, 30))
        self.btn_plus = CustomButton('+', size=(30, 30))
        
        # Estilo para los botones
        button_style = """
            QPushButton {
                background: #4CAF50;
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #4CAF50;
            }
            QPushButton:hover {
                background: #5CBF60;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """
        self.btn_minus.setStyleSheet(button_style)
        self.btn_plus.setStyleSheet(button_style)
        
        # Crear el selector
        self.selector = Selector('Velocidad', Config.speeds, '{0:d}/min', 
                                self.btn_minus, self.btn_plus, 
                                self.update_selector, ticks=Config.speeds, parent=self)
        
        # APLICAR EL CONTORNO ROJO AL SELECTOR
        # self.selector.setStyleSheet("""
        #     Selector QLabel {
        #         color: #333333;
        #         background-color: transparent;
        #         border: 1px solid #FF0000;
        #         font-weight: bold;
        #     }
        #     Selector QSlider {
        #         border: 1px solid #FF0000;
        #     }
        # """)
        
        # Conectar botones
        self.btn_plus.clicked.connect(self.selector.next_value)
        self.btn_minus.clicked.connect(self.selector.prev_value)
        
        # Centrar el selector
        main_layout.addStretch()
        main_layout.addWidget(self.selector, 0, Qt.AlignCenter)
        main_layout.addStretch()
        
        # Etiqueta de estado
        self.status_label = QLabel("Estado: Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background: #e8f5e8;
                border: 1px solid #4CAF50;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                color: #2e7d32;
            }
        """)
        main_layout.addWidget(self.status_label)
        
        # Aplicar fondo a la ventana
        self.setStyleSheet("""
            QMainWindow {
                background: #555555;
            }
        """)
    
    def update_selector(self):
        """Callback cuando cambia el valor del selector"""
        value = self.selector.get_value()
        self.status_label.setText(f"Valor seleccionado: {value}/min")
        print(f"Selector actualizado a: {value}/min")

def main():
    app = QApplication(sys.argv)
    
    # Configurar estilo de la aplicación
    app.setStyle('Fusion')
    
    window = SimpleSelectorTest()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()