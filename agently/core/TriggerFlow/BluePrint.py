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
import copy
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowAllHandlers, TriggerFlowHandler
    from .Chunk import TriggerFlowChunk
    from .TriggerFlow import TriggerFlow

from .Execution import TriggerFlowExecution


class TriggerFlowBluePrint:
    def __init__(self, *, name: str | None = None):
        self.name = name if name is not None else f"BluePrint-{ uuid.uuid4().hex }"
        self._handlers: "TriggerFlowAllHandlers" = {
            "event": {},
            "flow_data": {},
            "runtime_data": {},
        }
        self.chunks: dict[str, TriggerFlowChunk] = {}

    def add_handler(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        handler_id = str(id) if id is not None else f"Handler<{ handler.__name__ }>-{ uuid.uuid4().hex }"
        handlers = self._handlers[type]
        if target not in handlers:
            handlers[target] = {}
        for id, stored_handler in handlers[target].items():
            if handler == stored_handler:
                return id
        handlers[target][handler_id] = handler
        return handler_id

    def remove_handler(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
        handler: "TriggerFlowHandler | str",
    ):
        handlers = self._handlers[type]
        if target in handlers:
            if isinstance(handler, str):
                handlers[target].pop(handler)
            else:
                for id, stored_handler in handlers[target].items():
                    if handler == stored_handler:
                        del handlers[target][id]
                        return

    def remove_all(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
    ):
        handlers = self._handlers[type]
        if target in handlers:
            handlers[target] = {}

    def add_event_handler(
        self,
        event: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("event", event, handler, id=id)

    def remove_event_handler(
        self,
        event: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("event", event, handler)

    def add_flow_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("flow_data", key, handler, id=id)

    def remove_flow_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("flow_data", key, handler)

    def add_runtime_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("runtime_data", key, handler, id=id)

    def remove_runtime_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("runtime_data", key, handler)

    def create_execution(
        self,
        trigger_flow: "TriggerFlow",
        *,
        execution_id: str | None = None,
        skip_exceptions: bool = False,
    ):
        handlers_snapshot: TriggerFlowAllHandlers = {
            "event": {k: v.copy() for k, v in self._handlers["event"].items()},
            "flow_data": {k: v.copy() for k, v in self._handlers["flow_data"].items()},
            "runtime_data": {k: v.copy() for k, v in self._handlers["runtime_data"].items()},
        }
        return TriggerFlowExecution(
            handlers=handlers_snapshot,
            trigger_flow=trigger_flow,
            id=execution_id,
            skip_exceptions=skip_exceptions,
        )

    def copy(self, *, name: str | None = None):
        new_blue_print = type(self)(name=name)
        new_blue_print._handlers = copy.deepcopy(self._handlers)
        new_blue_print.chunks = copy.deepcopy(self.chunks)
        return new_blue_print
