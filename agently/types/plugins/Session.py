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


from typing import Tuple, Callable, Sequence, Any, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.data import (
        ChatMessage,
        ChatMessageDict,
        SerializableValue,
    )
    from agently.utils import SettingsNamespace

AnalysisHandler = Callable[
    [
        "Sequence[ChatMessage]",
        "Sequence[ChatMessage]",
        "SerializableValue",
        "SettingsNamespace",
    ],
    str | None | Awaitable[str | None],
]

StandardAnalysisHandler = Callable[
    [
        "Sequence[ChatMessage]",
        "Sequence[ChatMessage]",
        "SerializableValue",
        "SettingsNamespace",
    ],
    Awaitable[str | None],
]

ResizeHandler = Callable[
    [
        "Sequence[ChatMessage]",
        "Sequence[ChatMessage]",
        "SerializableValue",
        "SettingsNamespace",
    ],
    Tuple[
        "Sequence[ChatMessage | ChatMessageDict] | None",
        "Sequence[ChatMessage | ChatMessageDict] | None",
        "SerializableValue",
    ]
    | Awaitable[
        Tuple[
            "Sequence[ChatMessage | ChatMessageDict] | None",
            "Sequence[ChatMessage | ChatMessageDict] | None",
            "SerializableValue",
        ]
    ],
]

StandardResizeHandler = Callable[
    [
        "Sequence[ChatMessage]",
        "Sequence[ChatMessage]",
        "SerializableValue",
        "SettingsNamespace",
    ],
    Awaitable[
        Tuple[
            "Sequence[ChatMessage | ChatMessageDict] | None",
            "Sequence[ChatMessage | ChatMessageDict] | None",
            "SerializableValue",
        ]
    ],
]

# Backward-compatible aliases.
ExecutionHandler = ResizeHandler
StandardExecutionHandler = StandardResizeHandler
