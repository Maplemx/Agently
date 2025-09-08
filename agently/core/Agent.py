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
        self.prompt = Prompt(
            name=f"Agent-{ self.name }-Prompt",
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
        )
        self.extension_handlers = ExtensionHandlers(
            {
                "prefixes": [],
                "suffixes": [],
            },
            name=f"Agent-{ self.name }-ExtensionHandlers",
        )
        self.request = ModelRequest(
            agent_name=self.name,
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
            parent_prompt=self.prompt,
            parent_extension_handlers=self.extension_handlers,
        )

        self.get_response = self.request.get_response
        self.get_meta = self.request.get_meta
        self.async_get_meta = self.request.async_get_meta
        self.get_text = self.request.get_text
        self.async_get_text = self.request.async_get_text
        self.get_result = self.request.get_result
        self.async_get_result = self.request.async_get_result
        self.get_result_object = self.request.get_result_object
        self.async_get_result_object = self.request.async_get_result_object
        self.get_generator = self.request.get_generator
        self.get_async_generator = self.request.get_async_generator

        self.start = self.get_result
        self.async_start = self.async_get_result

    # Basic Methods
    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)
        return self

    def set_agent_prompt(self, key: "PromptStandardSlot | str", value: Any):
        self.prompt.set(key, value)
        return self

    def set_request_prompt(self, key: "PromptStandardSlot | str", value: Any):
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

    def reset_action_results(self):
        del self.prompt["action_results"]
        return self

    def set_action_results(self, action_results: list[dict[str, Any]]):
        self.prompt.set("action_results", action_results)
        return self

    def add_action_results(self, action: str, result: Any):
        self.prompt.append("action_results", {action: result})
        return self

    # Quick Prompt
    def system(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("input", prompt)
        else:
            self.request.prompt.set("input", prompt)
        return self

    def rule(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("instruct", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.prompt.set("system.rule", prompt)
        else:
            self.request.prompt.set("instruct", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
            self.request.prompt.set("system.rule", prompt)
        return self

    def role(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("instruct", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.prompt.set("system.your_role", prompt)
        else:
            self.request.prompt.set("instruct", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
            self.request.prompt.set("system.your_role", prompt)
        return self

    def user_info(self, prompt: Any, *, always: bool = False):
        if always:
            self.prompt.set("instruct", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
            self.prompt.set("system.user_info", prompt)
        else:
            self.request.prompt.set("instruct", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
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
