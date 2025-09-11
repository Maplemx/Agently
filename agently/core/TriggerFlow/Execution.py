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


import uuid
import asyncio
import warnings

from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .TriggerFlow import TriggerFlow
    from agently.types.trigger_flow import TriggerFlowAllHandlers

from agently.utils import RuntimeData, FunctionShifter, GeneratorConsumer
from agently.types.trigger_flow import TriggerFlowEventData, RUNTIME_STREAM_STOP


class TriggerFlowExecution:
    def __init__(
        self,
        *,
        handlers: "TriggerFlowAllHandlers",
        trigger_flow: "TriggerFlow",
        id: str | None = None,
    ):
        # Basic Attributions
        self.id = id if id is not None else uuid.uuid4().hex
        self._handlers = handlers
        self._trigger_flow = trigger_flow
        self._runtime_data = RuntimeData()

        # Execution Status
        self._started = False
        self._result = None
        self._result_ready = asyncio.Event()
        self._runtime_stream_queue = asyncio.Queue()
        self._runtime_stream_consumer: GeneratorConsumer | None = None

        # Emit
        self.emit = FunctionShifter.syncify(self.async_emit)

        # Flow Data
        self.get_flow_data = self._trigger_flow.get_flow_data
        self.set_flow_data = self._trigger_flow.set_flow_data
        self.async_set_flow_data = self._trigger_flow.async_set_flow_data
        self.append_flow_data = self._trigger_flow.set_flow_data
        self.async_append_flow_data = self._trigger_flow.async_set_flow_data
        self.del_flow_data = self._trigger_flow.set_flow_data
        self.async_del_flow_data = self._trigger_flow.async_set_flow_data

        # Runtime Data
        self.get_runtime_data = self._runtime_data.get
        self.set_runtime_data = FunctionShifter.syncify(self.async_set_runtime_data)
        self.append_runtime_data = FunctionShifter.syncify(self.async_append_runtime_data)
        self.del_runtime_data = FunctionShifter.syncify(self.async_del_runtime_data)

        # Start
        self.start = FunctionShifter.syncify(self.async_start)

        # Runtime Stream
        self.put_into_stream = FunctionShifter.syncify(self.async_put_into_stream)
        self.stop_stream = FunctionShifter.syncify(self.async_stop_stream)

    # Emit Event
    async def async_emit(
        self,
        event: str,
        value: Any = None,
    ):
        from agently.base import async_system_message

        await async_system_message(
            "TRIGGER_FLOW",
            {
                "EVENT": event,
                "VALUE": value,
            },
        )
        tasks = []
        handlers = self._handlers["event"]

        if event in handlers:
            for handler_id, handler in handlers[event].items():
                await async_system_message(
                    "TRIGGER_FLOW",
                    {
                        "EVENT": event,
                        "HANDLER": handler_id,
                    },
                )
                tasks.append(
                    asyncio.ensure_future(
                        FunctionShifter.asyncify(handler)(
                            TriggerFlowEventData(
                                event=event,
                                value=value,
                                execution=self,
                            )
                        )
                    )
                )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # Change Runtime Data
    async def _async_change_runtime_data(
        self,
        operation: Literal["set", "append", "del"],
        key: str,
        value: Any,
    ):
        futures = []
        handlers = self._handlers["runtime_data"]

        match operation:
            case "set":
                self._runtime_data.set(key, value)
                value = self._runtime_data[key]
            case "append":
                self._runtime_data.append(key, value)
                value = self._runtime_data[key]
            case "del":
                if self._runtime_data.get(key, None):
                    del self._runtime_data[key]
                    value = None
                else:
                    return

        if key in handlers:
            for handler in handlers[key].values():
                futures.append(
                    FunctionShifter.future(handler)(
                        TriggerFlowEventData(
                            event=key,
                            value=value,
                            execution=self,
                        )
                    )
                )

        if futures:
            await asyncio.gather(*futures, return_exceptions=True)

    async def async_set_runtime_data(self, key: str, value: Any):
        return await self._async_change_runtime_data("set", key, value)

    async def async_append_runtime_data(self, key: str, value: Any):
        return await self._async_change_runtime_data("append", key, value)

    async def async_del_runtime_data(self, key: str):
        return await self._async_change_runtime_data("del", key, None)

    # Start
    async def async_start(self, initial_value: Any = None):
        await self.async_emit("START", initial_value)

    # Runtime Stream
    async def async_put_into_stream(self, stream_item: Any):
        await self._runtime_stream_queue.put(stream_item)

    async def async_stop_stream(self):
        await self._runtime_stream_queue.put(RUNTIME_STREAM_STOP)

    async def _consume_runtime_stream(
        self,
        *,
        initial_value: Any,
        timeout: int | None,
    ):
        temp_execution_task = None
        try:
            if not self._started:
                temp_execution_task = asyncio.create_task(self.async_start(initial_value=initial_value))
            while True:
                if timeout is not None:
                    try:
                        next_result = await asyncio.wait_for(
                            self._runtime_stream_queue.get(),
                            timeout=timeout,
                        )
                    except asyncio.TimeoutError:
                        warnings.warn(
                            f"Execution { self.id } runtime stream stopped because of timeout.\n"
                            f"Timeout seconds: { timeout }\n"
                            "You can use execution.get_async_runtime_stream(timeout=<int | None>) or execution.get_runtime_stream(timeout=<int | None>) to reset new timeout seconds or use None to wait forever."
                        )
                        break
                else:
                    next_result = await self._runtime_stream_queue.get()
                if next_result is not RUNTIME_STREAM_STOP:
                    yield next_result
                else:
                    break
        finally:
            if temp_execution_task:
                await temp_execution_task

    def get_async_runtime_stream(
        self,
        initial_value: Any = None,
        *,
        timeout: int | None = 10,
    ):
        if self._runtime_stream_consumer is None:
            self._runtime_stream_consumer = GeneratorConsumer(
                self._consume_runtime_stream(
                    initial_value=initial_value,
                    timeout=timeout,
                )
            )
        return self._runtime_stream_consumer.get_async_generator()

    def get_runtime_stream(
        self,
        initial_value: Any = None,
        *,
        timeout: int | None = 10,
    ):
        if self._runtime_stream_consumer is None:
            self._runtime_stream_consumer = GeneratorConsumer(
                self._consume_runtime_stream(
                    initial_value=initial_value,
                    timeout=timeout,
                )
            )
        return self._runtime_stream_consumer.get_generator()
