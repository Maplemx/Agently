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

import time
import yaml
import json
from typing import (
    Any,
    Literal,
    AsyncGenerator,
    TYPE_CHECKING,
    cast,
)
from typing_extensions import TypedDict

from httpx import AsyncClient, ReadError, HTTPStatusError, RequestError, Timeout
from httpx_sse import aconnect_sse, SSEError
from stamina import retry

from agently.types.plugins import ModelRequester
from agently.types.data import AgentlyRequestData, SerializableValue
from agently.utils import (
    SettingsNamespace,
    DataFormatter,
    DataLocator,
)

if TYPE_CHECKING:
    from agently.core.Prompt import Prompt
    from agently.utils import Settings
    from agently.types.data import AgentlyResponseGenerator, AgentlyRequestDataDict, ChatMessage


class ContentMapping(TypedDict):
    id: str | None
    role: str | None
    delta: str | None
    done: str | None
    usage: str | None
    finish_reason: str | None
    extra_delta: dict[str, str] | None
    extra_done: dict[str, str] | None


class ModelSettingsMapping(TypedDict):
    chat: str
    completions: str
    embeddings: str


class ModelRequesterSettings(TypedDict, total=False):
    model: str
    model_type: Literal["chat", "completions", "embeddings"]
    client_options: dict[str, "SerializableValue"]
    headers: dict[str, "SerializableValue"]
    proxy: str
    request_options: dict[str, "SerializableValue"]
    base_url: str
    path_mapping: ModelSettingsMapping
    default_model: ModelSettingsMapping
    auth: "SerializableValue"
    stream: bool
    rich_content: bool
    strict_role_orders: bool
    content_mapping: ContentMapping
    content_mapping_style: Literal["dot", "slash"]


class OpenAICompatible(ModelRequester):
    name = "OpenAICompatible"

    DEFAULT_SETTINGS = {
        "$mappings": {
            "path_mappings": {
                "OpenAICompatible": "plugins.ModelRequester.OpenAICompatible",
            },
        },
        "model_type": "chat",
        "model": None,
        "default_model": {
            "chat": "gpt-4.1",
            "completions": "gpt-3.5-turbo-instruct",
            "embeddings": "text-embedding-ada-002",
        },
        "client_options": {},
        "headers": {},
        "proxy": None,
        "request_options": {},
        "base_url": "https://api.openai.com/v1",
        "path_mapping": {
            "chat": "/chat/completions",
            "completions": "/completions",
            "embeddings": "/embeddings",
        },
        "auth": None,
        "stream": True,
        "rich_content": False,
        "strict_role_orders": True,
        "content_mapping": {
            "id": "id",
            "role": "choices[0].delta.role",
            "delta": "choices[0].delta.content",
            "done": None,
            "usage": "usage",
            "finish_reason": "choices[0].finish_reason",
            "extra_delta": {
                "tool_calls": "choices[0].delta.tool_calls",
                "function_call": "choices[0].delta.function_call",
            },
            "extra_done": None,
        },
        "content_mapping_style": "dot",
        "timeout": {
            "connect": 30.0,
            "read": 600.0,
            "write": 30.0,
            "pool": 30.0,
        },
    }

    def __init__(
        self,
        prompt: "Prompt",
        settings: "Settings",
    ):
        from agently.base import event_center

        self.prompt = prompt
        self.settings = settings
        self.plugin_settings = SettingsNamespace(self.settings, f"plugins.ModelRequester.{ self.name }")
        self.model_type = cast(str, self.plugin_settings.get("model_type"))
        self._messenger = event_center.create_messenger(self.name)

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    def generate_request_data(self) -> "AgentlyRequestData":
        agently_request_dict: AgentlyRequestDataDict = {
            "client_options": {},
            "headers": {},
            "data": {},
            "request_options": {},
            "request_url": "",
        }
        # main data
        match self.model_type:
            case "chat":
                request_data = {
                    "messages": self.prompt.to_messages(
                        rich_content=bool(
                            self.plugin_settings.get(
                                "rich_content",
                                False,
                            )
                        ),
                        strict_role_orders=bool(
                            self.plugin_settings.get(
                                "strict_role_orders",
                                False,
                            ),
                        ),
                    )
                }
            case "completions":
                request_data = {"prompt": self.prompt.to_text()}
            case "embeddings":
                sanitized_input = DataFormatter.sanitize(self.prompt["input"])
                request_data = {
                    "input": (
                        str(sanitized_input)
                        if isinstance(sanitized_input, (str, int, float, bool)) or sanitized_input is None
                        else yaml.safe_dump(sanitized_input)
                    )
                }
            case _:
                self._messenger.error(
                    TypeError(
                        f"Plugin Name: { self.name }\n" f"Error: Cannot support model type: '{ self.model_type }'"
                    ),
                    status="FAILED",
                )
                request_data = {}
        ## set
        agently_request_dict["data"] = request_data

        # headers
        headers = DataFormatter.to_str_key_dict(
            self.plugin_settings.get("headers"),
            value_format="str",
            default={},
        )
        headers.update({"Connection": "close"})
        ## set
        agently_request_dict["headers"] = headers

        # client options
        client_options = DataFormatter.to_str_key_dict(self.plugin_settings.get("client_options"))
        ## proxy
        proxy = self.plugin_settings.get("proxy", None)
        if proxy:
            client_options.update({"proxy": proxy})
        ## timeout
        timeout_configs = DataFormatter.to_str_key_dict(
            self.plugin_settings.get(
                "timeout",
                {
                    "connect": 30.0,
                    "read": 120.0,
                    "write": 30.0,
                    "pool": 30.0,
                },
            )
        )
        timeout = Timeout(**timeout_configs)
        client_options.update({"timeout": timeout})
        ## set
        agently_request_dict["client_options"] = client_options

        # request_options
        request_options = DataFormatter.to_str_key_dict(
            self.plugin_settings.get("request_options"),
            value_format="serializable",
        )
        ## !: ensure model
        request_options.update(
            {
                "model": self.plugin_settings.get(
                    "model",
                    DataFormatter.to_str_key_dict(
                        self.plugin_settings.get("default_model"),
                        value_format="serializable",
                        default={self.model_type: self.plugin_settings.get("default_model")},
                    )[self.model_type],
                )
            }
        )
        ## !: ensure stream
        is_stream = self.plugin_settings.get("stream", True)
        request_options.update({"stream": is_stream})
        ## set
        agently_request_dict["request_options"] = request_options

        # request url
        ## get base url
        base_url = str(self.plugin_settings.get("base_url"))
        base_url = base_url[:-1] if base_url[-1] == "/" else base_url
        ## get path mapping
        path_mapping = DataFormatter.to_str_key_dict(
            self.plugin_settings.get("path_mapping"),
            value_format="str",
        )
        path_mapping = {k: v if v[0] == "/" else f"/{ v }" for k, v in path_mapping.items()}
        ## set
        request_url = f"{ base_url }{ path_mapping[self.model_type] }"
        agently_request_dict["request_url"] = request_url

        return AgentlyRequestData(**agently_request_dict)

    async def _aiter_sse_with_retry(
        self,
        client: AsyncClient,
        method: str,
        url: str,
        *,
        headers: dict[str, Any],
        json: "SerializableValue",
    ):
        last_event_id = ""
        reconnection_delay = 0.0

        @retry(on=ReadError)
        async def _aiter_sse():
            nonlocal last_event_id, reconnection_delay
            time.sleep(reconnection_delay)
            headers.update({"Accept": "text/event-stream"})
            if last_event_id:
                headers.update({"Last-Event-ID": last_event_id})

            async with aconnect_sse(client, method, url, headers=headers, json=json) as event_source:
                try:
                    async for sse in event_source.aiter_sse():
                        last_event_id = sse.id
                        if sse.retry is not None:
                            reconnection_delay = sse.retry / 1000
                        yield sse
                except GeneratorExit:
                    pass

        return _aiter_sse()

    async def request_model(self, request_data: "AgentlyRequestData") -> AsyncGenerator[tuple[str, Any], None]:
        # auth
        auth = DataFormatter.to_str_key_dict(
            self.plugin_settings.get("auth", "None"),
            value_format="serializable",
            default={"api_key": self.plugin_settings.get("auth", "None")},
        )
        headers_with_auth = {**request_data.headers, "Authorization": f"Bearer { auth['api_key'] }"}

        # request
        # stream request
        if self.model_type in ("chat", "completions") and request_data.stream:
            async with AsyncClient(**request_data.client_options) as client:
                client.headers.update(headers_with_auth)
                full_request_data = DataFormatter.to_str_key_dict(request_data.data, value_format="serializable")
                full_request_data.update(request_data.request_options)
                try:
                    async for sse in await self._aiter_sse_with_retry(
                        client, "POST", request_data.request_url, json=full_request_data, headers=headers_with_auth
                    ):
                        yield sse.event, sse.data
                except SSEError as e:
                    response = await client.post(
                        request_data.request_url,
                        json=full_request_data,
                        headers=headers_with_auth,
                    )
                    content_type = response.headers.get("Content-Type", "")
                    if content_type.startswith("application/json"):
                        try:
                            error_json = response.json()
                        except Exception:
                            error_json = await response.aread()
                            error_json = json.loads(error_json.decode())
                        error = error_json["error"]
                        error_title = f"{ error['code'] if 'code' in error else 'unknown_code' } - { error['type'] if 'type' in error else 'unknown_type' }"
                        error_detail = error["message"] if "message" in error else ""
                        yield "error", error_detail
                    else:
                        self._messenger.error(
                            "Error: SSE Error\n" f"Detail: {e}\n" f"Request Data: {full_request_data}", status="FAILED"
                        )
                        yield "error", e
                except HTTPStatusError as e:
                    self._messenger.error(
                        "Error: HTTP Status Error\n"
                        f"Detail: { e.response.status_code } - { e.response.text }\n"
                        f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                except RequestError as e:
                    self._messenger.error(
                        "Error: Request Error\n" f"Detail: { e }\n" f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                except Exception as e:
                    self._messenger.error(
                        "Error: Unknown Error\n" f"Detail: { e }\n" f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                finally:
                    await client.aclose()
        # normal request
        else:
            async with AsyncClient(**request_data.client_options) as client:
                client.headers.update(headers_with_auth)
                full_request_data = DataFormatter.to_str_key_dict(request_data.data, value_format="serializable")
                full_request_data.update(request_data.request_options)
                try:
                    response = await client.post(
                        request_data.request_url,
                        json=full_request_data,
                    )
                    yield "message", response.content.decode()
                    yield "message", "[DONE]"
                except HTTPStatusError as e:
                    self._messenger.error(
                        "Error: HTTP Status Error\n"
                        f"Detail: { e.response.status_code } - { e.response.text }\n"
                        f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                except RequestError as e:
                    self._messenger.error(
                        "Error: Request Error\n" f"Detail: { e }\n" f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                except Exception as e:
                    self._messenger.error(
                        "Error: Unknown Error\n" f"Detail: { e }\n" f"Request Data: { full_request_data }",
                        status="FAILED",
                    )
                    yield "error", e
                finally:
                    await client.aclose()

    async def broadcast_response(self, response_generator: AsyncGenerator) -> "AgentlyResponseGenerator":
        meta = {}
        message_record = {}
        content_buffer = ""

        content_mapping = cast(
            ContentMapping,
            DataFormatter.to_str_key_dict(
                self.plugin_settings.get("content_mapping"),
                value_format="serializable",
            ),
        )
        id_mapping = content_mapping["id"]
        role_mapping = content_mapping["role"]
        delta_mapping = content_mapping["delta"]
        done_mapping = content_mapping["done"]
        usage_mapping = content_mapping["usage"]
        finish_reason_mapping = content_mapping["finish_reason"]
        extra_delta_mapping = content_mapping["extra_delta"]
        extra_done_mapping = content_mapping["extra_done"]

        content_mapping_style = str(self.plugin_settings.get("content_mapping_style"))
        if content_mapping_style not in ("dot", "slash"):
            content_mapping_style = "dot"

        async for event, message in response_generator:
            if event == "error":
                yield "error", message
            elif message != "[DONE]":
                yield "original_delta", message
                loaded_message = json.loads(message)
                message_record = loaded_message.copy()
                if "id" not in meta and id_mapping:
                    _id = DataLocator.locate_path_in_dict(
                        loaded_message,
                        id_mapping,
                        style=content_mapping_style,
                    )
                    if _id:
                        meta.update({"id": _id})
                if "role" not in meta and role_mapping:
                    role = DataLocator.locate_path_in_dict(
                        loaded_message,
                        role_mapping,
                        style=content_mapping_style,
                    )
                    if role:
                        meta.update({"role": role})
                if delta_mapping:
                    delta = DataLocator.locate_path_in_dict(
                        loaded_message,
                        delta_mapping,
                        style=content_mapping_style,
                    )
                    if delta:
                        content_buffer += str(delta)
                        yield "delta", delta
                if extra_delta_mapping:
                    for extra_key, extra_path in extra_delta_mapping.items():
                        extra_value = DataLocator.locate_path_in_dict(
                            loaded_message,
                            extra_path,
                            style=content_mapping_style,
                        )
                        if extra_value:
                            yield "extra", {extra_key: extra_value}
            else:
                done_content = None
                if done_mapping:
                    done_content = DataLocator.locate_path_in_dict(
                        message_record,
                        done_mapping,
                        style=content_mapping_style,
                    )
                if done_content:
                    yield "done", done_content
                else:
                    yield "done", content_buffer
                done_message = message_record
                if "message" not in done_message["choices"][0]:
                    done_message["choices"][0].update({"message": {}})
                done_message["choices"][0]["message"].update(
                    {
                        "role": meta["role"] if "role" in meta else "assistant",
                        "content": done_content if done_content else content_buffer,
                    }
                )
                yield "original_done", done_message
                if finish_reason_mapping:
                    meta.update(
                        {
                            "finish_reason": DataLocator.locate_path_in_dict(
                                message_record,
                                finish_reason_mapping,
                                style=content_mapping_style,
                            )
                        }
                    )
                if usage_mapping:
                    meta.update(
                        {
                            "usage": DataLocator.locate_path_in_dict(
                                message_record,
                                usage_mapping,
                                style=content_mapping_style,
                            )
                        }
                    )
                yield "meta", meta
                if extra_done_mapping:
                    for extra_key, extra_path in extra_done_mapping.items():
                        extra_value = DataLocator.locate_path_in_dict(
                            message_record,
                            extra_path,
                            style=content_mapping_style,
                        )
                        if extra_value:
                            yield "extra", {extra_key: extra_value}
