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

from typing import Optional, Any, Type, cast, overload
from agently.utils import (
    RuntimeData,
    Settings,
)
from agently.types.plugins import AgentlyPlugin, AgentlyPluginType
from agently.utils import create_messenger


class PluginManager:
    def __init__(
        self,
        settings: Settings,
        *,
        parent: Optional["PluginManager"] = None,
        name: Optional[str] = None,
    ):
        self.name = f"PluginManager-{ name }" if name is not None else "PluginManager"
        self.settings = settings
        self.plugins = RuntimeData(
            name=f"{ self.name }-Plugins",
            parent=parent.plugins if parent is not None else None,
        )

    def register(
        self,
        plugin_type: AgentlyPluginType,
        plugin_class: Type[AgentlyPlugin],
        *,
        activate: bool = True,
    ) -> "PluginManager":
        if hasattr(plugin_class, "_on_register"):
            plugin_class._on_register()
        self.plugins.update(
            {
                plugin_type: {
                    plugin_class.name: plugin_class,
                }
            }
        )
        if activate:
            self.settings.set(
                f"plugins.{ plugin_type }.activate",
                plugin_class.name,
            )
        default_settings = plugin_class.DEFAULT_SETTINGS.copy()
        if "$global" in default_settings:
            self.settings.update(default_settings["$global"])
            del default_settings["$global"]
        if "$mappings" in default_settings and isinstance(default_settings["$mappings"], dict):
            self.settings.update_mappings(default_settings["$mappings"])
            del default_settings["$mappings"]
        self.settings.set(
            f"plugins.{ plugin_type }.{ plugin_class.name }",
            default_settings,
        )
        return self

    def unregister(
        self,
        plugin_type: AgentlyPluginType,
        plugin_class: type[AgentlyPlugin] | str,
    ):
        _messenger = create_messenger("PluginManager")
        if plugin_type not in self.plugins:
            _messenger.error(ValueError(f"Plugin type '{ plugin_type }' is not in plugin information."), meta={})
        if isinstance(plugin_class, str):
            if plugin_class not in self.plugins[plugin_type]:
                _messenger.error(ValueError(f"Plugin class '{ plugin_class }' is not in plugin information."))
            plugin_class_name = plugin_class
            plugin_class = cast(type[AgentlyPlugin], self.plugins[plugin_type][plugin_class_name])
        else:
            if plugin_class.name not in self.plugins[plugin_type]:
                _messenger.error(ValueError(f"Plugin class '{ plugin_class.name }' is not in plugin information."))
            plugin_class_name = plugin_class.name
            plugin_class = cast(type[AgentlyPlugin], plugin_class)

        if hasattr(plugin_class, "_on_unregister"):
            plugin_class._on_unregister()
        del self.plugins[plugin_type][plugin_class_name]

    def get_plugin(self, plugin_type: AgentlyPluginType, plugin_name: str) -> AgentlyPlugin:
        return self.plugins[plugin_type][plugin_name]

    @overload
    def get_plugin_list(self, plugin_type: AgentlyPluginType) -> list[str]: ...

    @overload
    def get_plugin_list(self) -> dict[str, list[str]]: ...

    def get_plugin_list(self, plugin_type: AgentlyPluginType | None = None):
        if plugin_type is not None:
            return list(cast(dict[str, Any], self.plugins[plugin_type]).keys())
        else:
            result: dict[str, list[str]] = {}
            for plugin_type, plugins in self.plugins.items():
                result.update({str(plugin_type): list(plugins.keys())})
            return result
