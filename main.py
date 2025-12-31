import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from mainwin import Ui_MainWindow
from mainwin_op import MainWinOp
from data_config_op import DataConfigWin, DataConfigOp
from data_config_widget import Ui_Form
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)

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