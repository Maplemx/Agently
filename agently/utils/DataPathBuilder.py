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

from typing import Mapping, Sequence, Any, Literal, get_origin, get_args
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

    @staticmethod
    def get_value_by_path(
        data: Mapping[str, Any] | Sequence[Any], path: str, *, style: Literal["dot", "slash"] = "dot"
    ) -> Any:
        """
        Retrieve the value from a dictionary based on the given path.
        If the path does not exist, return None.

        :param data: The dictionary to search.
        :param path: The path to the desired value (dot or slash style).
        :param style: The style of the path, either "dot" or "slash".
        :return: The value at the specified path, or None if not found.
        """
        if not isinstance(data, dict):
            raise TypeError("The data parameter must be a dictionary.")

        if not path:
            return None

        keys = []
        if style == "dot":
            buffer = ""
            i = 0
            while i < len(path):
                if path[i] == "[":
                    if buffer:
                        keys.append(buffer)
                        buffer = ""
                    end = path.find("]", i)
                    keys.append(path[i + 1 : end])  # Keep as string to handle [*]
                    i = end + 1
                elif path[i] == ".":
                    if buffer:
                        keys.append(buffer)
                        buffer = ""
                    i += 1
                else:
                    buffer += path[i]
                    i += 1
            if buffer:
                keys.append(buffer)
        elif style == "slash":
            keys: list[Any] = path.strip("/").split("/")
            for i, key in enumerate(keys):
                if key.isdigit():
                    keys[i] = int(key)

        def resolve(current: Any, remaining_keys: list[Any]) -> Any:
            if not remaining_keys:
                return current

            key = remaining_keys[0]
            if key == "[*]":
                if isinstance(current, Sequence) and not isinstance(current, str):
                    results = []
                    for item in current:
                        result = resolve(item, remaining_keys[1:])
                        if isinstance(result, list):
                            results.extend(result)
                        elif result is not None:
                            results.append(result)
                    return results
                else:
                    return None
            elif isinstance(current, Mapping) and key in current:
                return resolve(current[key], remaining_keys[1:])
            elif (
                not isinstance(current, str)
                and isinstance(current, Sequence)
                and isinstance(key, int)
                and 0 <= key < len(current)
            ):
                return resolve(current[key], remaining_keys[1:])
            else:
                return None

        return resolve(data, keys)
