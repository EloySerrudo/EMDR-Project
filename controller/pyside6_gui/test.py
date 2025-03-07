from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QWidget, QMainWindow, QApplication, QVBoxLayout, QHBoxLayout, QGridLayout, QStackedLayout


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

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Layouts en PySide')
        # Layout Grid
        layout = QGridLayout()
        layout.addWidget(Color('red'),0,0)
        layout.addWidget(Color('blue'),0,1)
        layout.addWidget(Color('green'),0,2)
        layout.addWidget(Color('yellow'),1,0)
        layout.addWidget(Color('purple'),2,0)
        layout.addWidget(Color('pink'),3,0)

        # Crear QStackedLayout
        stackedLayout = QStackedLayout()
        
        # Primera página con QGridLayout
        grid1 = QGridLayout()
        grid1.addWidget(Color('cyan'), 0, 0)
        grid1.addWidget(Color('lightcyan'), 0, 1)
        grid1.addWidget(Color('darkcyan'), 1, 0)
        grid1.addWidget(Color('teal'), 1, 1)
        page1 = QWidget()
        page1.setLayout(grid1)
        stackedLayout.addWidget(page1)
        
        # Segunda página con QGridLayout
        grid2 = QGridLayout()
        grid2.addWidget(Color('magenta'), 0, 0)
        grid2.addWidget(Color('lightpink'), 0, 1)
        grid2.addWidget(Color('deeppink'), 1, 0)
        grid2.addWidget(Color('purple'), 1, 1)
        page2 = QWidget()
        page2.setLayout(grid2)
        stackedLayout.addWidget(page2)
        
        # Tercera página con QGridLayout
        grid3 = QGridLayout()
        grid3.addWidget(Color('orange'), 0, 0)
        grid3.addWidget(Color('darkorange'), 0, 1)
        grid3.addWidget(Color('coral'), 1, 0)
        grid3.addWidget(Color('tomato'), 1, 1)
        page3 = QWidget()
        page3.setLayout(grid3)
        stackedLayout.addWidget(page3)
        
        # Crear contenedor para el QStackedLayout
        stackedWidget = QWidget()
        stackedWidget.setLayout(stackedLayout)
        
        # Añadir el widget al QGridLayout, posición (1,1), abarcando 3 filas y 2 columnas
        layout.addWidget(stackedWidget, 1, 1, 3, 2)  # From (1,1) to (3,2)
        
        # Seleccionar la página visible inicial (opcional)
        stackedLayout.setCurrentIndex(0)

        # Creamos un componente generico para poder publicar el layout
        componente = QWidget()
        componente.setLayout(layout)
        self.setCentralWidget(componente)

if __name__ == '__main__':
    app = QApplication([])
    ventana = VentanaPrincipal()
    ventana.show()
    app.exec()