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

import asyncio
import contextlib
import warnings

from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator, Literal, Mapping, cast
from pydantic import BaseModel

import json5

from agently.types.plugins import ResponseParser
from agently.utils import (
    DataPathBuilder,
    RuntimeDataNamespace,
    GeneratorConsumer,
    DataLocator,
    FunctionShifter,
    StreamingJSONCompleter,
    StreamingJSONParser,
)

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.types.data import AgentlyModelResult, AgentlyResponseGenerator, AgentlyModelResult, SerializableData
    from agently.utils import Settings


class AgentlyResponseParser(ResponseParser):
    name = "AgentlyResponseParser"
    DEFAULT_SETTINGS = {
        "$global": {
            "response": {
                "streaming_parse": False,
                "streaming_parse_path_style": "dot",
            },
        },
    }

    def __init__(
        self,
        agent_name: str,
        response_id: str,
        prompt: "Prompt",
        response_generator: "AgentlyResponseGenerator",
        settings: "Settings",
    ):
        self.agent_name = agent_name
        self.response_id = response_id
        self.response_generator = response_generator
        self.settings = settings
        self.plugin_settings = RuntimeDataNamespace(self.settings, f"plugins.ResponseParser.{ self.name }")
        self.full_result_data: AgentlyModelResult = {
            "result_consumer": None,
            "meta": {},
            "original_delta": [],
            "original_done": {},
            "text_result": "",
            "cleaned_result": "",
            "parsed_result": None,
            "result_object": None,
            "errors": [],
            "extra": {},
        }
        self._prompt_object = prompt.to_prompt_object()
        self._OutputModel = prompt.to_output_model() if self._prompt_object.output_format == "json" else None
        self._response_consumer: GeneratorConsumer | None = None
        self._consumer_lock = asyncio.Lock()
        self._streaming_json_parser = (
            StreamingJSONParser(self._prompt_object.output) if self._prompt_object.output_format == "json" else None
        )

        self.get_meta = FunctionShifter.syncify(self.async_get_meta)
        self.get_text = FunctionShifter.syncify(self.async_get_text)
        self.get_result = FunctionShifter.syncify(self.async_get_result)
        self.get_result_object = FunctionShifter.syncify(self.async_get_result_object)

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    async def _ensure_consumer(self):
        if self._response_consumer is None:
            async with self._consumer_lock:
                if self._response_consumer is None:
                    self._response_consumer = GeneratorConsumer(self._extract())

    async def _extract(self):
        from agently.base import async_system_message

        buffer = ""
        try:
            async for event, data in self.response_generator:
                yield event, data
                match event:
                    case "original_delta":
                        self.full_result_data["original_delta"].append(data)
                    case "delta":
                        buffer += str(data)
                        await async_system_message(
                            "MODEL_REQUEST",
                            {
                                "agent_name": self.agent_name,
                                "response_id": self.response_id,
                                "content": {
                                    "stage": "Streaming",
                                    "detail": str(data),
                                    "delta": True,
                                },
                            },
                        )
                    case "original_done":
                        self.full_result_data["original_done"] = data
                    case "done":
                        self.full_result_data["text_result"] = str(data)
                        if buffer != self.full_result_data["text_result"]:
                            warnings.warn(
                                "Buffered streaming result is not exactly the same as final result.\n"
                                f"Buffered Result: { buffer }\n"
                                f"Final Result: { self.full_result_data['text_result'] }\n"
                            )
                        if self._prompt_object.output_format == "json":
                            cleaned_json = DataLocator.locate_output_json(str(data), self._prompt_object.output)
                            if cleaned_json:
                                completer = StreamingJSONCompleter()
                                completer.reset(cleaned_json)
                                completed = completer.complete()
                                parsed = json5.loads(completed)
                                try:
                                    if self._OutputModel:
                                        result_object = self._OutputModel.model_validate(parsed)
                                    else:
                                        result_object = None
                                except:
                                    result_object = None
                                self.full_result_data["cleaned_result"] = completed
                                self.full_result_data["parsed_result"] = parsed
                                self.full_result_data["result_object"] = result_object
                                await async_system_message(
                                    "MODEL_REQUEST",
                                    {
                                        "agent_name": self.agent_name,
                                        "response_id": self.response_id,
                                        "content": {
                                            "stage": "Done",
                                            "detail": str(data),
                                        },
                                    },
                                )
                            else:
                                self.full_result_data["cleaned_result"] = None
                                self.full_result_data["parsed_result"] = None
                                await async_system_message(
                                    "MODEL_REQUEST",
                                    {
                                        "agent_name": self.agent_name,
                                        "response_id": self.response_id,
                                        "content": {
                                            "stage": "Done",
                                            "detail": "❌ Can not parse this result!",
                                        },
                                    },
                                )
                        else:
                            self.full_result_data["parsed_result"] = str(data)
                            await async_system_message(
                                "MODEL_REQUEST",
                                {
                                    "agent_name": self.agent_name,
                                    "response_id": self.response_id,
                                    "content": {
                                        "stage": "Done",
                                        "detail": str(data),
                                    },
                                },
                            )
                    case "meta":
                        if isinstance(data, Mapping):
                            self.full_result_data["meta"].update(dict(data))
                    case "error":
                        if isinstance(data, Exception):
                            self.full_result_data["errors"].append(data)
        finally:
            if hasattr(self.response_generator, "aclose"):
                with contextlib.suppress(RuntimeError):
                    await self.response_generator.aclose()

    async def async_get_meta(self) -> "SerializableData":
        await self._ensure_consumer()
        await cast(GeneratorConsumer, self._response_consumer).get_result()
        return self.full_result_data["meta"]

    async def async_get_result(
        self,
        *,
        content: Literal['original', 'parsed', "all"] = "parsed",
    ) -> Any:
        await self._ensure_consumer()
        await cast(GeneratorConsumer, self._response_consumer).get_result()
        match content:
            case "original":
                return self.full_result_data["original_done"].copy()
            case "parsed":
                parsed = self.full_result_data["parsed_result"]
                return parsed.copy() if hasattr(parsed, "copy") else parsed  # type: ignore
            case "all":
                return self.full_result_data.copy()

    async def async_get_result_object(self) -> BaseModel | None:
        if self._prompt_object.output_format != "json":
            raise TypeError(
                "Error: Cannot build an output model for a non-structure output.\n"
                f"Output Format: { self._prompt_object.output_format }\n"
                f"Output Prompt: { self._prompt_object.output }"
            )
        await self._ensure_consumer()
        await cast(GeneratorConsumer, self._response_consumer).get_result()
        return self.full_result_data["result_object"]

    async def async_get_text(self) -> str:
        await self._ensure_consumer()
        await cast(GeneratorConsumer, self._response_consumer).get_result()
        return self.full_result_data["text_result"]

    async def get_async_generator(
        self,
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] | None = "delta",
    ) -> AsyncGenerator:
        await self._ensure_consumer()
        parsed_generator = cast(GeneratorConsumer, self._response_consumer).get_async_generator()
        _streaming_parse_path_style = self.settings.get("response.streaming_parse_path_style", "dot")
        async for event, data in parsed_generator:
            match content:
                case "all":
                    yield event, data
                case "delta":
                    if event == "delta":
                        yield data
                case "instant" | "streaming_parse":
                    if self._streaming_json_parser is not None:
                        streaming_parsed = None
                        if event == "delta":
                            streaming_parsed = self._streaming_json_parser.parse_chunk(data)
                        elif event == "done":
                            streaming_parsed = self._streaming_json_parser.finalize()
                        if streaming_parsed:
                            async for streaming_data in streaming_parsed:
                                if _streaming_parse_path_style == "slash":
                                    streaming_data.path = DataPathBuilder.convert_dot_to_slash(streaming_data.path)
                                yield streaming_data
                case "original":
                    if event.startswith("original"):
                        yield data

    def get_generator(
        self,
        content: Literal['all', 'delta', 'original', 'instant', 'streaming_parse'] | None = "delta",
    ) -> Generator:
        asyncio.run(self._ensure_consumer())
        parsed_generator = cast(GeneratorConsumer, self._response_consumer).get_generator()
        _streaming_parse_path_style = self.settings.get("response.streaming_parse_path_style", "dot")
        for event, data in parsed_generator:
            match content:
                case "all":
                    yield event, data
                case "delta":
                    if event == "delta":
                        yield data
                case "instant" | "streaming_parse":
                    if self._streaming_json_parser is not None:
                        streaming_parsed = None
                        if event == "delta":
                            streaming_parsed = self._streaming_json_parser.parse_chunk(data)
                        elif event == "done":
                            streaming_parsed = self._streaming_json_parser.finalize()
                        if streaming_parsed:
                            for streaming_data in FunctionShifter.syncify_async_generator(streaming_parsed):
                                if _streaming_parse_path_style == "slash":
                                    streaming_data.path = DataPathBuilder.convert_dot_to_slash(streaming_data.path)
                                yield streaming_data
                case "original":
                    if event.startswith("original"):
                        yield data
