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

import json
import yaml
import toml
from typing import TYPE_CHECKING, Literal, cast
from agently.utils import SerializableRuntimeData, SerializableRuntimeDataNamespace

if TYPE_CHECKING:
    from agently.types.data import SerializableData, SerializableValue


class Settings(SerializableRuntimeData):

    def __init__(
        self,
        data: "SerializableData | None" = None,
        *,
        name: str | None = None,
        parent: "Settings | None" = None,
    ):
        super().__init__(
            data,
            name=name,
            parent=parent,
        )
        self._path_mappings = SerializableRuntimeData(parent=parent._path_mappings if parent is not None else None)
        self._kv_mappings = SerializableRuntimeData(parent=parent._kv_mappings if parent is not None else None)

    def register_path_mappings(self, simplify_path: str, actual_path: str):
        if simplify_path in self._kv_mappings:
            raise ValueError(
                f"Cannot register '{ simplify_path }' to path mappings, because it was registered in key-value mappings."
            )
        self._path_mappings.set(simplify_path, actual_path)
        return self

    def register_kv_mappings(
        self,
        simplify_path: str,
        simplify_value: str | int | float | bool,
        actual_settings: "SerializableData",
    ):
        if simplify_path in self._path_mappings:
            raise ValueError(
                f"Cannot register '{ simplify_path }' to key-value mappings, because it was registered in path mappings."
            )
        self._kv_mappings.set(
            f"{ simplify_path }.{ simplify_value }",
            actual_settings,
        )
        return self

    def update_mappings(self, mappings_dict: dict):
        if "path_mappings" in mappings_dict and isinstance(mappings_dict["path_mappings"], dict):
            self._path_mappings.update(mappings_dict["path_mappings"])
        if "key_value_mappings" in mappings_dict and isinstance(mappings_dict["key_value_mappings"], dict):
            for key, value_actual_settings in mappings_dict["key_value_mappings"].items():
                for value, actual_settings in value_actual_settings.items():
                    if isinstance(actual_settings, dict):
                        self._kv_mappings.set(f"{ key }.{ value }", actual_settings)
        if "kv_mappings" in mappings_dict and isinstance(mappings_dict["kv_mappings"], dict):
            for key, value_actual_settings in mappings_dict["kv_mappings"].items():
                for value, actual_settings in value_actual_settings.items():
                    if isinstance(actual_settings, dict):
                        self._kv_mappings.set(f"{ key }.{ value }", actual_settings)

    def load_mappings(
        self,
        data_type: Literal[
            "json_file",
            "yaml_file",
            "toml_file",
            "json",
            "yaml",
            "toml",
        ],
        value: str,
    ):
        data = None
        if data_type.endswith("_file"):
            with open(value, "r", encoding="utf-8") as file:
                match data_type:
                    case "json_file":
                        data = json.load(file)
                    case "yaml_file":
                        data = yaml.safe_load(file)
                    case "toml_file":
                        data = toml.load(file)
                    case _:
                        raise TypeError(f"[Agently Settings] Cannot load type: '{ type }'")
        else:
            match data_type:
                case "json":
                    data = json.loads(value)
                case "yaml":
                    data = yaml.safe_load(value)
                case "toml":
                    data = toml.loads(value)
        if data and isinstance(data, dict):
            self.update_mappings(data)
        else:
            raise TypeError(f"[Agently Settings] Cannot load parsed data, expect dictionary type, got: { type(data) }")

    def set_settings(self, key: str, value: "SerializableValue"):
        if key in self._path_mappings:
            self.update({str(self._path_mappings[key]): value})
            return self
        elif key in self._kv_mappings:
            actual_settings = self._kv_mappings.get(f"{ key }.{ value }")
            if actual_settings:
                self.update(cast("SerializableData", actual_settings))
                return self
        self.set(key, value)
        return self


class SettingsNamespace(SerializableRuntimeDataNamespace):
    def __init__(self, root_settings: "Settings", namespace: str):
        super().__init__(root_runtime_data=root_settings, namespace=namespace)
