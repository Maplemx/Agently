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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowHandler, TriggerFlowEventData

from agently.utils import FunctionShifter


class TriggerFlowChunk:
    def __init__(
        self,
        handler: "TriggerFlowHandler",
        *,
        name: str | None = None,
    ):
        self.name = name if name is not None else uuid.uuid4().hex
        self._handler = handler
        self.trigger = f"Chunk[{ handler.__name__ }]-{ self.name }"

    async def async_call(self, data: "TriggerFlowEventData"):
        result = await FunctionShifter.asyncify(self._handler)(data)
        await data.async_emit(self.trigger, result, layer_marks=data.layer_marks.copy())
        return result

    def call(self, data: "TriggerFlowEventData"):
        result = FunctionShifter.syncify(self._handler)(data)
        data.emit(self.trigger, result, layer_marks=data.layer_marks.copy())
        return result
