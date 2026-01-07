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


from types import MappingProxyType
from typing import Any

SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "print": print,
    "sorted": sorted,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "bool": bool,
}

SAFE_TYPES = [int, float, str, list, dict, set, tuple, bool, type(None)]


class PythonSandbox:
    def __init__(
        self,
        preset_objects: dict[str, object] | None = None,
        base_vars: dict[str, Any] | None = None,
        allowed_return_types: list[type] = SAFE_TYPES,
    ):
        self.preset_objects = preset_objects or {}
        self.base_vars = base_vars or {}
        self.allowed_return_types = allowed_return_types

        self.safe_globals = MappingProxyType(
            {
                "__builtins__": SAFE_BUILTINS,
                **self.preset_objects,
                **self.base_vars,
            }
        )

    def _check_safe_value(self, value):
        if isinstance(value, tuple(self.allowed_return_types)):
            return value
        raise ValueError(f"Type of return '{ type(value) }' can not be used in Python Sandbox.")

    def _wrap_obj(self, obj):
        sandbox = self

        class ObjectWrapper:
            def __init__(self, obj):
                self._obj = obj

            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError(f"Can not access private attribute '{name}'.")
                attr = getattr(self._obj, name)
                if callable(attr):

                    def method(*args, **kwargs):
                        result = attr(*args, **kwargs)
                        return sandbox._check_safe_value(result)

                    return method
                return sandbox._check_safe_value(attr)

        self.allowed_return_types.append(ObjectWrapper)

        return ObjectWrapper(obj)

    def run(self, code: str):
        safe_objects = {k: self._wrap_obj(v) for k, v in self.preset_objects.items()}
        globals_dict = dict(self.safe_globals)
        globals_dict.update(safe_objects)

        local_vars = {}
        exec(code, globals_dict, local_vars)
        for k, v in local_vars.items():
            self._check_safe_value(v)
        return local_vars
