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

import asyncio
import inspect
from pathlib import Path

from typing import TYPE_CHECKING, Any, Mapping

from agently.types.data import ErrorInfo, RuntimeEvent
from agently.utils import FunctionShifter

if TYPE_CHECKING:
    from agently.types.data import EventHook, RunContext, RuntimeEventLevel
    from agently.types.plugins import EventHooker


_INTERNAL_SOURCE_MODULES = {
    "agently.core.EventCenter",
    "agently.utils.RuntimeEmitter",
}


def _infer_runtime_source() -> str:
    frame = inspect.currentframe()
    try:
        current = frame.f_back if frame is not None else None
        while current is not None:
            module_name = str(current.f_globals.get("__name__", ""))
            if module_name in _INTERNAL_SOURCE_MODULES:
                current = current.f_back
                continue

            source_instance = current.f_locals.get("self")
            if source_instance is not None:
                source_name = getattr(source_instance, "name", None)
                if isinstance(source_name, str) and source_name:
                    return source_name
                class_name = getattr(source_instance.__class__, "__name__", None)
                if isinstance(class_name, str) and class_name:
                    return class_name

            source_class = current.f_locals.get("cls")
            class_name = getattr(source_class, "__name__", None)
            if isinstance(class_name, str) and class_name:
                return class_name

            if module_name and module_name != "__main__":
                return module_name.rsplit(".", 1)[-1]

            file_name = current.f_code.co_filename
            if file_name:
                return Path(file_name).stem

            current = current.f_back
    finally:
        del frame
    return "Agently"


class EventCenter:
    def __init__(self):
        self._hooks: dict[str, tuple[set[str] | None, "EventHook"]] = {}
        self._hookers: dict[str, type["EventHooker"]] = {}
        self.emit = FunctionShifter.syncify(self.async_emit)

    def register_hook(
        self,
        callback: "EventHook",
        *,
        event_types: str | list[str] | None = None,
        hook_name: str | None = None,
    ):
        if hook_name is None:
            hook_name = callback.__name__
        normalized_event_types: set[str] | None = None
        if event_types is not None:
            normalized_event_types = {event_types} if isinstance(event_types, str) else set(event_types)
        self._hooks[hook_name] = (normalized_event_types, callback)

    def unregister_hook(self, hook_name: str):
        if hook_name in self._hooks:
            del self._hooks[hook_name]

    def register_hooker_plugin(self, hooker: type["EventHooker"]):
        if hasattr(hooker, "_on_register"):
            hooker._on_register()
        self.register_hook(hooker.handler, event_types=hooker.event_types, hook_name=hooker.name)
        self._hookers[hooker.name] = hooker

    def unregister_hooker_plugin(self, hooker: str | type["EventHooker"]):
        if isinstance(hooker, str):
            if hooker not in self._hookers:
                return
            hooker = self._hookers[hooker]
        self.unregister_hook(hooker.name)
        if hasattr(hooker, "_on_unregister"):
            hooker._on_unregister()
        del self._hookers[hooker.name]

    async def async_emit(self, event: "Mapping[str, Any] | RuntimeEvent"):
        if isinstance(event, RuntimeEvent):
            event_object = event
        else:
            event_data: dict[str, Any] = dict(event)
            if not event_data.get("source"):
                event_data["source"] = _infer_runtime_source()
            event_object = RuntimeEvent.model_validate(event_data)
        tasks = []
        for event_types, callback in self._hooks.values():
            if event_types is not None and event_object.event_type not in event_types:
                continue
            coro = FunctionShifter.asyncify(callback)
            tasks.append(asyncio.create_task(coro(event_object)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def create_emitter(
        self,
        source: str | None = None,
        *,
        base_meta: dict[str, Any] | None = None,
        base_run: "RunContext | None" = None,
    ):
        return RuntimeEventEmitter(
            self,
            source if source is not None else _infer_runtime_source(),
            base_meta=base_meta,
            base_run=base_run,
        )


class RuntimeEventEmitter:
    def __init__(
        self,
        event_center: EventCenter,
        source: str,
        *,
        base_meta: dict[str, Any] | None = None,
        base_run: "RunContext | None" = None,
    ):
        self._event_center = event_center
        self._source = source
        self._base_meta = base_meta if base_meta is not None else {}
        self._base_run = base_run

        self.emit = FunctionShifter.syncify(self.async_emit)
        self.debug = FunctionShifter.syncify(self.async_debug)
        self.info = FunctionShifter.syncify(self.async_info)
        self.warning = FunctionShifter.syncify(self.async_warning)
        self.error = FunctionShifter.syncify(self.async_error)
        self.critical = FunctionShifter.syncify(self.async_critical)

    def update_base_meta(self, update_dict: dict[str, Any]):
        self._base_meta.update(update_dict)

    async def async_emit(
        self,
        event_type: str,
        *,
        level: "RuntimeEventLevel" = "INFO",
        message: str | None = None,
        payload: Any = None,
        error: ErrorInfo | Exception | None = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        final_meta = self._base_meta.copy()
        if meta is not None:
            final_meta.update(meta)
        final_error: ErrorInfo | None = None
        if isinstance(error, Exception):
            final_error = ErrorInfo.from_exception(error)
        else:
            final_error = error
        await self._event_center.async_emit(
            RuntimeEvent(
                event_type=event_type,
                source=self._source,
                level=level,
                message=message,
                payload=payload,
                error=final_error,
                run=run if run is not None else self._base_run,
                meta=final_meta,
            )
        )

    async def async_debug(
        self,
        message: Any,
        *,
        event_type: str = "runtime.debug",
        payload: Any = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        await self.async_emit(
            event_type,
            level="DEBUG",
            message=str(message),
            payload=payload,
            run=run,
            meta=meta,
        )

    async def async_info(
        self,
        message: Any,
        *,
        event_type: str = "runtime.info",
        payload: Any = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        await self.async_emit(
            event_type,
            level="INFO",
            message=str(message),
            payload=payload,
            run=run,
            meta=meta,
        )

    async def async_warning(
        self,
        message: Any,
        *,
        event_type: str = "runtime.warning",
        payload: Any = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        await self.async_emit(
            event_type,
            level="WARNING",
            message=str(message),
            payload=payload,
            run=run,
            meta=meta,
        )

    async def async_error(
        self,
        error: str | Exception,
        *,
        event_type: str = "runtime.error",
        message: str | None = None,
        payload: Any = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        final_error = error if isinstance(error, Exception) else RuntimeError(error)
        await self.async_emit(
            event_type,
            level="ERROR",
            message=message if message is not None else str(final_error),
            payload=payload,
            error=final_error,
            run=run,
            meta=meta,
        )
        from agently.base import settings

        if settings.get("runtime.raise_error"):
            raise final_error

    async def async_critical(
        self,
        critical: str | Exception,
        *,
        event_type: str = "runtime.critical",
        message: str | None = None,
        payload: Any = None,
        run: "RunContext | None" = None,
        meta: dict[str, Any] | None = None,
    ):
        final_critical = critical if isinstance(critical, Exception) else RuntimeError(critical)
        await self.async_emit(
            event_type,
            level="CRITICAL",
            message=message if message is not None else str(final_critical),
            payload=payload,
            error=final_critical,
            run=run,
            meta=meta,
        )
        from agently.base import settings

        if settings.get("runtime.raise_critical"):
            raise final_critical
