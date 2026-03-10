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
from collections.abc import Mapping

from typing import Any, Callable, Literal, TYPE_CHECKING
from agently.types.data import AVOID_COPY

if TYPE_CHECKING:
    from agently.core import TriggerFlowExecution
    from agently.core.TriggerFlow.Signal import TriggerFlowSignal

from agently.utils import RuntimeData


class TriggerFlowBlockData:
    global_data = RuntimeData()

    def __init__(
        self,
        outer_block: "TriggerFlowBlockData | None" = None,
        data: dict[str, Any] | None = None,
    ):
        self.outer_block = outer_block
        self.data = data if data is not None else {}


_MISSING = object()


class _TriggerFlowDataNamespace:
    def __init__(
        self,
        *,
        getter: Callable[..., Any],
        setter: Callable[..., Any],
        appender: Callable[..., Any],
        deleter: Callable[..., Any],
        async_setter: Callable[..., Any],
        async_appender: Callable[..., Any],
        async_deleter: Callable[..., Any],
    ):
        self._getter = getter
        self._setter = setter
        self._appender = appender
        self._deleter = deleter
        self.async_set = async_setter
        self.async_append = async_appender
        self.async_del = async_deleter

    def get(
        self,
        key: Any | None = None,
        default: Any = None,
        *,
        inherit: bool = True,
    ):
        return self._getter(key, default, inherit=inherit)

    def set(
        self,
        key: str,
        value: Any,
        *,
        emit: bool = True,
    ):
        return self._setter(key, value, emit=emit)

    def append(
        self,
        key: str,
        value: Any,
        *,
        emit: bool = True,
    ):
        return self._appender(key, value, emit=emit)

    def delete(
        self,
        key: str,
        *,
        emit: bool = True,
    ):
        return self._deleter(key, emit=emit)

    def to_dict(self, *, inherit: bool = True):
        data = self.get(None, {}, inherit=inherit)
        return data if isinstance(data, dict) else {}

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

    def __getitem__(self, key: Any):
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __contains__(self, key: Any):
        return self.get(key, _MISSING) is not _MISSING

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())


class _TriggerFlowResourcesView(Mapping[str, Any]):
    def __init__(self, execution: "TriggerFlowExecution"):
        self._execution = execution

    def to_dict(self):
        return self._execution.get_runtime_resources()

    def __getitem__(self, key: str):
        value = self._execution.get_runtime_resource(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())

    def get(self, key: str, default: Any = None):
        return self._execution.get_runtime_resource(key, default)


class _TriggerFlowSignalInfo:
    def __init__(
        self,
        *,
        trigger_event: str,
        trigger_type: Literal["event", "runtime_data", "flow_data", "collect"],
        value: Any,
        signal: "TriggerFlowSignal | None",
        signal_id: str | None,
        signal_source: str | None,
        signal_meta: dict[str, Any],
    ):
        self.trigger_event = trigger_event
        self.trigger_type = trigger_type
        self.value = value
        self.signal = signal
        self.signal_id = signal_id
        self.signal_source = signal_source
        self.signal_meta = signal_meta

    @property
    def event(self):
        return self.trigger_event

    @property
    def type(self):
        return self.trigger_type

    @property
    def source(self):
        return self.signal_source

    @property
    def meta(self):
        return self.signal_meta

    def to_dict(self):
        return {
            "trigger_event": self.trigger_event,
            "trigger_type": self.trigger_type,
            "value": self.value,
            "signal_id": self.signal_id,
            "signal_source": self.signal_source,
            "signal_meta": self.signal_meta.copy(),
        }


class TriggerFlowRuntimeData:
    def __init__(
        self,
        *,
        trigger_event: str,
        trigger_type: Literal["event", "runtime_data", "flow_data", "collect"],
        value: Any,
        execution: "TriggerFlowExecution",
        _layer_marks: list[str] | None = None,
        signal: "TriggerFlowSignal | None" = None,
    ):
        self.trigger_event = trigger_event
        self.trigger_type: Literal["event", "runtime_data", "flow_data", "collect"] = trigger_type
        self.event = trigger_event
        self.type = trigger_type
        self.value = value
        self.execution = execution
        self.execution_id = execution.id
        self._layer_marks = _layer_marks if _layer_marks is not None else []
        self.settings = execution.settings
        self.signal = signal
        self.signal_id = signal.id if signal is not None else None
        self.signal_source = signal.source if signal is not None else None
        self.signal_meta = signal.meta.copy() if signal is not None else {}
        self.signal_info = _TriggerFlowSignalInfo(
            trigger_event=trigger_event,
            trigger_type=trigger_type,
            value=value,
            signal=signal,
            signal_id=self.signal_id,
            signal_source=self.signal_source,
            signal_meta=self.signal_meta.copy(),
        )

        self.get_flow_data = execution.get_flow_data
        self.set_flow_data = execution.set_flow_data
        self.append_flow_data = execution.append_flow_data
        self.del_flow_data = execution.del_flow_data
        self.async_set_flow_data = execution.async_set_flow_data
        self.async_append_flow_data = execution.async_append_flow_data
        self.async_del_flow_data = execution.async_del_flow_data

        self.get_runtime_data = execution.get_runtime_data
        self.set_runtime_data = execution.set_runtime_data
        self.append_runtime_data = execution.append_runtime_data
        self.del_runtime_data = execution.del_runtime_data
        self.async_set_runtime_data = execution.async_set_runtime_data
        self.async_append_runtime_data = execution.async_append_runtime_data
        self.async_del_runtime_data = execution.async_del_runtime_data
        self.state = _TriggerFlowDataNamespace(
            getter=self.get_runtime_data,
            setter=self.set_runtime_data,
            appender=self.append_runtime_data,
            deleter=self.del_runtime_data,
            async_setter=self.async_set_runtime_data,
            async_appender=self.async_append_runtime_data,
            async_deleter=self.async_del_runtime_data,
        )
        self.flow_state = _TriggerFlowDataNamespace(
            getter=self.get_flow_data,
            setter=self.set_flow_data,
            appender=self.append_flow_data,
            deleter=self.del_flow_data,
            async_setter=self.async_set_flow_data,
            async_appender=self.async_append_flow_data,
            async_deleter=self.async_del_flow_data,
        )
        self.resources = _TriggerFlowResourcesView(execution)

        self.get_resource = execution.get_runtime_resource
        self.require_resource = execution.require_runtime_resource
        self.set_resource = execution.set_runtime_resource
        self.del_resource = execution.del_runtime_resource

        self.emit = execution.emit
        self.async_emit = execution.async_emit

        self.put = execution.put_into_stream
        self.async_put = execution.async_put_into_stream
        self.put_into_stream = execution.put_into_stream
        self.async_put_into_stream = execution.async_put_into_stream
        self.stop_stream = execution.stop_stream
        self.async_stop_stream = execution.async_stop_stream

        self.pause_for = execution.pause_for
        self.async_pause_for = execution.async_pause_for
        self.continue_with = execution.continue_with
        self.async_continue_with = execution.async_continue_with
        self.get_status = execution.get_status
        self.is_waiting = execution.is_waiting
        self.get_interrupt = execution.get_interrupt
        self.get_pending_interrupts = execution.get_pending_interrupts

        self.set_result = execution.set_result
        self.get_result = execution.get_result
        self.get_last_signal = execution.get_last_signal

        self._system_runtime_data = execution._system_runtime_data

    @property
    def upper_layer_mark(self):
        return self._layer_marks[-2] if len(self._layer_marks) > 1 else None

    @property
    def layer_mark(self):
        return self._layer_marks[-1] if len(self._layer_marks) > 0 else None

    def layer_in(self):
        self._layer_marks.append(uuid.uuid4().hex)

    def layer_out(self):
        self._layer_marks = self._layer_marks[:-1] if len(self._layer_marks) > 0 else []


TriggerFlowEventData = TriggerFlowRuntimeData
TriggerFlowHandler = Callable[[TriggerFlowRuntimeData], Any]
TriggerFlowHandlers = dict[str, dict[str, TriggerFlowHandler]]
TriggerFlowAllHandlers = dict[Literal["event", "flow_data", "runtime_data"], TriggerFlowHandlers]

RUNTIME_STREAM_STOP = AVOID_COPY()
