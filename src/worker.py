import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox
from PyQt6.QtCore import QProcess
import json

class SimpleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("简单PyQt窗口")
        self.setGeometry(100, 100, 300, 200)  # 窗口位置和大小: x, y, w, h
        self.init_ui()
        # Process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        self.process.finished.connect(self.on_finished)


    def init_ui(self):
        # 创建按钮
        button = QPushButton("点击我", self)
        button.setGeometry(100, 80, 100, 40)  # 按钮位置和大小
        button.clicked.connect(self.on_button_click)

    def on_button_click(self):
        # run cmd
        program = 'python'
        args = ['-u', 'src/grpc_process.py']
        self.run_command(program, args)

    def on_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        info = json.loads(text)
        print(info)

    def on_stderr(self):
        text = self.process.readAllStandardError().data().decode()
    
    def run_command(self, program, arguments):
        self.process.start(program, arguments)
        
    def on_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            print("OK.")
        else:
            print("Failed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleWindow()
    window.show()
    sys.exit(app.exec())