import time, json, sys
from multiprocessing import shared_memory
import numpy as np
from typing import Union
import asyncio
import logging
from argparse import ArgumentParser

sys.path.insert(0, 'panoseti_grpc')
from daq_data.client import AioDaqDataClient

sys.path.insert(0, 'utils')
from utils import make_rich_logger

class DaqDataBackend(object):
    def __init__(self, grpc_config_path: str, mode: str) -> None:
        # create logger
        self.logger = make_rich_logger('grpc_process.log', logging.WARNING, mode='a')
        self.logger.info('********************************************')
        self.logger.info('PANOSETI gRPC process started.')
        self.logger.info('********************************************')
        # get configs
        with open(grpc_config_path, "r") as f:
            grpc_config = json.load(f)
        self.daq_config_path = grpc_config['daq_config_path']
        self.net_config_path = grpc_config['net_config_path']
        self.hp_io_cfg_path = grpc_config['hp_io_cfg_path']
        self.logger.info(f"daq_config_path: {self.daq_config_path}")
        self.logger.info(f"net_config_path: {self.net_config_path}")
        self.logger.info(f"hp_io_cfg_path: {self.hp_io_cfg_path}")
        with open(self.hp_io_cfg_path, "r") as f:
            self.hp_io_cfg = json.load(f)
        self.shutdown_event = None
        # get bytes_per_pixel
        self.mode = mode
        if mode == 'mov8':
            self.dtype = np.uint8
            self.size = 32
            self.bytes_per_pixel = 1
        elif mode == 'mov16':
            self.dtype = np.uint16
            self.size = 32
            self.bytes_per_pixel = 2
        elif mode == 'ph256':
            self.dtype = np.int16
            self.size = 16
            self.bytes_per_pixel = 2
        elif mode == 'ph1024':
            self.dtype = np.int16
            self.size = 32
            self.bytes_per_pixel = 2
        else:
            self.logger.error(f"Mode ({mode}) is not supported.")
            raise ValueError(f"Mode ({mode}) is not supported.")
        self.logger.info(f"mode is {mode}.")
        self.logger.info(f"img size is {self.size} x {self.size}.")
        self.logger.info(f"{self.bytes_per_pixel} bytes per pixel.")
        # create a shared memory, the size is size * size
        self.shm = shared_memory.SharedMemory(
            create=True,  
            size=self.size * self.size
            )
        self.img = np.ndarray((self.size, self.size), dtype=self.dtype, buffer=self.shm.buf)

    def send_shm_info(self):
        self.logger.info("Sending the shm info...")
        print(
            json.dumps({
                "shm": self.shm.name,
                "shape": [self.size, self.size],
                "dtype": self.mode
            }), flush=True
        )
    
    async def send_images(self, ph_data=True, mov_data=False):
        self.logger.info("Sending images...")
        # use self.addc
        host = None
        self.shutdown_event = asyncio.Event()
        async with AioDaqDataClient(self.daq_config_path, self.net_config_path, stop_event=self.shutdown_event, log_level=logging.DEBUG) as addc:
            await addc.init_hp_io(host, self.hp_io_cfg, timeout=15.0)
            valid_daq_hosts = await addc.get_valid_daq_hosts()
            if host is not None and host not in valid_daq_hosts:
                raise ValueError(f"Invalid host: {host}. Valid hosts: {valid_daq_hosts}")
            stream_images_responses = await addc.stream_images(
            host,
            stream_movie_data=mov_data,
            stream_pulse_height_data=ph_data,
            update_interval_seconds=1.0,
            module_ids=[],
            parse_pano_images=True,
            wait_for_ready=True,
            )
            async for parsed_pano_image in stream_images_responses:
                if self.shutdown_event.is_set():
                    break
                self.img[:] = parsed_pano_image['image_array']
                metadata = {k: v for k, v in parsed_pano_image.items() if k != "image_array"}
                print(metadata)

    def close(self):
        self.logger.info("Deattach the shm.")
        self.shm.close()
        self.shm.unlink()

if __name__ == '__main__':
    parser = ArgumentParser(description="Usage for PANOSETI gRPC.")
    # config file option
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="configs/grpc_config.json",
        help="grpc config file."
    )
    # mode option
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=['mov8', 'mov16', 'ph256', 'ph1024'],
        default='ph1024',
        help="Mode options."
    )
    # parse the args
    args = parser.parse_args()
    # start!
    backend = DaqDataBackend(args.config, args.mode)
    backend.send_shm_info()
    #backend.send_images()
    backend.close()