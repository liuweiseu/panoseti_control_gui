import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon
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
    script_path = os.path.realpath(__file__)
    curdir = os.path.dirname(script_path)
    app.setWindowIcon(QIcon(f"{curdir}/icon/casper_icon.png"))
    w = MainWinOp()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    