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

import re
import json5
from typing import Literal, Any, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.data import SerializableData


class DataLocator:
    @staticmethod
    def locate_path_in_dict(
        original_dict: dict,
        path: str,
        style: Literal["dot", "slash"] = "dot",
        *,
        default: Any = None,
    ):
        if path == "" or not isinstance(path, str):
            return original_dict
        match style:
            case "dot":
                try:
                    result = original_dict
                    path_parts = path.split(".")
                    for path_part in path_parts:
                        if "[" in path_part:
                            path_key_and_index = path_part.split("[")
                            path_key = path_key_and_index[0]
                            path_index = int(path_key_and_index[1][:-1])
                            if isinstance(result, Mapping):
                                result = result[path_key]
                            else:
                                return default
                            if not isinstance(result, str) and isinstance(result, Sequence):
                                result = result[path_index]
                            else:
                                return default
                        else:
                            if isinstance(result, Mapping):
                                result = result[path_part]
                            else:
                                return default
                    return result
                except Exception:
                    return default
            case "slash":
                result = original_dict
                path_parts = path.split("/")
                try:
                    for path_part in path_parts:
                        if path_part:
                            if isinstance(result, Mapping):
                                result = result[path_part]
                            elif not isinstance(result, str) and isinstance(result, Sequence):
                                result = result[int(path_part)]
                            else:
                                return default
                    return result
                except Exception:
                    return default

    @staticmethod
    def locate_all_json(original_text: str) -> list[str]:
        pattern = r'"""(.*?)"""'
        original_text = re.sub(pattern, lambda match: json5.dumps(match.group(1)), original_text, flags=re.DOTALL)
        original_text = original_text.replace("\"\"\"", "\"").replace("[OUTPUT]", "$<<OUTPUT>>")
        stage = 1
        json_blocks = []
        block_num = 0
        layer = 0
        skip_next = False
        in_quote = False
        for index, char in enumerate(original_text):
            if skip_next:
                skip_next = False
                continue
            if stage == 1:
                if char == "\\":
                    skip_next = True
                    continue
                if char == "[" or char == "{":
                    json_blocks.append(char)
                    stage = 2
                    layer += 1
                    continue
            elif stage == 2:
                if not in_quote:
                    if char == "\\":
                        skip_next = True
                        if original_text[index + 1] == "\"":
                            char = "\""
                        else:
                            continue
                    if char == "\"":
                        in_quote = True
                    if char == "[" or char == "{":
                        layer += 1
                    elif char == "]" or char == "}":
                        layer -= 1
                    # elif char in ("\t", " ", "\n"):
                    # char = ""
                    json_blocks[block_num] += char
                else:
                    if char == "\\":
                        char += original_text[index + 1]
                        skip_next = True
                    elif char == "\n":
                        char = "\\n"
                    elif char == "\t":
                        char = "\\t"
                    elif char == "\"":
                        in_quote = not in_quote
                    json_blocks[block_num] += char
                if layer == 0:
                    json_blocks[block_num] = json_blocks[block_num].replace("$<<OUTPUT>>", "[OUTPUT]")
                    block_num += 1
                    stage = 1
        return json_blocks

    @staticmethod
    def locate_output_json(original_text: str, output_prompt_dict: "SerializableData"):
        all_json = DataLocator.locate_all_json(original_text)
        if len(all_json) == 0:
            return None
        if len(all_json) == 1:
            return all_json[0]
        else:
            for index, json_string in enumerate(all_json):
                if index + 1 == len(all_json):
                    break
                try:
                    temp = json5.loads(json_string)
                    if isinstance(temp, dict):
                        for key in temp.keys():
                            if key in output_prompt_dict:
                                return json_string
                except:
                    continue
            return all_json[-1]
