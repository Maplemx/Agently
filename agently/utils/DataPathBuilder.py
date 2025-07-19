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

from typing import Any, Literal, get_origin, get_args
from collections import OrderedDict


class DataPathBuilder:
    @staticmethod
    def build_dot_path(keys: list[str | int]) -> str:
        if not keys:
            return ""

        parts = []
        for i, key in enumerate(keys):
            if isinstance(key, int):
                parts.append(f"[{ key }]")
            elif str(key) in ("*", "[]", "[*]"):
                parts.append("[*]")
            else:
                if i == 0:
                    parts.append(str(key))
                else:
                    parts.append(f".{key}")
        return "".join(parts)

    @staticmethod
    def build_slash_path(keys: list[str | int]) -> str:
        if not keys:
            return ""

        parts = ["/"]
        for key in keys:
            parts.append(str(key))
            parts.append("/")
        return "".join(parts[:-1])

    @staticmethod
    def convert_dot_to_slash(dot_path: str) -> str:
        """
        Convert dot-style path to slash-style path.
        Example: 'user.name' -> '/user/name', 'tasks[*].id' -> '/tasks/[*]/id'
        """
        if not dot_path:
            return "/"

        parts = []
        buffer = ""
        i = 0
        while i < len(dot_path):
            if dot_path[i] == "[":
                if buffer:
                    parts.append(buffer)
                    buffer = ""
                end = dot_path.find("]", i)
                parts.append(dot_path[i : end + 1])
                i = end + 1
            elif dot_path[i] == ".":
                if buffer:
                    parts.append(buffer)
                    buffer = ""
                i += 1
            else:
                buffer += dot_path[i]
                i += 1
        if buffer:
            parts.append(buffer)

        return "/" + "/".join(parts)

    @staticmethod
    def convert_slash_to_dot(slash_path: str) -> str:
        """
        Convert slash-style path to dot-style path.
        Example: '/user/name' -> 'user.name', '/tasks/[*]/id' -> 'tasks[*].id'
        """
        if not slash_path or slash_path == "/":
            return ""

        parts = slash_path.strip("/").split("/")
        dot_parts = []
        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                dot_parts.append(part)
            elif not dot_parts:
                dot_parts.append(part)
            else:
                dot_parts.append(f".{part}")

        return "".join(dot_parts)

    @staticmethod
    def extract_possible_paths(agently_output_dict: dict[str, Any], *, style: Literal["dot", "slash"] = "dot"):
        """
        Extract Agently style output dictionary to find all possible paths from model structured response.
        """
        if not isinstance(agently_output_dict, dict):
            raise TypeError("extract_all_paths expects a dict[str, Any] as input")
        all_paths: set[str] = set()

        def extract_paths(value: Any, path_keys: list[str | int]):
            current_path = (
                DataPathBuilder.build_dot_path(path_keys)
                if style == "dot"
                else DataPathBuilder.build_slash_path(path_keys)
            )
            all_paths.add(current_path)

            if isinstance(value, tuple) and value:
                extract_paths(value[0], path_keys)
                return

            if isinstance(value, dict):
                for k, v in value.items():
                    extract_paths(v, path_keys + [k])
                return

            origin = get_origin(value)
            if origin is list:
                args = get_args(value)
                if args:
                    extract_paths(args[0], path_keys + ["[*]"])
                return

            if isinstance(value, list):
                for idx, item in enumerate(value):
                    extract_paths(item, path_keys + ["[*]"])
                return

        extract_paths(agently_output_dict, [])
        return all_paths

    @staticmethod
    def extract_parsing_key_orders(
        agently_output_dict: dict[str, Any], *, style: Literal["dot", "slash"] = "dot"
    ) -> list[str]:
        """
        Traverse the schema in recursive order and return a list of paths preserving the field definition order.
        """
        ordered_paths: OrderedDict[str, None] = OrderedDict()

        def traverse(value: Any, path_keys: list[str | int]):
            if isinstance(value, tuple) and value:
                traverse(value[0], path_keys)
                current_path = (
                    DataPathBuilder.build_dot_path(path_keys)
                    if style == "dot"
                    else DataPathBuilder.build_slash_path(path_keys)
                )
                ordered_paths[current_path] = None
                return

            if isinstance(value, dict):
                for k, v in value.items():
                    traverse(v, path_keys + [k])
                current_path = (
                    DataPathBuilder.build_dot_path(path_keys)
                    if style == "dot"
                    else DataPathBuilder.build_slash_path(path_keys)
                )
                ordered_paths[current_path] = None
                return

            origin = get_origin(value)
            if origin is list:
                args = get_args(value)
                if args:
                    traverse(args[0], path_keys + ["[*]"])
                current_path = (
                    DataPathBuilder.build_dot_path(path_keys)
                    if style == "dot"
                    else DataPathBuilder.build_slash_path(path_keys)
                )
                ordered_paths[current_path] = None
                return

            if isinstance(value, list):
                for item in value:
                    traverse(item, path_keys + ["[*]"])
                current_path = (
                    DataPathBuilder.build_dot_path(path_keys)
                    if style == "dot"
                    else DataPathBuilder.build_slash_path(path_keys)
                )
                ordered_paths[current_path] = None
                return

            current_path = (
                DataPathBuilder.build_dot_path(path_keys)
                if style == "dot"
                else DataPathBuilder.build_slash_path(path_keys)
            )
            ordered_paths[current_path] = None

        traverse(agently_output_dict, [])
        return list(ordered_paths.keys())
