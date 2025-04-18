import queue
import threading
from .Stage import Stage

class Tunnel:
    def __init__(self, private_max_workers=1, max_concurrent_tasks=None, on_error=None, timeout=10):
        self._private_max_worker = private_max_workers
        self._max_concurrent_tasks = max_concurrent_tasks
        self._on_error = on_error
        self._timeout = timeout
        self._data_queue = queue.Queue()
        self._close_event = threading.Event()
        self._stage = None
    
    def _defer_close_stage(self):
        def close_stage():
            self._close_event.wait()
            if self._stage is not None:
                self._stage.close()
                self._stage = None
        defer_thread = threading.Thread(target=close_stage)
        defer_thread.start()
    
    def _get_stage(self):
        if self._stage is not None:
            return self._stage
        else:
            self._stage = Stage(private_max_workers=self._private_max_worker, max_concurrent_tasks=self._max_concurrent_tasks, on_error=self._on_error)
            return self._stage
    
    def put(self, data):
        self._data_queue.put(data)
    
    def put_stop(self):
        self._data_queue.put(StopIteration)
    
    def get(self):
        self._defer_close_stage()
        stage = self._get_stage()
        def queue_consumer():
            try_count = 0
            while True:
                try:
                    if self._timeout is not None:
                        data = self._data_queue.get(timeout=self._timeout)
                    else:
                        data = self._data_queue.get()
                except queue.Empty:
                    if self._timeout is not None and try_count < 3:
                        try_count += 1
                        continue
                    break
                if data is StopIteration:
                    break
                yield data
            self._close_event.set()
        return stage.go(queue_consumer)