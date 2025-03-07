import sys
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QWidget, QMainWindow, QApplication, QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout, QStackedLayout, QPushButton


class Color(QWidget):
    def __init__(self, nuevo_color):
        super().__init__()
        # Indicamos que se puede agregar un color de fondo
        self.setAutoFillBackground(True)
        paletaColores = self.palette()
        # Creamos el componente de color de fondo aplicando el nuevo color
        paletaColores.setColor(QPalette.Window, QColor(nuevo_color))
        # Aplicamos el nuevo color al componente
        self.setPalette(paletaColores)

class Controller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('EMDR Controller')
        self.resize(480, 320)
        # Creamos los layouts
        layout_principal = QVBoxLayout()
        layout_botones_1 = QHBoxLayout()
        layout_H = QHBoxLayout()
        layout_botones_2 = QVBoxLayout()
        self.layout_tipo_stack = QStackedLayout()
        # Agregamos los layout hijos al layout principal
        layout_principal.addLayout(layout_botones_1)
        layout_principal.addLayout(layout_H)

        layout_H.addLayout(layout_botones_2)
        layout_H.addLayout(self.layout_tipo_stack)

        # Creamos los botones
        btn_play = QPushButton('Play')
        # Publicar este boton en el layout de botones
        layout_botones_1.addWidget(btn_play)
        # Publicamos el color rojo al layout de tipo stack
        self.layout_tipo_stack.addWidget(Color('red')) # Index 0
        # Conectamos el evento pressed del boton respectivo
        btn_play.pressed.connect(lambda:self.activar_tabulador(0))

        # Creamos el boton azul
        btn_play24 = QPushButton('Play 24')
        layout_botones_1.addWidget(btn_play24)
        self.layout_tipo_stack.addWidget(Color('blue')) # Index 1
        btn_play24.pressed.connect(lambda:self.activar_tabulador(1))

        # Creamos el boton amarillo
        btn_stop = QPushButton('Stop')
        layout_botones_1.addWidget(btn_stop)
        self.layout_tipo_stack.addWidget(Color('yellow')) # Index 2
        btn_stop.pressed.connect(lambda: self.activar_tabulador(2))

        # Creamos el boton verde
        btn_pause = QPushButton('Pause')
        layout_botones_1.addWidget(btn_pause)
        self.layout_tipo_stack.addWidget(Color('green')) # Index 3
        btn_pause.pressed.connect(lambda: self.activar_tabulador(3))
        
        # Creamos los botones verticales
        btn_lightbar = QPushButton('Lightbar')
        layout_botones_2.addWidget(btn_lightbar)
        self.layout_tipo_stack.addWidget(Color('violet'))
        btn_lightbar.pressed.connect(lambda: self.activar_tabulador(4))
        
        btn_buzzer = QPushButton('Buzzer')
        layout_botones_2.addWidget(btn_buzzer)
        self.layout_tipo_stack.addWidget(Color('orange'))
        btn_buzzer.pressed.connect(lambda: self.activar_tabulador(5))
        
        btn_headphones = QPushButton('Headphones')
        layout_botones_2.addWidget(btn_headphones)
        self.layout_tipo_stack.addWidget(Color('pink'))
        btn_headphones.pressed.connect(lambda: self.activar_tabulador(6))

        # Creamos un componente generico para poder publicar el layout
        componente = QWidget()
        componente.setLayout(layout_principal)
        self.setCentralWidget(componente)

    def activar_tabulador(self, indice):
        self.layout_tipo_stack.setCurrentIndex(indice)
        print(f'Indice seleccionado: {indice}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = Controller()
    ventana.show()
    sys.exit(app.exec())