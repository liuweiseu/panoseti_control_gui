import time, json, sys
from multiprocessing import shared_memory, resource_tracker
import numpy as np
from typing import Union
import asyncio
import logging
from argparse import ArgumentParser
import socket

from panoseti_grpc.daq_data.client import AioDaqDataClient
import signal

from panoseti_grpc.telemetry.logger import get_logger

SOCK_PATH = "/tmp/panoseti_meta.sock"

class DaqDataBackend(object):
    def __init__(self, grpc_config_path: str, mode: str) -> None:
        # create logger
        self.logger = get_logger('pseti_gui.grpc_process', log_dir='/var/log/panoseti')
        self.logger.info('********************************************')
        self.logger.info('PANOSETI gRPC process started.')
        self.logger.info('********************************************')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(SOCK_PATH)
        # get configs
        with open(grpc_config_path, "r") as f:
            grpc_config = json.load(f)
        # Single-target connection: the server may be an edge DAQ node (dev/
        # single-machine setups) or a headnode/gateway that fans in multiple
        # edge nodes server-side -- pseti-gui doesn't need to know which.
        self.host = grpc_config.get('host', 'localhost')
        self.port = grpc_config.get('port', 50051)
        self.logger.info(f"host: {self.host}")
        self.logger.info(f"port: {self.port}")
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
            size=self.size * self.size * self.bytes_per_pixel
            )
        resource_tracker.unregister(self.shm._name, 'shared_memory')
        self.img = np.ndarray((self.size, self.size), dtype=self.dtype, buffer=self.shm.buf)

    def send_metadata(self, metadata):
        self.sock.sendall(json.dumps(metadata, default=str).encode() + b'\n')

    def send_shm_info(self):
        self.logger.info("Sending the shm info...")
        self.send_metadata({
                "shm": self.shm.name,
                "shape": [self.size, self.size],
                "mode": self.mode
            })

    async def send_images(self, ph_data=True, mov_data=False):
        self.logger.info("Sending images...")
        # The data source (real Hashpipe UDS acquisition or a simulation) is
        # initialized elsewhere -- production edge servers auto-start via
        # init_from_default, and `pseti start` is what triggers acquisition
        # otherwise. This process only attaches to an already-running stream.
        async with AioDaqDataClient(self.host, self.port, log_level=logging.DEBUG) as addc:
            stream_images_responses = addc.stream_images(
                stream_movie_data=mov_data,
                stream_pulse_height_data=ph_data,
                update_interval_seconds=1.0,
                module_ids=(),
                parse_pano_images=True,
                wait_for_ready=True,
            )
            async for parsed_pano_image in stream_images_responses:
                self.img[:] = parsed_pano_image['image_array']
                metadata = {k: v for k, v in parsed_pano_image.items() if k != "image_array"}
                self.send_metadata(metadata)

    def close(self):
        self.logger.info("Deattach the shm.")
        self.shm.close()
        try:
            #self.shm.unlink()
            pass
        except:
            self.logger.error('grpc_process failed.')
        self.logger.info("Deattached the shm.")

async def run(args):
    backend = DaqDataBackend(args.config, args.mode)
    backend.send_shm_info()
    await backend.send_images()
    backend.close()

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
    # deal with SIGINT
    def handler(signum, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)
    # start!
    asyncio.run(run(args))
