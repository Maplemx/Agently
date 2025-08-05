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
