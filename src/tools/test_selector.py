#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Importar el Selector personalizado
# Ajusta la ruta según tu estructura de proyecto
# Ajustar el path para importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.views.components.selectors import Selector

# Simular Config.speeds para la prueba
class Config:
    speeds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200]

# Crear CustomButton simplificado para la prueba
class CustomButton(QPushButton):
    def __init__(self, x, y, text, size=None, parent=None):
        super().__init__(text, parent)
        self.pos_x = x
        self.pos_y = y
        if size:
            self.setFixedSize(*size)

class SelectorTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prueba del Widget Selector")
        self.setGeometry(100, 100, 800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("Prueba del Widget Selector")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #333; margin-bottom: 20px;")
        main_layout.addWidget(title)
        
        # Crear múltiples selectores para probar diferentes configuraciones
        self.create_speed_selector_test(main_layout)
        # self.create_numeric_selector_test(main_layout)
        # self.create_no_slider_selector_test(main_layout)
        
        # Información de estado
        self.status_label = QLabel("Estado: Listo para probar")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                color: #333;
            }
        """)
        main_layout.addWidget(self.status_label)
        
        # Aplicar estilo general a la ventana
        self.setStyleSheet("""
            QMainWindow {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                  stop: 0 #323232,
                                  stop: 0.3 #2c2c2c,
                                  stop: 0.6 #252525,
                                  stop: 0.8 #1a1a1a,
                                  stop: 1 #000000);
            }
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """)
    
    def create_speed_selector_test(self, main_layout):
        """Crea el test del selector de velocidad (igual al código original)"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 2px solid #444444;
                border-radius: 12px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        
        # Título del test
        test_title = QLabel("Test 1: Selector de Velocidad (con slider y ticks)")
        test_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        test_title.setStyleSheet("color: #0066cc; margin-bottom: 10px;")
        frame_layout.addWidget(test_title)
        
        # Estilo para los botones (simulando el original)
        speed_button_style = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4CAF50,
                                          stop: 1 #45a049);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #4CAF50;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5CBF60,
                                          stop: 1 #4CAF50);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #3d8b40,
                                          stop: 1 #2e7d32);
            }
        """
        
        # Botón menos
        self.btn_speed_minus = CustomButton(0, 1, '-', size=(30, 30))
        self.btn_speed_minus.setStyleSheet(speed_button_style)
        
        # Botón más
        self.btn_speed_plus = CustomButton(2, 1, '+', size=(30, 30))
        self.btn_speed_plus.setStyleSheet(speed_button_style)
        
        # Selector de velocidad (exactamente como en el código original)
        self.sel_speed = Selector('Velocidad', Config.speeds, '{0:d}/min', 
                                  self.btn_speed_minus, self.btn_speed_plus, 
                                  self.update_speed, ticks=Config.speeds, parent=self)
    
        # Conectar botones (exactamente como en el código original)
        self.btn_speed_plus.clicked.connect(self.sel_speed.next_value)
        self.btn_speed_minus.clicked.connect(self.sel_speed.prev_value)
        
        frame_layout.addWidget(self.sel_speed)
        
        # Botón para obtener valor actual
        get_value_btn = QPushButton("Obtener Valor Actual")
        get_value_btn.clicked.connect(lambda: self.show_current_value(self.sel_speed, "Velocidad"))
        get_value_btn.setStyleSheet("background: #2196F3; color: white; padding: 8px; border-radius: 4px;")
        frame_layout.addWidget(get_value_btn)
        
        main_layout.addWidget(frame)
    
    def create_numeric_selector_test(self, main_layout):
        """Crea un test con selector numérico simple"""
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        
        # Título del test
        test_title = QLabel("Test 2: Selector Numérico Simple (sin valores predefinidos)")
        test_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        test_title.setStyleSheet("color: #FF9800; margin-bottom: 10px;")
        frame_layout.addWidget(test_title)
        
        # Container horizontal
        numeric_container = QHBoxLayout()
        
        # Selector numérico simple
        self.sel_numeric = Selector('Número', None, '{0:d}', None, None, 
                                   self.update_numeric, parent=self)
        
        # Botones de control
        btn_minus = QPushButton('-')
        btn_plus = QPushButton('+')
        btn_minus.setFixedSize(30, 30)
        btn_plus.setFixedSize(30, 30)
        
        btn_minus.clicked.connect(self.sel_numeric.prev_value)
        btn_plus.clicked.connect(self.sel_numeric.next_value)
        
        btn_style = "background: #FF5722; color: white; border-radius: 15px; font-weight: bold;"
        btn_minus.setStyleSheet(btn_style)
        btn_plus.setStyleSheet(btn_style)
        
        numeric_container.addStretch()
        numeric_container.addWidget(btn_minus)
        numeric_container.addWidget(self.sel_numeric)
        numeric_container.addWidget(btn_plus)
        numeric_container.addStretch()
        
        frame_layout.addLayout(numeric_container)
        
        # Botón para obtener valor
        get_value_btn = QPushButton("Obtener Valor Actual")
        get_value_btn.clicked.connect(lambda: self.show_current_value(self.sel_numeric, "Numérico"))
        get_value_btn.setStyleSheet("background: #FF9800; color: white; padding: 8px; border-radius: 4px;")
        frame_layout.addWidget(get_value_btn)
        
        main_layout.addWidget(frame)
    
    def create_no_slider_selector_test(self, main_layout):
        """Crea un test con selector sin slider"""
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        
        # Título del test
        test_title = QLabel("Test 3: Selector sin Slider (solo etiquetas)")
        test_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        test_title.setStyleSheet("color: #9C27B0; margin-bottom: 10px;")
        frame_layout.addWidget(test_title)
        
        # Container horizontal
        no_slider_container = QHBoxLayout()
        
        # Valores de prueba
        test_values = ['Bajo', 'Medio', 'Alto', 'Máximo']
        
        # Selector sin slider
        self.sel_no_slider = Selector('Nivel', test_values, '{0}', None, None, 
                                     self.update_no_slider, show_slider=False, parent=self)
        
        # Botones de control
        btn_prev = QPushButton('◀')
        btn_next = QPushButton('▶')
        btn_prev.setFixedSize(30, 30)
        btn_next.setFixedSize(30, 30)
        
        btn_prev.clicked.connect(self.sel_no_slider.prev_value)
        btn_next.clicked.connect(self.sel_no_slider.next_value)
        
        btn_style = "background: #9C27B0; color: white; border-radius: 15px; font-weight: bold;"
        btn_prev.setStyleSheet(btn_style)
        btn_next.setStyleSheet(btn_style)
        
        no_slider_container.addStretch()
        no_slider_container.addWidget(btn_prev)
        no_slider_container.addWidget(self.sel_no_slider)
        no_slider_container.addWidget(btn_next)
        no_slider_container.addStretch()
        
        frame_layout.addLayout(no_slider_container)
        
        # Botón para obtener valor
        get_value_btn = QPushButton("Obtener Valor Actual")
        get_value_btn.clicked.connect(lambda: self.show_current_value(self.sel_no_slider, "Sin Slider"))
        get_value_btn.setStyleSheet("background: #9C27B0; color: white; padding: 8px; border-radius: 4px;")
        frame_layout.addWidget(get_value_btn)
        
        main_layout.addWidget(frame)
    
    def update_speed(self):
        """Callback para el selector de velocidad"""
        value = self.sel_speed.get_value()
        self.status_label.setText(f"Velocidad actualizada: {value}/min")
        print(f"Velocidad cambiada a: {value}/min")
    
    def update_numeric(self):
        """Callback para el selector numérico"""
        value = self.sel_numeric.get_value()
        self.status_label.setText(f"Valor numérico actualizado: {value}")
        print(f"Valor numérico cambiado a: {value}")
    
    def update_no_slider(self):
        """Callback para el selector sin slider"""
        value = self.sel_no_slider.get_value()
        self.status_label.setText(f"Nivel actualizado: {value}")
        print(f"Nivel cambiado a: {value}")
    
    def show_current_value(self, selector, name):
        """Muestra el valor actual del selector"""
        value = selector.get_value()
        self.status_label.setText(f"Valor actual de {name}: {value}")
        print(f"Valor actual de {name}: {value}")

def main():
    app = QApplication(sys.argv)
    
    # Configurar estilo de la aplicación
    app.setStyle('Fusion')
    
    window = SelectorTestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()