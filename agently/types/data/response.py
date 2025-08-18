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

from typing import TYPE_CHECKING, Any, AsyncGenerator, Literal, TypeAlias
from typing_extensions import TypedDict

from pydantic import BaseModel

if TYPE_CHECKING:
    from agently.utils import GeneratorConsumer
    from agently.types.data.serializable import SerializableValue

AgentlyModelResponseEvent = Literal["error", "original_delta", "delta", "original_done", "done", "meta", "extra"]

AgentlyModelResponseMessage: TypeAlias = tuple[AgentlyModelResponseEvent, Any]
AgentlyResponseGenerator: TypeAlias = AsyncGenerator[AgentlyModelResponseMessage, None]


class AgentlyModelResult(TypedDict):
    result_consumer: "GeneratorConsumer | None"
    meta: dict[str, Any]
    original_delta: list[dict[str, Any]]
    original_done: dict[str, Any]
    text_result: str
    cleaned_result: str | None
    parsed_result: "SerializableValue"
    result_object: BaseModel | None
    errors: list[Exception]
    extra: dict[str, Any] | None


class StreamingData(BaseModel):
    """
    Represents a streaming event for a specific path in a JSON structure.

    Attributes:
        path (str): The dot-style path to the field in the JSON object.
        value (Any): The current value at this path.
        delta (Optional[str]): The incremental content (for delta events, typically used for string updates).
        is_complete (bool): Whether this path/field is considered complete and will not change further.
        event_type (Literal["delta", "done"]): The type of event ("delta" for incremental update, "done" for completion).
    """

    path: str
    value: Any
    delta: str | None = None
    is_complete: bool = False
    event_type: Literal["delta", "done"] = "done"
