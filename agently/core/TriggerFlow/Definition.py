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
import inspect
import re
import uuid
from typing import Any, Literal


FLOW_CONFIG_VERSION = "trigger_flow/v1"
TriggerFlowSignalType = Literal["event", "runtime_data", "flow_data"]


def make_signal_ref(
    trigger_type: TriggerFlowSignalType,
    trigger_event: str,
    *,
    role: str | None = None,
):
    signal = {
        "id": f"{ trigger_type }:{ trigger_event }",
        "trigger_type": trigger_type,
        "trigger_event": str(trigger_event),
    }
    if role is not None:
        signal["role"] = role
    return signal


def make_internal_event(*parts: str):
    joined = ":".join(str(part) for part in parts if part)
    return f"__trigger_flow__:{ joined }:{ uuid.uuid4().hex }"


def build_callable_ref(
    handler: Any,
    *,
    explicit_name: str | None = None,
):
    raw_name = getattr(handler, "__name__", None)
    qualname = getattr(handler, "__qualname__", None)
    module = getattr(handler, "__module__", None)
    source_file = None
    source_line = None

    try:
        source_file = inspect.getsourcefile(handler) or inspect.getfile(handler)
    except (OSError, TypeError):
        source_file = None

    try:
        _, source_line = inspect.getsourcelines(handler)
    except (OSError, TypeError):
        source_line = None

    is_lambda = raw_name == "<lambda>"
    name = explicit_name if explicit_name is not None else raw_name

    if is_lambda:
        kind = "anonymous"
    elif explicit_name is not None:
        kind = "registered"
    elif raw_name:
        kind = "inspected"
    else:
        kind = "unknown"

    return {
        "kind": kind,
        "name": name,
        "callable_name": raw_name,
        "module": module,
        "qualname": qualname,
        "file": source_file,
        "line": source_line,
    }


def is_callable_ref_exportable(callable_ref: dict[str, Any] | None):
    if not isinstance(callable_ref, dict):
        return False
    if callable_ref.get("kind") not in {"registered", "inspected"}:
        return False
    return bool(callable_ref.get("name"))


def render_callable_ref(callable_ref: dict[str, Any] | None):
    if not isinstance(callable_ref, dict):
        return "unknown"
    if callable_ref.get("name"):
        label = str(callable_ref["name"])
    elif callable_ref.get("callable_name"):
        label = str(callable_ref["callable_name"])
    else:
        label = "unknown"
    if callable_ref.get("kind") == "anonymous":
        if callable_ref.get("file") and callable_ref.get("line"):
            return f"{ label }@{ callable_ref['file'] }:{ callable_ref['line'] }"
        return label
    return label


def _copy_signal(signal: dict[str, Any]):
    copied = {
        "id": str(signal["id"]),
        "trigger_type": str(signal["trigger_type"]),
        "trigger_event": str(signal["trigger_event"]),
    }
    if signal.get("role") is not None:
        copied["role"] = str(signal["role"])
    return copied


def _dedupe_signals(signals: list[dict[str, Any]]):
    seen = set()
    result = []
    for signal in signals:
        key = (
            signal.get("id"),
            signal.get("trigger_type"),
            signal.get("trigger_event"),
            signal.get("role"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(_copy_signal(signal))
    return result


def _sanitize_mermaid_id(value: str):
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", str(value))
    if not sanitized:
        sanitized = "node"
    if sanitized[0].isdigit():
        sanitized = f"n_{ sanitized }"
    return sanitized


def _format_signal_label(signal: dict[str, Any]):
    trigger_type = signal["trigger_type"]
    trigger_event = signal["trigger_event"]
    if trigger_type == "event":
        return str(trigger_event)
    return f"{ trigger_type }:{ trigger_event }"


def _escape_mermaid_label(label: str):
    return str(label).replace('"', "'")


class TriggerFlowDefinition:
    def __init__(
        self,
        *,
        name: str | None = None,
        operators: list[dict[str, Any]] | None = None,
        meta: dict[str, Any] | None = None,
    ):
        self.name = name if name is not None else f"TriggerFlowDefinition-{ uuid.uuid4().hex }"
        self.meta = copy.deepcopy(meta) if meta is not None else {}
        self.operators = copy.deepcopy(operators) if operators is not None else []
        self._operator_index: dict[str, dict[str, Any]] = {}
        for operator in self.operators:
            self._operator_index[str(operator["id"])] = operator

    def copy(self):
        return type(self)(
            name=self.name,
            operators=self.operators,
            meta=self.meta,
        )

    def add_operator(
        self,
        *,
        id: str | None = None,
        kind: str,
        name: str | None = None,
        listen_signals: list[dict[str, Any]] | None = None,
        emit_signals: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
        handler_ref: dict[str, Any] | None = None,
        condition_ref: dict[str, Any] | None = None,
        group_id: str | None = None,
        group_kind: str | None = None,
    ):
        operator_id = str(id) if id is not None else uuid.uuid4().hex
        if operator_id in self._operator_index:
            raise ValueError(f"TriggerFlow operator '{ operator_id }' already exists.")
        operator = {
            "id": operator_id,
            "kind": str(kind),
            "name": name,
            "listen_signals": _dedupe_signals(listen_signals or []),
            "emit_signals": _dedupe_signals(emit_signals or []),
            "options": copy.deepcopy(options) if options is not None else {},
            "handler_ref": copy.deepcopy(handler_ref) if handler_ref is not None else None,
            "condition_ref": copy.deepcopy(condition_ref) if condition_ref is not None else None,
            "group_id": group_id,
            "group_kind": group_kind,
        }
        self.operators.append(operator)
        self._operator_index[operator_id] = operator
        return operator

    def get_operator(self, operator_id: str):
        if operator_id not in self._operator_index:
            raise KeyError(f"TriggerFlow operator '{ operator_id }' not found.")
        return self._operator_index[operator_id]

    def update_operator(self, operator_id: str, **changes):
        operator = self.get_operator(operator_id)
        for key, value in changes.items():
            if key in {"listen_signals", "emit_signals"}:
                operator[key] = _dedupe_signals(value or [])
            elif key in {"handler_ref", "condition_ref"}:
                operator[key] = copy.deepcopy(value) if value is not None else None
            elif key == "options":
                operator[key] = copy.deepcopy(value) if value is not None else {}
            else:
                operator[key] = value
        return operator

    def append_listen_signals(self, operator_id: str, signals: list[dict[str, Any]]):
        operator = self.get_operator(operator_id)
        operator["listen_signals"] = _dedupe_signals([*operator["listen_signals"], *signals])
        return operator

    def set_emit_signals(self, operator_id: str, signals: list[dict[str, Any]]):
        operator = self.get_operator(operator_id)
        operator["emit_signals"] = _dedupe_signals(signals)
        return operator

    def to_dict(self, *, validate_serializable: bool = False, name: str | None = None):
        if validate_serializable:
            self.validate_serializable()
        return {
            "version": FLOW_CONFIG_VERSION,
            "name": name if name is not None else self.name,
            "operators": copy.deepcopy(self.operators),
            "meta": copy.deepcopy(self.meta),
        }

    @classmethod
    def from_dict(cls, config: dict[str, Any]):
        if not isinstance(config, dict):
            raise TypeError(f"Cannot load TriggerFlow config, expect dictionary but got: { type(config) }")
        version = config.get("version", None)
        if version != FLOW_CONFIG_VERSION:
            raise ValueError(
                f"Cannot load TriggerFlow config version '{ version }'. Expected '{ FLOW_CONFIG_VERSION }'."
            )
        operators = config.get("operators", [])
        if not isinstance(operators, list):
            raise TypeError("Cannot load TriggerFlow config, expect key 'operators' as a list.")
        meta = config.get("meta", {})
        if not isinstance(meta, dict):
            raise TypeError("Cannot load TriggerFlow config, expect key 'meta' as a dictionary.")

        normalized_operators: list[dict[str, Any]] = []
        for operator in operators:
            if not isinstance(operator, dict):
                raise TypeError("Cannot load TriggerFlow config, expect every operator to be a dictionary.")
            operator_id = operator.get("id", None)
            kind = operator.get("kind", None)
            if not operator_id or not kind:
                raise ValueError(f"Cannot load TriggerFlow config operator without valid 'id' and 'kind': { operator }")
            listen_signals = operator.get("listen_signals", [])
            emit_signals = operator.get("emit_signals", [])
            if not isinstance(listen_signals, list) or not isinstance(emit_signals, list):
                raise TypeError(
                    f"Cannot load TriggerFlow config operator '{ operator_id }', expect signal fields to be lists."
                )
            normalized_operators.append(
                {
                    "id": str(operator_id),
                    "kind": str(kind),
                    "name": operator.get("name"),
                    "listen_signals": _dedupe_signals(listen_signals),
                    "emit_signals": _dedupe_signals(emit_signals),
                    "options": copy.deepcopy(operator.get("options", {})),
                    "handler_ref": copy.deepcopy(operator.get("handler_ref")),
                    "condition_ref": copy.deepcopy(operator.get("condition_ref")),
                    "group_id": operator.get("group_id"),
                    "group_kind": operator.get("group_kind"),
                }
            )

        return cls(
            name=str(config.get("name", f"TriggerFlowDefinition-{ uuid.uuid4().hex }")),
            operators=normalized_operators,
            meta=meta,
        )

    def validate_serializable(self):
        for operator in self.operators:
            if operator.get("handler_ref") is not None and not is_callable_ref_exportable(operator["handler_ref"]):
                label = render_callable_ref(operator.get("handler_ref"))
                raise ValueError(
                    f"Cannot export TriggerFlow config because operator '{ operator['id'] }' "
                    f"({ operator['kind'] }) uses a non-serializable handler '{ label }'."
                )
            if operator.get("condition_ref") is not None and not is_callable_ref_exportable(operator["condition_ref"]):
                label = render_callable_ref(operator.get("condition_ref"))
                raise ValueError(
                    f"Cannot export TriggerFlow config because operator '{ operator['id'] }' "
                    f"({ operator['kind'] }) uses a non-serializable condition '{ label }'."
                )
        return True

    def _operator_label(self, operator: dict[str, Any], *, mode: Literal["simplified", "detailed"]):
        kind = operator["kind"]
        name = operator.get("name")
        handler_ref = operator.get("handler_ref")
        condition_ref = operator.get("condition_ref")
        callable_label = render_callable_ref(handler_ref)
        if kind == "chunk":
            if mode == "detailed":
                if name and name != callable_label:
                    return f"chunk\\n{ name }\\n{ callable_label }"
                return f"chunk\\n{ name or callable_label }"
            return str(name or callable_label)
        if kind == "signal_gate":
            return f"when\\n{ operator['options'].get('mode', 'simple') }"
        if kind == "batch_fanout":
            return "batch"
        if kind == "batch_collect":
            return "batch collect"
        if kind == "for_each_split":
            return "for each"
        if kind == "for_each_collect":
            return "for each collect"
        if kind == "match_route":
            return f"match\\n{ operator['options'].get('mode', 'hit_first') }"
        if kind == "match_case":
            if operator["options"].get("is_else"):
                return "else"
            if condition_ref is not None:
                return f"case\\n{ render_callable_ref(condition_ref) }"
            if "condition_value" in operator["options"]:
                return f"case\\n{ operator['options']['condition_value'] }"
            return "case"
        if kind == "match_collect":
            return "match result"
        if kind == "collect_branch":
            return f"collect\\n{ operator['options'].get('collection_name', '') }"
        if kind == "result_sink":
            return "result"
        return str(name or kind)

    def to_mermaid(self, *, mode: Literal["simplified", "detailed"] = "simplified"):
        if mode not in {"simplified", "detailed"}:
            raise ValueError(f"Unsupported Mermaid mode '{ mode }'. Use 'simplified' or 'detailed'.")

        node_defs: dict[str, str] = {}
        operator_node_ids: dict[str, str] = {}
        emitted_by_signal: dict[str, list[str]] = {}
        consumed_by_signal: dict[str, list[str]] = {}
        signal_lookup: dict[str, dict[str, Any]] = {}

        def get_group_node(operator: dict[str, Any]):
            if mode == "simplified" and operator.get("group_id") and operator.get("group_kind") in {
                "batch",
                "for_each",
                "match",
            }:
                group_id = f"group_{ _sanitize_mermaid_id(str(operator['group_id'])) }"
                if group_id not in node_defs:
                    node_defs[group_id] = (
                        f'{ group_id }["{ _escape_mermaid_label(str(operator["group_kind"])) }"]'
                    )
                return group_id
            return ""

        def get_operator_node(operator: dict[str, Any]):
            collapsed_node = get_group_node(operator)
            if collapsed_node:
                return collapsed_node
            node_id = f"op_{ _sanitize_mermaid_id(str(operator['id'])) }"
            if node_id in node_defs:
                return node_id
            label = self._operator_label(operator, mode=mode)
            shape = f'{ node_id }["{ _escape_mermaid_label(label) }"]'
            if operator["kind"] in {"signal_gate", "match_route"}:
                shape = f'{ node_id }{{"{ _escape_mermaid_label(label) }"}}'
            elif operator["kind"] in {"result_sink"}:
                shape = f'{ node_id }(["{ _escape_mermaid_label(label) }"])'
            elif operator["kind"] in {"batch_collect", "for_each_collect", "match_collect"}:
                shape = f'{ node_id }[["{ _escape_mermaid_label(label) }"]]'
            node_defs[node_id] = shape
            return node_id

        for operator in self.operators:
            operator_node_ids[operator["id"]] = get_operator_node(operator)
            for signal in operator["listen_signals"]:
                signal_lookup[signal["id"]] = signal
                consumed_by_signal.setdefault(signal["id"], []).append(operator["id"])
            for signal in operator["emit_signals"]:
                signal_lookup[signal["id"]] = signal
                emitted_by_signal.setdefault(signal["id"], []).append(operator["id"])

        edges: list[str] = []
        seen_edges: set[tuple[str, str, str]] = set()
        external_nodes: dict[str, str] = {}

        def ensure_external_node(signal: dict[str, Any], *, prefix: str):
            node_id = external_nodes.get(signal["id"])
            if node_id is not None:
                return node_id
            node_id = f"{ prefix }_{ _sanitize_mermaid_id(signal['id']) }"
            external_nodes[signal["id"]] = node_id
            node_defs[node_id] = f'{ node_id }["{ _escape_mermaid_label(_format_signal_label(signal)) }"]'
            return node_id

        def add_edge(source: str, target: str, label: str):
            key = (source, target, label)
            if source == target or key in seen_edges:
                return
            seen_edges.add(key)
            edge = f"{ source } --> { target }"
            if label:
                edge = f'{ source } -->|{ _escape_mermaid_label(label) }| { target }'
            edges.append(edge)

        for signal_id, consumers in consumed_by_signal.items():
            signal = signal_lookup[signal_id]
            producers = emitted_by_signal.get(signal_id, [])
            if not producers:
                source_node = ensure_external_node(signal, prefix="signal_in")
                for consumer_id in consumers:
                    add_edge(
                        source_node,
                        operator_node_ids[consumer_id],
                        _format_signal_label(signal),
                    )
                continue
            for producer_id in producers:
                for consumer_id in consumers:
                    add_edge(
                        operator_node_ids[producer_id],
                        operator_node_ids[consumer_id],
                        _format_signal_label(signal) if mode == "detailed" else "",
                    )

        for signal_id, producers in emitted_by_signal.items():
            if signal_id in consumed_by_signal:
                continue
            signal = signal_lookup[signal_id]
            if signal.get("role") != "declared_emit":
                continue
            target_node = ensure_external_node(signal, prefix="signal_out")
            for producer_id in producers:
                add_edge(
                    operator_node_ids[producer_id],
                    target_node,
                    _format_signal_label(signal),
                )

        lines = ["flowchart TD"]
        lines.extend(node_defs.values())
        lines.extend(edges)
        return "\n".join(lines)
