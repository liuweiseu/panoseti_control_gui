import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox
from PyQt6.QtCore import QProcess
from PyQt6.QtCore import QSocketNotifier

SOCK_PATH = "/tmp/meta.sock"

import json
import signal
import os
import socket

SERVER_NAME = 'panoseti_grpc_visualization'
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
        self.process_done = False
        if os.path.exists(SOCK_PATH):
            os.remove(SOCK_PATH)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(SOCK_PATH)
        self.server.listen(1)
        self.server_notifier = QSocketNotifier(
            self.server.fileno(),
            QSocketNotifier.Type.Read
        )
        self.server_notifier.activated.connect(self._on_new_connection)
        self.conn = None
        self.conn_notifier = None

    def _on_new_connection(self):
        # 防止重复触发
        self.server_notifier.setEnabled(False)

        self.conn, _ = self.server.accept()
        self.conn.setblocking(False)
        # 监听连接 socket
        self.conn_notifier = QSocketNotifier(
            self.conn.fileno(),
            QSocketNotifier.Type.Read
        )
        self.conn_notifier.activated.connect(self._on_ready_read)

    def init_ui(self):
        # 创建按钮
        button = QPushButton("点击我", self)
        button.setGeometry(100, 80, 100, 40)  # 按钮位置和大小
        button.clicked.connect(self.on_button_click)

    def on_button_click(self):
        # run cmd
        program = 'python'
        args = ['-u', 'src/grpc_process.py', '-m', 'ph256']
        self.run_command(program, args)

    def on_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        print(text)

    def on_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        print(text)
    
    def run_command(self, program, arguments):
        self.process.start(program, arguments)
        
    def on_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            print("OK.")
        else:
            print(exitStatus)
            print(exitCode)
            print("Failed.")
    
    def closeEvent(self, event):
        pid = self.process.processId()
        print(f"pid: {pid}")
        os.kill(pid, signal.SIGINT)
        self.process.waitForFinished(3000)
        event.accept()
    
    def _on_ready_read(self):
        data = self.conn.recv(4096)
        if not data:
            self.conn_notifier.setEnabled(False)
            self.conn.close()
            return
        for line in data.split(b"\n"):
            if line:
                print(line)
                #metadata = json.loads(line.decode())
        #print(metadata)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleWindow()
    window.show()
    sys.exit(app.exec())