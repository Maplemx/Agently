import asyncio
import threading

class StageResponse:
    def __init__(self, stage, task, on_success=None, on_error=None):
        self._stage = stage
        self._stage._responses.add(self)
        self._loop = self._stage._loop
        self._on_success = on_success
        self._on_error = on_error
        if asyncio.iscoroutine(task):
            self._task = asyncio.run_coroutine_threadsafe(task, self._loop)
        elif asyncio.isfuture(task):
            self._task = task
        self._task.add_done_callback(self._on_task_done)
        self._result_ready = threading.Event()
        self._status = None
        self._result = None
        self._error = None
        self._final_result = None
    
    def _on_task_done(self, future):
        try:
            self._status = True
            self._result = future.result()
            if self._on_success:
                self._final_result = self._on_success(self._result)
            self._result_ready.set()
            self._stage._responses.discard(self)
        except Exception as e:
            self._status = False
            self._error = e
            if self._on_error:
                self._final_result = self._on_error(self._error)
                self._result_ready.set()
                self._stage._responses.discard(self)
            else:
                self._result_ready.set()
                self._stage._responses.discard(self)
                raise self._error
    
    def get(self):
        self._result_ready.wait()
        if self._status == True:
            return self._result
        elif self._on_error is None:
            raise self._error
    
    def get_final(self):
        self._result_ready.wait()
        if self._final_result:
            return self._final_result
        else:
            return self._result