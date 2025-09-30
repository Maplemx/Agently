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


import yaml
import json5
from pathlib import Path

from typing import Any
from json import JSONDecodeError

from agently.core import BaseAgent


class ConfigurePromptExtension(BaseAgent):
    def _execute_prompt_configure(self, prompt: dict[str, Any]):
        for prompt_key, prompt_value in prompt.items():
            match prompt_key:
                case ".agent":
                    if isinstance(prompt_value, dict):
                        for agent_prompt_key, agent_prompt_value in prompt_value.items():
                            self.set_agent_prompt(agent_prompt_key, agent_prompt_value)
                    else:
                        self.set_agent_prompt("system", prompt_value)
                case ".request":
                    if isinstance(prompt_value, dict):
                        for request_prompt_key, request_prompt_value in prompt_value.items():
                            self.set_request_prompt(request_prompt_key, request_prompt_value)
                    else:
                        self.set_request_prompt("input", prompt_value)
                case ".alias":
                    if isinstance(prompt_value, dict):
                        for alias_name, alias_parameters in prompt_value.items():
                            if hasattr(self, alias_name) and callable(getattr(self, alias_name)):
                                if isinstance(alias_parameters, dict):
                                    args = []
                                    kwargs = {}

                                    for parameter_name, parameter_value in alias_parameters.items():
                                        if parameter_name == ".args":
                                            if isinstance(parameter_value, list):
                                                args = parameter_value
                                            else:
                                                raise TypeError(
                                                    f"Cannot execute prompt alias configures, expect value of key '.args' of '{ alias_name }' as a list"
                                                    "But received:"
                                                    f"{ parameter_value }"
                                                )
                                        else:
                                            kwargs[parameter_name] = parameter_value

                                    getattr(self, alias_name)(*args, **kwargs)
                                elif alias_parameters is None:
                                    getattr(self, alias_name)()
                                else:
                                    raise ValueError(
                                        "Cannot execute prompt alias configures, expect data structure like:"
                                        f"{{ '{ alias_name }':"
                                        "  { '<alias_parameter_name> | *args': '<alias_parameter_value>',"
                                        "    ..."
                                        "  }"
                                        "}"
                                        "But received:"
                                        f"{ prompt_value }"
                                    )
                    else:
                        raise ValueError(
                            "Cannot execute prompt alias configures, expect data structure like:"
                            "{ '<alias_name>':"
                            "  { '<alias_parameter_name> | *args': '<alias_parameter_value>',"
                            "    ..."
                            "  }"
                            "}"
                            "But received:"
                            f"{ prompt_value }"
                        )
                case _:
                    if prompt_key.startswith("$"):
                        self.set_agent_prompt(prompt_key[1:], prompt_value)
                    else:
                        self.set_request_prompt(prompt_key, prompt_value)

    def load_yaml_prompt(self, path_or_content: str):
        path = Path(path_or_content)
        if path.exists() and path.is_file():
            try:
                with path.open("r", encoding="utf-8") as file:
                    prompt = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise ValueError(f"Cannot load YAML file '{ path_or_content }'.\nError: { e }")
        else:
            try:
                prompt = yaml.safe_load(path_or_content)
            except yaml.YAMLError as e:
                raise ValueError(f"Cannot load YAML content or file path not existed.\nError: { e }")
        if isinstance(prompt, dict):
            self._execute_prompt_configure(prompt)
        else:
            raise TypeError(
                "Cannot execute YAML prompt configures, expect prompt configures as a dictionary data but got:"
                f"{ prompt }"
            )

    def load_json_prompt(self, path_or_content: str):
        path = Path(path_or_content)
        if path.exists() and path.is_file():
            try:
                with path.open("r", encoding="utf-8") as file:
                    prompt = json5.load(file)
            except JSONDecodeError as e:
                raise ValueError(f"Cannot load JSON file '{ path_or_content }'.\nError: { e }")
        else:
            try:
                prompt = json5.loads(path_or_content)
            except yaml.YAMLError as e:
                raise ValueError(f"Cannot load JSON content or file path not existed.\nError: { e }")
        if isinstance(prompt, dict):
            self._execute_prompt_configure(prompt)
        else:
            raise TypeError(
                "Cannot execute JSON prompt configures, expect prompt configures as a dictionary data but got:"
                f"{ prompt }"
            )
