import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from mainwin import Ui_MainWindow
from mydialog import MyDialog

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.pushButton.clicked.connect(self.open_dialog)

    def open_dialog(self):
        dlg = MyDialog(self)

        # 模态弹窗
        if dlg.exec():
            print("用户输入")
        else:
            print("取消或关闭")
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())