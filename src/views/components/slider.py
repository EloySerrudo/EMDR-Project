import sys
from PySide6.QtWidgets import QApplication, QWidget, QSlider, QLabel, QFormLayout
from PySide6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('PyQt QSlider')
        self.setMinimumWidth(200)

        # create a grid layout
        layout = QFormLayout()
        self.setLayout(layout)

        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(0, 100)
        slider.setValue(50)
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setTickPosition(QSlider.TickPosition.TicksAbove)

        slider.valueChanged.connect(self.update)

        self.result_label = QLabel('', self)

        layout.addRow(slider)
        layout.addRow(self.result_label)

        # show the window
        self.show()

    def update(self, value):
        self.result_label.setText(f'Current Value: {value}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())