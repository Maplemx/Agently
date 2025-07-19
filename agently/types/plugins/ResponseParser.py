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
from agently.utils import FunctionShifter

if TYPE_CHECKING:
    from agently.core import Prompt, EventCenterMessenger
    from agently.types.data import AgentlyResponseGenerator, SerializableData, StreamingData
    from agently.utils import SerializableRuntimeData
    from pydantic import BaseModel


class ResponseParser(AgentlyPlugin, Protocol):
    name: str
    settings: "SerializableRuntimeData"
    messenger: "EventCenterMessenger"
    DEFAULT_SETTINGS: dict[str, Any] = {}

    response_generator: "AgentlyResponseGenerator"

    def __init__(
        self,
        prompt: "Prompt",
        response_generator: "AgentlyResponseGenerator",
        settings: "SerializableRuntimeData",
        messenger: "EventCenterMessenger",
    ): ...

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    @FunctionShifter.hybrid_func
    async def get_meta(self) -> "SerializableData": ...

    @FunctionShifter.hybrid_func
    async def get_result(
        self,
        *,
        content: Literal["original", "parsed", "all"] = "parsed",
    ) -> Any: ...

    @FunctionShifter.hybrid_func
    async def get_result_object(self) -> "BaseModel | None": ...

    @FunctionShifter.hybrid_func
    async def get_text(self) -> str: ...

    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["all"] = "all",
    ) -> AsyncGenerator[tuple[str, Any], None]: ...
    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["delta", "original"],
    ) -> AsyncGenerator[str, None]: ...
    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["instant", "streaming_parse"],
    ) -> AsyncGenerator["StreamingData", None]: ...
    def get_async_generator(
        self,
        *,
        content: Literal["all", "delta", "original", "instant", "streaming_parse"] = "all",
    ) -> AsyncGenerator:
        """
        'instant' is Agently v3 compatible for 'streaming_parse'
        """
        ...

    @overload
    def get_generator(
        self,
        *,
        content: Literal["all"] = "all",
    ) -> Generator[tuple[str, Any], None, None]: ...
    @overload
    def get_generator(
        self,
        *,
        content: Literal["delta", "original"],
    ) -> Generator[str, None, None]: ...
    @overload
    def get_generator(
        self,
        *,
        content: Literal["instant", "streaming_parse"],
    ) -> Generator["StreamingData", None, None]: ...
    def get_generator(
        self,
        *,
        content: Literal["all", "delta", "original", "instant", "streaming_parse"] = "all",
    ) -> Generator:
        """
        'instant' is Agently v3 compatible for 'streaming_parse'
        """
        ...
