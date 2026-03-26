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

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator, cast

if TYPE_CHECKING:
    from agently.types.data import RunContext


_MISSING = object()

_current_parent_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_parent_run_context",
    default=None,
)
_current_request_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_request_run_context",
    default=None,
)
_current_model_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_model_run_context",
    default=None,
)
_current_agent_turn_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_agent_turn_run_context",
    default=None,
)
_current_chunk_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_chunk_run_context",
    default=None,
)
_current_tool_phase_run_context: ContextVar["RunContext | None"] = ContextVar(
    "agently_current_tool_phase_run_context",
    default=None,
)


@contextmanager
def bind_runtime_context(
    *,
    parent_run_context: "RunContext | None | object" = _MISSING,
    request_run_context: "RunContext | None | object" = _MISSING,
    model_run_context: "RunContext | None | object" = _MISSING,
    agent_turn_run_context: "RunContext | None | object" = _MISSING,
    chunk_run_context: "RunContext | None | object" = _MISSING,
    tool_phase_run_context: "RunContext | None | object" = _MISSING,
) -> Iterator[None]:
    tokens = []
    try:
        if parent_run_context is not _MISSING:
            tokens.append(
                (
                    _current_parent_run_context,
                    _current_parent_run_context.set(cast("RunContext | None", parent_run_context)),
                )
            )
        if request_run_context is not _MISSING:
            tokens.append(
                (
                    _current_request_run_context,
                    _current_request_run_context.set(cast("RunContext | None", request_run_context)),
                )
            )
        if model_run_context is not _MISSING:
            tokens.append(
                (
                    _current_model_run_context,
                    _current_model_run_context.set(cast("RunContext | None", model_run_context)),
                )
            )
        if agent_turn_run_context is not _MISSING:
            tokens.append(
                (
                    _current_agent_turn_run_context,
                    _current_agent_turn_run_context.set(cast("RunContext | None", agent_turn_run_context)),
                )
            )
        if chunk_run_context is not _MISSING:
            tokens.append(
                (
                    _current_chunk_run_context,
                    _current_chunk_run_context.set(cast("RunContext | None", chunk_run_context)),
                )
            )
        if tool_phase_run_context is not _MISSING:
            tokens.append(
                (
                    _current_tool_phase_run_context,
                    _current_tool_phase_run_context.set(cast("RunContext | None", tool_phase_run_context)),
                )
            )
        yield
    finally:
        for context_var, token in reversed(tokens):
            context_var.reset(token)


def get_current_parent_run_context():
    return _current_parent_run_context.get()


def get_current_request_run_context():
    return _current_request_run_context.get()


def get_current_model_run_context():
    return _current_model_run_context.get()


def get_current_agent_turn_run_context():
    return _current_agent_turn_run_context.get()


def get_current_chunk_run_context():
    return _current_chunk_run_context.get()


def get_current_tool_phase_run_context():
    return _current_tool_phase_run_context.get()


def resolve_parent_run_context(parent_run_context: "RunContext | None" = None):
    if parent_run_context is not None:
        return parent_run_context
    tool_phase_run_context = get_current_tool_phase_run_context()
    if tool_phase_run_context is not None:
        return tool_phase_run_context
    chunk_run_context = get_current_chunk_run_context()
    if chunk_run_context is not None:
        return chunk_run_context
    return get_current_parent_run_context()
