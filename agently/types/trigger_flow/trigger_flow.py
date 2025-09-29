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

from typing import Any, Callable, Literal, TYPE_CHECKING
from agently.types.data import AVOID_COPY

if TYPE_CHECKING:
    from agently.core import TriggerFlowExecution

from agently.utils import RuntimeData


class TriggerFlowBlockData:
    global_data = RuntimeData()

    def __init__(
        self,
        outer_block: "TriggerFlowBlockData | None" = None,
        data: dict[str, Any] | None = None,
    ):
        self.outer_block = outer_block
        self.data = data if data is not None else {}


class TriggerFlowEventData:
    def __init__(
        self,
        *,
        trigger_event: str,
        trigger_type: Literal["event", "runtime_data", "flow_data"],
        value: Any,
        execution: "TriggerFlowExecution",
        layer_marks: list[str] | None = None,
    ):
        self.trigger_event = trigger_event
        self.trigger_type = trigger_type
        self.event = trigger_event
        self.type = trigger_type
        self.value = value
        self.execution_id = execution.id
        self.layer_marks = layer_marks if layer_marks is not None else []
        self.settings = execution.settings

        self.get_flow_data = execution.get_flow_data
        self.set_flow_data = execution.set_flow_data
        self.append_flow_data = execution.append_flow_data
        self.del_flow_data = execution.del_flow_data
        self.async_set_flow_data = execution.async_set_flow_data
        self.async_append_flow_data = execution.async_append_flow_data
        self.async_del_flow_data = execution.async_del_flow_data

        self.get_runtime_data = execution.get_runtime_data
        self.set_runtime_data = execution.set_runtime_data
        self.append_runtime_data = execution.append_runtime_data
        self.del_runtime_data = execution.del_runtime_data
        self.async_set_runtime_data = execution.async_set_runtime_data
        self.async_append_runtime_data = execution.async_append_runtime_data
        self.async_del_runtime_data = execution.async_del_runtime_data

        self.emit = execution.emit
        self.async_emit = execution.async_emit

        self.put = execution.put_into_stream
        self.async_put = execution.async_put_into_stream
        self.put_into_stream = execution.put_into_stream
        self.async_put_into_stream = execution.async_put_into_stream
        self.stop_stream = execution.stop_stream
        self.async_stop_stream = execution.async_stop_stream

        self._system_runtime_data = execution._system_runtime_data

    @property
    def upper_layer_mark(self):
        return self.layer_marks[-2] if len(self.layer_marks) > 1 else None

    @property
    def layer_mark(self):
        return self.layer_marks[-1] if len(self.layer_marks) > 0 else None

    def layer_in(self):
        self.layer_marks.append(uuid.uuid4().hex)

    def layer_out(self):
        self.layer_marks = self.layer_marks[:-1] if len(self.layer_marks) > 0 else []


TriggerFlowHandler = Callable[[TriggerFlowEventData], Any]
TriggerFlowHandlers = dict[str, dict[str, TriggerFlowHandler]]
TriggerFlowAllHandlers = dict[Literal["event", "flow_data", "runtime_data"], TriggerFlowHandlers]

RUNTIME_STREAM_STOP = AVOID_COPY()
