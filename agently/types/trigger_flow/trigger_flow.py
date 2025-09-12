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


from typing import Any, Callable, Literal, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from agently.core import TriggerFlowExecution
    from agently.core.TriggerFlow import TriggerFlowBaseProcess


class TriggerFlowBlockData(BaseModel):
    outer_block: "TriggerFlowBlockData | None"
    data: dict[str, Any] = {}


class TriggerFlowEventData:
    def __init__(
        self,
        *,
        event: str,
        value: Any,
        execution: "TriggerFlowExecution",
    ):
        self.event = event
        self.value = value
        self.execution_id = execution.id

        self.get_flow_data = execution.get_flow_data
        self.set_flow_data = execution.set_flow_data
        self.append_flow_data = execution.append_flow_data
        self.del_flow_data = execution.del_flow_data

        self.get_runtime_data = execution.get_runtime_data
        self.set_runtime_data = execution.set_runtime_data
        self.append_runtime_data = execution.append_runtime_data
        self.del_runtime_data = execution.del_runtime_data

        self.emit = execution.emit
        self.async_emit = execution.async_emit

        self.put = execution.put_into_stream
        self.async_put = execution.async_put_into_stream
        self.put_into_stream = execution.put_into_stream
        self.async_put_into_stream = execution.async_put_into_stream
        self.stop_stream = execution.stop_stream
        self.async_stop_stream = execution.async_stop_stream


TriggerFlowHandler = Callable[[TriggerFlowEventData], Any]
TriggerFlowHandlers = dict[str, dict[str, TriggerFlowHandler]]
TriggerFlowAllHandlers = dict[Literal["event", "flow_data", "runtime_data"], TriggerFlowHandlers]

RUNTIME_STREAM_STOP = object()
EMPTY_RESULT = object()
