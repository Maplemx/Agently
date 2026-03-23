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

import asyncio
import inspect
import warnings

from typing import Any, AsyncGenerator, Literal, TYPE_CHECKING, cast, overload, Generator

from agently.utils import FunctionShifter, DataLocator

if TYPE_CHECKING:
    from pydantic import BaseModel

    from agently.core import Prompt, ExtensionHandlers
    from agently.core.PluginManager import PluginManager
    from agently.utils import Settings
    from agently.types.data import (
        AgentlyModelResponseMessage,
        InstantStreamingContentType,
        ResponseContentType,
        RunContext,
        SpecificEvents,
        StreamingData,
    )
    from agently.types.plugins import ResponseParser


DEFAULT_SPECIFIC_EVENTS: "SpecificEvents" = [
    "reasoning_delta",
    "delta",
    "reasoning_done",
    "done",
    "tool_calls",
]


class ModelResponseResult:
    def __init__(
        self,
        agent_name: str,
        response_id: str,
        prompt: "Prompt",
        response_generator: AsyncGenerator["AgentlyModelResponseMessage", None],
        plugin_manager: "PluginManager",
        settings: "Settings",
        extension_handlers: "ExtensionHandlers",
        *,
        request_run_context: "RunContext | None" = None,
        model_run_context: "RunContext | None" = None,
        attempt_index: int = 1,
    ):
        self.agent_name = agent_name
        self.plugin_manager = plugin_manager
        self.settings = settings
        self.request_run_context = request_run_context
        self.model_run_context = model_run_context
        self.run_context = request_run_context
        self.attempt_index = attempt_index
        ResponseParser = cast(
            type["ResponseParser"],
            self.plugin_manager.get_plugin(
                "ResponseParser",
                str(self.settings["plugins.ResponseParser.activate"]),
            ),
        )
        self._response_id = response_id
        self._extension_handlers = extension_handlers
        self._response_parser = ResponseParser(
            agent_name,
            response_id,
            prompt,
            response_generator,
            self.settings,
            run_context=self.model_run_context,
        )
        self._finally_handlers_ran = False
        self._finally_handlers_lock = asyncio.Lock()
        self._run_finally_handlers_once_sync = FunctionShifter.syncify(self._run_finally_handlers_once)
        self.prompt = prompt
        self.full_result_data = self._response_parser.full_result_data
        self.get_meta = FunctionShifter.syncify(self.async_get_meta)
        self.get_text = FunctionShifter.syncify(self.async_get_text)
        self.get_data = FunctionShifter.syncify(self.async_get_data)
        self.get_data_object = FunctionShifter.syncify(self.async_get_data_object)

    async def _run_finally_handlers_once(self):
        if self._finally_handlers_ran:
            return
        async with self._finally_handlers_lock:
            if self._finally_handlers_ran:
                return
            # Mark as executed before invoking handlers so handlers can safely
            # call result getters without re-entering this hook chain.
            self._finally_handlers_ran = True
            finally_handlers = self._extension_handlers.get("finally", [])
            for handler in finally_handlers:
                if inspect.iscoroutinefunction(handler):
                    await handler(
                        self,
                        self.settings,
                    )
                elif inspect.isgeneratorfunction(handler):
                    for _ in handler(
                        self,
                        self.settings,
                    ):
                        pass
                elif inspect.isasyncgenfunction(handler):
                    async for _ in handler(
                        self,
                        self.settings,
                    ):
                        pass
                elif inspect.isfunction(handler):
                    handler(
                        self,
                        self.settings,
                    )

    @overload
    async def async_get_data(
        self,
        *,
        type: Literal['parsed'],
        ensure_keys: list[str],
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
        _retry_count: int = 0,
    ) -> dict[str, Any]: ...

    @overload
    async def async_get_data(
        self,
        *,
        type: Literal['original', 'parsed', 'all'] = "parsed",
        ensure_keys: list[str] | None = None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
        _retry_count: int = 0,
    ) -> Any: ...

    async def async_get_data(
        self,
        *,
        type: Literal['original', 'parsed', 'all'] = "parsed",
        ensure_keys: list[str] | None = None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
        _retry_count: int = 0,
    ) -> Any:
        if type == "parsed" and ensure_keys:
            try:
                data = await self._response_parser.async_get_data(type=type)
                for ensure_key in ensure_keys:
                    EMPTY = object()
                    if DataLocator.locate_path_in_dict(data, ensure_key, key_style, default=EMPTY) is EMPTY:
                        raise
                await self._run_finally_handlers_once()
                return data
            except:
                from agently.base import async_emit_runtime
                from agently.core.ModelResponse import ModelResponse

                await async_emit_runtime(
                    {
                        "event_type": "model.retrying",
                        "source": "ModelResponseResult",
                        "level": "WARNING",
                        "message": "No target data in response. Preparing retry.",
                        "payload": {
                            "agent_name": self.agent_name,
                            "response_id": self._response_id,
                            "retry_count": _retry_count,
                            "attempt_index": self.attempt_index,
                            "next_attempt_index": self.attempt_index + 1,
                            "model_run_id": self.model_run_context.run_id if self.model_run_context is not None else None,
                            "response_text": await self._response_parser.async_get_text(),
                            "ensure_keys": ensure_keys,
                            "key_style": key_style,
                        },
                        "run": self.request_run_context,
                    }
                )

                if _retry_count < max_retries:
                    data = await ModelResponse(
                        self.agent_name,
                        self.plugin_manager,
                        self.settings,
                        self.prompt,
                        self._extension_handlers,
                        run_context=self.request_run_context,
                        attempt_index=self.attempt_index + 1,
                    ).result.async_get_data(
                        type=type,
                        ensure_keys=ensure_keys,
                        key_style=key_style,
                        max_retries=max_retries,
                        raise_ensure_failure=raise_ensure_failure,
                        _retry_count=_retry_count + 1,
                    )
                    await self._run_finally_handlers_once()
                    return data
                else:
                    if raise_ensure_failure:
                        await self._run_finally_handlers_once()
                        raise ValueError(
                            f"Can not generate ensure keys { ensure_keys } within { max_retries } retires."
                        )
                    data = await self._response_parser.async_get_data(type=type)
                    await self._run_finally_handlers_once()
                    return data
        data = await self._response_parser.async_get_data(type=type)
        await self._run_finally_handlers_once()
        return data

    @overload
    async def async_get_data_object(
        self,
    ) -> "BaseModel | None": ...

    @overload
    async def async_get_data_object(
        self,
        *,
        ensure_keys: list[str],
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
    ) -> "BaseModel": ...

    @overload
    async def async_get_data_object(
        self,
        *,
        ensure_keys: None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
    ) -> "BaseModel | None": ...

    async def async_get_data_object(
        self,
        *,
        ensure_keys: list[str] | None = None,
        key_style: Literal["dot", "slash"] = "dot",
        max_retries: int = 3,
        raise_ensure_failure: bool = True,
    ):
        if ensure_keys:
            await self.async_get_data(
                ensure_keys=ensure_keys,
                key_style=key_style,
                max_retries=max_retries,
                _retry_count=0,
                raise_ensure_failure=raise_ensure_failure,
            )
            result_object = await self._response_parser.async_get_data_object()
            await self._run_finally_handlers_once()
            return result_object
        result_object = await self._response_parser.async_get_data_object()
        await self._run_finally_handlers_once()
        return result_object

    async def async_get_meta(self):
        meta = await self._response_parser.async_get_meta()
        await self._run_finally_handlers_once()
        return meta

    async def async_get_text(self):
        text = await self._response_parser.async_get_text()
        await self._run_finally_handlers_once()
        return text

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
    ) -> Generator:
        if type is None:
            if content is not None:
                warnings.warn(
                    "Parameter `content` in method .get_generator() is  deprecated and will be removed in future "
                    "version, please use parameter `type` instead."
                )
                type = content
            else:
                type = "delta"
        parsed_generator = self._response_parser.get_generator(type=type, specific=specific)
        completed = False
        for data in parsed_generator:
            yield data
        completed = True
        if completed:
            self._run_finally_handlers_once_sync()

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

    async def get_async_generator(
        self,
        type: "ResponseContentType | None" = None,
        content: "ResponseContentType | None" = None,
        *,
        specific: "SpecificEvents" = DEFAULT_SPECIFIC_EVENTS,
    ) -> AsyncGenerator:
        if type is None:
            if content is not None:
                warnings.warn(
                    "Parameter `content` in method .get_async_generator() is  deprecated and will be removed in "
                    "future version, please use parameter `type` instead."
                )
                type = content
            else:
                type = "delta"
        parsed_generator = self._response_parser.get_async_generator(type=type, specific=specific)
        completed = False
        async for data in parsed_generator:
            yield data
        completed = True
        if completed:
            await self._run_finally_handlers_once()
