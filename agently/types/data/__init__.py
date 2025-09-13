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


class AVOID_COPY:
    __slots__ = ("id",)

    def __init__(self):
        import uuid

        self.id = uuid.uuid4().hex

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return (self.__class__, (), {"id": self.id})


EMPTY = AVOID_COPY()

from .serializable import SerializableData, SerializableValue
from .prompt import (
    ChatMessage,
    ChatMessageContent,
    TextMessageContent,
    PromptModel,
    PromptStandardSlot,
    ToolMeta,
)
from .request import (
    AgentlyRequestData,
    AgentlyRequestDataDict,
)

from .response import (
    AgentlyModelResult,
    AgentlyModelResponseEvent,
    AgentlyModelResponseMessage,
    AgentlyResponseGenerator,
    StreamingData,
)

from .event import (
    AgentlyEvent,
    AgentlySystemEvent,
    MessageLevel,
    EventStatus,
    EventMessageDict,
    EventMessage,
    EventHook,
)

from .tool import (
    ArgumentDesc,
    KwargsType,
    ReturnType,
    MCPConfig,
    MCPConfigs,
)
