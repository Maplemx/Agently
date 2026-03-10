# Copyright 2023-2026 AgentEra(Agently.Tech)
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

from dataclasses import dataclass, field
from typing import Any, Literal


TriggerFlowSignalType = Literal["event", "runtime_data", "flow_data"]


@dataclass(slots=True)
class TriggerFlowSignal:
    id: str
    trigger_event: str
    trigger_type: TriggerFlowSignalType
    value: Any = None
    layer_marks: list[str] = field(default_factory=list)
    source: str = "runtime"
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        trigger_event: str,
        trigger_type: TriggerFlowSignalType = "event",
        value: Any = None,
        layer_marks: list[str] | None = None,
        source: str = "runtime",
        meta: dict[str, Any] | None = None,
    ):
        return cls(
            id=uuid.uuid4().hex,
            trigger_event=trigger_event,
            trigger_type=trigger_type,
            value=value,
            layer_marks=layer_marks.copy() if layer_marks is not None else [],
            source=source,
            meta=meta.copy() if meta is not None else {},
        )

    def to_debug_dict(self):
        return {
            "SIGNAL_ID": self.id,
            "TYPE": self.trigger_type,
            "EVENT": self.trigger_event,
            "VALUE": self.value,
            "SOURCE": self.source,
            "META": self.meta,
        }

    def to_state_dict(self):
        return {
            "id": self.id,
            "trigger_event": self.trigger_event,
            "trigger_type": self.trigger_type,
            "value": self.value,
            "layer_marks": self.layer_marks.copy(),
            "source": self.source,
            "meta": self.meta.copy(),
        }
