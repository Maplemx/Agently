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


from agently.utils import LazyImport

LazyImport.import_package("fastapi", version_constraint=">=0.104")

import json
from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agently.utils import FunctionShifter
from agently.types.data import SerializableMapping, SerializableValue

from typing import Any, Sequence, Callable, AsyncGenerator, Generator, Protocol, TYPE_CHECKING, ParamSpec, cast

if TYPE_CHECKING:
    from fastapi.params import Depends
    from agently.core import BaseAgent, ModelRequest, TriggerFlow, TriggerFlowExecution

P = ParamSpec("P")


class FastAPIHelperGeneratorFunction(Protocol[P]):
    def __call__(
        self,
        request_data: SerializableMapping,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Generator[SerializableValue, None, None] | AsyncGenerator[SerializableValue, None]: ...


FastAPIHelperResponseWarper = Callable[[SerializableValue | Exception], SerializableValue]


class FastAPIHelperRequestData(BaseModel):
    data: dict[str, Any]
    options: dict[str, Any]


class FastAPIHelper(FastAPI):
    def __init__(
        self,
        *,
        response_provider: "BaseAgent | ModelRequest | TriggerFlow | TriggerFlowExecution | FastAPIHelperGeneratorFunction",
        response_warper: FastAPIHelperResponseWarper | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.response_provider = response_provider
        self.response_warper: FastAPIHelperResponseWarper = (
            response_warper if response_warper is not None else self._default_response_warper
        )

    def _default_response_warper(self, response_data: SerializableValue | Exception):
        if isinstance(response_data, Exception):
            status = 400
            if isinstance(response_data, ValueError):
                status = 422
            elif isinstance(response_data, TimeoutError):
                status = 504
            return {
                "status": status,
                "data": None,
                "msg": str(response_data),
                "error": self._serialize_exception(response_data),
            }
        return {
            "status": 200,
            "data": response_data,
            "msg": None,
        }

    @staticmethod
    def _to_json_safe(value: Any) -> SerializableValue:
        return cast(SerializableValue, json.loads(json.dumps(value, ensure_ascii=False, default=str)))

    def _serialize_exception(self, error: Exception) -> SerializableValue:
        error_data: dict[str, SerializableValue] = {
            "type": error.__class__.__name__,
            "module": error.__class__.__module__,
            "message": str(error),
            "args": self._to_json_safe([str(arg) for arg in getattr(error, "args", [])]),
        }

        if hasattr(error, "errors") and callable(getattr(error, "errors", None)):
            try:
                error_data["validation_errors"] = self._to_json_safe(error.errors())  # type: ignore
            except Exception:
                # Keep default shape stable even if .errors() exists but fails.
                pass

        if error.__cause__ is not None:
            error_data["cause"] = self._to_json_safe(
                {
                    "type": error.__cause__.__class__.__name__,
                    "message": str(error.__cause__),
                }
            )

        if error.__context__ is not None and not error.__suppress_context__:
            error_data["context"] = self._to_json_safe(
                {
                    "type": error.__context__.__class__.__name__,
                    "message": str(error.__context__),
                }
            )

        return error_data

    def _dump_json(self, item: SerializableValue | Exception):
        return json.dumps(
            self.response_warper(item),
            ensure_ascii=False,
            default=str,
        )

    def _parse_request_payload(self, payload: Any) -> FastAPIHelperRequestData:
        try:
            if isinstance(payload, (str, bytes)):
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8", errors="replace")
                return FastAPIHelperRequestData.model_validate_json(payload)
            return FastAPIHelperRequestData.model_validate(payload)
        except Exception as e:
            raise ValueError(
                "Invalid request payload, expected JSON object with keys 'data' and 'options'. " f"Error: { e }"
            )

    def _get_async_generator(
        self,
        request_data: "SerializableMapping",
        *,
        options: "SerializableMapping | None" = None,
    ) -> AsyncGenerator:
        from agently.core import BaseAgent, ModelRequest, TriggerFlow, TriggerFlowExecution

        if options is None:
            options = {}

        if isinstance(self.response_provider, BaseAgent):
            if hasattr(self.response_provider, "load_json_prompt"):
                from agently.builtins.agent_extensions import ConfigurePromptExtension

                class ConfigurePromptAgent(ConfigurePromptExtension, BaseAgent): ...

                self.response_provider = cast(ConfigurePromptAgent, self.response_provider)
                self.response_provider.load_json_prompt(json.dumps(request_data, ensure_ascii=False))
                return FunctionShifter.auto_options_func(self.response_provider.get_async_generator)(**options)
            else:
                input_data = {}
                for key, value in request_data.items():
                    if hasattr(self.response_provider, key):
                        getattr(self.response_provider, key)(value)
                    else:
                        input_data[key] = value
                self.response_provider.input(input_data)
                return FunctionShifter.auto_options_func(self.response_provider.get_async_generator)(**options)
        elif isinstance(self.response_provider, ModelRequest):
            input_data = {}
            for key, value in request_data.items():
                if hasattr(self.response_provider, key):
                    getattr(self.response_provider, key)(value)
                else:
                    input_data[key] = value
            self.response_provider.input(input_data)
            return FunctionShifter.auto_options_func(self.response_provider.get_async_generator)(**options)
        elif isinstance(self.response_provider, (TriggerFlow, TriggerFlowExecution)):
            if (
                isinstance(self.response_provider, TriggerFlowExecution)
                and "concurrency" in options
                and isinstance(options["concurrency"], int)
            ):
                self.response_provider.set_concurrency(options["concurrency"])
            return FunctionShifter.auto_options_func(self.response_provider.get_async_runtime_stream)(
                request_data, **options
            )
        elif isinstance(self.response_provider, Callable):
            generator = FunctionShifter.auto_options_func(self.response_provider)(request_data, **options)
            if isinstance(generator, Generator):
                return FunctionShifter.asyncify_sync_generator(generator)
            elif isinstance(generator, AsyncGenerator):
                return generator
            else:
                raise TypeError(
                    f"[Agently FastAPI Helper] FastAPI Helper expected response provider as Agent, ModelRequest, TriggerFlow, TriggerFlowExecution, GeneratorFunction or AsyncGeneratorFunction but got: { self.response_provider } returns { generator }"
                )
        else:
            raise TypeError(
                f"[Agently FastAPI Helper] FastAPI Helper expected response provider as Agent, ModelRequest, TriggerFlow, TriggerFlowExecution, GeneratorFunction or AsyncGeneratorFunction but got: { self.response_provider }"
            )

    async def _async_get_result(
        self,
        request_data: "SerializableMapping",
        *,
        options: "SerializableMapping | None" = None,
    ):
        from agently.core import BaseAgent, ModelRequest, TriggerFlow, TriggerFlowExecution

        if options is None:
            options = {}

        if isinstance(self.response_provider, BaseAgent):
            if hasattr(self.response_provider, "load_json_prompt"):
                from agently.builtins.agent_extensions import ConfigurePromptExtension

                class ConfigurePromptAgent(ConfigurePromptExtension, BaseAgent): ...

                self.response_provider = cast(ConfigurePromptAgent, self.response_provider)
                self.response_provider.load_json_prompt(json.dumps(request_data, ensure_ascii=False))
                return await FunctionShifter.auto_options_func(self.response_provider.async_start)(**options)
            else:
                input_data = {}
                for key, value in request_data.items():
                    if hasattr(self.response_provider, key):
                        getattr(self.response_provider, key)(value)
                    else:
                        input_data[key] = value
                self.response_provider.input(input_data)
                return await FunctionShifter.auto_options_func(self.response_provider.async_start)(**options)
        elif isinstance(self.response_provider, ModelRequest):
            input_data = {}
            for key, value in request_data.items():
                if hasattr(self.response_provider, key):
                    getattr(self.response_provider, key)(value)
                else:
                    input_data[key] = value
            self.response_provider.input(input_data)
            return await FunctionShifter.auto_options_func(self.response_provider.async_start)(**options)
        elif isinstance(self.response_provider, (TriggerFlow, TriggerFlowExecution)):
            if (
                isinstance(self.response_provider, TriggerFlowExecution)
                and "concurrency" in options
                and isinstance(options["concurrency"], int)
            ):
                self.response_provider.set_concurrency(options["concurrency"])
            return await FunctionShifter.auto_options_func(self.response_provider.async_start)(request_data, **options)
        elif isinstance(self.response_provider, Callable):
            generator = FunctionShifter.auto_options_func(self.response_provider)(request_data, **options)
            if isinstance(generator, Generator):
                return [item for item in generator]
            elif isinstance(generator, AsyncGenerator):
                return [item async for item in generator]
            else:
                raise TypeError(
                    f"[Agently FastAPI Helper] FastAPI Helper expected response provider as Agent, ModelRequest, TriggerFlow, TriggerFlowExecution, GeneratorFunction or AsyncGeneratorFunction but got: { self.response_provider } returns { generator }"
                )
        else:
            raise TypeError(
                f"[Agently FastAPI Helper] FastAPI Helper expected response provider as Agent, ModelRequest, TriggerFlow, TriggerFlowExecution, GeneratorFunction or AsyncGeneratorFunction but got: { self.response_provider }"
            )

    async def websocket_handler(self, websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive()
                if data.get("type") == "websocket.disconnect":
                    break

                try:
                    text_data = data.get("text")
                    bytes_data = data.get("bytes")
                    request = self._parse_request_payload(text_data if text_data is not None else bytes_data)

                    async for item in self._get_async_generator(request.data, options=request.options):
                        await websocket.send_text(self._dump_json(cast("SerializableValue", item)))
                except Exception as e:
                    await websocket.send_text(self._dump_json(cast("SerializableValue | Exception", e)))
        except WebSocketDisconnect:
            return

    async def sse_handler(
        self,
        payload: str,
    ):
        async def event_stream():
            try:
                request = self._parse_request_payload(payload)
                async for item in self._get_async_generator(request.data, options=request.options):
                    yield f"data: {self._dump_json(cast('SerializableValue', item))}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {self._dump_json(cast('SerializableValue | Exception', e))}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
        )

    async def post_handler(self, body: Any = Body(default=None)):
        try:
            request = self._parse_request_payload(body)
            result = await self._async_get_result(request.data, options=request.options)
            return self.response_warper(cast("SerializableValue", result))
        except Exception as e:
            return self.response_warper(cast("SerializableValue | Exception", e))

    async def get_handler(
        self,
        payload: str,
    ):
        try:
            request = self._parse_request_payload(payload)
            result = await self._async_get_result(request.data, options=request.options)
            return self.response_warper(cast("SerializableValue", result))
        except Exception as e:
            return self.response_warper(cast("SerializableValue | Exception", e))

    def use_sse(
        self,
        path: str,
        name: str | None = None,
        *,
        dependencies: "Sequence[Depends] | None" = None,
    ):
        self.get(
            path,
            name=name,
            dependencies=dependencies,
        )(self.sse_handler)
        return self

    def use_websocket(
        self,
        path: str,
        name: str | None = None,
        *,
        dependencies: "Sequence[Depends] | None" = None,
    ):
        self.websocket(
            path,
            name,
            dependencies=dependencies,
        )(self.websocket_handler)
        return self

    def use_post(
        self,
        path: str,
        name: str | None = None,
        *,
        dependencies: "Sequence[Depends] | None" = None,
    ):
        self.post(
            path,
            name=name,
            dependencies=dependencies,
        )(self.post_handler)
        return self

    def use_get(
        self,
        path: str,
        name: str | None = None,
        *,
        dependencies: "Sequence[Depends] | None" = None,
    ):
        self.get(
            path,
            name=name,
            dependencies=dependencies,
        )(self.get_handler)
        return self
