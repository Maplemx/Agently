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

from typing import Any, TYPE_CHECKING, Literal, overload
from agently.base import settings, plugin_manager, tool, event_center, logger, print_, async_print
from agently.core import Prompt, ModelRequest, BaseAgent

if TYPE_CHECKING:
    from agently.types.data import MessageLevel, SerializableValue

settings.update_mappings(
    {
        "key_value_mappings": {
            "debug": {
                True: {
                    "runtime.show_model_logs": True,
                    "runtime.show_tool_logs": False,
                },
                False: {
                    "runtime.show_model_logs": False,
                    "runtime.show_tool_logs": True,
                },
                "silent": {
                    "runtime.show_model_logs": False,
                    "runtime.show_tool_logs": False,
                },
            }
        }
    }
)

# Extensions Installation
# BaseAgent + Extensions = Agent
from agently.builtins.agent_extensions import (
    ToolExtension,
    KeyWaiterExtension,
    AutoFuncExtension,
)


class Agent(
    ToolExtension,
    KeyWaiterExtension,
    AutoFuncExtension,
    BaseAgent,
): ...


class AgentlyMain:
    def __init__(self):
        self.settings = settings
        self.plugin_manager = plugin_manager
        self.event_center = event_center
        self.logger = logger
        self.print = print_
        self.async_print = async_print
        self.set_debug_console("OFF")
        self.tool = tool

    def set_debug_console(self, debug_console_status: Literal["ON", "OFF"]):
        match debug_console_status:
            case "OFF":
                self.event_center.unregister_hooker_plugin("ConsoleHooker")
            case "ON":
                from agently.builtins.hookers.ConsoleHooker import ConsoleHooker

                self.event_center.register_hooker_plugin(ConsoleHooker)

    def set_log_level(self, log_level: "MessageLevel"):
        self.logger.setLevel(log_level)
        return self

    @overload
    def set_settings(self, key: Literal["debug"], value: Literal[True, False, "silent"]): ...
    @overload
    def set_settings(self, key: str, value: "SerializableValue"): ...
    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)
        return self

    def create_prompt(self, name: str = "agently_prompt") -> Prompt:
        return Prompt(
            self.plugin_manager,
            self.settings,
            name=name,
        )

    def create_request(self, name: str | None = None) -> ModelRequest:
        return ModelRequest(
            self.plugin_manager,
            parent_settings=self.settings,
            agent_name=name,
        )

    def create_agent(self, name: str | None = None) -> Agent:
        return Agent(
            self.plugin_manager,
            parent_settings=self.settings,
            name=name,
        )
