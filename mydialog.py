from PyQt6.QtWidgets import QDialog
from data_config_win import Ui_DataConfigWin

class MyDialog(QDialog, Ui_DataConfigWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
