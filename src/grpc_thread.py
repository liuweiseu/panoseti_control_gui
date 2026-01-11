import sys
import asyncio
import threading
import json
import logging
import signal

from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, 'panoseti_grpc')
from daq_data.client import AioDaqDataClient
import daq_data.cli as cli

class DataSignal(QObject):
    new_data = pyqtSignal(object)

class AsyncioThread(threading.Thread):
    def __init__(self, grpc_config):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self.tasks = set()
        self.data_signal = DataSignal()
        self.daq_config_path = grpc_config['daq_config_path']
        self.net_config_path = grpc_config['net_config_path']
        self.shutdown_event = None

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    async def send_data_demo(self):
        while True:
            self.data_signal.new_data.emit('hello world')
            await asyncio.sleep(1)
    
    async def fetch_data(self):
        print('start fetch data.')
        print(self.daq_config_path)
        print(self.net_config_path)
        # use self.addc
        self.shutdown_event = asyncio.Event()
        async with AioDaqDataClient(self.daq_config_path, self.net_config_path, stop_event=self.shutdown_event, log_level=logging.DEBUG) as addc:
            host = None
            #hp_io_cfg_path = 'panoseti_grpc/daq_data/config/hp_io_config_simulate.json'
            hp_io_cfg_path = 'panoseti_grpc/daq_data/config/hp_io_config_palomar.json'
            with open(hp_io_cfg_path, "r") as f:
                hp_io_cfg = json.load(f)
            await addc.init_hp_io(host, hp_io_cfg, timeout=15.0)
            valid_daq_hosts = await addc.get_valid_daq_hosts()
            print('valid_daq_hosts:', valid_daq_hosts)
            if host is not None and host not in valid_daq_hosts:
                raise ValueError(f"Invalid host: {host}. Valid hosts: {valid_daq_hosts}")
            stream_images_responses = await addc.stream_images(
            host,
            stream_movie_data=False,
            stream_pulse_height_data=True,
            update_interval_seconds=1.0,
            module_ids=[],
            parse_pano_images=True,
            wait_for_ready=True,
            )
            async for parsed_pano_image in stream_images_responses:
                self.data_signal.new_data.emit(parsed_pano_image)

    def submit(self, coro):
        def _create():
            task = asyncio.create_task(coro)
            self.tasks.add(task)
        self.loop.call_soon_threadsafe(_create)

    def cancel_all(self):
        def _cancel():
            for task in self.tasks:
                task.cancel()
            self.tasks.clear()
        self.loop.call_soon_threadsafe(_cancel)
