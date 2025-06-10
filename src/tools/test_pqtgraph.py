import pyqtgraph as pg
from PySide6 import QtWidgets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Temperature vs time plot
        self.plot_graph = pg.PlotWidget()
        self.plot_graph.setBackground('#FFFFFF')
        self.plot_graph.showGrid(x=True, y=True, alpha=0.8)
        self.setCentralWidget(self.plot_graph)
        time = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        temperature = [31, 32, 34, 32, 33, 31, 29, 32, 35, 31]
        self.plot_graph.plot(
            time, 
            temperature, 
            pen=pg.mkPen('#2196F3', width=2)
        )
        # self.plot_graph.setXRange(
        #     -1, 11, padding=0
        # )
        view_box = self.plot_graph.getPlotItem().getViewBox()
        view_box.setXRange(-1, 11, padding=0.1)

app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()