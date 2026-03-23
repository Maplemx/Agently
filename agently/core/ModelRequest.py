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

from __future__ import annotations

from typing import Any, AsyncGenerator, Literal, TYPE_CHECKING, overload, Generator

from agently.core.Prompt import Prompt
from agently.core.ExtensionHandlers import ExtensionHandlers
from agently.utils import Settings, FunctionShifter

from agently.core.ModelResponse import ModelResponse
from agently.core.ModelResponseResult import ModelResponseResult

if TYPE_CHECKING:
    from agently.core import PluginManager
    from agently.types.data import (
        InstantStreamingContentType,
        PromptStandardSlot,
        ResponseContentType,
        RunContext,
        SpecificEvents,
        StreamingData,
    )


DEFAULT_SPECIFIC_EVENTS: "SpecificEvents" = [
    "reasoning_delta",
    "delta",
    "reasoning_done",
    "done",
    "tool_calls",
]


class ModelRequest:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        *,
        agent_name: str | None = None,
        agent_id: str | None = None,
        parent_settings: Settings | None = None,
        parent_prompt: Prompt | None = None,
        parent_extension_handlers: ExtensionHandlers | None = None,
    ):
        self.agent_name = agent_name if agent_name is not None else "Directly Request"
        self.agent_id = agent_id
        self.plugin_manager = plugin_manager
        self.settings = Settings(
            name="Request-Settings",
            parent=parent_settings,
        )
        self.prompt = Prompt(
            name="Request-Prompt",
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
            parent_prompt=parent_prompt,
        )
        self.extension_handlers = ExtensionHandlers(
            {
                "prefixes": [],
                "base_suffixes": [],
                "broadcast_suffixes": [],
            },
            name="Request-ExtensionHandlers",
            parent=parent_extension_handlers,
        )

        self.set_settings = self.settings.set_settings
        self.load_settings = self.settings.load

        self.get_meta = FunctionShifter.syncify(self.async_get_meta)
        self.get_text = FunctionShifter.syncify(self.async_get_text)
        self.get_data = FunctionShifter.syncify(self.async_get_data)
        self.get_data_object = FunctionShifter.syncify(self.async_get_data_object)

        self.start = self.get_data
        self.async_start = self.async_get_data

    def _create_request_run_context(
        self,
        response_id: str | None = None,
        *,
        parent_run_context: "RunContext | None" = None,
    ) -> "RunContext":
        from agently.types.data import RunContext

        session_id = self.settings.get("runtime.session_id", None)
        if session_id is not None:
            session_id = str(session_id)
        return RunContext.create(
            run_kind="request",
            parent=parent_run_context,
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            session_id=session_id,
            response_id=response_id,
        )

    def set_prompt(
        self,
        key: "PromptStandardSlot | str",
        value: tuple[type, str | None, str | None] | Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set(key, value, mappings)
        return self

    # Quick Prompt
    def system(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("input", prompt, mappings)
        return self

    def rule(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("system", ["{system.rule} ARE IMPORTANT RULES YOU SHALL FOLLOW!"])
        self.prompt.set("system.rule", prompt, mappings)
        return self

    def role(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("system", ["YOU MUST REACT AND RESPOND AS {system.your_role}!"])
        self.prompt.set("system.your_role", prompt, mappings)
        return self

    def user_info(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("system", ["{system.user_info} IS IMPORTANT INFORMATION ABOUT USER!"])
        self.prompt.set("system.user_info", prompt, mappings)
        return self

    def input(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("input", prompt, mappings)
        return self

    def info(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("info", prompt, mappings)
        return self

    def instruct(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("instruct", prompt, mappings)
        return self

    def examples(
        self,
        prompt: Any,
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("examples", prompt, mappings)
        return self

    def output(
        self,
        prompt: (
            dict[str, tuple[type, str | None, str, None] | Any]
            | list[tuple[type, str | None, str, None] | Any]
            | tuple[type, str | None, str, None]
            | Any
        ),
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("output", prompt, mappings)
        return self

    def attachment(
        self,
        prompt: list[dict[str, Any]],
        mappings: dict[str, Any] | None = None,
    ):
        self.prompt.set("attachment", prompt, mappings)
        return self

    # Response & Result
    def get_response(self, *, parent_run_context: "RunContext | None" = None):
        response = ModelResponse(
            self.agent_name,
            self.plugin_manager,
            self.settings,
            self.prompt,
            self.extension_handlers,
            run_context=self._create_request_run_context(parent_run_context=parent_run_context),
        )
        response.run_context.response_id = response.id
        self.prompt.clear()
        return response

    def get_result(self, *, parent_run_context: "RunContext | None" = None):
        return self.get_response(parent_run_context=parent_run_context).result

    async def async_get_meta(self, *, parent_run_context: "RunContext | None" = None):
        return await self.get_response(parent_run_context=parent_run_context).async_get_meta()

    async def async_get_text(self, *, parent_run_context: "RunContext | None" = None):
        return await self.get_response(parent_run_context=parent_run_context).async_get_text()

    async def async_get_data(
        self,
        *,
        type: Literal['original', 'parsed', 'all'] = "parsed",
        ensure_keys: list[str] | None = None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
        parent_run_context: "RunContext | None" = None,
    ):
        response = self.get_response(parent_run_context=parent_run_context)
        return await response.async_get_data(
            type=type,
            ensure_keys=ensure_keys,
            key_style=key_style,
            max_retries=max_retries,
            raise_ensure_failure=raise_ensure_failure,
        )

    async def async_get_data_object(
        self,
        *,
        ensure_keys: list[str] | None = None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
        parent_run_context: "RunContext | None" = None,
    ):
        response = self.get_response(parent_run_context=parent_run_context)
        return await response.async_get_data_object(
            ensure_keys=ensure_keys,
            key_style=key_style,
            max_retries=max_retries,
            raise_ensure_failure=raise_ensure_failure,
        )

    @overload
    def get_generator(
        self,
        type: "InstantStreamingContentType",
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> Generator["StreamingData", None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["all"],
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> Generator[tuple[str, Any], None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["delta", "specific", "original"],
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> Generator[str, None, None]: ...

    @overload
    def get_generator(
        self,
        type: "ResponseContentType | None" = "delta",
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> Generator: ...

    def get_generator(
        self,
        type: "ResponseContentType | None" = None,
        content: "ResponseContentType | None" = None,
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
        parent_run_context: "RunContext | None" = None,
    ) -> Generator:
        return self.get_response(parent_run_context=parent_run_context).get_generator(
            type=type,
            content=content,
            specific=specific,
        )  # type: ignore for `content` compatible

    @overload
    def get_async_generator(
        self,
        type: "InstantStreamingContentType",
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> AsyncGenerator["StreamingData", None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["all"],
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> AsyncGenerator[tuple[str, Any], None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["delta", "specific", "original"],
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> AsyncGenerator[str, None]: ...

    @overload
    def get_async_generator(
        self,
        type: "ResponseContentType | None" = "delta",
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> AsyncGenerator: ...

    def get_async_generator(
        self,
        type: "ResponseContentType | None" = None,
        content: "ResponseContentType | None" = None,
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
        parent_run_context: "RunContext | None" = None,
    ) -> AsyncGenerator:
        return self.get_response(parent_run_context=parent_run_context).get_async_generator(
            type=type,
            content=content,
            specific=specific,
        )  # type: ignore for `content` compatible


__all__ = [
    "ModelRequest",
    "ModelResponse",
    "ModelResponseResult",
]
