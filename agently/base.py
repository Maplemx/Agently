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

from typing import Any

from agently.utils import Settings, create_logger, FunctionShifter
from agently.core import PluginManager, EventCenter, Tool
from agently._default_init import _load_default_settings, _load_default_plugins, _hook_default_event_handlers

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


__all__ = ["settings", "plugin_manager", "event_center", "async_system_message", "system_message", "logger"]
