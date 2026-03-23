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

import json
from typing import TYPE_CHECKING, Any

from agently.types.plugins import EventHooker
from agently.utils import DataFormatter

if TYPE_CHECKING:
    from agently.types.data import RuntimeEvent
    from agently.utils import Settings


COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "gray": 90,
}


def color_text(text: str, color: str | None = None, bold: bool = False, underline: bool = False) -> str:
    codes = []
    if bold:
        codes.append("1")
    if underline:
        codes.append("4")
    if color and color in COLORS:
        codes.append(str(COLORS[color]))
    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def _stringify_payload(payload: Any, *, indent: int | None = None) -> str:
    if payload is None:
        return ""
    sanitized = DataFormatter.sanitize(payload)
    try:
        return json.dumps(sanitized, ensure_ascii=False, indent=indent)
    except TypeError:
        return str(sanitized)


def _payload_value(event: "RuntimeEvent", key: str, default: Any = None) -> Any:
    if isinstance(event.payload, dict):
        return event.payload.get(key, default)
    return default


def _event_detail(event: "RuntimeEvent", *, pretty_payload: bool = False) -> str:
    if event.message:
        return event.message
    if event.error is not None:
        return event.error.message
    return _stringify_payload(event.payload, indent=2 if pretty_payload else None)


def _resolve_agent_name(event: "RuntimeEvent") -> str | None:
    agent_name = _payload_value(event, "agent_name")
    if isinstance(agent_name, str) and agent_name:
        return agent_name
    if event.run is not None and event.run.agent_name:
        return event.run.agent_name
    meta_agent_name = event.meta.get("agent_name")
    return str(meta_agent_name) if isinstance(meta_agent_name, str) and meta_agent_name else None


def _resolve_response_id(event: "RuntimeEvent") -> str | None:
    response_id = _payload_value(event, "response_id")
    if isinstance(response_id, str) and response_id:
        return response_id
    if event.run is not None and event.run.response_id:
        return event.run.response_id
    return None


def _resolve_execution_id(event: "RuntimeEvent") -> str | None:
    execution_id = event.meta.get("execution_id")
    if isinstance(execution_id, str) and execution_id:
        return execution_id
    if event.run is not None and event.run.execution_id:
        return event.run.execution_id
    return None


def _should_render(event: "RuntimeEvent", settings: "Settings") -> bool:
    if event.level in ("WARNING", "ERROR", "CRITICAL"):
        return True
    if event.event_type.startswith("model."):
        return bool(settings.get("runtime.show_model_logs", False))
    if event.event_type.startswith("tool."):
        return bool(settings.get("runtime.show_tool_logs", False))
    if event.event_type.startswith("workflow.") or event.event_type.startswith("trigger_flow."):
        return bool(settings.get("runtime.show_trigger_flow_logs", False))
    return False


def _render_block(header: str, stage: str, detail: str, *, detail_color: str = "gray", end: str = "\n"):
    header_text = color_text(header, color="blue", bold=True)
    stage_label = color_text("Stage:", color="cyan", bold=True)
    stage_value = color_text(stage, color="yellow", underline=True)
    detail_label = color_text("Detail:", color="cyan", bold=True)
    detail_text = color_text(detail, color=detail_color)
    print(f"{header_text}\n{stage_label} {stage_value}\n{detail_label}\n{detail_text}", end=end, flush=True)


def _render_line(prefix: str, detail: str, *, color: str = "gray"):
    title = color_text(prefix, color="yellow", bold=True)
    body = color_text(detail, color=color)
    print(f"{title} {body}")


class RuntimeConsoleSinkHooker(EventHooker):
    name = "RuntimeConsoleSinkHooker"
    event_types = None

    _streaming_key: tuple[str | None, str | None] | None = None

    @staticmethod
    def _on_register():
        RuntimeConsoleSinkHooker._streaming_key = None

    @staticmethod
    def _on_unregister():
        RuntimeConsoleSinkHooker._streaming_key = None

    @staticmethod
    def _close_stream_if_needed():
        if RuntimeConsoleSinkHooker._streaming_key is not None:
            print()
            RuntimeConsoleSinkHooker._streaming_key = None

    @staticmethod
    def _handle_model_event(event: "RuntimeEvent"):
        agent_name = _resolve_agent_name(event) or event.source
        response_id = _resolve_response_id(event)
        response_label = f"[Agent-{ agent_name }]"
        if response_id:
            response_label = f"{ response_label } - [Response-{ response_id }]"

        if event.event_type == "model.streaming":
            delta = _payload_value(event, "delta", event.message or "")
            if not isinstance(delta, str):
                delta = str(delta)
            stream_key = (agent_name, response_id)
            if RuntimeConsoleSinkHooker._streaming_key == stream_key:
                print(color_text(delta, color="gray"), end="", flush=True)
                return
            RuntimeConsoleSinkHooker._close_stream_if_needed()
            _render_block(response_label, "Streaming", delta, detail_color="green", end="")
            RuntimeConsoleSinkHooker._streaming_key = stream_key
            return

        RuntimeConsoleSinkHooker._close_stream_if_needed()

        stage_mapping = {
            "model.requesting": "Requesting",
            "model.completed": "Done",
            "model.parse_failed": "Parse Failed",
            "model.retrying": "Retrying",
            "model.streaming_canceled": "Streaming Canceled",
            "model.requester.error": "Requester Error",
        }
        detail = event.message or ""
        if event.event_type == "model.requesting":
            request_text = _payload_value(event, "request_text")
            detail = str(request_text) if request_text else _stringify_payload(_payload_value(event, "request"), indent=2)
        elif event.event_type == "model.completed":
            detail = _stringify_payload(_payload_value(event, "result"), indent=2) or detail
        elif event.event_type == "model.retrying":
            response_text = _payload_value(event, "response_text")
            retry_count = _payload_value(event, "retry_count")
            detail = f"[Response]: { response_text }\n[Retried Times]: { retry_count }"
        elif event.error is not None:
            detail = event.error.message
        if not detail:
            detail = _stringify_payload(event.payload, indent=2)
        detail_color = "red" if event.level in ("WARNING", "ERROR", "CRITICAL") else "gray"
        _render_block(response_label, stage_mapping.get(event.event_type, event.event_type), detail, detail_color=detail_color)

    @staticmethod
    def _handle_tool_event(event: "RuntimeEvent"):
        RuntimeConsoleSinkHooker._close_stream_if_needed()
        tool_name = _payload_value(event, "tool_name", "unknown")
        agent_name = _resolve_agent_name(event)
        header = f"[Tool-{ tool_name }]"
        if agent_name:
            header = f"[Agent-{ agent_name }] - { header }"
        stage = "Completed" if _payload_value(event, "success", False) else "Failed"
        detail = _stringify_payload(event.payload, indent=2) or _event_detail(event, pretty_payload=True)
        detail_color = "gray" if stage == "Completed" else "red"
        _render_block(header, stage, detail, detail_color=detail_color)

    @staticmethod
    def _handle_trigger_flow_event(event: "RuntimeEvent"):
        RuntimeConsoleSinkHooker._close_stream_if_needed()
        execution_id = _resolve_execution_id(event)
        prefix = "[TriggerFlow]"
        if execution_id:
            prefix = f"{ prefix } [Execution-{ execution_id }]"
        detail = _event_detail(event, pretty_payload=True)
        _render_line(prefix, detail, color="yellow" if event.level == "DEBUG" else "gray")

    @staticmethod
    def _handle_generic_event(event: "RuntimeEvent"):
        RuntimeConsoleSinkHooker._close_stream_if_needed()
        detail = _event_detail(event, pretty_payload=True)
        prefix = f"[{ event.source }] [{ event.event_type }]"
        color = "gray"
        if event.level in ("WARNING", "ERROR", "CRITICAL"):
            color = "red"
        elif event.level == "INFO":
            color = "green"
        _render_line(prefix, detail, color=color)

    @staticmethod
    async def handler(event: "RuntimeEvent"):
        from agently.base import settings

        if not _should_render(event, settings):
            return
        if event.event_type.startswith("model."):
            RuntimeConsoleSinkHooker._handle_model_event(event)
            return
        if event.event_type.startswith("tool."):
            RuntimeConsoleSinkHooker._handle_tool_event(event)
            return
        if event.event_type.startswith("workflow.") or event.event_type.startswith("trigger_flow."):
            RuntimeConsoleSinkHooker._handle_trigger_flow_event(event)
            return
        RuntimeConsoleSinkHooker._handle_generic_event(event)
