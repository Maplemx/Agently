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

import inspect
import json
import uuid

from typing import AsyncGenerator, TYPE_CHECKING, cast

from agently.core.Prompt import Prompt
from agently.core.ExtensionHandlers import ExtensionHandlers
from agently.utils import Settings, DataFormatter

from agently.core.ModelResponseResult import ModelResponseResult

if TYPE_CHECKING:
    from agently.core import PluginManager
    from agently.types.data import AgentlyModelResponseMessage
    from agently.types.plugins import ModelRequester


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
            self.extension_handlers,
        )
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
