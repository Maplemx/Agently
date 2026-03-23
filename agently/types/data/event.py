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

import time
import traceback
import uuid
from typing import Any, Awaitable, Callable, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict

RuntimeEventLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

RunKind: TypeAlias = Literal["request", "workflow_execution", "tool_loop", "tool_call"] | str


class ErrorInfoDict(TypedDict, total=False):
    type: str
    message: str
    module: str | None
    traceback: str | None
    retryable: bool | None
    fatal: bool | None
    code: str | None
    details: dict[str, Any]


class RunContextDict(TypedDict, total=False):
    run_id: str
    run_kind: RunKind
    root_run_id: str | None
    parent_run_id: str | None
    agent_id: str | None
    agent_name: str | None
    session_id: str | None
    response_id: str | None
    execution_id: str | None
    meta: dict[str, Any]


class RuntimeEventDict(TypedDict, total=False):
    event_id: str
    event_type: str
    source: str
    level: RuntimeEventLevel
    message: str | None
    payload: Any
    error: ErrorInfoDict | Exception | None
    run: RunContextDict | None
    meta: dict[str, Any]
    timestamp: int


class ErrorInfo(BaseModel):
    type: str
    message: str
    module: str | None = None
    traceback: str | None = None
    retryable: bool | None = None
    fatal: bool | None = None
    code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_exception(cls, error: Exception) -> "ErrorInfo":
        return cls(
            type=error.__class__.__name__,
            message=str(error),
            module=error.__class__.__module__,
            traceback="".join(traceback.format_exception(type(error), error, error.__traceback__)),
        )


class RunContext(BaseModel):
    run_id: str
    run_kind: RunKind
    root_run_id: str | None = None
    parent_run_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    session_id: str | None = None
    response_id: str | None = None
    execution_id: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _apply_lineage_defaults(self):
        if self.root_run_id is None:
            self.root_run_id = self.run_id
        return self

    @classmethod
    def create(
        cls,
        *,
        run_kind: RunKind,
        run_id: str | None = None,
        parent: "RunContext | None" = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
        response_id: str | None = None,
        execution_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "RunContext":
        resolved_meta = {}
        if parent is not None:
            resolved_meta.update(parent.meta)
        if meta is not None:
            resolved_meta.update(meta)
        return cls(
            run_id=run_id if run_id is not None else uuid.uuid4().hex,
            run_kind=run_kind,
            root_run_id=parent.root_run_id if parent is not None else None,
            parent_run_id=parent.run_id if parent is not None else None,
            agent_id=agent_id if agent_id is not None else (parent.agent_id if parent is not None else None),
            agent_name=agent_name if agent_name is not None else (parent.agent_name if parent is not None else None),
            session_id=session_id if session_id is not None else (parent.session_id if parent is not None else None),
            response_id=response_id if response_id is not None else (parent.response_id if parent is not None else None),
            execution_id=execution_id if execution_id is not None else (parent.execution_id if parent is not None else None),
            meta=resolved_meta,
        )

    def create_child(
        self,
        *,
        run_kind: RunKind,
        run_id: str | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
        response_id: str | None = None,
        execution_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "RunContext":
        return type(self).create(
            run_kind=run_kind,
            run_id=run_id,
            parent=self,
            agent_id=agent_id,
            agent_name=agent_name,
            session_id=session_id,
            response_id=response_id,
            execution_id=execution_id,
            meta=meta,
        )


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str
    source: str = "Agently"
    level: RuntimeEventLevel = "INFO"
    message: str | None = None
    payload: Any = None
    error: ErrorInfo | None = None
    run: RunContext | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @model_validator(mode="before")
    @classmethod
    def _normalize_error(cls, value: Any):
        if not isinstance(value, dict):
            return value
        error = value.get("error")
        if isinstance(error, Exception):
            normalized = dict(value)
            normalized["error"] = ErrorInfo.from_exception(error)
            return normalized
        return value


EventHook = Callable[[RuntimeEvent], None | Awaitable[None]]
