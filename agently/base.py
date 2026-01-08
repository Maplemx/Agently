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

import logging
from typing import Any, Literal, Type, TYPE_CHECKING, TypeVar, Generic, cast

from agently.utils import Settings, create_logger, FunctionShifter, DataFormatter
from agently.core import PluginManager, EventCenter, Tool, Prompt, ModelRequest, BaseAgent
from agently._default_init import _load_default_settings, _load_default_plugins, _hook_default_event_handlers

if TYPE_CHECKING:
    from agently.types.data import MessageLevel, SerializableValue

# Basic Initialize

settings = Settings(
    name="global_settings",
)
_load_default_settings(settings)
plugin_manager = PluginManager(
    settings,
    name="global_plugin_manager",
)
_load_default_plugins(plugin_manager)
event_center = EventCenter()
_hook_default_event_handlers(event_center)
async_system_message = event_center.async_system_message
system_message = event_center.system_message
logger = create_logger()
httpx_level_name = settings.get("runtime.httpx_log_level", "WARNING")
httpx_level = getattr(logging, str(httpx_level_name).upper(), logging.WARNING)
logging.getLogger("httpx").setLevel(httpx_level)
logging.getLogger("httpcore").setLevel(httpx_level)
tool = Tool(plugin_manager, settings)
_agently_messenger = event_center.create_messenger("Agently")


def print_(content: Any, *args):
    message_sync = FunctionShifter.syncify(_agently_messenger.message)
    contents = [str(content)]
    if args:
        for arg in args:
            contents.append(str(arg))
    content_text = " ".join(contents)
    message_sync(content_text, event="log")


async def async_print(content: Any, *args):
    contents = [str(content)]
    if args:
        for arg in args:
            contents.append(str(arg))
    content_text = " ".join(contents)
    await _agently_messenger.async_message(content_text, event="log")


# Settings Mappings

settings.update_mappings(
    {
        "key_value_mappings": {
            "debug": {
                True: {
                    "runtime.show_model_logs": True,
                    "runtime.show_tool_logs": True,
                    "runtime.show_trigger_flow_logs": True,
                    "runtime.httpx_log_level": "INFO",
                },
                False: {
                    "runtime.show_model_logs": False,
                    "runtime.show_tool_logs": False,
                    "runtime.show_trigger_flow_logs": False,
                    "runtime.httpx_log_level": "WARNING",
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
    ConfigurePromptExtension,
)


class Agent(
    ToolExtension,
    KeyWaiterExtension,
    AutoFuncExtension,
    ConfigurePromptExtension,
    BaseAgent,
): ...


A = TypeVar("A", bound=Agent)

# Agently Main


class AgentlyMain(Generic[A]):
    def __init__(self, AgentType: Type[A] = Agent):
        self.settings = settings
        self.plugin_manager = plugin_manager
        self.event_center = event_center
        self.logger = logger
        self.print = print_
        self.async_print = async_print
        self.set_debug_console("OFF")
        self.tool = tool
        self.AgentType = AgentType

        def set_settings(key: str, value: "SerializableValue", *, auto_load_env: bool = False):
            self.settings.set_settings(key, value, auto_load_env=auto_load_env)
            if key in ("runtime.httpx_log_level", "debug"):
                level_name = self.settings.get("runtime.httpx_log_level", "WARNING")
                level = getattr(logging, str(level_name).upper(), logging.WARNING)
                logging.getLogger("httpx").setLevel(level)
                logging.getLogger("httpcore").setLevel(level)
            return self

        self.set_settings = set_settings

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

    def create_agent(self, name: str | None = None) -> A:
        return self.AgentType(
            self.plugin_manager,
            parent_settings=self.settings,
            name=name,
        )
