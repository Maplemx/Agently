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

from ._entrypoint import AgentlyMain


def load_default_plugins(Agently: AgentlyMain):
    from agently.builtins.plugins.PromptGenerator.AgentlyPromptGenerator import (
        AgentlyPromptGenerator,
    )

    Agently.plugin_manager.register("PromptGenerator", AgentlyPromptGenerator)

    from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
        OpenAICompatible,
    )

    Agently.plugin_manager.register("ModelRequester", OpenAICompatible)

    from agently.builtins.plugins.ResponseParser.AgentlyResponseParser import AgentlyResponseParser

    Agently.plugin_manager.register("ResponseParser", AgentlyResponseParser)


def load_default_settings(Agently: AgentlyMain):
    Agently.settings.load("yaml_file", f"{str(Path(__file__).resolve().parent)}/_default_settings.yaml")


def hook_default_event_handlers(Agently: AgentlyMain):
    from agently.builtins.hookers.PureLoggerHooker import PureLoggerHooker

    Agently.event_center.register_hooker_plugin(PureLoggerHooker)
