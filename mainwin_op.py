from PyQt6.QtCore import QProcess
import logging

from utils import create_logger

class MainWinOp(object):
    def __init__(self, win):
        create_logger('mainwin.log', 'MAINWIN', 'a')
        self.win = win
        self.ui = win
        self.setup_signal_functions()
        # Process
        self.process = QProcess(win)
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)

    # ------------------------------------------------------------------------
    # Low level APIs
    # ------------------------------------------------------------------------
    def on_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.append_log(text)

    def on_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.append_log(text)

    def append_log(self, text):
        self.ui.console_output.appendPlainText(text.rstrip())
    
    # ------------------------------------------------------------------------
    # Signal functions
    # ------------------------------------------------------------------------
    def run_command(self):
        self.ui.console_output.clear()

        # Linux / macOS 示例
        program = "python"
        arguments = ["cmd_test.py"]
        self.process.start(program, arguments)
    
    def reboot_clicked(self):
        self.run_command()

    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.ui.reboot.clicked.connect(self.reboot_clicked)

