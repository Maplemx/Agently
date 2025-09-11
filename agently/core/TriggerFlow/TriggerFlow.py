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

    async def _async_change_flow_data(self, operation: Literal["set", "append", "del"], key: str, value: Any):
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

    async def async_set_flow_data(self, key: str, value: Any):
        return await self._async_change_flow_data("set", key, value)

    async def async_append_flow_data(self, key: str, value: Any):
        return await self._async_change_flow_data("append", key, value)

    async def async_del_flow_data(self, key: str):
        return await self._async_change_flow_data("del", key, None)
