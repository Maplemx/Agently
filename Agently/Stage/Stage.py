import atexit
import inspect
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future
from .StageResponse import StageResponse
from .StageHybridGenerator import StageHybridGenerator
from .StageFunction import StageFunctionMixin

class BaseStage:
    _global_executor = None
    _global_max_workers = 5
    _executor_lock = threading.RLock()

    @staticmethod
    def _get_global_executor():
        if BaseStage._global_executor is None:
            with BaseStage._executor_lock:
                BaseStage._global_executor = ThreadPoolExecutor(max_workers=BaseStage._global_max_workers)
        return BaseStage._global_executor
        
    @staticmethod
    def set_global_max_workers(global_max_workers):
        BaseStage._global_max_workers = global_max_workers
        with BaseStage._executor_lock:
            if BaseStage._global_executor:
                BaseStage._global_executor.shutdown(wait=True)
                BaseStage._global_executor = ThreadPoolExecutor(max_workers=BaseStage._global_max_workers)
                atexit.register(BaseStage._global_executor.shutdown)
    
    def __init__(self, private_max_workers=5, max_concurrent_tasks=None, on_error=None, is_daemon=False):
        self._private_max_workers = private_max_workers
        self._max_concurrent_tasks = max_concurrent_tasks
        self._on_error = on_error
        self._is_daemon = is_daemon
        self._semaphore = None
        self._loop_thread = None
        self._loop = None
        self._current_executor = None
        self._loop_ready = threading.Event()
        self._responses = set()
        self._closed = False
        if self._is_daemon:
            atexit.register(self.close)
        self._initialize()
    
    def __enter__(self):
        self._initialize()
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()
        if type is not None and self._on_error is not None:
            self._on_error(value)
        return False

    @property
    def _executor(self):
        if self._current_executor is not None:
            return self._current_executor
        if self._private_max_workers:
            self._current_executor = ThreadPoolExecutor(max_workers=self._private_max_workers)
            return self._current_executor
        else:
            self._current_executor = BaseStage._get_global_executor()
            return self._current_executor
    
    def _initialize(self):
        self._closed = False
        if (
            not self._loop_thread
            or not self._loop_thread.is_alive()
            or not self._loop
            or not self._loop.is_running()
        ):
            self._loop_thread = threading.Thread(target=self._start_loop, daemon=self._is_daemon)
            self._loop_thread.start()
            self._loop_ready.wait()

    def _start_loop(self):
        self._loop = asyncio.new_event_loop()
        self._loop.set_exception_handler(self._loop_exception_handler)
        if self._max_concurrent_tasks:
            self._semaphore = asyncio.Semaphore(self._max_concurrent_tasks)
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(lambda: self._loop_ready.set())
        self._loop.run_forever()
    
    def _loop_exception_handler(self, loop, context):
        if self._on_error is not None:
            loop.call_soon_threadsafe(self._on_error, context["exception"])
        else:
            raise context["exception"]
    
    def go(self, task, *args, on_success=None, on_error=None, lazy=False, async_gen_interval=0.1, **kwargs):
        if not self._loop or self._loop.is_running():
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
                    result = await self._loop.run_in_executor(self._executor, lambda: item) if not self._executor._shutdown else item
                    yield result
            return self.go(async_generator())
        elif inspect.iscoroutinefunction(task) or inspect.isasyncgenfunction(task):
            return self.go(task(*args, **kwargs), **hybrid_generator_kwargs)
        elif inspect.isgeneratorfunction(task):
            return self.go(task(*args, **kwargs), **hybrid_generator_kwargs)
        elif inspect.isfunction(task) or inspect.ismethod(task):
            if not self._executor._shutdown:
                return StageResponse(self, self._loop.run_in_executor(self._executor, lambda: task(*args, **kwargs)), **response_kwargs)
            else:
                try:
                    future = Future()
                    return StageResponse(self, future, **response_kwargs)
                finally:
                    try:
                        future.set_result(task(*args, **kwargs))
                    except Exception as e:
                        future.set_exception(e)
        else:
            raise TypeError(f"Task seems like a value or an executed function not an executable task: { task }")
    
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
        if self._closed:
            return
        self._closed = True
        
        for response in self._responses.copy():
            response.get()
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop:
            pending = asyncio.all_tasks(self._loop)
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        if self._private_max_workers and self._current_executor is not None:
            self._current_executor.shutdown(wait=True)
            self._current_executor = None
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join()
            self._loop_thread = None
        if self._loop and not self._loop.is_closed():
            self._loop.close()
        self._loop = None

class Stage(BaseStage, StageFunctionMixin):
    pass