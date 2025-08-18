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

from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agently.core import PluginManager, EventCenter
    from agently.utils import Settings


def _load_default_plugins(plugin_manager: "PluginManager"):
    from agently.builtins.plugins.PromptGenerator.AgentlyPromptGenerator import (
        AgentlyPromptGenerator,
    )

    plugin_manager.register("PromptGenerator", AgentlyPromptGenerator)

    from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
        OpenAICompatible,
    )

    plugin_manager.register(
        "ModelRequester",
        OpenAICompatible,
        activate=True,
    )

    from agently.builtins.plugins.ResponseParser.AgentlyResponseParser import AgentlyResponseParser

    plugin_manager.register("ResponseParser", AgentlyResponseParser)

    from agently.builtins.plugins.ToolManager.AgentlyToolManager import AgentlyToolManager

    plugin_manager.register("ToolManager", AgentlyToolManager)


def _load_default_settings(settings: "Settings"):
    settings.load("yaml_file", f"{str(Path(__file__).resolve().parent)}/_default_settings.yaml")


def _hook_default_event_handlers(event_center: "EventCenter"):
    from agently.builtins.hookers.SystemMessageHooker import SystemMessageHooker

    event_center.register_hooker_plugin(SystemMessageHooker)

    from agently.builtins.hookers.PureLoggerHooker import PureLoggerHooker

    event_center.register_hooker_plugin(PureLoggerHooker)
