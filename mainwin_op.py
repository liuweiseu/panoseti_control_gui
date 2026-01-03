from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap

import logging, json
from pathlib import Path
import pyqtgraph as pg
import numpy as np

from mainwin import Ui_MainWindow
from data_config_op import DataConfigWin, DataConfigOp
import sys, asyncio, signal
sys.path.insert(0, 'panoseti_grpc')
from daq_data.client import AioDaqDataClient
import daq_data.cli as cli

from qasync import asyncSlot

from utils import create_logger

class MainWinOp(QMainWindow, Ui_MainWindow):
    def __init__(self, root_dir_config='root_dir.json'):
        create_logger('mainwin.log', 'MAINWIN', 'a')
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)
        self.setup_signal_functions()
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
            self.ps_grpc_daq = root_config['panoseti_grpc_config']['daq_config']
            self.ps_grpc_net = root_config['panoseti_grpc_config']['net_config']
            self.append_log(f'panoseti_sw: {self.ps_sw}')
            self.append_log(f'panoseti_grpc_daq: {self.ps_grpc_daq}')
            self.append_log(f'panoseti_grpc_daq: {self.ps_grpc_net}')
            self.append_log('********************************************')
        else:
            self.append_log('********************************************')
            self.append_log(f'\"{root_dir_config}\" doesn\'t exist!')
            self.append_log('********************************************')
        # add static figure by default
        pixmap = QPixmap("placeholder.png")
        pixmap = pixmap.scaled(350, 350) 
        self.static_label = []
        for i in range(4):
            label = QLabel()
            label.setPixmap(pixmap)
            label.setScaledContents(True)
            self.static_label.append(label)
        for r in range(2):
            for c in range(2):
                self.view_layout.addWidget(self.static_label[r*2+c], r,c,1,1)
        self.plot_widgets = []
        self.timers = []
        self.imgs = []
        self.shutdown_event = None
        self.loop = None
    
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

    async def aio_show_plot(self):
        self.append_log(f'Start panoseti grpc...')
        # 移除占位图片
        if self.static_label[0] is not None:
            for i in range(4):
                self.view_layout.removeWidget(self.static_label[i])
                self.static_label[i].deleteLater()
                self.static_label[i] = None
        # 创建 pyqtgraph 动态图
        if len(self.plot_widgets) < 4 :
            for r in range(2):
                for c in range(2):
                    plot_widget = pg.PlotWidget()
                    self.plot_widgets.append(plot_widget)
                    self.view_layout.addWidget(plot_widget, r, c, 1, 1)
                    # 创建 32x32 示例数据
                    data = np.random.rand(32, 32)
                    h, w = data.shape
                    # 在 pyqtgraph 中显示 2D 图
                    img = pg.ImageItem(data)
                    self.imgs.append(img)
                    plot_widget.addItem(img)
                    img.setRect(0,0,w,h)
                    # 可选：去掉坐标轴
                    plot_widget.hideAxis('bottom')
                    plot_widget.hideAxis('left')
                    # 设置color map
                    cmap = pg.colormap.get('plasma')  # PyQtGraph >=0.13
                    img.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
                    # set title
                    plot_widget.setTitle("Winter", color='w', size='12pt')
                    # 定时更新曲线
        # use self.addc
        async with self.addc as addc:
            host = None
            hp_io_cfg_path = 'panoseti_grpc/daq_data/config/hp_io_config_simulate.json'
            with open(hp_io_cfg_path, "r") as f:
                hp_io_cfg = json.load(f)
            await addc.init_hp_io(host, hp_io_cfg, timeout=15.0)
            valid_daq_hosts = await addc.get_valid_daq_hosts()
            print('valid_daq_hosts:', valid_daq_hosts)
            if host is not None and host not in valid_daq_hosts:
                raise ValueError(f"Invalid host: {host}. Valid hosts: {valid_daq_hosts}")
            
            stream_images_responses = await addc.stream_images(
            host,
            stream_movie_data=True,
            stream_pulse_height_data=True,
            update_interval_seconds=1.0,
            module_ids=[],
            parse_pano_images=True,
            wait_for_ready=True,
            )
            self.append_log(f'go!')
            async for parsed_pano_image in stream_images_responses:
                self.imgs[0].setImage(parsed_pano_image['image_array'])
            self.append_log(f'Done!')
        
        for i in range(4):
            timer = pg.QtCore.QTimer()
            self.timers.append(timer)
            timer.timeout.connect(lambda i=i: self.imgs[i].setImage(np.random.rand(32,32)))
            timer.start(100)

    def show_plot(self):
        self.append_log(f'Start panoseti grpc...')
        # 移除占位图片
        if self.static_label[0] is not None:
            for i in range(4):
                self.view_layout.removeWidget(self.static_label[i])
                self.static_label[i].deleteLater()
                self.static_label[i] = None
        # 创建 pyqtgraph 动态图
        if len(self.plot_widgets) <4 :
            for r in range(2):
                for c in range(2):
                    plot_widget = pg.PlotWidget()
                    self.plot_widgets.append(plot_widget)
                    self.view_layout.addWidget(plot_widget, r, c, 1, 1)
                    # 创建 32x32 示例数据
                    data = np.random.rand(32, 32)
                    h, w = data.shape
                    # 在 pyqtgraph 中显示 2D 图
                    img = pg.ImageItem(data)
                    self.imgs.append(img)
                    plot_widget.addItem(img)
                    img.setRect(0,0,w,h)
                    # 可选：去掉坐标轴
                    plot_widget.hideAxis('bottom')
                    plot_widget.hideAxis('left')
                    # 设置color map
                    cmap = pg.colormap.get('plasma')  # PyQtGraph >=0.13
                    img.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
                    # set title
                    plot_widget.setTitle("Winter", color='w', size='12pt')
                    # 定时更新曲线
        for i in range(4):
            timer = pg.QtCore.QTimer()
            self.timers.append(timer)
            timer.timeout.connect(lambda i=i: self.imgs[i].setImage(np.random.rand(32,32)))
            timer.start(100)
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
    
    def _signal_handler(self, *_):
            logging.getLogger("daq_data.client").info(
                "Shutdown signal received, closing client stream..."
            )
            self.shutdown_event.set()

    @asyncSlot(bool)
    async def run_grpc(self, checked: bool):
        # get panoseti_grpc client
        # use the same code from here:
        # https://github.com/panoseti/panoseti_grpc/blob/main/daq_data/cli.py#L182
        # Graceful Shutdown Setup
        self.shutdown_event = asyncio.Event()
        self.loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, self._signal_handler)
        self.addc = AioDaqDataClient(self.ps_grpc_daq, self.ps_grpc_net, stop_event=self.shutdown_event, log_level=logging.DEBUG)
        await self.aio_show_plot()
        # self.show_plot()

    @asyncSlot(bool)
    def on_click(self, checked: bool):
        self.append_log('clicked.')
        self.shutdown_event.set()
    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.reboot.clicked.connect(self.reboot_clicked)
        # self.start_grpc.clicked.connect(self.show_plot)
        self.start_grpc.clicked.connect(self.run_grpc)
        self.maroc_config.clicked.connect(self.on_click)

