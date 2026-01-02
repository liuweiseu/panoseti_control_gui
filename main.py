import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from mainwin import Ui_MainWindow
from mainwin_op import MainWinOp
from data_config_op import DataConfigWin, DataConfigOp
from data_config_widget import Ui_Form
from qasync import QEventLoop, asyncSlot
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
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    w = MainWinOp()
    w.show()
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
    