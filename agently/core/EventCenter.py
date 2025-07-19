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

import json
from typing import TYPE_CHECKING, Any, cast

from agently.types.data.serializable import SerializableData
from agently.types.data.event import EventMessage
from agently.utils import FunctionShifter

if TYPE_CHECKING:
    from agently.types.data.event import (
        AgentlyEvent,
        EventMessageDict,
        EventMessage,
        MessageLevel,
        EventStatus,
        EventHook,
    )
    from agently.types.plugins import EventHooker


class EventCenter:
    def __init__(self):
        self._hooks: dict[AgentlyEvent, dict[str, "EventHook"]] = {}
        self._hookers: dict[str, type[EventHooker]] = {}

    def register_hook(
        self,
        event: "AgentlyEvent",
        callback: "EventHook",
        *,
        hook_name: str | None = None,
    ):
        if hook_name is None:
            hook_name = callback.__name__
        if event not in self._hooks:
            self._hooks.update({event: {}})
        self._hooks[event].update({hook_name: callback})

    def unregister_hook(
        self,
        event: "AgentlyEvent",
        hook_name: str,
    ):
        if event in self._hooks and hook_name in self._hooks[event]:
            del self._hooks[event][hook_name]

    def register_hooker_plugin(self, hooker: type["EventHooker"]):
        if hasattr(hooker, "_on_register"):
            hooker._on_register()
        for event in hooker.events:
            self.register_hook(event, hooker.handler, hook_name=hooker.name)
        self._hookers.update({hooker.name: hooker})

    def unregister_hooker_plugin(self, hooker: str | type["EventHooker"]):
        if isinstance(hooker, str):
            if hooker in self._hookers:
                hooker = self._hookers[hooker]
            else:
                return
        for event in hooker.events:
            self.unregister_hook(event, hook_name=hooker.name)
        if hasattr(hooker, "_on_unregister"):
            hooker._on_unregister()
        del self._hookers[hooker.name]

    @FunctionShifter.hybrid_func
    async def emit(
        self,
        event: "AgentlyEvent",
        message: "EventMessageDict | EventMessage",
    ):
        if message is EventMessage:
            message_object = message
        else:
            message_dict = dict(message).copy()
            message_dict.update({"event": event})
            message_object = EventMessage(**message_dict)

        tasks = []

        if event in self._hooks:
            for callback in self._hooks[event].values():
                coro_callback = FunctionShifter.to_awaitable(callback)
                tasks.append(asyncio.ensure_future(coro_callback(message_object)))

            await asyncio.gather(*tasks)
        if event == "log" and len(tasks) == 0:
            print(*message_object.content if isinstance(message_object.content, list) else message_object.content)

    def create_messenger(self, module_name: str, *, base_meta: dict[str, Any] | None = None):
        if base_meta is None:
            base_meta = {}
        return EventCenterMessenger(
            self,
            module_name,
            base_meta=base_meta,
        )


class EventCenterMessenger:
    def __init__(
        self,
        event_center: EventCenter,
        module_name: str,
        *,
        base_meta: dict[str, Any] | None = None,
    ):
        self._event_center = event_center
        self._module_name = module_name
        self._base_meta = base_meta if base_meta is not None else {}

    def update_base_meta(self, update_dict: dict[str, Any]):
        self._base_meta.update(update_dict)

    @FunctionShifter.hybrid_func
    async def message(
        self,
        content: str,
        *,
        status: "EventStatus" = "",
        exception: Exception | None = None,
        level: "MessageLevel" = "INFO",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        await self._event_center.emit(
            "message",
            {
                "module_name": self._module_name,
                "status": status,
                "content": content,
                "exception": exception,
                "level": level,
                "meta": final_meta,
            },
        )

    @FunctionShifter.hybrid_func
    async def debug(
        self,
        content: str,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        await self._event_center.emit(
            "log",
            {
                "module_name": self._module_name,
                "status": status,
                "content": content,
                "level": "DEBUG",
                "meta": final_meta,
            },
        )

    @FunctionShifter.hybrid_func
    async def info(
        self,
        content: str,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        await self._event_center.emit(
            "log",
            {
                "module_name": self._module_name,
                "status": status,
                "content": content,
                "level": "INFO",
                "meta": final_meta,
            },
        )

    @FunctionShifter.hybrid_func
    async def warning(
        self,
        content: str,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        await self._event_center.emit(
            "log",
            {
                "module_name": self._module_name,
                "status": status,
                "content": content,
                "level": "WARNING",
                "meta": final_meta,
            },
        )

    @FunctionShifter.hybrid_func
    async def error(
        self,
        error: str | Exception,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        error = error if isinstance(error, Exception) else RuntimeError(error)
        await self._event_center.emit(
            "log",
            {
                "module_name": self._module_name,
                "status": status,
                "content": str(error),
                "exception": error,
                "level": "ERROR",
                "meta": final_meta,
            },
        )

        from agently.base import settings

        if settings.get("runtime.raise_error"):
            raise error

    @FunctionShifter.hybrid_func
    async def critical(
        self,
        critical: str | Exception,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any] | None = None,
    ):
        if meta is None:
            meta = {}
        final_meta = self._base_meta.copy()
        final_meta.update(meta)
        critical = critical if isinstance(critical, Exception) else RuntimeError(critical)
        await self._event_center.emit(
            "log",
            {
                "module_name": self._module_name,
                "status": status,
                "content": str(critical),
                "exception": critical,
                "level": "CRITICAL",
                "meta": final_meta,
            },
        )

        from agently.base import settings

        if settings.get("runtime.raise_critical"):
            raise critical

    @FunctionShifter.hybrid_func
    async def to_console(
        self,
        content: Any,
        *,
        status: "EventStatus" = "",
        table_name: str | None = None,
        row_id: int | str | None = None,
    ):
        final_meta = {}
        final_meta.update(self._base_meta)
        if table_name is not None:
            final_meta.update({"table_name": table_name})
        if row_id is not None:
            final_meta.update({"row_id": row_id})
        await self._event_center.emit(
            "console",
            {
                "module_name": self._module_name,
                "status": status,
                "content": content,
                "meta": final_meta,
            },
        )

    @FunctionShifter.hybrid_func
    async def to_data(
        self,
        data: SerializableData,
        *,
        status: "EventStatus" = "",
        meta: dict[str, Any],
    ):
        final_meta = self._base_meta
        final_meta.update(meta)
        await self._event_center.emit(
            "data",
            {
                "module_name": self._module_name,
                "status": status,
                "content": json.dumps(data),
                "meta": final_meta,
            },
        )
