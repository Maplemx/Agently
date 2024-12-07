import inspect
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .StageResponse import StageResponse
from .StageHybridGenerator import StageHybridGenerator
from .StageFunction import StageFunctionMixin

class BaseStage:
    def __init__(self, max_workers=5, max_concurrent_tasks=None, on_error=None, close_when_exception=False):
        self._max_workers = max_workers
        self._max_concurrent_tasks = max_concurrent_tasks
        self._on_error = on_error
        self._semaphore = None
        self._loop_thread = None
        self._loop = None
        self._executor = None
        self._responses = []
        #self._initialize()
    
    def _initialize(self):
        self._loop_ready = threading.Event()
        self._loop_thread = threading.Thread(target=self._start_loop)
        self._loop_thread.start()
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._loop_ready.wait()
        del self._loop_ready

    def _loop_exception_handler(self, loop, context):
        if self._on_error is not None:
            loop.call_soon_threadsafe(self._on_error, context["exception"])
        else:
            raise context["exception"]
    
    def _start_loop(self):
        self._loop = asyncio.new_event_loop()
        self._loop.set_exception_handler(self._loop_exception_handler)
        asyncio.set_event_loop(self._loop)
        if self._max_concurrent_tasks:
            self._semaphore = asyncio.Semaphore(self._max_concurrent_tasks)
        self._loop_ready.set()
        self._loop.run_forever()
    
    def go(self, task, *args, on_success=None, on_error=None, lazy=False, async_gen_interval=0.1, **kwargs):
        if not self._executor or not self._loop or not self._loop.is_running():
            self._initialize()
        response_kwargs = {
            "on_success": on_success,
            "on_error": on_error,
        }
        hybrid_generator_kwargs = {
            "on_success": on_success,
            "on_error": on_error,
            "lazy": lazy,
            "async_gen_interval": async_gen_interval,
        }
        if inspect.iscoroutine(task):
            if self._semaphore:
                if not self._semaphore.locked():
                    return StageResponse(self, task, **response_kwargs)
                else:
                    self._semaphore.acquire()
                    try:
                        return StageResponse(self, task, **response_kwargs)
                    finally:
                        self._semaphore.release()
            else:
                return StageResponse(self, task, **response_kwargs)
        elif inspect.isasyncgen(task):
            if self._semaphore:
                if not self._semaphore.locked():
                    return StageHybridGenerator(self, task, **hybrid_generator_kwargs)
                else:
                    self._semaphore.acquire()
                    try:
                        return StageHybridGenerator(self, task, **hybrid_generator_kwargs)
                    finally:
                        self._semaphore.release()
            else:
                return StageHybridGenerator(self, task, **hybrid_generator_kwargs)
        elif asyncio.isfuture(task):
            return StageResponse(self, task, **response_kwargs)
        elif inspect.isgenerator(task):
            async def async_generator():
                for item in task:
                    result = await self._loop.run_in_executor(self._executor, lambda: item)
                    yield result
            return self.go(async_generator())
        elif inspect.iscoroutinefunction(task) or inspect.isasyncgenfunction(task):
            return self.go(task(*args, **kwargs), **hybrid_generator_kwargs)
        elif inspect.isgeneratorfunction(task):
            return self.go(task(*args, **kwargs), **hybrid_generator_kwargs)
        elif inspect.isfunction(task) or inspect.ismethod(task):
            return StageResponse(self, self._loop.run_in_executor(self._executor, lambda: task(*args, **kwargs)), **response_kwargs)
        else:
            return task
    
    def go_all(self, *task_list):
        response_list = []
        for task in task_list:
            if isinstance(task, (tuple, list)):
                func, *args, kwargs = task
                response = self.go(func, *args, **kwargs)
            else:
                response = self.go(task)
            response_list.append(response)
        return response_list

    def get(self, task, *args, **kwargs):
        response = self.go(task, *args, **kwargs)
        if isinstance(response, StageResponse):
            return response.get()
        elif isinstance(response, StageHybridGenerator):
            result = []
            for item in response:
                result.append(item)
            return result
    
    def get_all(self, *task_list):
        result_list = []
        for task in task_list:
            if isinstance(task, (tuple, list)):
                func, *args, kwargs = task
                response = self.go(func, *args, **kwargs)
            else:
                response = self.go(task)
            if isinstance(response, StageResponse):
                result_list.append(response.get())
            else:
                result_list.append(response)
        return result_list

    def on_error(self, handler):
        self._on_error = handler
    
    def close(self):
        for response in self._responses:
            response._result_ready.wait()
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop:
            pending = asyncio.all_tasks(self._loop)
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join()
            self._loop_thread = None
        if self._loop and not self._loop.is_closed:
            self._loop.close()
        self._loop = None
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

class Stage(BaseStage, StageFunctionMixin):
    pass