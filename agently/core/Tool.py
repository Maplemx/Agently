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

from typing import TYPE_CHECKING, cast

from agently.utils import Settings

if TYPE_CHECKING:
    from agently.types.plugins import ToolManager
    from agently.core import PluginManager


class Tool:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        parent_settings: "Settings",
    ):
        self.settings = Settings(
            name="Tool-Settings",
            parent=parent_settings,
        )
        ToolManagerPlugin = cast(
            type["ToolManager"],
            plugin_manager.get_plugin(
                "ToolManager",
                str(self.settings["plugins.ToolManager.activate"]),
            ),
        )
        self.tool_manager = ToolManagerPlugin(self.settings)
        self.register = self.tool_manager.register
        self.tag = self.tool_manager.tag
        self.tool_func = self.tool_manager.tool_func
        self.get_tool_info = self.tool_manager.get_tool_info
        self.get_tool_list = self.tool_manager.get_tool_list
        self.get_tool_func = self.tool_manager.get_tool_func
        self.call_tool = self.tool_manager.call_tool
        self.async_call_tool = self.tool_manager.async_call_tool
        self.use_mcp = self.tool_manager.use_mcp
        self.async_use_mcp = self.tool_manager.async_use_mcp
