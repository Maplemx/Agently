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

from typing import TypeVar

from agently.utils import RuntimeData, RuntimeDataNamespace
from agently.types.data import SerializableData, SerializableValue

T = TypeVar("T")


class SerializableRuntimeData(RuntimeData):
    def __init__(
        self,
        data: SerializableData | None = None,
        *,
        name: str | None = None,
        parent: "SerializableRuntimeData | None" = None,
    ):
        super().__init__(dict(data) if data is not None else None, name=name, parent=parent)

    @property
    def data(self) -> SerializableValue:  # type: ignore
        data = self.get()
        data = data if data is not None else {}
        return data

    def __getitem__(self, key: str | None = None) -> SerializableValue:
        return super().__getitem__(key)

    def get(
        self,
        key: str | None = None,
        default: T = None,
        inherit: bool = True,
    ) -> SerializableValue | T:
        return super().get(key, default, inherit)

    def pop(self, key: str, default: SerializableValue = None) -> SerializableValue:
        return super().pop(key, default)

    def __contains__(self, key: str) -> bool:
        return super().__contains__(key)

    def __setitem__(self, key: str, value: SerializableValue):
        super().__setitem__(key, value)

    def set(self, key: str, value: SerializableValue):
        super().set(key, value)

    def update(self, new: SerializableData):
        super().update(dict(new))

    def __delitem__(self, key: str):
        super().__delitem__(key)


class SerializableRuntimeDataNamespace(RuntimeDataNamespace):
    def __init__(self, root_runtime_data: SerializableRuntimeData, namespace: str):
        super().__init__(root_runtime_data, namespace)

    @property
    def data(self) -> SerializableValue:
        return self.root.get(self.namespace)

    def __getitem__(self, key: str) -> SerializableValue:
        return super().__getitem__(key)

    def get(
        self,
        key: str | None = None,
        default: T = None,
        inherit: bool = True,
    ) -> SerializableValue | T:
        return super().get(key, default, inherit)

    def pop(self, key: str, default: SerializableValue = None) -> SerializableValue:
        return super().get(key, default)

    def __contains__(self, key: str) -> bool:
        return super().__contains__(key)

    def __setitem__(self, key: str, value: SerializableValue):
        return super().__setitem__(key, value)

    def set(self, key: str, value: SerializableValue):
        return super().set(key, value)

    def update(self, new: SerializableData):
        return super().update(dict(new))

    def __delitem__(self, key: str):
        return super().__delitem__(key)
