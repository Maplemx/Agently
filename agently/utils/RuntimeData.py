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

import datetime
from copy import deepcopy
from typing import Any, Literal, Sequence, Mapping, cast, Iterator, TypeVar
from pathlib import Path

import json
import yaml
import toml

from agently.types.data import SerializableValue
from .DataFormatter import DataFormatter

T = TypeVar("T")


class DictRef:
    def __init__(self, container: dict[Any, Any], key: Any = None):
        self.container = container
        self.key = key

    def get(self) -> Any:
        if self.key is not None:
            return self.container[self.key]
        return self.container

    def set(self, value: Any):
        if self.key is not None:
            self.container[self.key] = value
        else:
            if isinstance(self.container, dict) and isinstance(value, dict):
                self.container.clear()
                self.container.update(value)
            else:
                raise TypeError("Setting root container to non-dict is not supported.")

    def update(self, new: dict[Any, Any]):
        ref = self.get()
        if isinstance(ref, dict):
            return ref.update(new)
        else:
            raise TypeError(f"Key '{ self.key }' from container { self.container } is not a dictionary.")

    def move_in(self, key: Any):
        return DictRef(self.get(), key)


class RuntimeData:
    instance_counter = 0

    def __init__(
        self,
        data: dict[Any, Any] | None = None,
        *,
        name: str | None = None,
        parent: "RuntimeData | None" = None,
    ):
        self._data = data if data is not None else {}
        if name is None:
            self.name = f"runtime_data_{ RuntimeData.instance_counter }"
            RuntimeData.instance_counter += 1
        else:
            self.name = name
        self.parent = parent

    def __repr__(self) -> str:
        return f"RuntimeData(name={ self.name }, data={ str(self.data) })"

    def __eq__(self, equal_target: Any) -> bool:
        return self.data == equal_target

    def __iter__(self) -> Iterator[Any]:
        """Make RuntimeData iterable like a standard dict"""
        return iter(self.data)

    def __len__(self) -> int:
        """Return the number of items in the RuntimeData"""
        return len(self.data)

    @property
    def data(self) -> dict[Any, Any]:
        return cast(dict[Any, Any], self.get(default={}))

    def _copy(self, origin: Any) -> Any:
        try:
            if isinstance(origin, dict):
                result = {}
                for key, value in origin.items():
                    result[key] = self._copy(value)
                return result
            if isinstance(origin, list):
                return [self._copy(item) for item in origin]
            if isinstance(origin, set):
                return {self._copy(item) for item in origin}
            if isinstance(origin, tuple):
                return tuple(self._copy(item) for item in origin)
            if hasattr(origin, "__class__") and hasattr(origin, "__module__") and origin.__module__ != "builtins":
                return origin
            return deepcopy(origin)
        except:
            return origin

    def _merge_view(self, child_data: dict[Any, Any], parent_data: dict[Any, Any]) -> dict[Any, Any]:
        result = self._copy(parent_data)
        for key, value in child_data.items():
            if key not in parent_data:
                result.update({key: self._copy(value)})
            elif isinstance(value, dict) and isinstance(parent_data[key], dict):
                result.update({key: self._merge_view(value, parent_data[key])})
            elif isinstance(value, list):
                if isinstance(parent_data[key], (list, set, tuple)):
                    for item in parent_data[key]:
                        if item not in value:
                            value.append(self._copy(item))
                elif parent_data[key] not in value:
                    value.append(self._copy(parent_data[key]))
                result.update({key: self._copy(value)})
            elif isinstance(value, set):
                if isinstance(parent_data[key], (list, set, tuple)):
                    for item in parent_data[key]:
                        if item not in value:
                            value.add(self._copy(item))
                else:
                    value.add(self._copy(parent_data[key]))
                result.update({key: self._copy(value)})
            else:
                result.update({key: self._copy(value)})
        return result

    def _get_inherited_view(self, runtime_data: "RuntimeData", result: dict[Any, Any] | None = None) -> dict[Any, Any]:
        if result is None:
            result = {}
        result = self._merge_view(result, runtime_data.get(default={}, inherit=False))
        if runtime_data.parent is not None:
            return self._get_inherited_view(runtime_data.parent, result)
        return result

    def _get_item_by_dot_path(self, dot_path: str, inherit: bool = True):
        current = self._get_inherited_view(self, {}) if inherit else self._copy(self._data)
        path_list = dot_path.split(".")
        for path in path_list:
            if path in current:
                current = current[path]
            else:
                return None
        return current

    def __getitem__(self, key: Any = None) -> Any:
        if isinstance(key, str) and "." in key:
            return self._get_item_by_dot_path(key)
        elif key is None:
            return self._data
        else:
            # Return None for missing keys, don't use data property to avoid inheritance
            return self.data.get(key)

    def get(
        self,
        key: Any | None = None,
        default: T = None,
        inherit: bool = True,
    ) -> Any | T:
        if key is None:
            if inherit:
                return self._get_inherited_view(self, {})
            else:
                return self._copy(self._data)

        # Handle key lookup
        if inherit:
            data = self.data
        else:
            data = self._data

        if isinstance(key, str) and "." in key:
            # Handle dot path
            current = data
            path_list = key.split(".")
            try:
                for path in path_list:
                    if isinstance(current, dict) and path in current:
                        current = current[path]
                    else:
                        return default
                return current
            except:
                return default
        else:
            # Handle simple key
            if isinstance(data, dict):
                # Use get with a sentinel to distinguish None values from missing keys
                sentinel = object()
                result = data.get(key, sentinel)
                if result is sentinel:
                    return default
                return result
            return default

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def pop(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, str) and "." in key:
            val = self.get(key, default=None, inherit=False)
            if val is None:
                return default
            del self[key]
            return val
        else:
            if key in self._data:
                return self._data.pop(key)
            return default

    def clear(self):
        return self._data.clear()

    def __contains__(self, key: Any) -> bool:
        return key in self.data

    def _set_item(self, ref: DictRef, value: Any):
        if isinstance(ref.get(), dict) and isinstance(value, Mapping):
            for key, item_value in value.items():
                if key not in ref.get():
                    ref.get()[key] = self._copy(item_value)
                else:
                    self._set_item(ref.move_in(key), item_value)
            return
        if isinstance(ref.get(), list):
            if not isinstance(value, str) and isinstance(value, Sequence):
                for item in value:
                    if item not in ref.get():
                        ref.get().append(self._copy(item))
            elif value not in ref.get():
                ref.get().append(self._copy(value))
            return
        if isinstance(ref.get(), set):
            current_set = ref.get()
            from collections.abc import Iterable

            if not isinstance(value, (str, bytes)) and isinstance(value, Iterable):
                for item in value:
                    if item not in current_set:
                        current_set.add(self._copy(item))
            else:
                if value not in current_set:
                    current_set.add(self._copy(value))
            return
        else:
            existing = ref.get()
            if existing is None:
                if isinstance(value, list):
                    ref.set([self._copy(item) for item in value])
                else:
                    ref.set(self._copy(value))
            elif isinstance(existing, list):
                if isinstance(value, list):
                    for item in value:
                        if item not in existing:
                            existing.append(self._copy(item))
                else:
                    if value not in existing:
                        existing.append(self._copy(value))
            else:
                ref.set(self._copy(value))

    def _set_item_by_dot_path(self, dot_path: str, value: Any, *, cover: bool = False):
        current = DictRef(self._data)
        path_list = dot_path.split(".")
        walked_path = ""
        for path in path_list:
            if not isinstance(current.get(), dict):
                raise TypeError(
                    f"Can not set value to path '{ dot_path }' "
                    + f"because '{ walked_path[:-1] }' is not a dictionary."
                )
            walked_path += f"{ path }."
            if path not in current.get():
                current.update({path: {}})
            current = current.move_in(path)
        if cover:
            current.set(self._copy(value))
        else:
            self._set_item(current, value)

    def __setitem__(self, key: Any, value: Any):
        if isinstance(key, str) and "." in key:
            return self._set_item_by_dot_path(key, value)
        else:
            # For direct key assignment, use the merge behavior
            if key in self._data:
                existing = self._data[key]
                ref = DictRef(self._data, key)
                self._set_item(ref, value)
            else:
                self._data[key] = self._copy(value)

    def set(self, key: Any, value: Any):
        return self.__setitem__(key, value)

    def setdefault(self, key: Any, value: Any, *, inherit: bool = True):
        if self.get(key, inherit=inherit) is None:
            self.set(key, value)
        return self.get(key, inherit=inherit)

    def update(self, new: dict[Any, Any]):
        for key, value in new.items():
            self.set(key, value)

    def load(
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
                        raise TypeError(f"[Agently RuntimeData] Can not load type: '{ data_type }'")
        else:
            match data_type:
                case "json":
                    data = json.loads(value)
                case "yaml":
                    data = yaml.safe_load(value)
                case "toml":
                    data = toml.loads(value)
        if data and isinstance(data, dict):
            self.update(data)
        else:
            raise TypeError(
                f"[Agently RuntimeData] Can not load parsed data, expect dictionary type, got: { type(data) }"
            )

    def _get_serializable_data(self, data: Any) -> SerializableValue:
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        elif isinstance(data, RuntimeData):
            return self._get_serializable_data(data.data)
        elif isinstance(data, Path):
            return str(data)
        elif isinstance(data, dict):
            return {str(k): self._get_serializable_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return [self._get_serializable_data(v) for v in data]
        elif hasattr(data, "__dict__") and vars(data) != {}:
            return self._get_serializable_data(vars(data))
        else:
            return str(data)

    def dump(self, data_type: Literal["json", "yaml", "toml"]) -> str:
        serializable_data = self._get_serializable_data(self.data)
        if not isinstance(serializable_data, dict):
            raise TypeError("Can not dump not-dictionary runtime data.")
        match data_type:
            case "json":
                return json.dumps(serializable_data)
            case "yaml":
                return yaml.safe_dump(serializable_data)
            case "toml":
                return toml.dumps(DataFormatter.to_str_key_dict(serializable_data, default_key="data"))

    def __delitem__(self, key: Any):
        if isinstance(key, str) and "." in key:
            path_list = key.split(".")
            current = DictRef(self._data)
            for path in path_list[:-1]:
                cur = current.get()
                if not isinstance(cur, dict):
                    return
                if path in cur:
                    current = current.move_in(path)
                else:
                    return
            last_key = path_list[-1]
            cur = current.get()
            if isinstance(cur, dict) and last_key in cur:
                del cur[last_key]
        else:
            if key in self._data:
                del self._data[key]

    def append(self, key: Any, value: Any):
        if isinstance(key, str) and "." in key:
            current = self._get_item_by_dot_path(key, inherit=False)
        else:
            current = self._data.get(key)

        if current is None:
            new_value = [self._copy(value)]
        elif isinstance(current, set):
            current = current.copy()  # Create a copy to avoid modifying original
            current.add(self._copy(value))
            self._set_item_by_dot_path(key, current, cover=True)
            return
        elif isinstance(current, list):
            new_value = current.copy()  # Create a copy to avoid modifying original
            new_value.append(self._copy(value))
        else:
            new_value = [current, self._copy(value)]

        if isinstance(key, str) and "." in key:
            self._set_item_by_dot_path(key, new_value, cover=True)
        else:
            self._data[key] = new_value

    def extend(self, key: Any, values: Sequence[Any]):
        if isinstance(key, str) and "." in key:
            current = self._get_item_by_dot_path(key, inherit=False)
        else:
            current = self._data.get(key)

        if current is None:
            new_value = [self._copy(item) for item in values]
        elif isinstance(current, list):
            new_value = current.copy()  # Create a copy to avoid modifying original
            new_value.extend([self._copy(item) for item in values])
        else:
            new_value = [current]
            new_value.extend([self._copy(item) for item in values])

        if isinstance(key, str) and "." in key:
            self._set_item_by_dot_path(key, new_value, cover=True)
        else:
            self._data[key] = new_value

    def delete(self, key: Any):
        self.__delitem__(key)

    def namespace(self, namespace_path: str):
        return RuntimeDataNamespace(self, namespace_path)


class RuntimeDataNamespace:
    def __init__(self, root_runtime_data: RuntimeData, namespace: str):
        self.root = root_runtime_data
        self.namespace = namespace

    def __repr__(self) -> str:
        return f"RuntimeDataNamespace(root=RuntimeData(name={ str(self.root.name) }), data={ str(self.data) })"

    def __eq__(self, equal_target: Any) -> bool:
        return self.data == equal_target

    def __iter__(self) -> Iterator[Any]:
        """Make namespace iterable"""
        data = self.data
        if isinstance(data, dict):
            return iter(data)
        return iter({})

    def __len__(self) -> int:
        """Return the number of items in the namespace"""
        data = self.data
        if isinstance(data, dict):
            return len(data)
        return 0

    @property
    def data(self) -> Any:
        return self.root.get(self.namespace)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and "." in key:
            return self.root.get(f"{ self.namespace }.{ key }")
        else:
            ns_data = self.data
            if isinstance(ns_data, dict):
                return ns_data.get(key)
            return None

    def get(
        self,
        key: Any | None = None,
        default: T = None,
        inherit: bool = True,
    ) -> Any | T:
        if inherit:
            if key is not None:
                result = self[key]
            else:
                result = self.data
        else:
            if key is not None:
                ns_data = self.root.get(self.namespace, inherit=False)
                if isinstance(ns_data, dict):
                    if isinstance(key, str) and "." in key:
                        # Handle dot path within namespace
                        current = ns_data
                        for path_part in key.split("."):
                            if isinstance(current, dict) and path_part in current:
                                current = current[path_part]
                            else:
                                return default
                        return current
                    else:
                        return ns_data.get(key)
                return None
            else:
                result = self.root.get(self.namespace, inherit=False)
        return result if result is not None else default

    def keys(self):
        ns = self.data
        if isinstance(ns, dict):
            return ns.keys()
        return {}.keys()

    def values(self):
        ns = self.data
        if isinstance(ns, dict):
            return ns.values()
        return {}.values()

    def items(self):
        ns = self.data
        if isinstance(ns, dict):
            return ns.items()
        return {}.items()

    def __setitem__(self, key: Any, value: Any):
        if isinstance(key, str) and "." in key:
            return self.root.set(f"{self.namespace}.{key}", value)
        else:
            # Ensure namespace exists
            if self.root.get(self.namespace, inherit=False) is None:
                self.root._data[self.namespace] = {}

            self.root.set(f"{self.namespace}.{key}", value)

    def __delitem__(self, key: Any):
        if isinstance(key, str) and "." in key:
            del self.root[f"{ self.namespace }.{ key }"]
        else:
            ns = self.root.get(self.namespace, inherit=False)
            if isinstance(ns, dict) and key in ns:
                del ns[key]
                self.root._data[self.namespace] = ns

    def pop(self, key: str, default: Any = None) -> Any:
        if isinstance(key, str) and "." in key:
            return self.root.pop(f"{ self.namespace }.{ key }", default)
        else:
            ns = self.root.get(self.namespace, inherit=False)
            if isinstance(ns, dict) and key in ns:
                val = ns.pop(key)
                self.root._data[self.namespace] = ns
                return val
            return default

    def clear(self):
        self.root._data[self.namespace] = {}

    def __contains__(self, key: Any) -> bool:
        return key in self.keys()

    def set(self, key: Any, value: Any):
        return self.__setitem__(key, value)

    def setdefault(self, key: Any, value: Any, *, inherit: bool = True):
        if self.get(key, inherit=inherit) is None:
            self.set(key, value)
        return self.get(key, inherit=inherit)

    def update(self, new: dict[Any, Any]):
        for key, value in new.items():
            self.set(key, value)

    def append(self, key: str, value: Any):
        full_key = f"{ self.namespace }.{ key }"
        self.root.append(full_key, value)

    def extend(self, key: str, values: Sequence[Any]):
        full_key = f"{ self.namespace }.{ key }"
        self.root.extend(full_key, values)

    def delete(self, key: Any):
        self.__delitem__(key)
