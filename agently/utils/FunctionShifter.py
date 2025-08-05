import asyncio
import threading
from functools import wraps

import inspect
from typing import Any, Callable, Coroutine, TypeVar, ParamSpec

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


class FunctionShifter:
    @staticmethod
    def run_async_func_in_thread(func, *args, **kwargs):
        result: dict[str, Any] = {}

        def runner():
            try:
                result["data"] = asyncio.run(func(*args, **kwargs))
            except Exception as e:
                result["exception"] = e

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()

        if "exception" in result:
            raise result["exception"]
        return result["data"]

    @staticmethod
    def syncify(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, R]:
        if inspect.isfunction(func):
            return func

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            have_running_loop = None
            try:
                asyncio.get_running_loop()
                have_running_loop = True
            except RuntimeError:
                have_running_loop = False

            if have_running_loop:
                return FunctionShifter.run_async_func_in_thread(func, *args, **kwargs)
            else:
                assert inspect.iscoroutinefunction(func)
                return asyncio.run(func(*args, **kwargs))

        return wrapper

    @staticmethod
    def asyncify(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        if inspect.iscoroutinefunction(func):
            return func

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            assert inspect.isfunction(func)
            return await asyncio.to_thread(func, *args, **kwargs)

        return wrapper
