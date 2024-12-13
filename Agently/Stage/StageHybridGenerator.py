import queue
import asyncio
import threading

class StageHybridGenerator:
    def __init__(self, stage, task, on_success=None, on_error=None, lazy=None, async_gen_interval=0.1):
        self._stage = stage
        self._stage._responses.add(self)
        self._loop = stage._loop
        self._on_success = on_success
        self._on_error = on_error
        self._task = task
        self._result = []
        self._error = None
        self._result_queue = queue.Queue()
        self._result_ready = threading.Event()
        self._completed = False
        self._final_result = None
        self._is_lazy = lazy
        self._async_gen_interval = async_gen_interval
        if not self._is_lazy:
            self._run_consume_async_gen(self._task)
    
    def _run_consume_async_gen(self, task):
        consume_result = asyncio.run_coroutine_threadsafe(self._consume_async_gen(task), self._loop)
        consume_result.add_done_callback(self._on_consume_async_gen_done)
    
    def _on_consume_async_gen_done(self, future):
        future.result()
        if self._error is not None:
            def raise_error():
                raise self._error
            self._loop.call_soon_threadsafe(raise_error)
        if self._on_success:
            self._final_result = self._on_success(self._result)
        self._result_ready.set()
        self._stage._responses.discard(self)
    
    async def _consume_async_gen(self, task):
        try:
            async for item in task:
                self._result_queue.put(item)
                self._result.append(item)
            self._completed = True
        except Exception as e:
            if self._on_error:
                handled_result = self._on_error(e)
                self._result_queue.put(handled_result)
                self._result.append(handled_result)
            else:
                self._result_queue.put(e)
                self._result.append(e)
                self._error = e
        finally:
            self._result_queue.put(StopIteration)
    
    async def __aiter__(self):
        if self._is_lazy:
            self._run_consume_async_gen(self._task)
        while True:
            try:
                item = self._result_queue.get_nowait()
                if item is StopIteration:
                    break
                yield item
            except queue.Empty:
                await asyncio.sleep(self._async_gen_interval)

    def __iter__(self):
        if self._is_lazy:
            self._run_consume_async_gen(self._task)
        while True:
            item = self._result_queue.get()
            if item is StopIteration:
                break
            yield item
    
    def get(self):
        self._result_ready.wait()
        return self._result

    def get_final(self):
        self._result_ready.wait()
        if self._final_result:
            return self._final_result
        else:
            return self._result