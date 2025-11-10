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

from typing import Any, Protocol, AsyncGenerator, Generator, Literal, TYPE_CHECKING, overload

from agently.types.plugins import AgentlyPlugin

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.types.data import AgentlyResponseGenerator, SerializableData, StreamingData, AgentlyModelResult
    from agently.utils import Settings
    from pydantic import BaseModel


class ResponseParser(AgentlyPlugin, Protocol):
    name: str
    agent_name: str
    response_id: str
    settings: "Settings"
    DEFAULT_SETTINGS: dict[str, Any] = {}

    full_result_data: "AgentlyModelResult"

    response_generator: "AgentlyResponseGenerator"

    def __init__(
        self,
        agent_name: str,
        response_id: str,
        prompt: "Prompt",
        response_generator: "AgentlyResponseGenerator",
        settings: "Settings",
    ): ...

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    def get_meta(self) -> "SerializableData": ...

    async def async_get_meta(self) -> "SerializableData": ...

    def get_data(
        self,
        *,
        type: Literal["original", "parsed", "all"] = "parsed",
    ) -> Any: ...

    async def async_get_data(
        self,
        *,
        type: Literal["original", "parsed", "all"] = "parsed",
    ) -> Any: ...

    def get_data_object(self) -> "BaseModel | None": ...

    async def async_get_data_object(self) -> "BaseModel | None": ...

    def get_text(self) -> str: ...

    async def async_get_text(self) -> str: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["instant", "streaming_parse"],
    ) -> AsyncGenerator["StreamingData", None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["all"],
    ) -> AsyncGenerator[tuple[str, Any], None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["delta", "typed_delta", "original"],
    ) -> AsyncGenerator[str, None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> AsyncGenerator: ...

    def get_async_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> AsyncGenerator:
        """
        'instant' is Agently v3 compatible for 'streaming_parse'
        """
        ...

    @overload
    def get_generator(
        self,
        type: Literal["instant", "streaming_parse"],
    ) -> Generator["StreamingData", None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["all"],
    ) -> Generator[tuple[str, Any], None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["delta", "typed_delta", "original"],
    ) -> Generator[str, None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> Generator: ...

    def get_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> Generator:
        """
        'instant' is Agently v3 compatible for 'streaming_parse'
        """
        ...
