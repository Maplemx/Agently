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

from typing import Any, Generator, AsyncGenerator, Literal, TYPE_CHECKING, overload

from agently.core import Prompt, ModelRequest
from agently.utils import FunctionShifter, Settings

if TYPE_CHECKING:
    from agently.core import PluginManager
    from agently.types.data import PromptStandardSlot, ChatMessage, StreamingData, SerializableValue


class BaseAgent:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        *,
        parent_settings: "Settings | None" = None,
        name: str | None = None,
    ):
        self.id = uuid.uuid4().hex
        self.name = name if name is not None else self.id[:7]

        from agently.base import event_center

        self._messenger = event_center.create_messenger(
            f"Agent-{ self.name }", base_meta={"table_name": f"Agent-{ self.name }"}
        )

        self.plugin_manager = plugin_manager
        self.settings = Settings(
            name=f"Agent-{ self.name }-Settings",
            parent=parent_settings,
        )
        self.prompt = Prompt(
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
        )
        self.request = ModelRequest(
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
            parent_prompt=self.prompt,
            messenger=self._messenger,
        )

    # Basic Methods
    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)
        return self

    def set_agent_prompt(self, key: "PromptStandardSlot | str", value: tuple[type, str | None, str | None] | Any):
        self.prompt.set(key, value)
        return self

    def set_request_prompt(self, key: "PromptStandardSlot | str", value: tuple[type, str | None, str | None] | Any):
        self.request.prompt.set(key, value)
        return self

    def remove_agent_prompt(self, key: "PromptStandardSlot | str"):
        self.prompt.set(key, None)
        return self

    def remove_request_prompt(self, key: "PromptStandardSlot | str"):
        self.request.prompt.set(key, None)
        return self

    def reset_chat_history(self):
        del self.prompt["chat_history"]
        return self

    def set_chat_history(self, chat_history: "list[dict[str, Any] | ChatMessage]"):
        del self.prompt["chat_history"]
        if not isinstance(chat_history, list):
            chat_history = [chat_history]
        self.prompt.set("chat_history", chat_history)
        return self

    def add_chat_history(self, chat_history: "list[dict[str, Any] | ChatMessage] | dict[str, Any] | ChatMessage"):
        self.prompt.set("chat_history", chat_history)
        return self

    def get_response(self):
        return self.request.get_response()

    @FunctionShifter.hybrid_func
    async def get_meta(self):
        return await self.request.get_response().get_meta()

    @FunctionShifter.hybrid_func
    async def get_text(self):
        return await self.request.get_response().get_text()

    @FunctionShifter.hybrid_func
    async def get_result(
        self,
        *,
        content: Literal['original', 'parsed', 'all'] = "parsed",
    ):
        return await self.request.get_response().get_result(content=content)

    @FunctionShifter.hybrid_func
    async def get_result_object(self):
        return await self.request.get_response().get_result_object()

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
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] = "all",
    ):
        return self.request.get_response().get_generator(content=content)

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
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] = "all",
    ):
        return self.request.get_response().get_async_generator(content=content)

    # Quick Prompt
    def system(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("input", prompt)
        else:
            self.request.prompt.set("input", prompt)
        return self

    def rule(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("system", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.prompt.set("system.rule", prompt)
        else:
            self.request.prompt.set("system", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.request.prompt.set("system.rule", prompt)
        return self

    def role(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("system", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.prompt.set("system.your_role", prompt)
        else:
            self.request.prompt.set("system", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.request.prompt.set("system.your_role", prompt)
        return self

    def user_info(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("system", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
            self.prompt.set("system.user_info", prompt)
        else:
            self.request.prompt.set("system", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
            self.request.prompt.set("system.user_info", prompt)
        return self

    def input(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("input", prompt)
        else:
            self.request.prompt.set("input", prompt)
        return self

    def info(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("info", prompt)
        else:
            self.request.prompt.set("info", prompt)
        return self

    def instruct(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("instruct", prompt)
        else:
            self.request.prompt.set("instruct", prompt)
        return self

    def output(
        self,
        prompt: (
            dict[str, tuple[type, str | None, str, None] | Any]
            | list[tuple[type, str | None, str, None] | Any]
            | tuple[type, str | None, str, None]
            | Any
        ),
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("output", prompt)
        else:
            self.request.prompt.set("output", prompt)
        return self
