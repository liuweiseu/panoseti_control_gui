import asyncio
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

class DataSignal(QObject):
    new_data = pyqtSignal(object)

class AsyncioThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self.tasks = set()
        self.data_signal = DataSignal()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    async def send_data(self):
        while True:
            self.data_signal.new_data.emit('hello world')
            await asyncio.sleep(1)
        
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
