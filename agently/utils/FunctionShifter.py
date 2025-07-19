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

import asyncio
import inspect
import threading
from functools import wraps
from typing import Any, Callable, Coroutine, Awaitable, TypeVar, overload, ParamSpec, cast

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


class FunctionShifter:
    @staticmethod
    @overload
    def ensure_awaitable(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        """
        If already a coroutine function, returns as-is.
        """
        ...

    @staticmethod
    @overload
    def ensure_awaitable(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
        """
        If not a coroutine, wraps into an awaitable.
        """
        ...

    @staticmethod
    def ensure_awaitable(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, Awaitable[R]]:
        """
        Wraps any callable so that it returns a coroutine function.
        If `func` is already async, it returns it directly.
        Otherwise, it runs the synchronous function in a separate thread
        to make it awaitable without blocking the event loop.
        """
        if inspect.iscoroutinefunction(func):
            return func  # type: ignore

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await asyncio.to_thread(func, *args, **kwargs)  # type: ignore

        return wrapper

    @staticmethod
    @overload
    def ensure_sync(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, R]:
        """
        Wraps coroutine function to run synchronously.
        """
        ...

    @staticmethod
    @overload
    def ensure_sync(func: Callable[P, R]) -> Callable[P, R]:
        """
        If already sync, returns as-is.
        """
        ...

    @staticmethod
    def ensure_sync(func: Callable[P, R | Coroutine[Any, Any, R]]) -> Callable[P, R]:
        """
        Wraps any callable to make it synchronous blocking.
        If `func` is async, it runs the coroutine in a new thread
        and waits for its completion.
        If `func` is sync, calls it directly.
        """
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    # Check if inside an event loop
                    loop = asyncio.get_running_loop()
                    # If inside, create new thread to run
                    result_holder = {}
                    exception_holder = {}

                    def runner():
                        try:
                            result_holder["result"] = asyncio.run(func(*args, **kwargs))
                        except Exception as e:
                            exception_holder["exception"] = e

                    thread = threading.Thread(target=runner)
                    thread.start()
                    thread.join()

                    if "exception" in exception_holder:
                        raise exception_holder["exception"]
                    return result_holder["result"]

                except RuntimeError:
                    # No running event loop, run directly
                    return asyncio.run(func(*args, **kwargs))

            return wrapper
        else:
            return func  # type: ignore

    @staticmethod
    def to_awaitable(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
        """
        Converts a callable into a coroutine function matching the original signature.
        Handles both sync and async callables.

        Usage:
            coro_func = FunctionShifter.to_awaitable(func)
            result = await coro_func(*args, **kwargs)
        """
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def coro_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return await func(*args, **kwargs)

            return coro_wrapper
        else:

            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return await asyncio.to_thread(func, *args, **kwargs)

            return wrapper

    @staticmethod
    def to_sync(func: Callable[P, R]) -> Callable[P, R]:
        """
        Wraps any callable so it executes synchronously when called,
        matching the original signature.

        Usage:
            sync_func = FunctionShifter.to_sync(func)
            result = sync_func(*args, **kwargs)
        """
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            def coro_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    # Check if inside an event loop
                    loop = asyncio.get_running_loop()
                    # If inside, create new thread to run
                    result_holder = {}
                    exception_holder = {}

                    def runner():
                        try:
                            result_holder["result"] = asyncio.run(func(*args, **kwargs))
                        except Exception as e:
                            exception_holder["exception"] = e

                    thread = threading.Thread(target=runner)
                    thread.start()
                    thread.join()

                    if "exception" in exception_holder:
                        raise exception_holder["exception"]
                    return result_holder["result"]

                except RuntimeError:
                    # No running event loop, run directly
                    return asyncio.run(func(*args, **kwargs))

            return coro_wrapper
        else:

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return func(*args, **kwargs)

            return wrapper

    @staticmethod
    def hybrid_func(func: Callable[P, R]) -> Callable[P, R | Awaitable[R]]:
        """
        Wraps a function to adapt automatically for sync or async context.
        Returns awaitable if called from async context, otherwise returns result directly.
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | Awaitable[R]:
            try:
                # Check if inside an event loop
                loop = asyncio.get_running_loop()
                # In async context, return awaitable
                coro = FunctionShifter.ensure_awaitable(func)(*args, **kwargs)
                task = asyncio.create_task(coro) # type: ignore
                return task
            except RuntimeError:
                # In sync context, return direct result
                return FunctionShifter.ensure_sync(func)(*args, **kwargs)

        return wrapper
