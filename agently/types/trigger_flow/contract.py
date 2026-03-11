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

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import TypeAdapter
from typing_extensions import NotRequired, TypedDict

InputT = TypeVar("InputT")
StreamT = TypeVar("StreamT")
ResultT = TypeVar("ResultT")


class TriggerFlowContractEntry(TypedDict):
    label: str
    schema: dict[str, Any] | None


class TriggerFlowInterrupt(TypedDict):
    id: str
    type: str
    status: Literal["waiting", "resumed"]
    payload: NotRequired[Any]
    resume_event: NotRequired[str | None]
    response: NotRequired[Any]


class TriggerFlowInterruptEvent(TypedDict):
    type: Literal["interrupt"]
    action: Literal["pause", "resume"]
    execution_id: str
    interrupt: TriggerFlowInterrupt
    signal: NotRequired[dict[str, Any] | None]
    value: NotRequired[Any]


TriggerFlowSystemStreamEvent: TypeAlias = TriggerFlowInterruptEvent
TRIGGER_FLOW_INTERRUPT_EVENT_SCHEMA = TypeAdapter(TriggerFlowInterruptEvent).json_schema()


class TriggerFlowSystemStreamMetadata(TypedDict, total=False):
    interrupt: TriggerFlowContractEntry


class TriggerFlowContractMetadata(TypedDict, total=False):
    initial_input: TriggerFlowContractEntry | None
    stream: TriggerFlowContractEntry | None
    result: TriggerFlowContractEntry | None
    meta: dict[str, Any]
    system_stream: TriggerFlowSystemStreamMetadata


@dataclass(frozen=True)
class TriggerFlowContractSpec(Generic[InputT, StreamT, ResultT]):
    initial_input: Any | None = None
    stream: Any | None = None
    result: Any | None = None
    meta: dict[str, Any] = field(default_factory=dict)
