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
import queue as sync_queue
from types import AsyncGeneratorType, GeneratorType
from typing import AsyncGenerator, Generator, cast, Any


class GeneratorConsumer:
    """
    A utility to wrap a Generator or AsyncGenerator and allow multiple
    asynchronous or synchronous consumers to subscribe to its output,
    with history replay, error propagation, and graceful shutdown.
    """

    def __init__(self, original_generator: AsyncGenerator | Generator):
        """
        Initialize the consumer with a generator or async generator.

        Args:
            original_generator: The original generator to consume.

        Raises:
            TypeError: If input is neither Generator nor AsyncGenerator.
        """
        if isinstance(original_generator, GeneratorType):
            self._generator_type = "Generator"
        elif isinstance(original_generator, AsyncGeneratorType):
            self._generator_type = "AsyncGenerator"
        else:
            raise TypeError(f"Expected Generator or AsyncGenerator, got: {original_generator}")

        self.original_generator = original_generator
        self._history: list = []
        self._listeners: list[asyncio.Queue] = []
        self._consume_task: asyncio.Task | None = None
        self._done = asyncio.Event()
        self._sentinel = object()
        self._exception: Exception | None = None
        self._closed = False
        self._closing_lock = asyncio.Lock()
        self._generator_closed = False

    async def _consume(self):
        """
        Internal coroutine that consumes the generator and dispatches messages.
        """
        try:
            if self._generator_type == "Generator":
                for msg in cast(Generator, self.original_generator):
                    await self._broadcast(msg)
            else:  # AsyncGenerator
                async for msg in cast(AsyncGenerator, self.original_generator):
                    await self._broadcast(msg)
        except Exception as e:
            self._exception = e
            await self._broadcast(e)
        finally:
            self._done.set()
            if not self._generator_closed:
                await self._broadcast(self._sentinel)
                self._generator_closed = True

    async def _broadcast(self, msg: Any):
        """
        Broadcast a message to all listeners and store history if it's not an error or sentinel.

        Args:
            msg: The message, exception, or sentinel object to broadcast.
        """
        if msg is not self._sentinel and not isinstance(msg, Exception):
            self._history.append(msg)

        for queue in self._listeners:
            await queue.put(msg)

    async def _ensure_started(self):
        """
        Start the internal consumer task if it hasn't been started.
        """
        if self._consume_task is None:
            self._consume_task = asyncio.create_task(self._consume())

    async def get_async_generator(self) -> AsyncGenerator:
        """
        Get an async generator that receives messages from the source,
        including all past history.

        Raises:
            Exception: If the source generator raised an exception.
        """
        if self._closed:
            raise RuntimeError("GeneratorConsumer has been closed.")

        await self._ensure_started()
        queue = asyncio.Queue()
        self._listeners.append(queue)

        try:
            for msg in self._history:
                await queue.put(msg)

            if self._exception:
                await queue.put(self._exception)
            elif self._done.is_set():
                await queue.put(self._sentinel)

            while True:
                msg = await queue.get()
                if msg is self._sentinel:
                    break
                if isinstance(msg, Exception):
                    raise msg
                yield msg
        finally:
            self._listeners.remove(queue)

    def get_generator(self) -> Generator:
        """
        Get a synchronous generator that receives messages from the source.

        Raises:
            Exception: If the source generator raised an exception.
        """
        if self._closed:
            raise RuntimeError("GeneratorConsumer has been closed.")

        sync_q: sync_queue.Queue = sync_queue.Queue()

        def run_bridge():
            async def bridge():
                await self._ensure_started()
                queue = asyncio.Queue()
                self._listeners.append(queue)

                try:
                    for msg in self._history:
                        await queue.put(msg)

                    if self._exception:
                        await queue.put(self._exception)
                    elif self._done.is_set():
                        await queue.put(self._sentinel)

                    while True:
                        msg = await queue.get()
                        if msg is self._sentinel:
                            break
                        sync_q.put(msg)
                except Exception as e:
                    sync_q.put(e)
                finally:
                    self._listeners.remove(queue)
                    sync_q.put(self._sentinel)

            try:
                asyncio.run(bridge())
            except Exception as e:
                sync_q.put(e)
                sync_q.put(self._sentinel)

        threading.Thread(target=run_bridge, daemon=True).start()

        def generator():
            while True:
                msg = sync_q.get()
                if msg is self._sentinel:
                    break
                if isinstance(msg, Exception):
                    raise msg
                yield msg

        return generator()

    async def get_result(self) -> list:
        """
        Wait for the generator to finish and return the full history.

        Returns:
            A list of all messages produced by the generator.
        """
        await self._ensure_started()
        await self._done.wait()

        if self._exception:
            raise self._exception

        return self._history

    async def close(self):
        """
        Gracefully cancel the consumer and notify all listeners.
        After calling this, no new listeners can be added.
        """
        self._closed = True
        async with self._closing_lock:
            if self._consume_task:
                self._consume_task.cancel()
                try:
                    await self._consume_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self._exception = e
            self._done.set()
            if not self._generator_closed:
                await self._broadcast(self._sentinel)
                self._generator_closed = True
