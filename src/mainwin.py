from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap

import logging, json, os
from pathlib import Path
import pyqtgraph as pg
import numpy as np

from src.mainwin_ui import Ui_MainWindow
from src.data_config_win import DataConfigWin, DataConfigOp
import asyncio, signal
from multiprocessing import shared_memory, resource_tracker

# from qasync import asyncSlot
from src.grpc_thread import AsyncioThread

from utils.utils import make_rich_logger

NUM_PLOTS = 4
class MainWin(QMainWindow, Ui_MainWindow):
    def __init__(self, root_dir_config='configs/panoseti_config.json'):
        self.logger = make_rich_logger('mainwin.log', logging.WARNING, mode='a')
        self.logger.info('********************************************')
        self.logger.info('Main Window started.')
        self.logger.info('********************************************')
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)
        # Process for panoseti software
        self.ps_process = QProcess(self)
        self.ps_process.readyReadStandardOutput.connect(self.ps_stdout)
        self.ps_process.readyReadStandardError.connect(self.ps_stderr)
        self.ps_process.finished.connect(self.ps_finished)
        # Process for panoseti grpc
        self.grpc_process = QProcess(self)
        self.grpc_process.readyReadStandardOutput.connect(self.grpc_stdout)
        self.grpc_process.readyReadStandardError.connect(self.grpc_stderr)
        self.grpc_process.finished.connect(self.grpc_finished)
        # use shared memory to get image data
        self.shm = None
        self.shm_name = None
        self.img = None
        fpath = Path(root_dir_config)
        if fpath.exists():
            with open(root_dir_config, 'r', encoding='utf-8') as f:
                root_config = json.load(f)
            self.ps_sw = root_config['panoseti_sw']['sw_path']
            self.ps_sw_daq_config = f"{self.ps_sw}/control/configs/daq_config.json"
            self.ps_sw_network_config = f"{self.ps_sw}/control/configs/network_config.json"
            self.ps_sw_obs_config = f"{self.ps_sw}/control/configs/obs_config.json"
            self.ps_sw_data_config = f"{self.ps_sw}/control/configs/data_config.json"
            self.ps_sw_python = root_config['panoseti_sw']['python_path']
            self.ps_sw_control = f"{self.ps_sw}/control"
            self.grpc_config = {}
            self.grpc_config['daq_config_path'] = self.ps_sw_daq_config
            self.grpc_config['net_config_path'] = self.ps_sw_network_config
            self.grpc_config['obs_config_path'] = self.ps_sw_obs_config
            #self.grpc_config['hp_io_cfg_path'] = 'panoseti_grpc/daq_data/config/hp_io_config_simulate.json'
            self.grpc_config['hp_io_cfg_path'] = 'panoseti_grpc/daq_data/config/hp_io_config_palomar.json'
            self.logger.info(f"panoseti_sw_path: {self.ps_sw}")
            self.logger.info(f"panoseti_python_path: {self.ps_sw_python}")
            self.logger.info(f"panoseti_grpc_daq: {self.grpc_config['daq_config_path']}")
            self.logger.info(f"panoseti_grpc_net: {self.grpc_config['net_config_path']}")
            self.logger.info(f"panoseti_grpc_obs: {self.grpc_config['obs_config_path']}")
            self.logger.info(f"panoseti_grpc_hp_io: {self.grpc_config['hp_io_cfg_path']}")
            self.append_log('************************************************************************')
            self.append_log(f"panoseti_sw_path: {self.ps_sw}")
            self.append_log(f"panoseti_python_path: {self.ps_sw_python}")
            self.append_log('************************************************************************')
            # check if the ps_sw_path exists or not
            ps_sw_path = Path(self.ps_sw)
            if ps_sw_path.exists() and ps_sw_path.is_dir():
                pass
            else:
                self.append_log('* WARNING * : panoseti_sw_path doesn\'t exist.')
                self.append_log('************************************************************************')
            # check if the python evn exists or not
            py_path = Path(self.ps_sw_python)
            if py_path.exists():
                pass
            else:
                self.append_log('* WARNING * : panoseti_python_path doesn\'t exist.')
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
        self.setup_signal_functions()
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
        self.data_config_op = DataConfigOp(self.data_config_win, self.ps_sw_data_config)
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
    def ps_stdout(self):
        text = self.ps_process.readAllStandardOutput().data().decode()
        self.append_log(text)

    def ps_stderr(self):
        text = self.ps_process.readAllStandardError().data().decode()
        self.append_log(text)

    def ps_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            self.append_log('---------------------------------------------------------------------------')
        else:
            self.append_log("Command failed")
            self.append_log('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

    def append_log(self, text):
        self.console_output.appendPlainText(text.rstrip())

    def start_grpc_clicked(self, mode='ph256'):
        self.logger.info('Start PANOSETI gPRC process.')
        program = 'python'
        args = ['-u', 'src/grpc_process.py', '-m', 'ph256']
        self.grpc_process.start(program, args)

    def stop_grpc_clicked(self):
        self.logger.info('Stop PANOSETI gPRC process.')
        self.shm.close()
        # self.shm.unlink()
        pid = self.grpc_process.processId()
        self.logger.debug(f"PANOSETI gPRC PID: {pid}")
        os.kill(pid, signal.SIGINT)
        self.grpc_process.waitForFinished(3000)

    def _get_dytpe_from_mode(self, mode):
        if mode == 'ph1024' or mode == 'ph256':
            dtype = np.int16
        elif mode == 'mov8':
            dtype = np.uint8
        elif mode == 'mov16':
            dtype = np.uint16
        else:
            self.logger.error(f"mode({mode}) is not supported.")

    def grpc_stdout(self):
        # we get an image every time when this function is called
        text =  self.grpc_process.readAllStandardOutput().data().decode()
        print(text)
        metadata = json.loads(text)
        if 'shm' in metadata:
            # this is from send_shm_info
            self.shm_name = metadata['shm']
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=False)
            # resource_tracker.unregister(self.shm_name, 'shared_memory')
            h, w = metadata['shape']
            mode = metadata['mode']
            dtype = self._get_dytpe_from_mode(mode)
            self.img = np.ndarray((h, w), dtype=dtype, buffer=self.shm.buf)
        else:
            # this is from send_images
            data = metadata
            # image_array = self.img.copy()
            # data['image_array'] = image_array
            # self.plot_data(data)

    def grpc_stderr(self):
        text =  self.grpc_process.readAllStandardError().data().decode()
        self.logger.error(f"PANOSETI gPRC executed failed: {text}")
    
    def grpc_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            self.logger.info('PANOSETI gRPC process exited gracefully.')
        else:
            self.logger.error('PANOSETI gPRC process exited failed.')

    # ---------------------------------------------------------------------------
    # plot figures
    # ---------------------------------------------------------------------------
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
        self.ps_process.start(program, arguments)
    
    def power_on_clicked(self):
        os.chdir(self.ps_sw_control)
        program = self.ps_sw_python
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('power.py on')
        self.append_log('---------------------------------------------------------------------------')
        arguments = ['-u', 'power.py', 'on']
        self.run_command(program, arguments)

    def power_off_clicked(self):
        os.chdir(self.ps_sw_control)
        program = self.ps_sw_python
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('power.py off')
        self.append_log('---------------------------------------------------------------------------')
        arguments = ['-u', 'power.py', 'off']
        self.run_command(program, arguments)

    def redis_on_clicked(self):
        os.chdir(self.ps_sw_control)
        program = self.ps_sw_python
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --redis_daemons')
        self.append_log('---------------------------------------------------------------------------')
        arguments = ['-u', 'config.py', '--redis_daemons']
        self.run_command(program, arguments)

    def redis_off_clicked(self):
        os.chdir(self.ps_sw_control)
        program = self.ps_sw_python
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --stop_redis_daemons')
        self.append_log('---------------------------------------------------------------------------')
        arguments = ['-u', 'config.py', '--stop_redis_daemons']
        self.run_command(program, arguments)

    def reboot_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --reboot')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','config.py', '--reboot']
        self.run_command(program, arguments)

    def marocconfig_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --maroc_config')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','config.py', '--maroc_config']
        self.run_command(program, arguments)
    
    def maskconfig_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --mask_config')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','config.py', '--mask_config']
        self.run_command(program, arguments)

    def calbrateph_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --calibrate_ph')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','config.py', '--calibrate_ph']
        self.run_command(program, arguments)
    
    def showbaselines_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('config.py --show_ph_baselines')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','config.py', '--show_ph_baselines']
        self.run_command(program, arguments)

    def getuid_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('get_uids.py')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','get_uids.py']
        self.run_command(program, arguments)

    def startdaq_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('start.py')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','start.py']
        self.run_command(program, arguments)

    def stopdaq_clicked(self):
        os.chdir(self.ps_sw_control)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('stop.py')
        self.append_log('---------------------------------------------------------------------------')
        program = self.ps_sw_python
        arguments = ['-u','stop.py']
        self.run_command(program, arguments)

    def submit_task(self):
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('Start Visualization.')
        self.append_log('---------------------------------------------------------------------------')
        self.grpc_thread.submit(self.grpc_thread.fetch_data())

    def cancel_all(self):
        self.append_log('---------------------------------------------------------------------------')
        self.append_log('Stop Visualization.')
        self.append_log('---------------------------------------------------------------------------')
        self.grpc_thread.loop.call_soon_threadsafe(self.grpc_thread.shutdown_event.set)
        self.grpc_thread.cancel_all()
    
    def plot_data(self, data):
        mid = data['module_id']
        self.logger.debug(f"telescipe ID: {self.telescope_info[mid]}")
        for k, v in self.telescope_info[mid].items():
            name = k
            loc = v
        data['name'] = name
        self.show_plot(loc[0], loc[1], data)

    def closeEvent(self, event):
        #self.stop_grpc_clicked()
        event.accept()
    # ---------------------------------------------------------------------------
    # Setup signal function
    # ---------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.power_on.clicked.connect(self.power_on_clicked)
        self.power_off.clicked.connect(self.power_off_clicked)
        self.redis_on.clicked.connect(self.redis_on_clicked)
        self.redis_off.clicked.connect(self.redis_off_clicked)
        self.reboot.clicked.connect(self.reboot_clicked)
        self.start_grpc.clicked.connect(self.start_grpc_clicked)
        self.stop_grpc.clicked.connect(self.stop_grpc_clicked)
        self.maroc_config.clicked.connect(self.marocconfig_clicked)
        self.mask_config.clicked.connect(self.maskconfig_clicked)
        self.cal_ph.clicked.connect(self.calbrateph_clicked)
        self.show_baselines.clicked.connect(self.showbaselines_clicked)
        self.get_uid.clicked.connect(self.getuid_clicked)
        self.start_daq.clicked.connect(self.startdaq_clicked)
        self.stop_daq.clicked.connect(self.stopdaq_clicked)

