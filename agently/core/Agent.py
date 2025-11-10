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

from typing import Any, TYPE_CHECKING

from agently.core import Prompt, ExtensionHandlers, ModelRequest
from agently.utils import Settings

if TYPE_CHECKING:
    from agently.core import PluginManager
    from agently.types.data import PromptStandardSlot, ChatMessage, SerializableValue


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

        self.plugin_manager = plugin_manager
        self.settings = Settings(
            name=f"Agent-{ self.name }-Settings",
            parent=parent_settings,
        )
        self.agent_prompt = Prompt(
            name=f"Agent-{ self.name }-Prompt",
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
        )
        self.extension_handlers = ExtensionHandlers(
            {
                "request_prefixes": [],
                "broadcast_prefixes": [],
                "broadcast_suffixes": [],
                "finally": [],
            },
            name=f"Agent-{ self.name }-ExtensionHandlers",
        )
        self.request = ModelRequest(
            agent_name=self.name,
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
            parent_prompt=self.agent_prompt,
            parent_extension_handlers=self.extension_handlers,
        )
        self.request_prompt = self.request.prompt
        self.prompt = self.request_prompt

        self.get_response = self.request.get_response
        self.get_result = self.request.get_result
        self.get_meta = self.request.get_meta
        self.async_get_meta = self.request.async_get_meta
        self.get_text = self.request.get_text
        self.async_get_text = self.request.async_get_text
        self.get_data = self.request.get_data
        self.async_get_data = self.request.async_get_data
        self.get_data_object = self.request.get_data_object
        self.async_get_data_object = self.request.async_get_data_object
        self.get_generator = self.request.get_generator
        self.get_async_generator = self.request.get_async_generator

        self.start = self.get_data
        self.async_start = self.async_get_data

    # Basic Methods
    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)
        return self

    def set_agent_prompt(
        self,
        key: "PromptStandardSlot | str",
        value: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set(key, value, mappings)
        return self

    def set_request_prompt(
        self,
        key: "PromptStandardSlot | str",
        value: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.request.prompt.set(key, value, mappings)
        return self

    def remove_agent_prompt(self, key: "PromptStandardSlot | str"):
        self.prompt.set(key, None)
        return self

    def remove_request_prompt(self, key: "PromptStandardSlot | str"):
        self.request.prompt.set(key, None)
        return self

    def reset_chat_history(self):
        if "chat_history" in self.prompt:
            self.prompt.set("chat_history", [])
        return self

    def set_chat_history(self, chat_history: "list[dict[str, Any] | ChatMessage]"):
        self.reset_chat_history()
        if not isinstance(chat_history, list):
            chat_history = [chat_history]
        self.prompt.set("chat_history", chat_history)
        return self

    def add_chat_history(self, chat_history: "list[dict[str, Any] | ChatMessage] | dict[str, Any] | ChatMessage"):
        if not isinstance(chat_history, list):
            chat_history = [chat_history]
        self.prompt.set("chat_history", chat_history)
        return self

    def reset_action_results(self):
        if "action_results" in self.prompt:
            del self.prompt["action_results"]
        return self

    def set_action_results(self, action_results: list[dict[str, Any]]):
        self.prompt.set("action_results", action_results)
        return self

    def add_action_results(self, action: str, result: Any):
        self.prompt.append("action_results", {action: result})
        return self

    # Quick Prompt
    def system(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("input", prompt, mappings)
        else:
            self.request.prompt.set("input", prompt, mappings)
        return self

    def rule(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("instruct", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.prompt.set("system.rule", prompt, mappings)
        else:
            self.request.prompt.set("instruct", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.request.prompt.set("system.rule", prompt, mappings)
        return self

    def role(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("instruct", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.prompt.set("system.your_role", prompt, mappings)
        else:
            self.request.prompt.set("instruct", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.request.prompt.set("system.your_role", prompt, mappings)
        return self

    def user_info(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("instruct", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
            self.prompt.set("system.user_info", prompt, mappings)
        else:
            self.request.prompt.set("instruct", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
            self.request.prompt.set("system.user_info", prompt, mappings)
        return self

    def input(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("input", prompt, mappings)
        else:
            self.request.prompt.set("input", prompt, mappings)
        return self

    def info(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("info", prompt, mappings)
        else:
            self.request.prompt.set("info", prompt, mappings)
        return self

    def instruct(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("instruct", prompt, mappings)
        else:
            self.request.prompt.set("instruct", prompt, mappings)
        return self

    def examples(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("examples", prompt, mappings)
        else:
            self.request.prompt.set("examples", prompt, mappings)
        return self

    def output(
        self,
        prompt: (
            dict[str, tuple[type, str | None, str, None] | Any]
            | list[tuple[type, str | None, str, None] | Any]
            | tuple[type, str | None, str, None]
            | Any
        ),
        mappings: dict[str, Any] | None = None,
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("output", prompt, mappings)
        else:
            self.request.prompt.set("output", prompt, mappings)
        return self

    def options(
        self,
        options: dict[str, Any],
        *,
        always: bool = False,
    ):
        if always:
            self.prompt.set("options", options)
        else:
            self.request.prompt.set("options", options)
        return self
