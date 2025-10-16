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

from typing import Callable, Any, Literal, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from .Execution import TriggerFlowExecution
    from .Chunk import TriggerFlowHandler
    from agently.types.data import SerializableValue

from agently.types.trigger_flow import TriggerFlowBlockData
from agently.utils import Settings, RuntimeData, FunctionShifter
from .BluePrint import TriggerFlowBluePrint
from .Process import TriggerFlowProcess, TriggerFlowProcess
from .Chunk import TriggerFlowChunk


class TriggerFlow:
    def __init__(
        self,
        blue_print: TriggerFlowBluePrint | None = None,
        *,
        name: str | None = None,
        skip_exceptions: bool = False,
    ):
        from agently.base import settings

        self.name = name or uuid.uuid4().hex
        self.settings = Settings(
            name=f"TriggerFlow-{ self.name }-Settings",
            parent=settings,
        )

        self._flow_data = RuntimeData()
        self._blue_print = blue_print if blue_print is not None else TriggerFlowBluePrint()
        self._skip_exceptions = skip_exceptions
        self._executions: dict[str, "TriggerFlowExecution"] = {}
        self._start_process = TriggerFlowProcess(
            trigger_event="START",
            blue_print=self._blue_print,
            block_data=TriggerFlowBlockData(
                outer_block=None,
            ),
        )

        self.chunks = self._blue_print.chunks

        self.get_flow_data = self._flow_data.get
        self.set_flow_data = FunctionShifter.syncify(self.async_set_flow_data)
        self.append_flow_data = FunctionShifter.syncify(self.async_append_flow_data)
        self.del_flow_data = FunctionShifter.syncify(self.async_del_flow_data)

        self.when = self._start_process.when
        self.to = self._start_process.to
        self.side_branch = self._start_process.side_branch
        self.batch = self._start_process.batch
        self.for_each = self._start_process.for_each

        self.start_execution = FunctionShifter.syncify(self.async_start_execution)
        self.start = FunctionShifter.syncify(self.async_start)

    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)
        return self

    @overload
    def chunk(self, handler_or_name: "TriggerFlowHandler") -> TriggerFlowChunk: ...

    @overload
    def chunk(self, handler_or_name: str) -> "Callable[[TriggerFlowHandler], TriggerFlowChunk]": ...

    def chunk(
        self, handler_or_name: "TriggerFlowHandler | str"
    ) -> "TriggerFlowChunk | Callable[[TriggerFlowHandler], TriggerFlowChunk]":
        if isinstance(handler_or_name, str):

            def wrapper(func: "TriggerFlowHandler"):
                chunk = TriggerFlowChunk(func, name=handler_or_name)
                self._blue_print.chunks[handler_or_name] = chunk
                return chunk

            return wrapper
        else:
            chunk = TriggerFlowChunk(handler_or_name, name=handler_or_name.__name__)
            self._blue_print.chunks[handler_or_name.__name__] = chunk
            return chunk

    def create_execution(self, *, skip_exceptions: bool | None = None):
        execution_id = uuid.uuid4().hex
        skip_exceptions = skip_exceptions if skip_exceptions is not None else self._skip_exceptions
        execution = self._blue_print.create_execution(
            self,
            execution_id=execution_id,
            skip_exceptions=skip_exceptions,
        )
        self._executions[execution_id] = execution
        return execution

    def remove_execution(self, execution: "TriggerFlowExecution | str"):
        if isinstance(execution, str):
            if execution in self._executions:
                del self._executions[execution]
        else:
            if execution.id in self._executions:
                del self._executions[execution.id]

    async def async_start_execution(self, initial_value: Any, *, wait_for_result: bool = False):
        execution = self.create_execution()
        await execution.async_start(initial_value, wait_for_result=wait_for_result)
        return execution

    async def _async_change_flow_data(
        self,
        operation: Literal["set", "append", "del"],
        key: str,
        value: Any,
        *,
        emit: bool = True,
    ):
        futures = []
        match operation:
            case "set":
                self._flow_data.set(key, value)
                value = self._flow_data[key]
            case "append":
                self._flow_data.append(key, value)
                value = self._flow_data[key]
            case "del":
                if self._flow_data.get(key, None):
                    del self._flow_data[key]
                    value = None
                else:
                    return

        if emit:
            for execution in self._executions.values():
                handlers = execution._handlers["flow_data"]
                if key in handlers:
                    futures.append(
                        execution.async_emit(
                            key,
                            value,
                            trigger_type="flow_data",
                        )
                    )
            if futures:
                await asyncio.gather(*futures, return_exceptions=True)

    async def async_set_flow_data(
        self,
        key: str,
        value: Any,
        *,
        emit: bool = True,
    ):
        return await self._async_change_flow_data("set", key, value, emit=emit)

    async def async_append_flow_data(
        self,
        key: str,
        value: Any,
        *,
        emit: bool = True,
    ):
        return await self._async_change_flow_data("append", key, value, emit=emit)

    async def async_del_flow_data(
        self,
        key: str,
        *,
        emit: bool = True,
    ):
        return await self._async_change_flow_data("del", key, None, emit=emit)

    async def async_start(
        self,
        initial_value: Any = None,
        *,
        wait_for_result: bool = True,
        timeout: int | None = 10,
    ):
        execution = await self.async_start_execution(initial_value)
        if wait_for_result:
            return await execution.async_get_result(timeout=timeout)

    def get_async_runtime_stream(
        self,
        initial_value: Any = None,
        *,
        timeout: int | None = 10,
    ):
        execution = self.create_execution()
        return execution.get_async_runtime_stream(
            initial_value,
            timeout=timeout,
        )

    def get_runtime_stream(
        self,
        initial_value: Any = None,
        *,
        timeout: int | None = 10,
    ):
        execution = self.create_execution()
        return execution.get_runtime_stream(
            initial_value,
            timeout=timeout,
        )

    def save_blue_print(self):
        return self._blue_print.copy()

    def load_blue_print(self, new_blue_print: TriggerFlowBluePrint):
        self._blue_print = new_blue_print
