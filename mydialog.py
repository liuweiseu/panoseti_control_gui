from PyQt6.QtWidgets import QDialog
from dialog import Ui_Dialog

class MyDialog(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
