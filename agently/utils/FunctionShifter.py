# Copyright 2023-2025 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import queue
import asyncio
import threading
from functools import wraps

import inspect
from typing import Any, Callable, Coroutine, TypeVar, ParamSpec, Generator, AsyncGenerator
from asyncio import Future

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


class FunctionShifter:
    _future_loop = None
    _future_thread = None
    _future_lock = threading.Lock()

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
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    return asyncio.run(func(*args, **kwargs))
                else:
                    # Running loop exists, move coroutine to thread
                    return FunctionShifter.run_async_func_in_thread(func, *args, **kwargs)

            return wrapper
        else:
            assert inspect.isfunction(func)
            return func

    @staticmethod
    def asyncify(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        if inspect.iscoroutinefunction(func):
            return func

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            assert inspect.isfunction(func)
            return await asyncio.to_thread(func, *args, **kwargs)

        return wrapper

    @staticmethod
    def future(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, Future[R]]:
        async_func = FunctionShifter.asyncify(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                if FunctionShifter._future_thread is None or FunctionShifter._future_loop is None:
                    with FunctionShifter._future_lock:
                        if FunctionShifter._future_thread is None or FunctionShifter._future_loop is None:
                            FunctionShifter._future_loop = asyncio.new_event_loop()
                            FunctionShifter._future_thread = threading.Thread(
                                target=FunctionShifter._future_loop.run_forever, daemon=True
                            ).start()
                loop = FunctionShifter._future_loop

            future = asyncio.ensure_future(async_func(*args, **kwargs), loop=loop)
            exception = future.add_done_callback(lambda t: t.exception())
            if exception:
                raise exception
            return future

        return wrapper

    @staticmethod
    def syncify_async_generator(async_gen: AsyncGenerator[R, Any]) -> Generator[R, Any, Any]:

        q: "queue.Queue" = queue.Queue()
        SENTINEL = object()

        async def _consume():
            try:
                async for item in async_gen:
                    q.put(("item", item))
            except Exception as e:
                q.put(("error", e))
            finally:
                q.put(("end", SENTINEL))

        def _runner():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_consume())
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        try:
            while True:
                kind, payload = q.get()
                if kind == "item":
                    yield payload
                elif kind == "error":
                    raise payload
                elif kind == "end":
                    break
        finally:
            thread.join()

    @staticmethod
    def auto_options_func(func: Callable[..., R]) -> Callable[..., R]:
        signature = inspect.signature(func)
        params = signature.parameters
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

        @wraps(func)
        def _wrapper(*args, **kwargs):
            if not accepts_kwargs:
                kwargs = {
                    name: value
                    for name, value in kwargs.items()
                    if name in params
                    and params[name].kind
                    in (
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    )
                }

            result = func(*args, **kwargs)
            return result

        return _wrapper
