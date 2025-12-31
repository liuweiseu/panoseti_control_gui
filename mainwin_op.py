from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap

import logging, json
from pathlib import Path
import pyqtgraph as pg
import numpy as np

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
        # add static figure by default
        pixmap = QPixmap("placeholder.png")
        pixmap = pixmap.scaled(350, 350) 
        self.ui.static_label = []
        for i in range(4):
            label = QLabel()
            label.setPixmap(pixmap)
            label.setScaledContents(True)
            self.ui.static_label.append(label)
        for r in range(2):
            for c in range(2):
                self.ui.view_layout.addWidget(self.ui.static_label[r*2+c], r,c,1,1)
        self.plot_widgets = []
        self.timers = []
        self.imgs = []
        
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
    # plot figures
    # ------------------------------------------------------------------------
    def show_plot(self):
        self.append_log(f'Start panoseti grpc...')
        # 移除占位图片
        if self.ui.static_label[0] is not None:
            for i in range(4):
                self.ui.view_layout.removeWidget(self.ui.static_label[i])
                self.ui.static_label[i].deleteLater()
                self.ui.static_label[i] = None
            

        # 创建 pyqtgraph 动态图
        if len(self.plot_widgets) <4 :
            for r in range(2):
                for c in range(2):
                    plot_widget = pg.PlotWidget()
                    self.plot_widgets.append(plot_widget)
                    self.ui.view_layout.addWidget(plot_widget, r, c, 1, 1)
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
    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.ui.reboot.clicked.connect(self.reboot_clicked)
        self.ui.start_grpc.clicked.connect(self.show_plot)

