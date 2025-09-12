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

from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .Execution import TriggerFlowExecution

from agently.types.trigger_flow import TriggerFlowBlockData, TriggerFlowEventData
from agently.utils import RuntimeData, FunctionShifter
from .BluePrint import TriggerFlowBluePrint
from .Process import TriggerFlowProcess, TriggerFlowProcess


class TriggerFlow:
    def __init__(
        self,
        blue_print: TriggerFlowBluePrint | None = None,
    ):
        self._flow_data = RuntimeData()
        self._blue_print = blue_print if blue_print is not None else TriggerFlowBluePrint()
        self._executions: dict[str, "TriggerFlowExecution"] = {}
        self._start_process = TriggerFlowProcess(
            trigger_event="START",
            blue_print=self._blue_print,
            block_data=TriggerFlowBlockData(
                outer_block=None,
            ),
        )

        self.get_flow_data = self._flow_data.get
        self.set_flow_data = FunctionShifter.syncify(self.async_set_flow_data)
        self.append_flow_data = FunctionShifter.syncify(self.async_append_flow_data)
        self.del_flow_data = FunctionShifter.syncify(self.async_del_flow_data)

        self.to = self._start_process.to
        self.side_branch = self._start_process.side_branch
        self.batch = self._start_process.batch
        self.for_each = self._start_process.for_each

        self.start_execution = FunctionShifter.syncify(self.async_start_execution)
        self.start = FunctionShifter.syncify(self.async_start)

    def when(
        self,
        target: str,
        *,
        type: Literal["event", "runtime_data", "flow_data"] = "event",
    ):
        return TriggerFlowProcess(
            trigger_event=target,
            trigger_type=type,
            blue_print=self._blue_print,
            block_data=TriggerFlowBlockData(
                outer_block=None,
            ),
        )

    def when_event(self, event: str):
        return self.when(event, type="event")

    def when_runtime_data(self, key: str):
        return self.when(key, type="runtime_data")

    def when_flow_data(self, key: str):
        return self.when(key, type="flow_data")

    def create_execution(self):
        execution_id = uuid.uuid4().hex
        execution = self._blue_print.create_execution(self, execution_id=execution_id)
        self._executions[execution_id] = execution
        return execution

    def remove_execution(self, execution: "TriggerFlowExecution | str"):
        if isinstance(execution, str):
            if execution in self._executions:
                del self._executions[execution]
        else:
            if execution.id in self._executions:
                del self._executions[execution.id]

    async def async_start_execution(self, initial_value: Any):
        execution = self.create_execution()
        await execution.async_start(initial_value)
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
                    for handler in handlers[key].values():
                        futures.append(
                            FunctionShifter.future(handler)(
                                TriggerFlowEventData(
                                    event=key,
                                    value=value,
                                    execution=execution,
                                )
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
