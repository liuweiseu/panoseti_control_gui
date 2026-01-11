from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap

import logging, json, os
from pathlib import Path
import pyqtgraph as pg
import numpy as np

from src.mainwin_ui import Ui_MainWindow
from src.data_config_win import DataConfigWin, DataConfigOp
import asyncio

# from qasync import asyncSlot
from src.grpc_thread import AsyncioThread

from utils.utils import make_rich_logger

NUM_PLOTS = 4
class MainWin(QMainWindow, Ui_MainWindow):
    def __init__(self, root_dir_config='configs/root_dir.json'):
        self.logger = make_rich_logger('mainwin.log', logging.DEBUG, mode='a')
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
            self.ps_sw = root_config['panoseti_sw']
            self.ps_sw_control = f"{self.ps_sw}/control"
            self.grpc_config = {}
            self.grpc_config['daq_config_path'] = root_config['panoseti_grpc_config']['daq_config']
            self.grpc_config['net_config_path'] = root_config['panoseti_grpc_config']['net_config']
            self.grpc_config['obs_config_path'] = root_config['panoseti_grpc_config']['obs_config']
            self.append_log('************************************************************************')
            self.append_log(f"panoseti_sw: {self.ps_sw}")
            self.append_log(f"panoseti_grpc_daq: {self.grpc_config['daq_config_path']}")
            self.append_log(f"panoseti_grpc_net: {self.grpc_config['net_config_path']}")
            self.append_log(f"panoseti_grpc_obs: {self.grpc_config['obs_config_path']}")
            self.append_log('************************************************************************')
        else:
            self.append_log('************************************************************************')
            self.append_log(f'\"{root_dir_config}\" doesn\'t exist!')
            self.append_log('************************************************************************')
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
        self.power_status = 'off'
        self.visualization_status = 'off'
        # self.telescope_info = self._parse_obs_config()
        # use hard-coded name here for temp use
        # TODO: imporve this part
        self.telescope_info = [{'Simulation': [0, 0]}] * 1024
        self.telescope_info[250] = {'PTI': [0, 0]}
        self.telescope_info[252] = {'Fern': [0, 1]}
        self.telescope_info[253] = {'Winter': [1, 0]}
        self.telescope_info[254] = {'Gattini': [1, 1]}
    
    # ---------------------------------------------------------------------------
    # helper function
    # ---------------------------------------------------------------------------
    def _parse_obs_config(self):
        with open(self.grpc_config['obs_config_path'], 'r', encoding='utf-8') as f:
            config = json.load(f)
        domes = config['domes']
        # the max number of telescopes in the system is 1024
        telescope_name = ['Simulation'] * 1024
        for dome in domes:
            name = dome['name']
            modules_id = []
            i = 0
            for m in dome['modules']:
                ip_str = m['ip_addr'].split('.')
                mid = (int(ip_str[2]) << 6) + (int(ip_str[3]) >> 2)
                telescope_name[i] = f'{name}{i}'
                self.logger.debug(f'Found telescope at {name} site, and the module id is {mid}.')
        return telescope_name

    # ---------------------------------------------------------------------------
    # Sub Window creation
    # ---------------------------------------------------------------------------
    def open_data_config(self):
        if not hasattr(self, "data_config_win"):
            self.data_config_win = DataConfigWin()
        self.data_config_op = DataConfigOp(self.data_config_win)
        self.data_config_op.setup_signal_functions()
        self.data_config_win.show()

    # ---------------------------------------------------------------------------
    # Set placeholder
    # ---------------------------------------------------------------------------
    def set_placeholder(self, r, c):
        i = r * 2 + c
        pixmap = QPixmap("figure/placeholder.png")
        pixmap = pixmap.scaled(350, 350) 
        label = QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        self.static_label[i] = label
        self.view_layout.addWidget(self.static_label[i], r,c,1,1)
    # ---------------------------------------------------------------------------
    # Low level APIs
    # ---------------------------------------------------------------------------
    def on_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.append_log(text)

    def on_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.append_log(text)

    def append_log(self, text):
        self.console_output.appendPlainText(text.rstrip())
    
    # ---------------------------------------------------------------------------
    # plot figures
    # ---------------------------------------------------------------------------
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
            rdata = np.random.rand(32, 32)
            h, w = rdata.shape
            # show 2D img
            img = pg.ImageItem(rdata)
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
            plot_widget.setTitle("Simulation", color='w', size='12pt')
            text = pg.TextItem("Frame: 0", color='w', anchor=(0, 1))  # anchor=(0,1) 左下角
            text.setPos(0,0) 
            self.plot_widgets[i].addItem(text)
            self.qttexts[i] = text
        else:
            pass
        imgdata = data['image_array']
        h, w = imgdata.shape
        self.imgs[i].setRect(0,0,w,h)
        self.imgs[i].setImage(imgdata)
        self.qttexts[i].setText(f"Frame No: {data['frame_number']}")
        self.plot_widgets[i].setTitle(data['name'])

    # ---------------------------------------------------------------------------
    # Signal functions
    # ---------------------------------------------------------------------------
    def run_command(self, program, arguments):
        self.process.start(program, arguments)
    
    def power_clicked(self):
        os.chdir(self.ps_sw_control)
        program = 'python'
        if self.power_status == 'off':
            self.append_log('---------------------------------------------------------------------------')
            self.append_log('power.py on')
            self.append_log('---------------------------------------------------------------------------')
            arguments = ['-u', 'power.py', 'on']
            self.power_status = 'on'
            self.power.setText('Power Off')
        elif self.power_status == 'on':
            self.append_log('---------------------------------------------------------------------------')
            self.append_log('power.py off')
            self.append_log('---------------------------------------------------------------------------')
            arguments = ['-u','power.py', 'off']
            self.power_status = 'off'
            self.power.setText('Power On')
        self.run_command(program, arguments)

    def reboot_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --reboot')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','config.py', '--reboot']
        self.run_command(program, arguments)

    def marocconfig_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --maroc_config')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','config.py', '--maroc_config']
        self.run_command(program, arguments)
    
    def maskconfig_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --mask_config')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','config.py', '--mask_config']
        self.run_command(program, arguments)

    def calbrateph_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --calibrate_ph')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','config.py', '--calibrate_ph']
        self.run_command(program, arguments)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --show_ph_baselines')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','config.py', '--show_ph_baselines']
        self.run_command(program, arguments)


    def getuid_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('get_uids.py')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','get_uids.py']
        self.run_command(program, arguments)

    def startdaq_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('start.py')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','start.py']
        self.run_command(program, arguments)

    def stopdaq_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('stop.py')
        self.append_log('---------------------------------------------------------------------------')
        program = 'python'
        arguments = ['-u','stop.py']
        self.run_command(program, arguments)

    def submit_task(self):
        if self.visualization_status == 'off':
            self.append_log('---------------------------------------------------------------------------')
            self.append_log('Start Visualization.')
            self.append_log('---------------------------------------------------------------------------')
            self.grpc_thread.submit(self.grpc_thread.fetch_data())
            self.visualization_status = 'on'
            self.start_grpc.setText('Stop Visualization')
        elif self.visualization_status == 'on':
            self.append_log('---------------------------------------------------------------------------')
            self.append_log('Stop Visualization.')
            self.append_log('---------------------------------------------------------------------------')
            self.cancel_all()
            self.visualization_status = 'off'
            self.start_grpc.setText('Start Visualization')
        self.append_log('---------------------------------------------------------------------------')

    def cancel_all(self):
        self.grpc_thread.loop.call_soon_threadsafe(self.grpc_thread.shutdown_event.set)
        self.grpc_thread.cancel_all()
    
    def plot_data(self, data):
        mid = data['module_id']
        print(self.telescope_info[mid])
        for k, v in self.telescope_info[mid].items():
            name = k
            loc = v
        data['name'] = name
        self.show_plot(loc[0], loc[1], data)
    # ---------------------------------------------------------------------------
    # Setup signal function
    # ---------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.power.clicked.connect(self.power_clicked)
        self.reboot.clicked.connect(self.reboot_clicked)
        self.start_grpc.clicked.connect(self.submit_task)
        self.maroc_config.clicked.connect(self.marocconfig_clicked)
        self.mask_config.clicked.connect(self.maskconfig_clicked)
        self.cal_ph.clicked.connect(self.calbrateph_clicked)
        self.get_uid.clicked.connect(self.getuid_clicked)
        self.start_daq.clicked.connect(self.startdaq_clicked)
        self.stop_daq.clicked.connect(self.stopdaq_clicked)
        self.grpc_thread.data_signal.new_data.connect(self.plot_data)

