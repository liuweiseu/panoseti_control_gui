from PyQt6.QtWidgets import QDialog, QWidget
#from data_config_win import Ui_DataConfigWin
from src.data_config_ui import Ui_Form

import logging
import json
from pathlib import Path
from utils.utils import make_rich_logger

class DataConfigWin(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

class DataConfigOp(object):
    def __init__(self, win, src_config='configs/data_config.json'):
        self.logger = make_rich_logger('data_config_gen.log', logging.WARNING, mode='a')
        self.logger.info('********************************************')
        self.logger.info('Data Config Gen started.')
        self.logger.info('********************************************')
        self.win = win
        self.ui = win.ui
        self.src_config = src_config
        if self.src_config is not None:
            self.logger.info(f'Loading {src_config}...')
            fpath = Path(self.src_config)
            if fpath.exists():
                self.load_config()
        else:
            self.logger.info(f'No default data_config.json...')
        self.setup_signal_functions()
    
    # ------------------------------------------------------------------------
    # Low level APIs
    # ------------------------------------------------------------------------
    def get_run_type(self):
        txt = self.ui.run_type.text()
        self.logger.debug(f'Run Typs is {txt}.')
        return txt

    def set_run_type(self, txt):
        self.logger.debug(f'Set Run Type to {txt}.')
        self.ui.run_type.setText(txt)
    
    def get_detector_overvoltage(self):
        overvol = self.ui.detector_overvoltage.currentText()
        self.logger.debug(f'The Detector Overvoltage is {overvol}.')
        return int(overvol.strip('V'))
    
    def set_detector_overvoltage(self, overvol):
        self.logger.debug(f'Set Detector Overvoltage to {overvol}.')
        self.ui.detector_overvoltage.setCurrentText(f'{overvol}V')
    
    def get_max_file_size(self):
        fsize = self.ui.max_file_size.value()
        self.logger.debug(f'The Max File Size is {fsize}.')
        return fsize
    
    def set_max_file_size(self, fsize):
        self.logger.debug(f'Set Max File Size to {fsize}MB.')
        self.ui.max_file_size.setValue(fsize)

    def get_gain(self):
        gain = self.ui.gain.value()
        self.logger.debug(f'The Gain value is {gain}.')
        return gain
    
    def set_gain(self, gain):
        self.logger.debug(f'Set the Gain to {gain}.')
        self.ui.gain.setValue(gain)

    def get_ph_mode_enable(self):
        status = self.ui.ph_mode_enable.isChecked()
        self.logger.debug(f'The PH Mode status is {status}.')
        return status
    
    def set_ph_mode_enable(self, status):
        self.logger.debug(f'Set the PH Mode status to {status}.')
        self.ui.ph_mode_enable.setChecked(status)
    
    def get_ph_pe_threshold(self):
        threshold = self.ui.ph_pe_threshold.value()
        self.logger.debug(f'The PH Pe Threshold is {threshold}.')
        return threshold

    def set_ph_pe_threshold(self, threshold):
        self.logger.debug(f'Set PH Pe Threshold to {threshold}.')
        threshold = self.ui.ph_pe_threshold.setValue(threshold)

    def get_ph_pixel_trigger_mode(self):
        triggermode = self.ui.ph_trigger_mode.currentText()
        self.logger.debug(f'The trigger mode is {triggermode}.')
        return triggermode
    
    def set_ph_pixel_trigger_mode(self, triggermode):
        self.logger.debug(f'Set Trigger Mode to {triggermode}.')
        self.ui.ph_trigger_mode.setCurrentText(triggermode)

    def get_ph_any_trigger(self):
        status = self.ui.ph_any_trigger_enable.isChecked()
        self.logger.debug(f'The Any Trigger status is {status}.')
        return status
    
    def set_ph_any_trigger(self, status):
        self.logger.debug(f'Set Any Trigger to {status}.')
        self.ui.ph_any_trigger_enable.setChecked(status)
    
    def get_ph_group_frames(self):
        status = self.ui.ph_group_frame_enable.isChecked()
        self.logger.debug(f'The PH Group Frame staus is {status}.')
        return status
    
    def set_ph_group_frames(self, status):
        self.logger.debug(f'Set PH Group Frames status to {status}.')
        self.ui.ph_group_frame_enable.setChecked(status)

    def get_mov_mode_enable(self):
        status = self.ui.mov_mode_enable.isChecked()
        self.logger.debug(f'The MOV Mode status is {status}.')
        return status
    
    def set_mov_mode_enable(self, status):
        self.logger.debug(f'Set  MOV Mode status to {status}.')
        self.ui.mov_mode_enable.setChecked(status)
    
    def get_mov_integration_time(self):
        val = self.ui.mov_integration_time.value()
        self.logger.debug('The Integration Time is {val} usec.')
        return val
    
    def set_mov_integration_time(self, val):
        self.logger.debug(f'Set Integration Time to {val} usec.')
        self.ui.mov_integration_time.setValue(val)
    
    def get_mov_ph_threshold(self):
        threshold = self.ui.mov_ph_threshold.value()
        self.logger.debug(f'The MOV PH Threshold is {threshold}.')
        return threshold
    
    def set_mov_ph_threshold(self, threshold):
        self.logger.debug(f'Set MOV PH Threshold to {threshold}.')
        self.ui.mov_ph_threshold.setValue(threshold)
    
    def get_mov_sample_bits(self):
        bits = self.ui.mov_sample_bits.currentText()
        self.logger.debug(f'The MOV Sample Bits is {bits}.')
        return int(bits)

    def set_mov_sample_bits(self, bits):
        self.logger.debug(f'Set MOV Sample Bits it {bits}.')
        bits = self.ui.mov_sample_bits.setCurrentText(str(bits))

    def get_config_output_dir(self):
        outputdir = self.ui.config_output_dir.text()
        self.logger.debug(f'The Config Output Directory is {outputdir}.')
        return outputdir
    
    def set_config_output_dir(self, outputdir):
        self.logger.debug(f'Set the Config Output Directory to {outputdir}.')
        outputdir = self.ui.config_output_dir.setText(outputdir)
    
    def get_ph_frame(self):
        status = self.ui.ph_frame.isEnabled()
        self.logger.debug(f'The PH Frame status is {status}.')
        return status
    
    def set_ph_frame(self, status):
        self.logger.debug(f'Set PH Frame status to {status}.')
        self.ui.ph_frame.setEnabled(status)
    
    def get_mov_frame(self):
        status = self.ui.mov_frame.isEnabled()
        self.logger.debug(f'The MOV Frame status is {status}.')
        return status
    
    def set_mov_frame(self, status):
        self.logger.debug(f'Set MOV Frame status to {status}.')
        self.ui.mov_frame.setEnabled(status)

    def get_ph_group_frames_status(self):
        status = self.ui.ph_group_frame_enable.isEnabled()
        self.logger.debug(f'The PH Group Frames status is {status}.')
        return status
    
    def set_ph_group_frames_status(self, status):
        self.logger.debug(f'Set PH Group Frames status to {status}.')
        self.ui.ph_group_frame_enable.setEnabled(status)

    
    # ------------------------------------------------------------------------
    # Load and collect config
    # ------------------------------------------------------------------------
    def load_config(self):
        self.logger.info('-------------------------------------------------')
        self.logger.info(f'Loading default config from {self.src_config}...')
        self.logger.info('-------------------------------------------------')
        # load the config file
        with open(self.src_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # set run type
        self.set_run_type(config['run_type'])
        # set detector overvoltage
        self.set_detector_overvoltage(config['detector_overvoltage'])
        # set max file size
        self.set_max_file_size(config['max_file_size_mb'])
        # set gain
        self.set_gain(config['gain'])
        # check if mov mode is enabled
        if 'image' in config:
            self.set_mov_mode_enable(True)
            self.set_mov_frame(True)
            iconfig = config['image']
            # set integration time
            self.set_mov_integration_time(iconfig['integration_time_usec'])
            # set ph threshold
            self.set_mov_ph_threshold(iconfig['pe_threshold'])
            # set sample size
            self.set_mov_sample_bits(iconfig['quabo_sample_size'])
        else:
            self.set_mov_mode_enable(False)
            self.set_mov_frame(False)
        # check if ph mode is enabled
        if 'pulse_height':
            self.set_ph_mode_enable(True)
            self.set_ph_frame(True)
            pconfig = config['pulse_height']
            # set ph threshold
            self.set_ph_pe_threshold(pconfig['pe_threshold'])
            # set pixel mode
            if pconfig['two_pixel_trigger']:
                self.set_ph_pixel_trigger_mode('2 Pixels Trigger')
            elif pconfig['three_pixel_trigger']:
                self.set_ph_pixel_trigger_mode('3 Pixels Trigger')
            else:
                self.set_ph_pixel_trigger_mode('1 Pixel Trigger')
            # set any trigger
            if 'any_trigger' in pconfig:
                self.set_ph_any_trigger(True)
                self.set_ph_group_frames_status(True)
                if pconfig['any_trigger']['group_ph_frames']:
                    self.set_ph_group_frames(True)
                else:
                    self.set_ph_group_frames(False)
            else:
                self.set_ph_any_trigger(False)
                self.set_ph_group_frames_status(False)
        else:
            self.set_ph_mode_enable(False)
            self.set_ph_frame(False)
        # set output dir
        self.set_config_output_dir(self.src_config)
    
    def collect_config(self):
        config = {}
        # get run type
        config['run_type'] = self.get_run_type()
        # get detector_overvoltage
        config['detector_overvoltage'] = self.get_detector_overvoltage()
        # get gain
        config['gain'] = self.get_gain()
        # check if mov mode is enabled
        if self.get_mov_mode_enable():
            config['image'] = {}
            config['image']['integration_time_usec'] = self.get_mov_integration_time()
            config['image']['pe_threshold'] = self.get_mov_ph_threshold()
            config['image']['quabo_sample_size'] = self.get_mov_sample_bits()
        # check if ph mode is enabled
        if self.get_ph_mode_enable():
            config['pulse_height'] = {}
            config['pulse_height']['pe_threshold'] = self.get_ph_pe_threshold()
            ptm = self.get_ph_pixel_trigger_mode()
            if ptm == '1 Pixel Trigger':
                config['pulse_height']['two_pixel_trigger'] = 0
                config['pulse_height']['three_pixel_trigger'] = 0
            elif ptm == '2 Pixels Trigger':
                config['pulse_height']['two_pixel_trigger'] = 1
                config['pulse_height']['three_pixel_trigger'] = 0
            elif ptm == '3 Pixels Trigger':
                config['pulse_height']['two_pixel_trigger'] = 0
                config['pulse_height']['three_pixel_trigger'] = 1
            if self.get_ph_any_trigger():
                config['pulse_height']['any_trigger'] = {}
                if self.get_ph_group_frames():
                    config['pulse_height']['any_trigger']['group_ph_frames'] = 1
                else:
                    config['pulse_height']['any_trigger']['group_ph_frames'] = 0
        # set max file size
        config['max_file_size_mb'] = self.get_max_file_size()
        # get the output dir
        output = self.get_config_output_dir()
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    # ------------------------------------------------------------------------
    # Signal functions
    # ------------------------------------------------------------------------
    def PHModeEnable_StautsChanged(self):
        status = self.get_ph_mode_enable()
        if status:
            self.set_ph_frame(True)
        else:
            self.set_ph_frame(False)

    def MOVModeEnable_StatusChanged(self):
        status = self.get_mov_mode_enable()
        if status:
            self.set_mov_frame(True)
        else:
            self.set_mov_frame(False)
    
    def AnyTrigger_StatusChanged(self):
        status = self.get_ph_any_trigger()
        if status:
            self.set_ph_group_frames_status(True)
        else:
            self.set_ph_group_frames_status(False)
    
    def on_ok_clicked(self):
        self.collect_config()
        self.win.close()

    def on_cancel_clicked(self):
        self.win.close()
        
    # ------------------------------------------------------------------------
    # Setup signal function
    # ------------------------------------------------------------------------
    def setup_signal_functions(self):
        self.ui.ph_mode_enable.clicked.connect(self.PHModeEnable_StautsChanged)
        self.ui.mov_mode_enable.clicked.connect(self.MOVModeEnable_StatusChanged)
        self.ui.ph_any_trigger_enable.clicked.connect(self.AnyTrigger_StatusChanged)
        self.ui.data_config_button.accepted.connect(self.on_ok_clicked)
        self.ui.data_config_button.rejected.connect(self.on_cancel_clicked)
    
