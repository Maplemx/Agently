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

from typing import Any, AsyncGenerator, Literal, TYPE_CHECKING, cast, TypeAlias, overload, Generator

ContentKindTuple: TypeAlias = Literal["all", "delta", "original"]
ContentKindStreaming: TypeAlias = Literal["instant", "streaming_parse"]

from agently.core import Prompt
from agently.utils import Settings, FunctionShifter

if TYPE_CHECKING:
    from agently.core import PluginManager, EventCenterMessenger
    from agently.types.data import AgentlyModelResponseMessage, PromptStandardSlot, StreamingData, SerializableValue
    from agently.types.plugins import ModelRequester, ResponseParser


class ModelResponseResult:
    def __init__(
        self,
        prompt: Prompt,
        response_generator: AsyncGenerator["AgentlyModelResponseMessage", None],
        plugin_manager: "PluginManager",
        settings: Settings,
        messenger: "EventCenterMessenger",
    ):
        self.plugin_manager = plugin_manager
        self.settings = settings
        ResponseParser = cast(
            type["ResponseParser"],
            self.plugin_manager.get_plugin(
                "ResponseParser",
                str(self.settings["plugins.ResponseParser.activate"]),
            ),
        )
        _response_parser = ResponseParser(prompt, response_generator, self.settings, messenger)
        self.get_meta = _response_parser.get_meta
        self.get_text = _response_parser.get_text
        self.get_result = _response_parser.get_result
        self.get_result_object = _response_parser.get_result_object
        self.get_generator = _response_parser.get_generator
        self.get_async_generator = _response_parser.get_async_generator


class ModelResponse:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        settings: Settings,
        prompt: Prompt,
        messenger: "EventCenterMessenger",
    ):
        self.id = uuid.uuid4().hex
        self.plugin_manager = plugin_manager
        settings_snapshot = settings.get()
        self.settings = Settings(settings_snapshot if isinstance(settings_snapshot, dict) else {})
        prompt_snapshot = prompt.get()
        self.prompt = Prompt(
            self.plugin_manager,
            self.settings,
            prompt_dict=prompt_snapshot if isinstance(prompt_snapshot, dict) else {},
        )
        self._messenger = messenger
        self._messenger.update_base_meta({"row_id": self.id})
        self.result = ModelResponseResult(
            self.prompt,
            self._get_response_generator(),
            self.plugin_manager,
            self.settings,
            self._messenger,
        )
        self.get_meta = self.result.get_meta
        self.get_text = self.result.get_text
        self.get_result = self.result.get_result
        self.get_result_object = self.result.get_result_object
        self.get_generator = self.result.get_generator
        self.get_async_generator = self.result.get_async_generator

    def _get_response_generator(self) -> AsyncGenerator["AgentlyModelResponseMessage", None]:
        ModelRequester = cast(
            type["ModelRequester"],
            self.plugin_manager.get_plugin(
                "ModelRequester",
                str(self.settings["plugins.ModelRequester.activate"]),
            ),
        )
        model_requester = ModelRequester(self.prompt, self.settings)
        request_data = model_requester.generate_request_data()
        self._messenger.to_console(
            {
                "Status": "🛜 Requesting",
                "Request Data": request_data.model_dump(),
            },
        )
        response_generator = model_requester.request_model(request_data)
        return model_requester.broadcast_response(response_generator)


class ModelRequest:
    def __init__(
        self,
        plugin_manager: "PluginManager",
        *,
        parent_settings: Settings | None = None,
        parent_prompt: Prompt | None = None,
        messenger: "EventCenterMessenger | None" = None,
        request_name: str | None = None,
    ):
        self.plugin_manager = plugin_manager
        self.settings = Settings(
            name="Request-Settings",
            parent=parent_settings,
        )
        self.prompt = Prompt(
            plugin_manager=self.plugin_manager,
            parent_settings=self.settings,
            parent_prompt=parent_prompt,
        )
        if messenger is None:
            from agently.base import event_center

            self._messenger = event_center.create_messenger(
                "ModelRequest",
                base_meta={"table_name": "Direct Request" if request_name is None else request_name},
            )
        else:
            self._messenger = messenger
            if "table_name" not in self._messenger._base_meta or not self._messenger._base_meta["table_name"]:
                self._messenger.update_base_meta(
                    {"table_name": "Direct Request" if request_name is None else request_name}
                )

    def set_settings(self, key: str, value: "SerializableValue"):
        self.settings.set_settings(key, value)

    def set_prompt(self, key: "PromptStandardSlot | str", value: tuple[type, str | None, str | None] | Any):
        self.prompt.set(key, value)
        return self

    def get_response(self):
        response = ModelResponse(
            self.plugin_manager,
            self.settings,
            self.prompt,
            self._messenger,
        )
        self.prompt.clear()
        return response

    @FunctionShifter.hybrid_func
    async def get_meta(self):
        return await self.get_response().get_meta()

    @FunctionShifter.hybrid_func
    async def get_text(self):
        return await self.get_response().get_text()

    @FunctionShifter.hybrid_func
    async def get_result(
        self,
        *,
        content: Literal['original', 'parsed', 'all'] = "parsed",
    ):
        return await self.get_response().get_result(content=content)

    @FunctionShifter.hybrid_func
    async def get_result_object(self):
        return await self.get_response().get_result_object()

    @overload
    def get_generator(
        self,
        *,
        content: Literal["all", "delta", "original"],
    ) -> Generator[tuple[str, Any], None, None]: ...
    @overload
    def get_generator(
        self,
        *,
        content: Literal["instant", "streaming_parse"],
    ) -> Generator["StreamingData", None, None]: ...
    def get_generator(
        self,
        *,
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] = "all",
    ):
        return self.get_response().get_generator(content=content)

    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["all"],
    ) -> AsyncGenerator[tuple[str, Any], None]: ...
    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["delta", "original"],
    ) -> AsyncGenerator[str, None]: ...
    @overload
    def get_async_generator(
        self,
        *,
        content: Literal["instant", "streaming_parse"],
    ) -> AsyncGenerator["StreamingData", None]: ...
    def get_async_generator(
        self,
        *,
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] = "all",
    ):
        return self.get_response().get_async_generator(content=content)
