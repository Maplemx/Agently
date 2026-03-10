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


import uuid
import copy
import json
import asyncio
import contextlib
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from json import JSONDecodeError
from asyncio import Event, Semaphore
from collections.abc import Mapping
from typing import Any, Literal, TYPE_CHECKING, Sequence, cast

if TYPE_CHECKING:
    from agently.types.trigger_flow import (
        TriggerFlowAllHandlers,
        TriggerFlowHandler,
        TriggerFlowPathReadable,
        TriggerFlowPathWritable,
        TriggerFlowSubFlowCapture,
        TriggerFlowSubFlowWriteBack,
    )
    from .TriggerFlow import TriggerFlow

from agently.types.data import EMPTY
from agently.types.trigger_flow import RUNTIME_STREAM_STOP
from agently.utils import RuntimeData, RuntimeDataNamespace
from .Chunk import TriggerFlowChunk
from .Execution import TriggerFlowExecution
from .Definition import (
    TriggerFlowDefinition,
    build_callable_ref,
    is_callable_ref_exportable,
    make_signal_ref,
    render_callable_ref,
)

_SUB_FLOW_PATH_SEGMENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CAPTURE_TARGET_SCOPES = frozenset({"input", "runtime_data", "flow_data", "resources"})
_CAPTURE_SOURCE_SCOPES = frozenset({"value", "runtime_data", "flow_data", "resources"})
_WRITE_BACK_TARGET_SCOPES = frozenset({"value", "runtime_data", "flow_data"})
_WRITE_BACK_SOURCE_SCOPES = frozenset({"result"})


@dataclass(frozen=True)
class _CompiledSubFlowBinding:
    target_scope: Literal["input", "runtime_data", "flow_data", "resources", "value"]
    target_path: tuple[str, ...]
    source_scope: Literal["value", "runtime_data", "flow_data", "resources", "result"]
    source_path: tuple[str, ...]


def _clone_sub_flow_value(value: Any):
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


def _read_sub_flow_value_by_path(root_value: Any, path: tuple[str, ...], *, scope: str):
    current = root_value
    for segment in path:
        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue
        raise KeyError(f"TriggerFlow sub flow path '{ scope }.{ '.'.join(path) }' not found.")
    return _clone_sub_flow_value(current)


class _ParentSubFlowCaptureSource:
    def __init__(self, data):
        self._scopes = {
            "value": data.value,
            "runtime_data": data.state.to_dict(),
            "flow_data": data.flow_state.to_dict(),
            "resources": data.resources.to_dict(),
        }

    def read_path(self, scope: str, path: tuple[str, ...]):
        return _read_sub_flow_value_by_path(self._scopes[scope], path, scope=scope)


class _SubFlowWriteBackSource:
    def __init__(self, result: Any):
        self._result = result

    def read_path(self, scope: str, path: tuple[str, ...]):
        if scope != "result":
            raise KeyError(f"Unsupported TriggerFlow sub flow write back source scope '{ scope }'.")
        return _read_sub_flow_value_by_path(self._result, path, scope=scope)


class _SubFlowCaptureTarget:
    def __init__(self):
        self._has_input = False
        self._input_value = None
        self._runtime_data = RuntimeData()
        self._flow_data = RuntimeData()
        self._resources = RuntimeData()

    def write_path(self, scope: str, path: tuple[str, ...], value: Any):
        copied_value = _clone_sub_flow_value(value)
        if scope == "input":
            if len(path) == 0:
                self._input_value = copied_value
                self._has_input = True
                return
            current_input = self._input_value if isinstance(self._input_value, dict) else {}
            input_data = RuntimeData(_clone_sub_flow_value(current_input))
            input_data.set(".".join(path), copied_value)
            self._input_value = input_data.get(None, {}, inherit=False)
            self._has_input = True
            return

        target_scope = {
            "runtime_data": self._runtime_data,
            "flow_data": self._flow_data,
            "resources": self._resources,
        }[scope]
        target_scope.set(".".join(path), copied_value)

    def build_input(self):
        return _clone_sub_flow_value(self._input_value) if self._has_input else None

    def build_runtime_data(self):
        return self._runtime_data.get(None, {}, inherit=False)

    def build_flow_data(self):
        return self._flow_data.get(None, {}, inherit=False)

    def build_resources(self):
        return self._resources.get(None, {}, inherit=False)


class _SubFlowWriteBackTarget:
    def __init__(self, initial_value: Any):
        self._has_value_binding = False
        self._current_value = _clone_sub_flow_value(initial_value)
        initial_mapping = self._current_value if isinstance(self._current_value, dict) else {}
        self._value_data = RuntimeData(_clone_sub_flow_value(initial_mapping))
        self._runtime_data = RuntimeData()
        self._flow_data = RuntimeData()

    def write_path(self, scope: str, path: tuple[str, ...], value: Any):
        copied_value = _clone_sub_flow_value(value)
        if scope == "value":
            self._has_value_binding = True
            if len(path) == 0:
                self._current_value = copied_value
                return
            if not isinstance(self._current_value, dict):
                self._current_value = {}
                self._value_data = RuntimeData({})
            self._value_data.set(".".join(path), copied_value)
            self._current_value = self._value_data.get(None, {}, inherit=False)
            return

        target_scope = {
            "runtime_data": self._runtime_data,
            "flow_data": self._flow_data,
        }[scope]
        target_scope.set(".".join(path), copied_value)

    def apply(self, data):
        if self._has_value_binding:
            data.value = _clone_sub_flow_value(self._current_value)

        runtime_data_patch = self._runtime_data.get(None, {}, inherit=False)
        for key, value in runtime_data_patch.items():
            data.execution._runtime_data.set(key, _clone_sub_flow_value(value))

        flow_data_patch = self._flow_data.get(None, {}, inherit=False)
        for key, value in flow_data_patch.items():
            data.execution._trigger_flow._flow_data.set(key, _clone_sub_flow_value(value))


class TriggerFlowBluePrint:
    def __init__(self, *, name: str | None = None):
        self.name = name if name is not None else f"BluePrint-{ uuid.uuid4().hex }"
        self._handlers: "TriggerFlowAllHandlers" = {
            "event": {},
            "flow_data": {},
            "runtime_data": {},
        }
        self.chunks: dict[str, TriggerFlowChunk] = {}
        self.definition = TriggerFlowDefinition(name=self.name)
        self._chunk_registry: dict[str, Any] = {}
        self._condition_registry: dict[str, Any] = {}

    def _get_registry(self, registry_type: Literal["chunk", "condition"]):
        return self._chunk_registry if registry_type == "chunk" else self._condition_registry

    def _register_callable(
        self,
        registry_type: Literal["chunk", "condition"],
        handler: Any,
        *,
        name: str | None = None,
        strict: bool,
    ):
        callable_ref = build_callable_ref(handler, explicit_name=name)
        registry_name = callable_ref.get("name")
        if callable_ref["kind"] in {"registered", "inspected"} and registry_name:
            registry = self._get_registry(registry_type)
            existing = registry.get(str(registry_name))
            if existing is not None and existing is not handler:
                if strict or name is not None:
                    raise ValueError(
                        f"TriggerFlow { registry_type } handler '{ registry_name }' is already registered to another callable."
                    )
                fallback_ref = copy.deepcopy(callable_ref)
                fallback_ref["kind"] = "anonymous"
                return fallback_ref
            registry[str(registry_name)] = handler
            return callable_ref
        if strict:
            raise ValueError(
                f"TriggerFlow { registry_type } handler '{ render_callable_ref(callable_ref) }' "
                "must be a named function to support config import/export."
            )
        return callable_ref

    def register_chunk_handler(self, handler: Any, *, name: str | None = None):
        self._register_callable("chunk", handler, name=name, strict=True)
        return self

    def register_condition_handler(self, handler: Any, *, name: str | None = None):
        self._register_callable("condition", handler, name=name, strict=True)
        return self

    def _resolve_callable(self, registry_type: Literal["chunk", "condition"], callable_ref: dict[str, Any] | None):
        if not is_callable_ref_exportable(callable_ref):
            raise ValueError(
                f"Cannot load TriggerFlow config because { registry_type } reference "
                f"'{ render_callable_ref(callable_ref) }' is not serializable."
            )
        assert callable_ref is not None
        name = str(callable_ref["name"])
        registry = self._get_registry(registry_type)
        if name not in registry:
            raise ValueError(
                f"Cannot load TriggerFlow config because { registry_type } handler '{ name }' is not registered."
            )
        return registry[name]

    def make_signal(
        self,
        trigger_type: Literal["event", "runtime_data", "flow_data"],
        trigger_event: str,
        *,
        role: str | None = None,
    ):
        return make_signal_ref(trigger_type, trigger_event, role=role)

    def _mark_operator_group(
        self,
        operator_id: str,
        *,
        group_id: str | None = None,
        group_kind: str | None = None,
        parent_group_id: str | None = None,
        parent_group_kind: str | None = None,
    ):
        if group_id is None or group_kind is None:
            return self.definition.get_operator(operator_id)
        operator = self.definition.get_operator(operator_id)
        if operator.get("group_id") is None:
            operator["group_id"] = group_id
            operator["group_kind"] = group_kind
            operator["parent_group_id"] = parent_group_id
            operator["parent_group_kind"] = parent_group_kind
            return operator
        if operator.get("group_id") == group_id and operator.get("group_kind") == group_kind:
            if operator.get("parent_group_id") is None and parent_group_id is not None:
                operator["parent_group_id"] = parent_group_id
                operator["parent_group_kind"] = parent_group_kind
            return operator
        options = copy.deepcopy(operator.get("options", {}))
        usage_groups = options.get("usage_groups", [])
        group_entry = {
            "group_id": group_id,
            "group_kind": group_kind,
            "parent_group_id": parent_group_id,
            "parent_group_kind": parent_group_kind,
        }
        if group_entry not in usage_groups:
            usage_groups.append(group_entry)
        options["usage_groups"] = usage_groups
        operator["options"] = options
        return operator

    def create_chunk(
        self,
        handler: "TriggerFlowHandler",
        *,
        name: str | None = None,
        explicit_name: str | None = None,
    ):
        callable_ref = self._register_callable("chunk", handler, name=explicit_name, strict=False)
        chunk = TriggerFlowChunk(
            handler,
            name=name,
            callable_ref=callable_ref,
            blue_print=self,
        )
        self.chunks[chunk.name] = chunk
        self.sync_chunk_definition(chunk)
        return chunk

    def _merge_callable_registry(
        self,
        registry_type: Literal["chunk", "condition"],
        source_registry: dict[str, Any],
    ):
        target_registry = self._get_registry(registry_type)
        for name, handler in source_registry.items():
            existing = target_registry.get(name)
            if existing is not None and existing is not handler:
                raise ValueError(
                    f"TriggerFlow { registry_type } handler '{ name }' is already registered to another callable."
                )
            target_registry[name] = handler
        return self

    def _merge_registries_from_blue_print(self, blue_print: "TriggerFlowBluePrint"):
        self._merge_callable_registry("chunk", blue_print._chunk_registry)
        self._merge_callable_registry("condition", blue_print._condition_registry)
        return self

    def sync_chunk_definition(
        self,
        chunk: TriggerFlowChunk,
        *,
        group_id: str | None = None,
        group_kind: str | None = None,
        parent_group_id: str | None = None,
        parent_group_kind: str | None = None,
    ):
        emit_signals = [
            self.make_signal("event", chunk.trigger, role="continuation"),
            *[self.make_signal("event", signal, role="declared_emit") for signal in chunk.emit_signals],
        ]
        if chunk.id not in {operator["id"] for operator in self.definition.operators}:
            self.definition.add_operator(
                id=chunk.id,
                kind="chunk",
                name=chunk.name,
                handler_ref=chunk.callable_ref,
                emit_signals=emit_signals,
                group_id=group_id,
                group_kind=group_kind,
                parent_group_id=parent_group_id,
                parent_group_kind=parent_group_kind,
            )
        else:
            self.definition.update_operator(
                chunk.id,
                name=chunk.name,
                handler_ref=chunk.callable_ref,
                emit_signals=emit_signals,
            )
            self._mark_operator_group(
                chunk.id,
                group_id=group_id,
                group_kind=group_kind,
                parent_group_id=parent_group_id,
                parent_group_kind=parent_group_kind,
            )
        return self.definition.get_operator(chunk.id)

    def attach_chunk(
        self,
        chunk: TriggerFlowChunk,
        listen_signals: list[dict[str, Any]],
        *,
        group_id: str | None = None,
        group_kind: str | None = None,
        parent_group_id: str | None = None,
        parent_group_kind: str | None = None,
    ):
        self.sync_chunk_definition(
            chunk,
            group_id=group_id,
            group_kind=group_kind,
            parent_group_id=parent_group_id,
            parent_group_kind=parent_group_kind,
        )
        self.definition.append_listen_signals(chunk.id, listen_signals)
        self._mark_operator_group(
            chunk.id,
            group_id=group_id,
            group_kind=group_kind,
            parent_group_id=parent_group_id,
            parent_group_kind=parent_group_kind,
        )
        return self.definition.get_operator(chunk.id)

    def _parse_sub_flow_relative_path(self, path: str, *, option_name: str):
        if not isinstance(path, str):
            raise TypeError(
                f"TriggerFlow sub flow { option_name } target path must be a string, got: { type(path) }."
            )
        if path == "":
            raise ValueError(f"TriggerFlow sub flow { option_name } target path can not be empty.")
        segments = tuple(path.split("."))
        for segment in segments:
            if not _SUB_FLOW_PATH_SEGMENT_PATTERN.fullmatch(segment):
                raise ValueError(
                    f"TriggerFlow sub flow { option_name } target path '{ path }' contains invalid segment '{ segment }'."
                )
        return segments

    def _parse_sub_flow_source_path(
        self,
        path: str,
        *,
        mode: Literal["capture", "write_back"],
        target_scope: str,
    ):
        if not isinstance(path, str):
            raise TypeError(
                f"TriggerFlow sub flow { mode } source path for target scope '{ target_scope }' "
                f"must be a string, got: { type(path) }."
            )
        if path == "":
            raise ValueError(
                f"TriggerFlow sub flow { mode } source path for target scope '{ target_scope }' can not be empty."
            )
        segments = tuple(path.split("."))
        root_scope = segments[0]
        allowed_source_scopes = _CAPTURE_SOURCE_SCOPES if mode == "capture" else _WRITE_BACK_SOURCE_SCOPES
        if root_scope not in allowed_source_scopes:
            raise ValueError(
                f"TriggerFlow sub flow { mode } source scope '{ root_scope }' is not supported. "
                f"Allowed scopes: { sorted(allowed_source_scopes) }"
            )
        for segment in segments[1:]:
            if not _SUB_FLOW_PATH_SEGMENT_PATTERN.fullmatch(segment):
                raise ValueError(
                    f"TriggerFlow sub flow { mode } source path '{ path }' contains invalid segment '{ segment }'."
                )
        return root_scope, segments[1:]

    def _normalize_sub_flow_scope_binding(
        self,
        binding: Any,
        *,
        mode: Literal["capture", "write_back"],
        scope: str,
    ):
        if isinstance(binding, str):
            if scope not in {"input", "value"}:
                raise TypeError(
                    f"TriggerFlow sub flow { mode } scope '{ scope }' only accepts key-path mappings."
                )
            return binding

        if not isinstance(binding, Mapping):
            raise TypeError(
                f"TriggerFlow sub flow { mode } scope '{ scope }' expects a string or mapping, got: { type(binding) }."
            )

        normalized_binding: dict[str, str] = {}
        for target_path, source_path in binding.items():
            if not isinstance(target_path, str):
                raise TypeError(
                    f"TriggerFlow sub flow { mode } target path for scope '{ scope }' must be a string, "
                    f"got: { type(target_path) }."
                )
            if not isinstance(source_path, str):
                raise TypeError(
                    f"TriggerFlow sub flow { mode } source path for scope '{ scope }' must be a string, "
                    f"got: { type(source_path) }."
                )
            normalized_binding[str(target_path)] = str(source_path)
        return normalized_binding

    def _normalize_sub_flow_spec(
        self,
        spec: "TriggerFlowSubFlowCapture | TriggerFlowSubFlowWriteBack | None",
        *,
        mode: Literal["capture", "write_back"],
    ):
        if spec is None:
            return None
        if not isinstance(spec, Mapping):
            raise TypeError(f"TriggerFlow sub flow { mode } spec must be a mapping, got: { type(spec) }.")

        allowed_target_scopes = _CAPTURE_TARGET_SCOPES if mode == "capture" else _WRITE_BACK_TARGET_SCOPES
        normalized_spec: dict[str, str | dict[str, str]] = {}
        for target_scope, binding in spec.items():
            if not isinstance(target_scope, str):
                raise TypeError(
                    f"TriggerFlow sub flow { mode } target scope must be a string, got: { type(target_scope) }."
                )
            if target_scope not in allowed_target_scopes:
                raise ValueError(
                    f"TriggerFlow sub flow { mode } target scope '{ target_scope }' is not supported. "
                    f"Allowed scopes: { sorted(allowed_target_scopes) }"
                )
            normalized_spec[target_scope] = self._normalize_sub_flow_scope_binding(
                binding,
                mode=mode,
                scope=target_scope,
            )
        return normalized_spec

    def _validate_sub_flow_target_conflicts(
        self,
        target_paths: list[tuple[str, ...]],
        *,
        mode: Literal["capture", "write_back"],
        scope: str,
    ):
        seen_paths: set[tuple[str, ...]] = set()
        for target_path in sorted(target_paths, key=len):
            if target_path in seen_paths:
                raise ValueError(
                    f"TriggerFlow sub flow { mode } target path '{ scope }.{ '.'.join(target_path) }' is duplicated."
                )
            for depth in range(1, len(target_path)):
                if target_path[:depth] in seen_paths:
                    raise ValueError(
                        f"TriggerFlow sub flow { mode } target paths conflict under scope '{ scope }': "
                        f"'{ scope }.{ '.'.join(target_path[:depth]) }' and '{ scope }.{ '.'.join(target_path) }'."
                    )
            seen_paths.add(target_path)

    def _compile_sub_flow_bindings(
        self,
        spec: "TriggerFlowSubFlowCapture | TriggerFlowSubFlowWriteBack | None",
        *,
        mode: Literal["capture", "write_back"],
    ):
        normalized_spec = self._normalize_sub_flow_spec(spec, mode=mode)
        compiled_bindings: list[_CompiledSubFlowBinding] = []

        if normalized_spec is None:
            default_target_scope = "input" if mode == "capture" else "value"
            default_source_path = "value" if mode == "capture" else "result"
            source_scope, source_path = self._parse_sub_flow_source_path(
                default_source_path,
                mode=mode,
                target_scope=default_target_scope,
            )
            compiled_bindings.append(
                _CompiledSubFlowBinding(
                    target_scope=default_target_scope,
                    target_path=tuple(),
                    source_scope=cast(
                        Literal["value", "runtime_data", "flow_data", "resources", "result"],
                        source_scope,
                    ),
                    source_path=tuple(source_path),
                )
            )
            return normalized_spec, compiled_bindings

        for target_scope, binding in normalized_spec.items():
            if isinstance(binding, str):
                source_scope, source_path = self._parse_sub_flow_source_path(
                    binding,
                    mode=mode,
                    target_scope=target_scope,
                )
                compiled_bindings.append(
                    _CompiledSubFlowBinding(
                        target_scope=cast(
                            Literal["input", "runtime_data", "flow_data", "resources", "value"],
                            target_scope,
                        ),
                        target_path=tuple(),
                        source_scope=cast(
                            Literal["value", "runtime_data", "flow_data", "resources", "result"],
                            source_scope,
                        ),
                        source_path=tuple(source_path),
                    )
                )
                continue

            target_paths: list[tuple[str, ...]] = []
            for target_path_str, source_path_str in binding.items():
                target_path = self._parse_sub_flow_relative_path(
                    target_path_str,
                    option_name=f"{ mode }.{ target_scope }",
                )
                source_scope, source_path = self._parse_sub_flow_source_path(
                    source_path_str,
                    mode=mode,
                    target_scope=target_scope,
                )
                target_paths.append(target_path)
                compiled_bindings.append(
                    _CompiledSubFlowBinding(
                        target_scope=cast(
                            Literal["input", "runtime_data", "flow_data", "resources", "value"],
                            target_scope,
                        ),
                        target_path=target_path,
                        source_scope=cast(
                            Literal["value", "runtime_data", "flow_data", "resources", "result"],
                            source_scope,
                        ),
                        source_path=tuple(source_path),
                    )
                )
            self._validate_sub_flow_target_conflicts(
                target_paths,
                mode=mode,
                scope=target_scope,
            )

        return normalized_spec, compiled_bindings

    def _apply_sub_flow_bindings(
        self,
        bindings: Sequence[_CompiledSubFlowBinding],
        *,
        source: "TriggerFlowPathReadable",
        target: "TriggerFlowPathWritable",
    ):
        for binding in bindings:
            value = source.read_path(binding.source_scope, binding.source_path)
            target.write_path(binding.target_scope, binding.target_path, value)

    def _instantiate_isolated_sub_flow(self, trigger_flow: "TriggerFlow"):
        from .TriggerFlow import TriggerFlow

        isolated_sub_flow = TriggerFlow(
            blue_print=trigger_flow.save_blue_print(),
            name=trigger_flow.name,
            skip_exceptions=trigger_flow._skip_exceptions,
        )
        isolated_sub_flow.settings.update(
            copy.deepcopy(trigger_flow.settings.get(None, {}, inherit=False))
        )
        isolated_sub_flow._flow_data.update(
            copy.deepcopy(trigger_flow._flow_data.get(None, {}, inherit=False))
        )
        isolated_sub_flow._runtime_resources.update(
            copy.deepcopy(trigger_flow._runtime_resources.get(None, {}, inherit=False))
        )
        return isolated_sub_flow

    async def _bridge_sub_flow_runtime_stream(
        self,
        child_execution: TriggerFlowExecution,
        parent_execution: TriggerFlowExecution,
    ):
        while True:
            stream_item = await child_execution._runtime_stream_queue.get()
            if stream_item is RUNTIME_STREAM_STOP:
                return
            await parent_execution.async_put_into_stream(stream_item)

    def _build_sub_flow_from_operator(self, operator: dict[str, Any]):
        from .TriggerFlow import TriggerFlow

        options = operator.get("options", {})
        sub_flow_config = options.get("sub_flow_config")
        if not isinstance(sub_flow_config, dict):
            raise TypeError(
                f"TriggerFlow sub flow operator '{ operator['id'] }' missing valid 'sub_flow_config'."
            )

        sub_blue_print = type(self)(
            name=str(
                sub_flow_config.get("name")
                or options.get("sub_flow_name")
                or operator.get("name")
                or f"SubFlow-{ operator['id'] }"
            )
        )
        sub_blue_print._chunk_registry = self._chunk_registry.copy()
        sub_blue_print._condition_registry = self._condition_registry.copy()
        sub_blue_print.load_flow_config(copy.deepcopy(sub_flow_config))
        return TriggerFlow(
            blue_print=sub_blue_print,
            name=sub_blue_print.name,
        )

    def _compile_sub_flow_operator(
        self,
        operator: dict[str, Any],
        *,
        trigger_flow: "TriggerFlow | None" = None,
    ):
        emit_signal = operator["emit_signals"][0]
        options = operator.get("options", {})
        _, capture_bindings = self._compile_sub_flow_bindings(
            options.get("capture"),
            mode="capture",
        )
        _, write_back_bindings = self._compile_sub_flow_bindings(
            options.get("write_back"),
            mode="write_back",
        )
        concurrency = operator["options"].get("concurrency")
        sub_flow_template = trigger_flow if trigger_flow is not None else self._build_sub_flow_from_operator(operator)

        async def call_sub_flow(data):
            isolated_sub_flow = self._instantiate_isolated_sub_flow(sub_flow_template)

            capture_source = _ParentSubFlowCaptureSource(data)
            capture_target = _SubFlowCaptureTarget()
            self._apply_sub_flow_bindings(
                capture_bindings,
                source=capture_source,
                target=capture_target,
            )

            captured_flow_data = capture_target.build_flow_data()
            if captured_flow_data:
                isolated_sub_flow._flow_data.update(captured_flow_data)

            sub_flow_execution = isolated_sub_flow.create_execution(
                concurrency=concurrency,
            )
            captured_runtime_data = capture_target.build_runtime_data()
            if captured_runtime_data:
                sub_flow_execution._runtime_data.update(captured_runtime_data)

            captured_resources = capture_target.build_resources()
            if captured_resources:
                sub_flow_execution.update_runtime_resources(captured_resources)

            stream_bridge_task = asyncio.create_task(
                self._bridge_sub_flow_runtime_stream(
                    sub_flow_execution,
                    data.execution,
                )
            )
            try:
                await sub_flow_execution.async_start(
                    capture_target.build_input(),
                    wait_for_result=False,
                )
                if sub_flow_execution.is_waiting():
                    raise NotImplementedError(
                        "TriggerFlow sub flow does not yet support child flow pause/resume "
                        "or external re-entry."
                    )
                result = await sub_flow_execution.async_get_result(timeout=None)
            finally:
                stream_bridge_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stream_bridge_task

            write_back_target = _SubFlowWriteBackTarget(data.value)
            self._apply_sub_flow_bindings(
                write_back_bindings,
                source=_SubFlowWriteBackSource(result),
                target=write_back_target,
            )
            write_back_target.apply(data)
            await data.async_emit(
                emit_signal["trigger_event"],
                data.value,
                _layer_marks=data._layer_marks.copy(),
            )

        for signal in operator["listen_signals"]:
            self.add_handler(
                signal["trigger_type"],
                signal["trigger_event"],
                call_sub_flow,
            )

    def attach_sub_flow(
        self,
        trigger_flow: "TriggerFlow",
        listen_signals: list[dict[str, Any]],
        *,
        name: str | None = None,
        capture: "TriggerFlowSubFlowCapture | None" = None,
        write_back: "TriggerFlowSubFlowWriteBack | None" = None,
        concurrency: int | None = None,
        group_id: str | None = None,
        group_kind: str | None = None,
        parent_group_id: str | None = None,
        parent_group_kind: str | None = None,
    ):
        self._merge_registries_from_blue_print(trigger_flow._blue_print)
        normalized_capture, _ = self._compile_sub_flow_bindings(capture, mode="capture")
        normalized_write_back, _ = self._compile_sub_flow_bindings(write_back, mode="write_back")
        sub_flow_instance_id = uuid.uuid4().hex
        operator = self.definition.add_operator(
            id=f"sub-flow-{ sub_flow_instance_id }",
            kind="sub_flow",
            name=name if name is not None else trigger_flow.name,
            listen_signals=listen_signals,
            emit_signals=[
                self.make_signal(
                    "event",
                    f"SubFlow-{ sub_flow_instance_id }-Result",
                    role="continuation",
                )
            ],
            options={
                "sub_flow_name": trigger_flow.name,
                "sub_flow_config": trigger_flow._blue_print.definition.to_dict(name=trigger_flow.name),
                "capture": normalized_capture,
                "write_back": normalized_write_back,
                "concurrency": concurrency,
            },
            group_id=group_id,
            group_kind=group_kind,
            parent_group_id=parent_group_id,
            parent_group_kind=parent_group_kind,
        )
        self._compile_sub_flow_operator(
            operator,
            trigger_flow=trigger_flow,
        )
        return operator

    def add_handler(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        handler_id = str(id) if id is not None else f"Handler<{ handler.__name__ }>-{ uuid.uuid4().hex }"
        handlers = self._handlers[type]
        if target not in handlers:
            handlers[target] = {}
        for stored_id, stored_handler in handlers[target].items():
            if handler == stored_handler:
                return stored_id
        handlers[target][handler_id] = handler
        return handler_id

    def remove_handler(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
        handler: "TriggerFlowHandler | str",
    ):
        handlers = self._handlers[type]
        if target in handlers:
            if isinstance(handler, str):
                handlers[target].pop(handler)
            else:
                for id, stored_handler in handlers[target].items():
                    if handler == stored_handler:
                        del handlers[target][id]
                        return

    def remove_all(
        self,
        type: Literal["event", "flow_data", "runtime_data"],
        target: str,
    ):
        handlers = self._handlers[type]
        if target in handlers:
            handlers[target] = {}

    def add_event_handler(
        self,
        event: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("event", event, handler, id=id)

    def remove_event_handler(
        self,
        event: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("event", event, handler)

    def add_flow_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("flow_data", key, handler, id=id)

    def remove_flow_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("flow_data", key, handler)

    def add_runtime_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler",
        *,
        id: str | None = None,
    ):
        return self.add_handler("runtime_data", key, handler, id=id)

    def remove_runtime_data_handler(
        self,
        key: str,
        handler: "TriggerFlowHandler | str",
    ):
        return self.remove_handler("runtime_data", key, handler)

    def _reset_runtime(self):
        self._handlers = {
            "event": {},
            "flow_data": {},
            "runtime_data": {},
        }
        self.chunks = {}

    @staticmethod
    def _layer_key(data):
        return ".".join(data._layer_marks) if data._layer_marks else "__root__"

    def _compile_chunk_operator(self, operator: dict[str, Any]):
        handler = self._resolve_callable("chunk", operator.get("handler_ref"))
        continuation_signal = next(
            (
                signal
                for signal in operator["emit_signals"]
                if signal.get("role") != "declared_emit"
            ),
            self.make_signal("event", f"Chunk-{ operator['id'] }", role="continuation"),
        )
        chunk = TriggerFlowChunk(
            handler,
            chunk_id=operator["id"],
            name=operator.get("name"),
            trigger=continuation_signal["trigger_event"],
            callable_ref=operator.get("handler_ref"),
            blue_print=self,
            emit_signals=[
                signal["trigger_event"]
                for signal in operator["emit_signals"]
                if signal.get("role") == "declared_emit"
            ],
        )
        self.chunks[chunk.name] = chunk
        for signal in operator["listen_signals"]:
            self.add_handler(
                signal["trigger_type"],
                signal["trigger_event"],
                chunk.async_call,
            )

    def _compile_signal_gate_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]
        mode = operator["options"].get("mode", "and")
        values_template: dict[str, dict[str, Any]] = {}
        for signal in operator["listen_signals"]:
            values_template.setdefault(signal["trigger_type"], {})
            values_template[signal["trigger_type"]][signal["trigger_event"]] = EMPTY

        async def wait_trigger(data):
            match mode:
                case "or" | "simple_or":
                    await data.async_emit(
                        emit_signal["trigger_event"],
                        (
                            data.value
                            if mode == "simple_or"
                            else (data.trigger_type, data.trigger_event, data.value)
                        ),
                        _layer_marks=data._layer_marks.copy(),
                    )
                case "and":
                    state_key = f"when_states.{ operator['id'] }.{ self._layer_key(data) }"
                    state = data._system_runtime_data.get(state_key)
                    if not isinstance(state, dict):
                        state = copy.deepcopy(values_template)
                    if data.trigger_type in state and data.trigger_event in state[data.trigger_type]:
                        state[data.trigger_type][data.trigger_event] = data.value
                    data._system_runtime_data.set(state_key, state)
                    for trigger_event_dict in state.values():
                        for event_value in trigger_event_dict.values():
                            if event_value is EMPTY:
                                return
                    await data.async_emit(
                        emit_signal["trigger_event"],
                        state,
                        _layer_marks=data._layer_marks.copy(),
                    )
                    del data._system_runtime_data[state_key]

        for signal in operator["listen_signals"]:
            self.add_handler(
                signal["trigger_type"],
                signal["trigger_event"],
                wait_trigger,
            )

    def _compile_batch_fanout_operator(self, operator: dict[str, Any]):
        concurrency = operator["options"].get("concurrency")

        async def send_to_branches(data):
            async def emit_branch(signal: dict[str, Any]):
                if concurrency is None or concurrency <= 0:
                    await data.async_emit(
                        signal["trigger_event"],
                        data.value,
                        _layer_marks=data._layer_marks.copy(),
                    )
                    return
                semaphore_key = f"batch_fanout_semaphores.{ operator['id'] }"
                semaphore = data._system_runtime_data.get(semaphore_key, inherit=False)
                if not isinstance(semaphore, Semaphore):
                    semaphore = Semaphore(concurrency)
                    data._system_runtime_data.set(semaphore_key, semaphore)
                async with semaphore:
                    await data.async_emit(
                        signal["trigger_event"],
                        data.value,
                        _layer_marks=data._layer_marks.copy(),
                    )

            await asyncio.gather(*[emit_branch(signal) for signal in operator["emit_signals"]])

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], send_to_branches)

    def _compile_batch_collect_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]
        result_keys = dict(operator["options"].get("result_keys", {}))
        trigger_to_result_key = {signal_id: result_key for signal_id, result_key in result_keys.items()}
        triggers_template = {signal["id"]: False for signal in operator["listen_signals"]}
        results_template = {result_key: None for result_key in trigger_to_result_key.values()}

        async def wait_all_chunks(data):
            signal_id = f"{ data.trigger_type }:{ data.trigger_event }"
            if signal_id not in trigger_to_result_key:
                return
            layer_key = self._layer_key(data)
            state_key = f"batch_states.{ operator['id'] }.{ layer_key }"
            state = data._system_runtime_data.get(state_key)
            if not isinstance(state, dict):
                state = {
                    "results": copy.deepcopy(results_template),
                    "triggers": triggers_template.copy(),
                }
            state["results"][trigger_to_result_key[signal_id]] = data.value
            state["triggers"][signal_id] = True
            data._system_runtime_data.set(state_key, state)
            for done in state["triggers"].values():
                if done is False:
                    return
            await data.async_emit(
                emit_signal["trigger_event"],
                state["results"],
                _layer_marks=data._layer_marks.copy(),
            )
            del data._system_runtime_data[state_key]

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], wait_all_chunks)

    def _compile_for_each_split_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]
        concurrency = operator["options"].get("concurrency")

        async def send_items(data):
            data.layer_in()
            for_each_instance_id = data.layer_mark
            assert for_each_instance_id is not None
            send_tasks = []

            def prepare_item(item):
                data.layer_in()
                item_id = data.layer_mark
                assert item_id is not None
                layer_marks = data._layer_marks.copy()
                data._system_runtime_data.set(f"for_each_results.{ for_each_instance_id }.{ item_id }", EMPTY)
                data.layer_out()
                return layer_marks, item

            async def emit_item(item, layer_marks):
                if concurrency is None or concurrency <= 0:
                    await data.async_emit(
                        emit_signal["trigger_event"],
                        item,
                        layer_marks,
                    )
                else:
                    semaphore_key = f"for_each_semaphores.{ operator['id'] }"
                    semaphore = data._system_runtime_data.get(semaphore_key, inherit=False)
                    if not isinstance(semaphore, asyncio.Semaphore):
                        semaphore = asyncio.Semaphore(concurrency)
                        data._system_runtime_data.set(semaphore_key, semaphore)
                    async with semaphore:
                        await data.async_emit(
                            emit_signal["trigger_event"],
                            item,
                            layer_marks,
                        )

            if not isinstance(data.value, str) and isinstance(data.value, Sequence):
                items = list(data.value)
                for item in items:
                    layer_marks, item_value = prepare_item(item)
                    send_tasks.append(emit_item(item_value, layer_marks))
                await asyncio.gather(*send_tasks)
            else:
                layer_marks, item_value = prepare_item(data.value)
                await emit_item(item_value, layer_marks)

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], send_items)

    def _compile_for_each_collect_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]

        async def collect_results(data):
            for_each_instance_id = data.upper_layer_mark
            item_id = data.layer_mark
            assert for_each_instance_id is not None and item_id is not None
            for_each_results = RuntimeDataNamespace(data._system_runtime_data, "for_each_results")
            if for_each_instance_id in for_each_results and item_id in for_each_results[for_each_instance_id]:
                for_each_results.set(f"{ for_each_instance_id }.{ item_id }", data.value)
                for value in for_each_results.get(for_each_instance_id, {}).values():
                    if value is EMPTY:
                        return
                data.layer_out()
                data.layer_out()
                await data.async_emit(
                    emit_signal["trigger_event"],
                    list(for_each_results[for_each_instance_id].values()),
                    data._layer_marks.copy(),
                )
                for_each_results.delete(for_each_instance_id)

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], collect_results)

    def _compile_match_route_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]
        mode = operator["options"].get("mode", "hit_first")
        cases = []
        for case in operator["options"].get("cases", []):
            condition = None
            if case.get("condition_ref") is not None:
                condition = self._resolve_callable("condition", case["condition_ref"])
            elif "condition_value" in case:
                condition = case["condition_value"]
            cases.append(
                {
                    "route_signal": case.get("route_signal"),
                    "condition": condition,
                    "is_else": bool(case.get("is_else", False)),
                }
            )
        else_signal = operator["options"].get("else_signal")

        async def match_case(data):
            data.layer_in()
            matched_count = 0
            tasks = []
            for case in cases:
                if case["is_else"]:
                    continue
                condition = case["condition"]
                if callable(condition):
                    judgement = condition(data)
                else:
                    judgement = bool(data.value == condition)
                if judgement is True:
                    if mode == "hit_first":
                        await data.async_emit(
                            case["route_signal"]["trigger_event"],
                            data.value,
                            _layer_marks=data._layer_marks.copy(),
                        )
                        return
                    if mode == "hit_all":
                        data.layer_in()
                        matched_count += 1
                        data._system_runtime_data.set(
                            f"match_results.{ data.upper_layer_mark }.{ data.layer_mark }",
                            EMPTY,
                        )
                        tasks.append(
                            data.async_emit(
                                case["route_signal"]["trigger_event"],
                                data.value,
                                _layer_marks=data._layer_marks.copy(),
                            )
                        )
                        data.layer_out()
            await asyncio.gather(*tasks)
            if matched_count == 0:
                if isinstance(else_signal, dict):
                    await data.async_emit(
                        else_signal["trigger_event"],
                        data.value,
                        _layer_marks=data._layer_marks.copy(),
                    )
                else:
                    await data.async_emit(
                        emit_signal["trigger_event"],
                        data.value,
                        _layer_marks=data._layer_marks.copy(),
                    )

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], match_case)

    def _compile_match_case_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]

        async def pass_case(data):
            await data.async_emit(
                emit_signal["trigger_event"],
                data.value,
                _layer_marks=data._layer_marks.copy(),
            )

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], pass_case)

    def _compile_match_collect_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]

        async def collect_branch_result(data):
            match_results = data._system_runtime_data.get(f"match_results.{ data.upper_layer_mark }")
            if match_results:
                if data.layer_mark in match_results:
                    match_results[data.layer_mark] = data.value
                for value in match_results.values():
                    if value is EMPTY:
                        data._system_runtime_data.set(f"match_results.{ data.upper_layer_mark }", match_results)
                        return
                data.layer_out()
                await data.async_emit(
                    emit_signal["trigger_event"],
                    list(match_results.values()),
                    _layer_marks=data._layer_marks.copy(),
                )
                del data._system_runtime_data[f"match_results.{ data.upper_layer_mark }"]
            else:
                data.layer_out()
                await data.async_emit(
                    emit_signal["trigger_event"],
                    data.value,
                    _layer_marks=data._layer_marks.copy(),
                )

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], collect_branch_result)

    def _compile_collect_branch_operator(self, operator: dict[str, Any]):
        emit_signal = operator["emit_signals"][0]
        collect_id = operator["options"].get("collect_id", operator["id"])
        branch_ids = list(operator["options"].get("branch_ids", []))
        branch_id = operator["options"].get("branch_id")
        mode = operator["options"].get("mode", "filled_and_update")

        async def collect_branches(data):
            state_key = f"collect_states.{ collect_id }.{ self._layer_key(data) }"
            state = data._system_runtime_data.get(state_key)
            if not isinstance(state, dict):
                state = {configured_branch_id: EMPTY for configured_branch_id in branch_ids}
            if branch_id is not None:
                state[branch_id] = data.value
            data._system_runtime_data.set(state_key, state)

            for configured_branch_id in branch_ids:
                if state.get(configured_branch_id, EMPTY) is EMPTY:
                    return

            collected = {configured_branch_id: state[configured_branch_id] for configured_branch_id in branch_ids}
            await data.async_emit(
                emit_signal["trigger_event"],
                collected,
                _layer_marks=data._layer_marks.copy(),
            )
            if mode == "filled_then_empty":
                del data._system_runtime_data[state_key]

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], collect_branches)

    def _compile_result_sink_operator(self, operator: dict[str, Any]):
        async def set_default_result(data):
            result = data._system_runtime_data.get("result")
            if result is EMPTY:
                data.set_result(data.value)
            else:
                result_ready = data._system_runtime_data.get("result_ready")
                if isinstance(result_ready, Event):
                    result_ready.set()

        for signal in operator["listen_signals"]:
            self.add_handler(signal["trigger_type"], signal["trigger_event"], set_default_result)

    def _compile_operator(self, operator: dict[str, Any]):
        kind = operator["kind"]
        if kind == "chunk":
            self._compile_chunk_operator(operator)
        elif kind == "signal_gate":
            self._compile_signal_gate_operator(operator)
        elif kind == "batch_fanout":
            self._compile_batch_fanout_operator(operator)
        elif kind == "batch_collect":
            self._compile_batch_collect_operator(operator)
        elif kind == "for_each_split":
            self._compile_for_each_split_operator(operator)
        elif kind == "for_each_collect":
            self._compile_for_each_collect_operator(operator)
        elif kind == "match_route":
            self._compile_match_route_operator(operator)
        elif kind == "match_case":
            self._compile_match_case_operator(operator)
        elif kind == "match_collect":
            self._compile_match_collect_operator(operator)
        elif kind == "collect_branch":
            self._compile_collect_branch_operator(operator)
        elif kind == "sub_flow":
            self._compile_sub_flow_operator(operator)
        elif kind == "result_sink":
            self._compile_result_sink_operator(operator)
        else:
            raise ValueError(f"Unsupported TriggerFlow operator kind '{ kind }' in config compiler.")

    def _compile_definition(self):
        self._reset_runtime()
        for operator in self.definition.operators:
            self._compile_operator(operator)
        return self

    def get_flow_config(self, *, name: str | None = None):
        return self.definition.to_dict(
            validate_serializable=True,
            name=name if name is not None else self.name,
        )

    def get_json_flow(
        self,
        save_to: str | Path | None = None,
        *,
        encoding: str | None = "utf-8",
        name: str | None = None,
    ):
        content = json.dumps(
            self.get_flow_config(name=name),
            indent=2,
            ensure_ascii=False,
        )
        if save_to is not None:
            path = Path(save_to)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=encoding)
        return content

    def get_yaml_flow(
        self,
        save_to: str | Path | None = None,
        *,
        encoding: str | None = "utf-8",
        name: str | None = None,
    ):
        content = yaml.safe_dump(
            self.get_flow_config(name=name),
            indent=2,
            allow_unicode=True,
            sort_keys=False,
        )
        if save_to is not None:
            path = Path(save_to)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=encoding)
        return content

    def to_mermaid(self, *, mode: Literal["simplified", "detailed"] = "simplified", name: str | None = None):
        if name is not None:
            self.definition.name = name
        return self.definition.to_mermaid(mode=mode)

    def load_flow_config(
        self,
        config: dict[str, Any],
        *,
        replace: bool = True,
    ):
        self.definition = TriggerFlowDefinition.from_dict(config)
        self.name = self.definition.name
        self._compile_definition()
        return self

    def load_json_flow(
        self,
        path_or_content: str | Path,
        *,
        replace: bool = True,
        encoding: str | None = "utf-8",
    ):
        path = Path(path_or_content)
        is_json_file = False
        try:
            is_json_file = path.exists() and path.is_file()
        except (OSError, ValueError):
            is_json_file = False
        if is_json_file:
            try:
                content = path.read_text(encoding=encoding)
                config = json.loads(content)
            except (JSONDecodeError, ValueError) as e:
                raise ValueError(f"Cannot load TriggerFlow JSON file '{ path_or_content }'.\nError: { e }")
        else:
            try:
                config = json.loads(str(path_or_content))
            except (JSONDecodeError, ValueError) as e:
                raise ValueError(f"Cannot load TriggerFlow JSON content or file path not existed.\nError: { e }")
        if not isinstance(config, dict):
            raise TypeError(f"Cannot load TriggerFlow JSON config, expect dictionary but got: { type(config) }")
        return self.load_flow_config(config, replace=replace)

    def load_yaml_flow(
        self,
        path_or_content: str | Path,
        *,
        replace: bool = True,
        encoding: str | None = "utf-8",
    ):
        path = Path(path_or_content)
        is_yaml_file = False
        try:
            is_yaml_file = path.exists() and path.is_file()
        except (OSError, ValueError):
            is_yaml_file = False
        if is_yaml_file:
            try:
                content = path.read_text(encoding=encoding)
                config = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Cannot load TriggerFlow YAML file '{ path_or_content }'.\nError: { e }")
        else:
            try:
                config = yaml.safe_load(str(path_or_content))
            except yaml.YAMLError as e:
                raise ValueError(f"Cannot load TriggerFlow YAML content or file path not existed.\nError: { e }")
        if not isinstance(config, dict):
            raise TypeError(f"Cannot load TriggerFlow YAML config, expect dictionary but got: { type(config) }")
        return self.load_flow_config(config, replace=replace)

    def create_execution(
        self,
        trigger_flow: "TriggerFlow",
        *,
        execution_id: str | None = None,
        skip_exceptions: bool = False,
        concurrency: int | None = None,
    ):
        handlers_snapshot: TriggerFlowAllHandlers = {
            "event": {k: v.copy() for k, v in self._handlers["event"].items()},
            "flow_data": {k: v.copy() for k, v in self._handlers["flow_data"].items()},
            "runtime_data": {k: v.copy() for k, v in self._handlers["runtime_data"].items()},
        }
        return TriggerFlowExecution(
            handlers=handlers_snapshot,
            trigger_flow=trigger_flow,
            id=execution_id,
            skip_exceptions=skip_exceptions,
            concurrency=concurrency,
        )

    def copy(self, *, name: str | None = None):
        new_blue_print = type(self)(name=name if name is not None else self.name)
        new_blue_print._handlers = {
            "event": {key: value.copy() for key, value in self._handlers["event"].items()},
            "flow_data": {key: value.copy() for key, value in self._handlers["flow_data"].items()},
            "runtime_data": {key: value.copy() for key, value in self._handlers["runtime_data"].items()},
        }
        new_blue_print.definition = self.definition.copy()
        new_blue_print._chunk_registry = self._chunk_registry.copy()
        new_blue_print._condition_registry = self._condition_registry.copy()
        for chunk in self.chunks.values():
            new_blue_print.chunks[chunk.name] = TriggerFlowChunk(
                chunk._handler,
                chunk_id=chunk.id,
                name=chunk.name,
                trigger=chunk.trigger,
                callable_ref=chunk.callable_ref,
                blue_print=new_blue_print,
                emit_signals=chunk.emit_signals,
            )
        return new_blue_print
