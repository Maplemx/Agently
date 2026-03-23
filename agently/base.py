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

import logging
from typing import Any, Literal, Type, TYPE_CHECKING, TypeVar, Generic, cast

from agently.utils import Settings, create_logger
from agently.core import PluginManager, EventCenter, Tool, Prompt, ModelRequest, BaseAgent
from agently._default_init import _load_default_settings, _load_default_plugins, _hook_default_event_handlers

if TYPE_CHECKING:
    from agently.types.data import RuntimeEventLevel, SerializableValue

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
async_emit_runtime = event_center.async_emit
emit_runtime = event_center.emit
logger = create_logger()
httpx_level_name = settings.get("runtime.httpx_log_level", "WARNING")
httpx_level = getattr(logging, str(httpx_level_name).upper(), logging.WARNING)
logging.getLogger("httpx").setLevel(httpx_level)
logging.getLogger("httpcore").setLevel(httpx_level)
tool = Tool(plugin_manager, settings)
_agently_emitter = event_center.create_emitter("Agently")


def print_(content: Any, *args):
    contents = [str(content)]
    if args:
        for arg in args:
            contents.append(str(arg))
    content_text = " ".join(contents)
    _agently_emitter.info(content_text, event_type="runtime.print")


async def async_print(content: Any, *args):
    contents = [str(content)]
    if args:
        for arg in args:
            contents.append(str(arg))
    content_text = " ".join(contents)
    await _agently_emitter.async_info(content_text, event_type="runtime.print")


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
    StreamingPrintExtension,
    SessionExtension,
    ToolExtension,
    KeyWaiterExtension,
    AutoFuncExtension,
    ConfigurePromptExtension,
)


class Agent(
    StreamingPrintExtension,
    SessionExtension,
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
        self.emit_runtime = emit_runtime
        self.async_emit_runtime = async_emit_runtime
        self.logger = logger
        self.print = print_
        self.async_print = async_print
        self.tool = tool
        self.AgentType = AgentType

        def refresh_httpx_log_level():
            level_name = self.settings.get("runtime.httpx_log_level", "WARNING")
            level = getattr(logging, str(level_name).upper(), logging.WARNING)
            logging.getLogger("httpx").setLevel(level)
            logging.getLogger("httpcore").setLevel(level)

        def set_settings(
            key: str,
            value: "SerializableValue",
            *,
            auto_load_env: bool = False,
            raise_empty: bool = False,
        ):
            self.settings.set_settings(key, value, auto_load_env=auto_load_env, raise_empty=raise_empty)
            if key in ("runtime.httpx_log_level", "debug"):
                refresh_httpx_log_level()
            return self

        def load_settings(
            data_type: Literal["json_file", "yaml_file", "toml_file", "json", "yaml", "toml"],
            value: str,
            *,
            auto_load_env: bool = False,
            raise_empty: bool = False,
        ):
            self.settings.load(data_type, value, auto_load_env=auto_load_env, raise_empty=raise_empty)
            refresh_httpx_log_level()
            return self

        self.set_settings = set_settings
        self.load_settings = load_settings

    def set_debug_console(self, debug_console_status: Literal["ON", "OFF"]):
        # Deprecated: debug console mode is retired and no longer participates in runtime.
        if debug_console_status == "ON":
            self.logger.warning("`set_debug_console(\"ON\")` is deprecated and has no effect.")
        return self

    def set_log_level(self, log_level: "RuntimeEventLevel"):
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
