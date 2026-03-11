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

import copy
from typing import Any, Generic, TypeVar

from pydantic import TypeAdapter, ValidationError

from agently.types.trigger_flow import (
    TRIGGER_FLOW_INTERRUPT_EVENT_SCHEMA,
    TriggerFlowContractEntry,
    TriggerFlowContractMetadata,
    TriggerFlowContractSpec,
    TriggerFlowSystemStreamMetadata,
)

InputT = TypeVar("InputT")
StreamT = TypeVar("StreamT")
ResultT = TypeVar("ResultT")

CONTRACT_UNSET = object()

class TriggerFlowContract(Generic[InputT, StreamT, ResultT]):
    def __init__(
        self,
        *,
        initial_input: Any | None = None,
        stream: Any | None = None,
        result: Any | None = None,
        meta: dict[str, Any] | None = None,
    ):
        self.initial_input: Any | None = None
        self.stream: Any | None = None
        self.result: Any | None = None
        self.meta: dict[str, Any] = {}
        self._initial_input_adapter: TypeAdapter[Any] | None = None
        self._stream_adapter: TypeAdapter[Any] | None = None
        self._result_adapter: TypeAdapter[Any] | None = None
        self.update(
            initial_input=initial_input,
            stream=stream,
            result=result,
            meta=meta,
        )

    def _build_adapter(self, contract: Any | None, contract_name: str):
        if contract is None:
            return None
        try:
            return TypeAdapter(contract)
        except Exception as e:
            raise TypeError(
                f"Invalid TriggerFlow contract '{ contract_name }': { contract }\n"
                "Tips: use a Pydantic model, a Python type, or a supported typing annotation."
            ) from e

    def update(
        self,
        *,
        initial_input: Any = CONTRACT_UNSET,
        stream: Any = CONTRACT_UNSET,
        result: Any = CONTRACT_UNSET,
        meta: dict[str, Any] | None | object = CONTRACT_UNSET,
    ):
        if initial_input is not CONTRACT_UNSET:
            self.initial_input = initial_input
            self._initial_input_adapter = self._build_adapter(initial_input, "initial_input")
        if stream is not CONTRACT_UNSET:
            self.stream = stream
            self._stream_adapter = self._build_adapter(stream, "stream")
        if result is not CONTRACT_UNSET:
            self.result = result
            self._result_adapter = self._build_adapter(result, "result")
        if meta is not CONTRACT_UNSET:
            self.meta = dict(meta) if isinstance(meta, dict) else {}
        return self

    def snapshot(self) -> TriggerFlowContractSpec[InputT, StreamT, ResultT]:
        return TriggerFlowContractSpec[InputT, StreamT, ResultT](
            initial_input=self.initial_input,
            stream=self.stream,
            result=self.result,
            meta=self.meta.copy(),
        )

    def _export_entry(
        self,
        contract: Any | None,
        adapter: TypeAdapter[Any] | None,
    ) -> TriggerFlowContractEntry | None:
        if contract is None:
            return None
        schema = None
        if adapter is not None:
            try:
                schema = adapter.json_schema()
            except Exception:
                schema = None
        label = None
        if isinstance(schema, dict) and isinstance(schema.get("title"), str):
            label = schema["title"]
        if label is None and isinstance(contract, type) and hasattr(contract, "__name__"):
            label = contract.__name__
        if label is None:
            label = str(contract)
        return {
            "label": str(label),
            "schema": schema,
        }

    def export_metadata(self) -> TriggerFlowContractMetadata:
        initial_input = self._export_entry(self.initial_input, self._initial_input_adapter)
        stream = self._export_entry(self.stream, self._stream_adapter)
        result = self._export_entry(self.result, self._result_adapter)
        meta = self.meta.copy()
        system_stream: TriggerFlowSystemStreamMetadata = {
            "interrupt": {
                "label": "TriggerFlowInterruptEvent",
                "schema": copy.deepcopy(TRIGGER_FLOW_INTERRUPT_EVENT_SCHEMA),
            }
        }
        if initial_input is None and stream is None and result is None and not meta:
            return {}
        return {
            "initial_input": initial_input,
            "stream": stream,
            "result": result,
            "meta": meta,
            "system_stream": system_stream,
        }

    def _validate(self, contract_name: str, value: Any, adapter: TypeAdapter[Any] | None):
        if adapter is None:
            return value
        try:
            return adapter.validate_python(value)
        except ValidationError as e:
            raise ValueError(f"TriggerFlow contract validation failed for '{ contract_name }': { e }") from e

    def validate_initial_input(self, value: Any):
        return self._validate("initial_input", value, self._initial_input_adapter)

    def validate_stream_item(self, value: Any):
        return self._validate("stream", value, self._stream_adapter)

    def validate_result(self, value: Any):
        return self._validate("result", value, self._result_adapter)
