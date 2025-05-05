from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QPoint, QAbstractAnimation, QParallelAnimationGroup
from PySide6.QtCore import Property  # Añadir esta importación
from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QHBoxLayout
AlignLeft = Qt.AlignmentFlag.AlignLeft
AlignRight = Qt.AlignmentFlag.AlignRight
AnimForward = QAbstractAnimation.Direction.Forward
AnimBackward = QAbstractAnimation.Direction.Backward


class PyQtSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self):
        super().__init__()
        self.__initVal()
        self.__initUi()

    def __initVal(self):
        self.__circle_diameter = 20
        self.__animationEnabledFlag = False
        self.__pointAnimation = None
        self.__colorAnimation = None
        self.__point = QPoint(0, 0)  # Para propiedad point
        self.__color = 255  # Para propiedad color

    def __initUi(self):
        self.__circle = QPushButton()
        self.__circle.setCheckable(True)
        self.__circle.toggled.connect(self.__toggled)

        self.__layForBtnAlign = QHBoxLayout()
        self.__layForBtnAlign.setAlignment(AlignLeft)  # Comenzar alineado a la izquierda
        self.__layForBtnAlign.addWidget(self.__circle)
        self.__layForBtnAlign.setContentsMargins(0, 0, 0, 0)

        innerWidgetForStyle = QWidget()
        innerWidgetForStyle.setLayout(self.__layForBtnAlign)

        lay = QGridLayout()
        lay.addWidget(innerWidgetForStyle)
        lay.setContentsMargins(0, 0, 0, 0)

        self.setLayout(lay)

        self.__setStyle()

    # Define las propiedades requeridas para QPropertyAnimation
    def get_point(self):
        return self.__point
    
    def set_point(self, point):
        self.__point = point
        self.__circle.move(point)
    
    point = Property(QPoint, get_point, set_point)
    
    def get_color(self):
        return self.__color
    
    def set_color(self, color):
        self.__color = color
        self.__setColor(color)
    
    color = Property(int, get_color, set_color)

    def __setStyle(self):
        self.__circle.setFixedSize(self.__circle_diameter, self.__circle_diameter)
        self.setStyleSheet(
            f'QWidget {{ border: {self.__circle_diameter // 20}px solid #AAAAAA; '
            f'border-radius: {self.__circle_diameter // 2}px; }}')
        self.setFixedSize(self.__circle_diameter * 2, self.__circle_diameter)

    def setAnimation(self, f: bool):
        self.__animationEnabledFlag = f
        if self.__animationEnabledFlag:
            # INVERTIR: Animación va desde izquierda (encendido) a derecha (apagado)
            self.__colorAnimation = QPropertyAnimation(self, b'point')
            self.__colorAnimation.setDuration(100)
            self.__colorAnimation.setStartValue(QPoint(0, 0))  # Izquierda (ON)
            self.__colorAnimation.setEndValue(QPoint(self.__circle_diameter, 0))  # Derecha (OFF)

            self.__pointAnimation = QPropertyAnimation(self, b'color')
            self.__pointAnimation.setDuration(100)
            self.__pointAnimation.setStartValue(200)  # Más oscuro (ON) 
            self.__pointAnimation.setEndValue(255)  # Más claro (OFF)

            self.__animationGroup = QParallelAnimationGroup()
            self.__animationGroup.addAnimation(self.__colorAnimation)
            self.__animationGroup.addAnimation(self.__pointAnimation)

    def mousePressEvent(self, e):
        self.__circle.toggle()
        return super().mousePressEvent(e)

    def __toggled(self, f):
        if self.__animationEnabledFlag:
            if f:  # f es True cuando está encendido (ON) - INVERTIDO
                # Mover a la izquierda para ON (dirección inversa)
                self.__animationGroup.setDirection(AnimBackward)
                self.__animationGroup.start()
            else:  # f es False cuando está apagado (OFF) - INVERTIDO
                # Mover a la derecha para OFF (dirección normal)
                self.__animationGroup.setDirection(AnimForward)
                self.__animationGroup.start()
        else:
            if f:  # f es True cuando está encendido (ON) - INVERTIDO
                self.__circle.move(0, 0)  # INVERTIDO: izquierda = ON
                self.__layForBtnAlign.setAlignment(AlignLeft)
                self.__setColor(200)  # Más oscuro para ON
            else:  # f es False cuando está apagado (OFF) - INVERTIDO
                self.__circle.move(self.__circle_diameter, 0)  # INVERTIDO: derecha = OFF
                self.__layForBtnAlign.setAlignment(AlignRight)
                self.__setColor(255)  # Más claro para OFF
        self.toggled.emit(f)

    def __setColor(self, f: int):
        self.__circle.setStyleSheet(f'QPushButton {{ background-color: rgb({f}, {f}, 255); }}')

    def setCircleDiameter(self, diameter: int):
        self.__circle_diameter = diameter
        self.__setStyle()
        if self.__colorAnimation:
            self.__colorAnimation.setEndValue(QPoint(self.__circle_diameter, 0))

    def setChecked(self, f: bool):
        self.__circle.setChecked(f)
        self.__toggled(f)

    def isChecked(self):
        return self.__circle.isChecked()