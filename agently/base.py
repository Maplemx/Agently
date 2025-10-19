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

from typing import Any, Literal, Type, TYPE_CHECKING, TypeVar, Generic, cast

from agently.utils import Settings, create_logger, FunctionShifter
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
                },
                False: {
                    "runtime.show_model_logs": False,
                    "runtime.show_tool_logs": False,
                    "runtime.show_trigger_flow_logs": False,
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

    def create_agent(self, name: str | None = None) -> A:
        return self.AgentType(
            self.plugin_manager,
            parent_settings=self.settings,
            name=name,
        )
