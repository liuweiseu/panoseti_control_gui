import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from mainwin import Ui_MainWindow
from mainwin_op import MainWinOp
from data_config_op import DataConfigWin, DataConfigOp
from data_config_widget import Ui_Form
import asyncio
import signal
import logging
from pathlib import Path
import json

sys.path.insert(0, 'panoseti_grpc')
from daq_data.client import AioDaqDataClient
import daq_data.cli as cli

def main():
    app = QApplication(sys.argv)
    w = MainWinOp()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    