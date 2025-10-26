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
    def _generate_output_value(self, output_prompt_value: Any):
        if isinstance(output_prompt_value, dict):
            output_type = None
            output_desc = None
            if "$type" in output_prompt_value:
                output_type = output_prompt_value["$type"]
            if ".type" in output_prompt_value:
                output_type = output_prompt_value[".type"]
            if "$desc" in output_prompt_value:
                output_desc = output_prompt_value["$desc"]
            if ".desc" in output_prompt_value:
                output_desc = output_prompt_value[".desc"]
            if output_type or output_desc:
                return (
                    self._generate_output_value(output_type) if output_type is not None else Any,
                    output_desc,
                )
            else:
                return {key: self._generate_output_value(value) for key, value in output_prompt_value.items()}
        elif isinstance(output_prompt_value, list):
            return [self._generate_output_value(item) for item in output_prompt_value]
        else:
            return output_prompt_value

    def _execute_prompt_configure(self, prompt: dict[str, Any], variable_mappings: dict[str, Any] | None):
        for prompt_key, prompt_value in prompt.items():
            match prompt_key:
                case ".agent":
                    if isinstance(prompt_value, dict):
                        for agent_prompt_key, agent_prompt_value in prompt_value.items():
                            if agent_prompt_key != "output":
                                self.set_agent_prompt(
                                    agent_prompt_key,
                                    agent_prompt_value,
                                    variable_mappings,
                                )
                            else:
                                self.set_agent_prompt(
                                    agent_prompt_key,
                                    self._generate_output_value(agent_prompt_value),
                                    variable_mappings,
                                )
                    else:
                        self.set_agent_prompt(
                            "system",
                            prompt_value,
                            variable_mappings,
                        )
                case ".request":
                    if isinstance(prompt_value, dict):
                        for request_prompt_key, request_prompt_value in prompt_value.items():
                            if request_prompt_key != "output":
                                self.set_request_prompt(
                                    request_prompt_key,
                                    request_prompt_value,
                                    variable_mappings,
                                )
                            else:
                                self.set_request_prompt(
                                    request_prompt_key,
                                    self._generate_output_value(request_prompt_value),
                                    variable_mappings,
                                )
                    else:
                        self.set_request_prompt(
                            "input",
                            prompt_value,
                            variable_mappings,
                        )
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
                    if prompt_key.startswith("$") and not prompt_key.startswith("${"):
                        prompt_key = prompt_key[1:]
                        if prompt_key != "output":
                            self.set_agent_prompt(
                                prompt_key,
                                prompt_value,
                                variable_mappings,
                            )
                        else:
                            self.set_agent_prompt(
                                prompt_key,
                                self._generate_output_value(prompt_value),
                                variable_mappings,
                            )
                    else:
                        if prompt_key != "output":
                            self.set_request_prompt(
                                prompt_key,
                                prompt_value,
                                variable_mappings,
                            )
                        else:
                            self.set_request_prompt(
                                prompt_key,
                                self._generate_output_value(prompt_value),
                                variable_mappings,
                            )

    def load_yaml_prompt(self, path_or_content: str, mappings: dict[str, Any] | None = None):
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
            self._execute_prompt_configure(prompt, mappings)
        else:
            raise TypeError(
                "Cannot execute YAML prompt configures, expect prompt configures as a dictionary data but got:"
                f"{ prompt }"
            )

    def load_json_prompt(self, path_or_content: str, mappings: dict[str, Any] | None = None):
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
            self._execute_prompt_configure(prompt, mappings)
        else:
            raise TypeError(
                "Cannot execute JSON prompt configures, expect prompt configures as a dictionary data but got:"
                f"{ prompt }"
            )
