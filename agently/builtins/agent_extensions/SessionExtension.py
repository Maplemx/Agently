# Copyright 2023-2026 AgentEra(Agently.Tech)
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

from uuid import uuid4

from typing import TYPE_CHECKING, Sequence

from agently.core import BaseAgent, Session

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.core.ModelRequest import ModelResponseResult
    from agently.types.data import ChatMessage, ChatMessageDict
    from agently.utils import Settings
    from agently.types.plugins import SessionAnalysisHandler, SessionResizeHandler


class SessionExtension(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sessions: dict[str, Session] = {}
        self.activated_session: Session | None = None
        self.settings.setdefault("session.input_keys", None, inherit=True)
        self.settings.setdefault("session.reply_keys", None, inherit=True)

        self.__session_analysis_handler: "SessionAnalysisHandler | None" = None
        self.__session_resize_handlers: dict[str, "SessionResizeHandler"] = {}

        self.extension_handlers.append("request_prefixes", self._session_request_prefix)
        self.extension_handlers.append("finally", self._session_finally)

    def register_session_analysis_handler(self, handler: "SessionAnalysisHandler"):
        """
        Register analysis handler for session resize planning.

        Signature:
            `(full_context, context_window, memo, session_settings) -> str | None`.
        """
        self.__session_analysis_handler = handler
        for session in self.sessions.values():
            session.register_analysis_handler(handler)
        return self

    def register_session_resize_handler(self, strategy_name: str, handler: "SessionResizeHandler"):
        """
        Register resize handler for a strategy.

        Signature:
            `(full_context, context_window, memo, session_settings) -> (new_full_context, new_context_window, new_memo)`.
        """
        if not isinstance(strategy_name, str) or strategy_name.strip() == "":
            raise ValueError("strategy_name must be a non-empty string.")
        self.__session_resize_handlers[strategy_name] = handler
        for session in self.sessions.values():
            session.register_resize_handler(strategy_name, handler)
        return self

    def __bind_session_resize_pipeline(self, session: Session):
        session.register_analysis_handler(self.__session_analysis_handler)
        for strategy_name, handler in self.__session_resize_handlers.items():
            session.register_resize_handler(strategy_name, handler)

    def _refill_agent_chat_history_with_session(self):
        if self.activated_session is None:
            return self
        if "chat_history" in self.agent_prompt:
            del self.agent_prompt["chat_history"]
        self.agent_prompt.set("chat_history", self.activated_session.context_window)
        return self

    def activate_session(self, *, session_id: str | None = None):
        if session_id is not None and session_id in self.sessions:
            self.activated_session = self.sessions[session_id]
        else:
            if session_id is None:
                session_id = uuid4().hex
            self.activated_session = Session(
                id=session_id,
                auto_resize=True,
                settings=self.settings,
            )
            self.sessions[session_id] = self.activated_session

        self.__bind_session_resize_pipeline(self.activated_session)
        return self._refill_agent_chat_history_with_session()

    def deactivate_session(self):
        self.activated_session = None
        if "chat_history" in self.agent_prompt:
            del self.agent_prompt["chat_history"]
        self.agent_prompt.set("chat_history", [])
        return self

    def reset_chat_history(self):
        if self.activated_session is None:
            return super().reset_chat_history()
        self.activated_session.reset_chat_history()
        return self._refill_agent_chat_history_with_session()

    def set_chat_history(
        self,
        chat_history: "Sequence[ChatMessage | ChatMessageDict]",
    ):
        if self.activated_session is None:
            return super().set_chat_history(chat_history)
        self.activated_session.set_chat_history(chat_history)
        return self._refill_agent_chat_history_with_session()

    def add_chat_history(
        self,
        chat_history: "Sequence[ChatMessage | ChatMessageDict] | ChatMessage | ChatMessageDict",
    ):
        if self.activated_session is None:
            return super().add_chat_history(chat_history)
        self.activated_session.add_chat_history(chat_history)
        return self._refill_agent_chat_history_with_session()

    def clean_context_window(self):
        if self.activated_session is None:
            return super().reset_chat_history()
        self.activated_session.clean_context_window()
        return self._refill_agent_chat_history_with_session()

    async def _session_request_prefix(self, prompt: "Prompt", _settings: "Settings"):
        Session.apply_request_prefix(prompt, self.activated_session)

    async def _session_finally(self, result: "ModelResponseResult", settings: "Settings"):
        if self.activated_session is None:
            return

        user_content, assistant_content = await Session.resolve_finally_contents(
            result,
            settings,
            self.agent_prompt,
        )

        if user_content is not None and user_content != "":
            self.add_chat_history({"role": "user", "content": user_content})
        if assistant_content is not None and assistant_content != "":
            self.add_chat_history({"role": "assistant", "content": assistant_content})
