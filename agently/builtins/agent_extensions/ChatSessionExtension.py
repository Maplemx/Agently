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


import uuid
import yaml

from typing import Any, Literal, TYPE_CHECKING, cast

from agently.core import BaseAgent
from agently.types.data import ChatMessage
from agently.utils import RuntimeData, DataPathBuilder

if TYPE_CHECKING:
    from agently.types.data import ChatMessage, AgentlyModelResult, PromptStandardSlot
    from agently.core import Prompt
    from agently.core.ModelRequest import ModelResponseResult
    from agently.utils import Settings


class ChatSessionExtension(BaseAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._activated_chat_session = None
        self.settings.setdefault("record_input_paths", [], inherit=True)
        self.settings.setdefault("record_input_mode", "all", inherit=True)
        self.settings.setdefault("record_output_paths", [], inherit=True)
        self.settings.setdefault("record_output_mode", "all", inherit=True)
        self.chat_session_runtime = RuntimeData()

        self.extension_handlers.append("finally", self.__finally)

    def activate_chat_session(self, chat_session_id: str | None = None):
        if chat_session_id is None:
            chat_session_id = uuid.uuid4().hex
        self._activated_chat_session = chat_session_id
        chat_history = self.chat_session_runtime.get(chat_session_id, [])
        self.set_chat_history(chat_history)
        return chat_session_id

    def stop_chat_session(self):
        self._activated_chat_session = None
        self.set_chat_history([])
        return self

    def set_record_input_paths(
        self,
        *prompt_keys_and_paths: "PromptStandardSlot | tuple[PromptStandardSlot, str | None]",
        style: Literal["dot", "slash"] = "dot",
    ):
        record_input_paths = []
        for prompt_key_and_path in prompt_keys_and_paths:
            if isinstance(prompt_key_and_path, str):
                path = (prompt_key_and_path, None)
            else:
                if style == "slash":
                    path = (
                        prompt_key_and_path[0],
                        (
                            DataPathBuilder.convert_slash_to_dot(prompt_key_and_path[1])
                            if prompt_key_and_path[1] is not None
                            else None
                        ),
                    )
                else:
                    path = prompt_key_and_path
            if path not in record_input_paths:
                record_input_paths.append(path)
        self.settings.set("record_input_paths", record_input_paths)
        return self

    def add_record_input_paths(
        self,
        *prompt_keys_and_paths: "PromptStandardSlot | tuple[PromptStandardSlot, str | None]",
        style: Literal["dot", "slash"] = "dot",
    ):
        record_input_paths = self.settings.get("record_input_paths", [])
        assert isinstance(record_input_paths, list)
        for prompt_key_and_path in prompt_keys_and_paths:
            if isinstance(prompt_key_and_path, str):
                path = (prompt_key_and_path, None)
            else:
                if style == "slash":
                    path = (
                        prompt_key_and_path[0],
                        (
                            DataPathBuilder.convert_slash_to_dot(prompt_key_and_path[1])
                            if prompt_key_and_path[1] is not None
                            else None
                        ),
                    )
                else:
                    path = prompt_key_and_path
            if path not in record_input_paths:
                record_input_paths.append(path)
        self.settings.set("record_input_paths", record_input_paths)
        return self

    def add_record_input_path(
        self,
        prompt_key: "PromptStandardSlot",
        path: str | None = None,
        *,
        style: Literal["dot", "slash"] = "dot",
    ):
        record_input_paths = self.settings.get("record_input_paths", [])
        assert isinstance(record_input_paths, list)
        if path is not None and style == "slash":
            path = DataPathBuilder.convert_slash_to_dot(path)
        if (prompt_key, path) not in record_input_paths:
            record_input_paths.append((prompt_key, path))
        self.settings.set("record_input_paths", record_input_paths)
        return self

    def get_record_input_paths(self, *, style: Literal["dot", "slash"] = "dot"):
        if style == "dot":
            return self.settings.get("record_input_paths")
        else:
            result = []
            record_input_paths = self.settings.get("record_input_paths", [])
            if isinstance(record_input_paths, list):
                for path in record_input_paths:
                    if isinstance(path, str):
                        result.append(DataPathBuilder.convert_dot_to_slash(path))
            return result

    def clean_record_input_paths(self):
        self.settings.set("record_input_paths", [])
        return self

    def set_record_output_paths(
        self,
        *paths: str,
        style: Literal["dot", "slash"] = "dot",
    ):
        record_output_paths = []
        for path in paths:
            if style == "slash":
                path = DataPathBuilder.convert_slash_to_dot(path)
            if path not in record_output_paths:
                record_output_paths.append(path)
        self.settings.set("record_output_paths", record_output_paths)
        return self

    def add_record_output_paths(
        self,
        *paths: str,
        style: Literal["dot", "slash"] = "dot",
    ):
        record_output_paths = self.settings.get("record_output_paths", [])
        assert isinstance(record_output_paths, list)
        for path in paths:
            if style == "slash":
                path = DataPathBuilder.convert_slash_to_dot(path)
            if path not in record_output_paths:
                record_output_paths.append(path)
        self.settings.set("record_output_paths", record_output_paths)
        return self

    def add_record_output_path(
        self,
        path: str,
        *,
        style: Literal["dot", "slash"] = "dot",
    ):
        record_output_paths = self.settings.get("record_output_paths", [])
        assert isinstance(record_output_paths, list)
        if style == "slash":
            path = DataPathBuilder.convert_slash_to_dot(path)
        if path not in record_output_paths:
            record_output_paths.append(path)
        self.settings.set("record_output_paths", record_output_paths)
        return self

    def clean_record_output_paths(self):
        self.settings.set("record_output_paths", [])
        return self

    def get_record_output_paths(self, *, style: Literal["dot", "slash"] = "dot"):
        if style == "dot":
            return self.settings.get("record_output_paths")
        else:
            result = []
            record_output_paths = self.settings.get("record_output_paths", [])
            if isinstance(record_output_paths, list):
                for path in record_output_paths:
                    if isinstance(path, str):
                        result.append(DataPathBuilder.convert_dot_to_slash(path))
            return result

    def set_record_input_mode(self, mode: Literal["first", "all"]):
        self._record_input_mode = mode
        return self

    def set_record_output_mode(self, mode: Literal["first", "all"]):
        self._record_output_mode = mode
        return self

    def add_chat_history(self, chat_history: list[dict[str, Any] | ChatMessage] | dict[str, Any] | ChatMessage):
        super().add_chat_history(chat_history)
        if self._activated_chat_session is not None:
            self.chat_session_runtime.set(self._activated_chat_session, self.prompt.get("chat_history"))
        return self

    async def __finally(self, result: "ModelResponseResult", settings: "Settings"):
        # Find user chat content to record
        record_input_paths = settings.get("record_input_paths")
        record_input_mode = settings.get("record_input_mode")
        if isinstance(record_input_paths, str):
            record_input_paths = [record_input_paths]
        if not isinstance(record_input_paths, list) or len(record_input_paths) == 0:
            self.add_chat_history({"role": "user", "content": result.prompt.to_messages()[-1]["content"]})
        else:
            record_input_paths = cast(
                "list[tuple[PromptStandardSlot, str | None]]",
                record_input_paths,
            )
            content = {}
            for prompt_key, path in record_input_paths:
                if path is None:
                    value = result.prompt.get(prompt_key)
                    if record_input_mode == "first":
                        content = str(value)
                        break
                    content[prompt_key] = value
                else:
                    prompt_value = result.prompt.get(prompt_key)
                    if isinstance(prompt_value, dict):
                        path_value = DataPathBuilder.get_value_by_path(prompt_value, path)
                        if path_value:
                            if record_input_mode == "first":
                                content = path_value
                                break
                            if prompt_key not in content or not isinstance(content[prompt_key], dict):
                                content[prompt_key] = {}
                            content[prompt_key][path] = path_value
            self.add_chat_history(
                {
                    "role": "user",
                    "content": yaml.safe_dump(content) if isinstance(content, dict) else content,
                }
            )
        # Find assistant chat content to record
        record_output_paths = self.settings.get("record_output_paths")
        record_output_mode = self.settings.get("record_output_mode")
        if not isinstance(record_output_paths, list) or len(record_output_paths) == 0:
            self.add_chat_history(
                {
                    "role": "assistant",
                    "content": result.full_result_data["text_result"],
                }
            )
            return
        if isinstance(record_output_paths, list):
            original_result = result.full_result_data["parsed_result"]
            content = {}
            if isinstance(original_result, dict):
                for path in record_output_paths:
                    path_value = DataPathBuilder.get_value_by_path(original_result, str(path))
                    if path_value:
                        if record_output_mode == "first":
                            self.add_chat_history(
                                {
                                    "role": "assistant",
                                    "content": path_value,
                                }
                            )
                            return
                        content[path] = path_value
                self.add_chat_history(
                    {
                        "role": "assistant",
                        "content": yaml.safe_dump(content),
                    }
                )
                return
            self.add_chat_history(
                {
                    "role": "assistant",
                    "content": result.full_result_data["text_result"],
                }
            )
