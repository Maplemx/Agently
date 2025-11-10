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

import json
import uuid

import inspect
from typing import Any, AsyncGenerator, Literal, TYPE_CHECKING, cast, TypeAlias, overload, Generator

ContentKindTuple: TypeAlias = Literal["all", "delta", "original"]
ContentKindStreaming: TypeAlias = Literal["instant", "streaming_parse"]

from agently.core import Prompt, ExtensionHandlers
from agently.utils import Settings, FunctionShifter, DataFormatter

if TYPE_CHECKING:
    from agently.core import PluginManager
    from agently.types.data import AgentlyModelResponseMessage, PromptStandardSlot, StreamingData, SerializableValue
    from agently.types.plugins import ModelRequester, ResponseParser


class ModelResponseResult:
    def __init__(
        self,
        agent_name: str,
        response_id: str,
        prompt: Prompt,
        response_generator: AsyncGenerator["AgentlyModelResponseMessage", None],
        plugin_manager: "PluginManager",
        settings: Settings,
    ):
        self.agent_name = agent_name
        self.plugin_manager = plugin_manager
        self.settings = settings
        ResponseParser = cast(
            type["ResponseParser"],
            self.plugin_manager.get_plugin(
                "ResponseParser",
                str(self.settings["plugins.ResponseParser.activate"]),
            ),
        )
        _response_parser = ResponseParser(agent_name, response_id, prompt, response_generator, self.settings)
        self.prompt = prompt
        self.full_result_data = _response_parser.full_result_data
        self.get_meta = _response_parser.get_meta
        self.async_get_meta = _response_parser.async_get_meta
        self.get_text = _response_parser.get_text
        self.async_get_text = _response_parser.async_get_text
        self.get_data = _response_parser.get_data
        self.async_get_data = _response_parser.async_get_data
        self.get_data_object = _response_parser.get_data_object
        self.async_get_data_object = _response_parser.async_get_data_object
        self.get_generator = _response_parser.get_generator
        self.get_async_generator = _response_parser.get_async_generator


class ModelResponse:

    def __init__(
        self,
        agent_name: str,
        plugin_manager: "PluginManager",
        settings: Settings,
        prompt: Prompt,
        extension_handlers: ExtensionHandlers,
    ):
        self.agent_name = agent_name
        self.id = uuid.uuid4().hex
        self.plugin_manager = plugin_manager
        settings_snapshot = settings.get()
        self.settings = Settings(settings_snapshot if isinstance(settings_snapshot, dict) else {})
        self.settings.set("$log.cancel_logs", False)
        prompt_snapshot = prompt.get()
        self.prompt = Prompt(
            self.plugin_manager,
            self.settings,
            prompt_dict=prompt_snapshot if isinstance(prompt_snapshot, dict) else {},
        )
        extension_handlers_snapshot = extension_handlers.get()
        self.extension_handlers = ExtensionHandlers(
            extension_handlers_snapshot if isinstance(extension_handlers_snapshot, dict) else {}
        )
        self.result = ModelResponseResult(
            self.agent_name,
            self.id,
            self.prompt,
            self._get_response_generator(),
            self.plugin_manager,
            self.settings,
        )
        self.get_result = self.result
        self.get_meta = self.result.get_meta
        self.async_get_meta = self.result.async_get_meta
        self.get_text = self.result.get_text
        self.async_get_text = self.result.async_get_text
        self.get_data = self.result.get_data
        self.async_get_data = self.result.async_get_data
        self.get_data_object = self.result.get_data_object
        self.async_get_data_object = self.result.async_get_data_object
        self.get_generator = self.result.get_generator
        self.get_async_generator = self.result.get_async_generator

    def cancel_logs(self):
        self.settings.set("$log.cancel_logs", True)

    async def _get_response_generator(self) -> AsyncGenerator["AgentlyModelResponseMessage", None]:
        from agently.base import async_system_message

        ModelRequester = cast(
            type["ModelRequester"],
            self.plugin_manager.get_plugin(
                "ModelRequester",
                str(self.settings["plugins.ModelRequester.activate"]),
            ),
        )
        request_prefixes = self.extension_handlers.get("request_prefixes", [])
        for prefix in request_prefixes:
            if inspect.iscoroutinefunction(prefix):
                await prefix(self.prompt, self.settings)
            elif inspect.isfunction(prefix):
                prefix(self.prompt, self.settings)
        model_requester = ModelRequester(self.prompt, self.settings)
        request_data = model_requester.generate_request_data()
        request_data_dict = DataFormatter.sanitize(request_data.model_dump())
        await async_system_message(
            "MODEL_REQUEST",
            {
                "agent_name": self.agent_name,
                "response_id": self.id,
                "content": {
                    "stage": "Requesting",
                    "detail": json.dumps(
                        {
                            "data": request_data_dict["data"] if "data" in request_data_dict else None,
                            "request_options": (
                                request_data_dict["request_options"] if "request_options" in request_data_dict else None
                            ),
                            "request_url": (
                                request_data_dict["request_url"] if "request_url" in request_data_dict else None
                            ),
                            "stream": (request_data_dict["stream"] if "stream" in request_data_dict else None),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                    .replace("\\n", "\n")
                    .replace("\\\"", "\""),
                },
            },
            self.settings,
        )
        response_generator = model_requester.request_model(request_data)
        broadcast_generator = model_requester.broadcast_response(response_generator)
        broadcast_prefixes = self.extension_handlers.get("broadcast_prefixes", [])
        broadcast_suffixes = self.extension_handlers.get("broadcast_suffixes", {})
        for prefix in broadcast_prefixes:
            if inspect.iscoroutinefunction(prefix):
                result = await prefix(
                    self.result.full_result_data,
                    self.settings,
                )
                if result is not None:
                    yield result
            elif inspect.isgeneratorfunction(prefix):
                for result in prefix(
                    self.result.full_result_data,
                    self.settings,
                ):
                    if result is not None:
                        yield result
            elif inspect.isasyncgenfunction(prefix):
                async for result in prefix(
                    self.result.full_result_data,
                    self.settings,
                ):
                    if result is not None:
                        yield result
            elif inspect.isfunction(prefix):
                result = prefix(
                    self.result.full_result_data,
                    self.settings,
                )
                if result is not None:
                    yield result
        async for event, data in broadcast_generator:
            yield event, data
            suffixes = broadcast_suffixes[event] if event in broadcast_suffixes else []
            for suffix in suffixes:
                if inspect.iscoroutinefunction(suffix):
                    result = await suffix(
                        event,
                        data,
                        self.result.full_result_data,
                        self.settings,
                    )
                    if result is not None:
                        yield result
                elif inspect.isgeneratorfunction(suffix):
                    for result in suffix(
                        event,
                        data,
                        self.result.full_result_data,
                        self.settings,
                    ):
                        if result is not None:
                            yield result
                elif inspect.isasyncgenfunction(suffix):
                    async for result in suffix(
                        event,
                        data,
                        self.result.full_result_data,
                        self.settings,
                    ):
                        if result is not None:
                            yield result
                elif inspect.isfunction(suffix):
                    result = suffix(
                        event,
                        data,
                        self.result.full_result_data,
                        self.settings,
                    )
                    if result is not None:
                        yield result
        finally_handlers = self.extension_handlers.get("finally", [])
        for handler in finally_handlers:
            if inspect.iscoroutinefunction(handler):
                result = await handler(
                    self.result,
                    self.settings,
                )
                if result is not None:
                    yield result
            elif inspect.isgeneratorfunction(handler):
                for result in handler(
                    self.result,
                    self.settings,
                ):
                    if result is not None:
                        yield result
            elif inspect.isasyncgenfunction(handler):
                async for result in handler(
                    self.result,
                    self.settings,
                ):
                    if result is not None:
                        yield result
            elif inspect.isfunction(handler):
                result = handler(
                    self.result,
                    self.settings,
                )
                if result is not None:
                    yield result


class ModelRequest:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        *,
        agent_name: str | None = None,
        parent_settings: Settings | None = None,
        parent_prompt: Prompt | None = None,
        parent_extension_handlers: ExtensionHandlers | None = None,
    ):
        self.agent_name = agent_name if agent_name is not None else "Directly Request"
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

        self.get_meta = FunctionShifter.syncify(self.async_get_meta)
        self.get_text = FunctionShifter.syncify(self.async_get_text)
        self.get_data = FunctionShifter.syncify(self.async_get_data)
        self.get_data_object = FunctionShifter.syncify(self.async_get_data_object)

    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)

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
        self.prompt.set("system", ["YOU MUST REACT AND RESPOND AS {system.role}!"])
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

    def get_response(self):
        response = ModelResponse(
            self.agent_name,
            self.plugin_manager,
            self.settings,
            self.prompt,
            self.extension_handlers,
        )
        self.prompt.clear()
        return response

    async def get_result(self):
        return self.get_response().result

    async def async_get_meta(self):
        return await self.get_response().async_get_meta()

    async def async_get_text(self):
        return await self.get_response().async_get_text()

    async def async_get_data(
        self,
        *,
        type: Literal['original', 'parsed', 'all'] = "parsed",
    ):
        return await self.get_response().async_get_data(type=type)

    async def async_get_data_object(self):
        return await self.get_response().async_get_data_object()

    @overload
    def get_generator(
        self,
        type: Literal["instant", "streaming_parse"],
    ) -> Generator["StreamingData", None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["all"],
    ) -> Generator[tuple[str, Any], None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["delta", "typed_delta", "original"],
    ) -> Generator[str, None, None]: ...

    @overload
    def get_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> Generator: ...

    def get_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> Generator:
        return self.get_response().get_generator(type=type)

    @overload
    def get_async_generator(
        self,
        type: Literal["instant", "streaming_parse"],
    ) -> AsyncGenerator["StreamingData", None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["all"],
    ) -> AsyncGenerator[tuple[str, Any], None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["delta", "typed_delta", "original"],
    ) -> AsyncGenerator[str, None]: ...

    @overload
    def get_async_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> AsyncGenerator: ...

    def get_async_generator(
        self,
        type: Literal["all", "original", "delta", "typed_delta", "instant", "streaming_parse"] | None = "delta",
    ) -> AsyncGenerator:
        return self.get_response().get_async_generator(type=type)
