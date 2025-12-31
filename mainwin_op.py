from PyQt6.QtCore import QProcess
import logging, json
from pathlib import Path

from utils import create_logger

class MainWinOp(object):
    def __init__(self, win, root_dir_config='root_dir.json'):
        create_logger('mainwin.log', 'MAINWIN', 'a')
        self.win = win
        self.ui = win
        self.setup_signal_functions()
        # Process
        self.process = QProcess(win)
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        fpath = Path(root_dir_config)
        if fpath.exists():
            with open(root_dir_config, 'r', encoding='utf-8') as f:
                root_config = json.load(f)
            self.append_log('********************************************')
            self.ps_sw = root_config['panoseti_sw']
            self.ps_grpc = root_config['panoseti_grpc']
            self.append_log(f'panoseti_sw: {self.ps_sw}')
            self.append_log(f'panoseti_grpc: {self.ps_grpc}')
            self.append_log('********************************************')
        else:
            self.append_log('********************************************')
            self.append_log(f'\"{root_dir_config}\" doesn\'t exist!')
            self.append_log('********************************************')

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
    def run_command(self, program, arguments):
        self.process.start(program, arguments)
    
    def reboot_clicked(self):
        program = 'python'
        arguments = [f'{self.ps_sw}/config.py', '--reboot']
        self.run_command(program, arguments)

    def marocconfig_clicked(self):
        program = 'python'
        arguments = [f'{self.ps_sw}/config.py', '--maroc_config']
        self.run_command(program, arguments)
    
    def maskconfig_clicked(self):
        program = 'python'
        arguments = [f'{self.ps_sw}/config.py', '--mask_config']
        self.run_command(program, arguments)

    def calbrateph_clicked(self):
        program = 'python'
        arguments = [f'{self.ps_sw}/config.py', '--mask_config']
        self.run_command(program, arguments)
    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.ui.reboot.clicked.connect(self.reboot_clicked)

