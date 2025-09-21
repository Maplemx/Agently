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

import time
from typing import Any, Awaitable, Callable, Literal, TypeAlias
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

AgentlyEvent: TypeAlias = Literal["message", "error", "data", "log", "console", "AGENTLY_SYS"]

AgentlySystemEvent: TypeAlias = Literal["MODEL_REQUEST", "TOOL", "TRIGGER_FLOW"]

MessageLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

EventStatus: TypeAlias = Literal["INIT", "DOING", "DONE", "PENDING", "SUCCESS", "FAILED", "UNKNOWN", ""] | str


class EventMessageDict(TypedDict, total=False):
    module_name: str
    status: EventStatus
    content: Any
    exception: Exception | None
    level: MessageLevel
    meta: dict[str, Any]
    timestamp: int


class EventMessage(BaseModel):
    event: AgentlyEvent = "message"
    status: EventStatus = ""
    module_name: str = "Agently"
    content: Any
    exception: Exception | None = None
    level: MessageLevel = "INFO"
    meta: dict[str, Any] = {}
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))

    model_config = {
        "arbitrary_types_allowed": True,
    }


EventHook = Callable[[EventMessage], None | Awaitable[None]]
