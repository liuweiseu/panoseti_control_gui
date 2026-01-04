from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap

import logging, json
from pathlib import Path
import pyqtgraph as pg
import numpy as np

from mainwin import Ui_MainWindow
from data_config_op import DataConfigWin, DataConfigOp
import asyncio

# from qasync import asyncSlot
from grpc_thread import AsyncioThread

from utils import create_logger

NUM_PLOTS = 4
class MainWinOp(QMainWindow, Ui_MainWindow):
    def __init__(self, root_dir_config='root_dir.json'):
        create_logger('mainwin.log', 'MAINWIN', 'a')
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)
        # Process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        fpath = Path(root_dir_config)
        if fpath.exists():
            with open(root_dir_config, 'r', encoding='utf-8') as f:
                root_config = json.load(f)
            self.append_log('********************************************')
            self.ps_sw = root_config['panoseti_sw']
            self.grpc_config = {}
            self.grpc_config['daq_config_path'] = root_config['panoseti_grpc_config']['daq_config']
            self.grpc_config['net_config_path'] = root_config['panoseti_grpc_config']['net_config']
            self.append_log(f"panoseti_sw: {self.ps_sw}")
            self.append_log(f"panoseti_grpc_daq: {self.grpc_config['daq_config_path']}")
            self.append_log(f"panoseti_grpc_daq: {self.grpc_config['net_config_path']}")
            self.append_log('********************************************')
        else:
            self.append_log('********************************************')
            self.append_log(f'\"{root_dir_config}\" doesn\'t exist!')
            self.append_log('********************************************')
        # add static figure by default
        self.static_label = [None] * NUM_PLOTS
        for r in range(2):
            for c in range(2):
                self.set_placeholder(r, c)
        self.plot_widgets = [None] * NUM_PLOTS
        self.timers = [None] * NUM_PLOTS
        self.imgs = [None] * NUM_PLOTS
        self.qttexts = [None] * NUM_PLOTS
        self.shutdown_event = None
        self.grpc_thread = AsyncioThread(self.grpc_config)
        self.grpc_thread.start()
        self.setup_signal_functions()
    

    # ------------------------------------------------------------------------
    # Sub Window creation
    # ------------------------------------------------------------------------
    def open_data_config(self):
        if not hasattr(self, "data_config_win"):
            self.data_config_win = DataConfigWin()
        self.data_config_op = DataConfigOp(self.data_config_win)
        self.data_config_op.setup_signal_functions()
        self.data_config_win.show()

    # ------------------------------------------------------------------------
    # Set placeholder
    # ------------------------------------------------------------------------
    def set_placeholder(self, r, c):
        i = r * 2 + c
        pixmap = QPixmap("placeholder.png")
        pixmap = pixmap.scaled(350, 350) 
        label = QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        self.static_label[i] = label
        self.view_layout.addWidget(self.static_label[i], r,c,1,1)
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
        self.console_output.appendPlainText(text.rstrip())
    
    # ------------------------------------------------------------------------
    # plot figures
    # ------------------------------------------------------------------------
    def start_grpc_clicked(self):
        asyncio.run_coroutine_threadsafe(self.show_plot(), self.loop)

    def show_plot(self, r, c, data):
        i = r * 2 + c
        if self.static_label[i] is not None:
            self.view_layout.removeWidget(self.static_label[i])
            self.static_label[i].deleteLater()
            self.static_label[i] = None
            # create obj
            plot_widget = pg.PlotWidget()
            self.plot_widgets[i] = plot_widget
            self.view_layout.addWidget(plot_widget, r, c, 1, 1)
            # create random data for default viewer
            data = np.random.rand(32, 32)
            h, w = data.shape
            # show 2D img
            img = pg.ImageItem(data)
            self.imgs[i] = img
            plot_widget.addItem(img)
            img.setRect(0,0,w,h)
            # remove axis
            plot_widget.hideAxis('bottom')
            plot_widget.hideAxis('left')
            # set color map
            cmap = pg.colormap.get('plasma')  # PyQtGraph >=0.13
            img.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
            # set title
            plot_widget.setTitle("Winter", color='w', size='12pt')
            text = pg.TextItem("Frame: 0", color='w', anchor=(0, 1))  # anchor=(0,1) 左下角
            text.setPos(0,0) 
            self.plot_widgets[i].addItem(text)
            self.qttexts[i] = text
        else:
            pass
        self.imgs[i].setImage(data['image_array'])
        self.qttexts[i].setText(f"Frame No: {data['frame_number']}")

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

    def submit_task(self):
        self.append_log('Start Task.')
        self.grpc_thread.submit(self.grpc_thread.fetch_data())

    def cancel_all(self):
        self.append_log('Cancel Task.')
        self.grpc_thread.loop.call_soon_threadsafe(self.grpc_thread.shutdown_event.set)
        self.grpc_thread.cancel_all()
    
    def plot_data(self, data):
        self.show_plot(0, 0, data)
    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.reboot.clicked.connect(self.reboot_clicked)
        self.start_grpc.clicked.connect(self.submit_task)
        self.maroc_config.clicked.connect(self.cancel_all)
        self.grpc_thread.data_signal.new_data.connect(self.plot_data)

