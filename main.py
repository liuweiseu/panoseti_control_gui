import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QPixmap
from mainwin import Ui_MainWindow
from mainwin_op import MainWinOp
from data_config_op import DataConfigWin, DataConfigOp
from data_config_widget import Ui_Form
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)
        # add static figure by default
        self.static_label0 = QLabel()
        self.static_label1 = QLabel()
        self.static_label2 = QLabel()
        self.static_label3 = QLabel()
        pixmap = QPixmap("placeholder.png")
        pixmap = pixmap.scaled(350, 350) 
        self.static_label0.setPixmap(pixmap)
        self.static_label0.setScaledContents(True)
        self.static_label1.setPixmap(pixmap)
        self.static_label1.setScaledContents(True)
        self.static_label2.setPixmap(pixmap)
        self.static_label2.setScaledContents(True)
        self.static_label3.setPixmap(pixmap)
        self.static_label3.setScaledContents(True)
        self.view_layout.addWidget(self.static_label0, 0,0,1,1)
        self.view_layout.addWidget(self.static_label1, 0,1,1,1)
        self.view_layout.addWidget(self.static_label2, 1,0,1,1)
        self.view_layout.addWidget(self.static_label3, 1,1,1,1)


    def open_data_config(self):
        if not hasattr(self, "data_config_win"):
            self.data_config_win = DataConfigWin()
        self.data_config_op = DataConfigOp(self.data_config_win)
        self.data_config_op.setup_signal_functions()
        self.data_config_win.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    op = MainWinOp(w)
    w.show()
    sys.exit(app.exec())