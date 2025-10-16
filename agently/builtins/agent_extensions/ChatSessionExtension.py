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

from typing import Literal, TYPE_CHECKING

from agently.core import BaseAgent
from agently.utils import DataPathBuilder

if TYPE_CHECKING:
    from agently.types.data import ChatMessage


class ChatSessionExtension(BaseAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chat_sessions: "dict[str, list[ChatMessage]]" = {}
        self._activated_chat_session = None
        self._content_paths: list[str] = []

        self.set_content_path = self.set_content_paths

    def activate_chat_session(self, chat_session_name: str | None):
        if chat_session_name is None:
            chat_session_name = uuid.uuid4().hex
        if chat_session_name not in self._chat_sessions:
            self._chat_sessions[chat_session_name] = []
        self._activate_chat_session = chat_session_name
        return self

    def stop_chat_session(self):
        self._activate_chat_session = None
        return self

    def set_content_paths(self, *args: str, style: Literal["dot_style", "slash_style"] = "dot_style"):
        if style == "slash_style":
            self._content_paths = [DataPathBuilder.convert_slash_to_dot(path) for path in args]
        else:
            self._content_paths = list(args)
        return self
