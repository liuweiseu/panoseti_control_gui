from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSocketNotifier

import json, os, sys
from pathlib import Path
import pyqtgraph as pg
import numpy as np
import socket

from pseti_gui.mainwin_ui import Ui_MainWindow
from pseti_gui.data_config_win import DataConfigWin, DataConfigOp
import asyncio, signal
from multiprocessing import shared_memory, resource_tracker

from panoseti_grpc.telemetry.logger import get_logger

NUM_PLOTS = 4

SOCK_PATH = "/tmp/panoseti_meta.sock"
FIGURE_DIR = Path(__file__).resolve().parent / "figure"
class MainWin(QMainWindow, Ui_MainWindow):
    def __init__(self):
        self.logger = get_logger('pseti_gui.mainwin', log_dir='/var/log/panoseti')
        self.logger.info('********************************************')
        self.logger.info('Main Window started.')
        self.logger.info('********************************************')
        super().__init__()
        self.setupUi(self)
        self.actiondata_config.triggered.connect(self.open_data_config)
        # Both child processes' stdout/stderr are pipes, not a real terminal,
        # so their own Rich console can't query a terminal width and falls
        # back to a hardcoded 80 columns -- wrapping log lines far short of
        # this pane's actual width. Rich (via shutil.get_terminal_size())
        # honors the COLUMNS/LINES env vars before falling back, so set them
        # wide here instead of touching the panoseti/panoseti_grpc loggers.
        wide_console_env = QProcessEnvironment.systemEnvironment()
        wide_console_env.insert('COLUMNS', '200')
        wide_console_env.insert('LINES', '50')
        # Process for panoseti software
        self.ps_process = QProcess(self)
        self.ps_process.setProcessEnvironment(wide_console_env)
        self.ps_process.readyReadStandardOutput.connect(self.ps_stdout)
        self.ps_process.readyReadStandardError.connect(self.ps_stderr)
        self.ps_process.finished.connect(self.ps_finished)
        # Process for panoseti grpc
        self.grpc_process = QProcess(self)
        self.grpc_process.setProcessEnvironment(wide_console_env)
        self.grpc_process.readyReadStandardOutput.connect(self.grpc_stdout)
        self.grpc_process.readyReadStandardError.connect(self.grpc_stderr)
        self.grpc_process.finished.connect(self.grpc_finished)
        self.grpc_process_exit = False
        # set socket notifier
        if os.path.exists(SOCK_PATH):
            os.remove(SOCK_PATH)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(SOCK_PATH)
        self.server.listen(1)
        self.server_notifier = QSocketNotifier(
            self.server.fileno(),
            QSocketNotifier.Type.Read
        )
        self.server_notifier.activated.connect(self._on_new_connection)
        self.conn = None
        self.conn_notifier = None
        # use shared memory to get image data
        self.shm = None
        self.shm_name = None
        self.img = None
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
        # use hard-coded name here for temp use
        # TODO: imporve this part
        self.telescope_info = [{'Simulation': [0, 0]}] * 1024
        self.telescope_info[250] = {'PTI': [0, 0]}
        self.telescope_info[252] = {'Fern': [0, 1]}
        self.telescope_info[253] = {'Winter': [1, 0]}
        self.telescope_info[254] = {'Gattini': [1, 1]}
    
    # ---------------------------------------------------------------------------
    # signal functions for socket
    # ---------------------------------------------------------------------------
    def _on_new_connection(self):
        self.server_notifier.setEnabled(False)
        self.conn, _ = self.server.accept()
        self.conn.setblocking(False)
        self.conn_notifier = QSocketNotifier(
            self.conn.fileno(),
            QSocketNotifier.Type.Read
        )
        self.conn_notifier.activated.connect(self._on_ready_read)

    def _on_ready_read(self):
        data = self.conn.recv(4096)
        if not data:
            self.conn_notifier.setEnabled(False)
            self.conn.close()
            return
        for line in data.split(b"\n"):
            if line:
                metadata = json.loads(line.decode())
        if 'shm' in metadata:
            # this is from send_shm_info
            self.shm_name = metadata['shm']
            self.logger.debug(f"shm_name is {self.shm_name}")
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=False)
            h, w = metadata['shape']
            mode = metadata['mode']
            dtype = self._get_dytpe_from_mode(mode)
            self.img = np.ndarray((h, w), dtype=dtype, buffer=self.shm.buf)
        else:
            # this is from send_images
            data = metadata
            image_array = self.img.copy()
            data['image_array'] = image_array
            self.plot_data(data)

    # ---------------------------------------------------------------------------
    # Sub Window creation
    # ---------------------------------------------------------------------------
    def open_data_config(self):
        if not hasattr(self, "data_config_win"):
            self.data_config_win = DataConfigWin()
            self.data_config_op = DataConfigOp(self.data_config_win)
        self.data_config_win.show()

    # ---------------------------------------------------------------------------
    # Set placeholder
    # ---------------------------------------------------------------------------
    def set_placeholder(self, r, c):
        i = r * 2 + c
        pixmap = QPixmap(str(FIGURE_DIR / "placeholder.png"))
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

    def start_grpc_clicked(self, mode='ph1024'):
        self.logger.info('Start PANOSETI gPRC process.')
        self.grpc_process_exit = False
        program = sys.executable
        args = ['-u', '-m', 'pseti_gui.grpc_process', '-m', 'ph1024']
        self.grpc_process.start(program, args)

    def stop_grpc_clicked(self):
        self.logger.info('Stop PANOSETI gPRC process.')
        # close shared memory
        if self.shm is not None:
            self.shm.close()
        # send SIGINT to the grpc process
        pid = self.grpc_process.processId()
        if pid != 0:
            self.logger.debug(f"PANOSETI gPRC PID: {pid}")
            os.kill(pid, signal.SIGINT)
        else:
            self.logger.debug("No PANOSETI gRPC process found.")
        self.grpc_process.waitForFinished(3000)
        # try to unlink shared memory
        # it may already be unlinked on the grpc process
        if self.shm is not None:
            try:
                self.shm.unlink()
            except:
                self.logger.debug('Shared Memory may already be unlinked.')
            self.shm = None
        # re-enable the notificer
        self.server_notifier.setEnabled(True)
        self.grpc_process_exit = True

    def _get_dytpe_from_mode(self, mode):
        if mode == 'ph1024' or mode == 'ph256':
            dtype = np.int16
        elif mode == 'mov8':
            dtype = np.uint8
        elif mode == 'mov16':
            dtype = np.uint16
        else:
            self.logger.error(f"mode({mode}) is not supported.")
        return dtype

    def grpc_stdout(self):
        # we get an image every time when this function is called
        # text already ends in '\n' (grpc_process's own Rich handler
        # terminates every line) -- print() would otherwise add a second one.
        text =  self.grpc_process.readAllStandardOutput().data().decode()
        print(text, end='')

    def grpc_stderr(self):
        text =  self.grpc_process.readAllStandardError().data().decode()
        print(text, end='')
    
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
    
    def run_pseti(self, *pseti_args):
        # `pseti` is resolved on PATH (installed via `uv tool install`), not
        # via panoseti_sw.python_path -- decouples pseti-gui from needing to
        # know where the panoseti/control checkout or its interpreter live.
        cmdline = 'pseti ' + ' '.join(pseti_args)
        self.append_log('---------------------------------------------------------------------------')
        self.append_log(cmdline)
        self.append_log('---------------------------------------------------------------------------')
        self.run_command('pseti', list(pseti_args))

    def power_on_clicked(self):
        self.run_pseti('power', 'on')

    def power_off_clicked(self):
        self.run_pseti('power', 'off')

    def redis_on_clicked(self):
        self.run_pseti('cfg', 'redis-daemons')

    def redis_off_clicked(self):
        self.run_pseti('cfg', 'stop-redis-daemons')

    def reboot_clicked(self):
        self.run_pseti('cfg', 'reboot')

    def marocconfig_clicked(self):
        self.run_pseti('cfg', 'maroc-config', '--non-interactive')

    def maskconfig_clicked(self):
        self.run_pseti('cfg', 'mask-config')

    def calbrateph_clicked(self):
        self.run_pseti('cfg', 'calibrate-ph')

    def showbaselines_clicked(self):
        self.run_pseti('cfg', 'show-ph-baselines')

    def getuid_clicked(self):
        self.run_pseti('uids')

    def startdaq_clicked(self):
        self.run_pseti('start', '--yes')

    def stopdaq_clicked(self):
        self.run_pseti('stop', '--yes')

    def plot_data(self, data):
        mid = data['module_id']
        self.logger.debug(f"telescipe ID: {self.telescope_info[mid]}")
        for k, v in self.telescope_info[mid].items():
            name = k
            loc = v
        data['name'] = name
        self.show_plot(loc[0], loc[1], data)

    def closeEvent(self, event):
        # call stop_grpc to stop grpc process
        if self.grpc_process_exit == False:
            self.stop_grpc_clicked()
        # delete uds
        if os.path.exists(SOCK_PATH):
            os.remove(SOCK_PATH)
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

