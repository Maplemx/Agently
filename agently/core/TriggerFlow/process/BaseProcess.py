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
from asyncio import Event, Semaphore

from typing import Callable, Any, Literal, TYPE_CHECKING, overload, cast
from typing_extensions import Self


if TYPE_CHECKING:
    from ..BluePrint import TriggerFlowBluePrint
    from agently.types.trigger_flow import (
        TriggerFlowHandler,
        TriggerFlowRuntimeData,
        TriggerFlowSubFlowCapture,
        TriggerFlowSubFlowWriteBack,
    )
    from ..TriggerFlow import TriggerFlow

from ..Chunk import TriggerFlowChunk
from agently.types.data import EMPTY
from agently.types.trigger_flow import TriggerFlowBlockData

_UNSET = object()


class TriggerFlowBaseProcess:

    def __init__(
        self,
        *,
        flow_chunk,
        trigger_event: str,
        blue_print: "TriggerFlowBluePrint",
        block_data: "TriggerFlowBlockData",
        trigger_type: Literal["event", "runtime_data", "flow_data"] = "event",
        definition_signals: list[dict[str, Any]] | None = None,
        definition_group_id: str | None | object = _UNSET,
        definition_group_kind: str | None | object = _UNSET,
        **options,
    ):
        self._flow_chunk = flow_chunk
        self.trigger_event = trigger_event
        self.trigger_type: Literal["event", "runtime_data", "flow_data"] = trigger_type
        self._blue_print = blue_print
        self._block_data = block_data
        self._options = options
        self._definition_signals = copy.deepcopy(definition_signals) if definition_signals is not None else []
        self._definition_group_id = None if definition_group_id is _UNSET else definition_group_id
        self._definition_group_kind = None if definition_group_kind is _UNSET else definition_group_kind

    def _new(
        self,
        trigger_event: str,
        blue_print: "TriggerFlowBluePrint",
        block_data: "TriggerFlowBlockData",
        trigger_type: Literal["event", "runtime_data", "flow_data"] = "event",
        definition_signals: list[dict[str, Any]] | None = None,
        definition_group_id: str | None | object = _UNSET,
        definition_group_kind: str | None | object = _UNSET,
        **options,
    ):
        return type(self)(
            flow_chunk=self._flow_chunk,
            trigger_event=trigger_event,
            trigger_type=trigger_type,
            blue_print=blue_print,
            block_data=block_data,
            definition_signals=definition_signals if definition_signals is not None else self._definition_signals,
            definition_group_id=(
                self._definition_group_id if definition_group_id is _UNSET else definition_group_id
            ),
            definition_group_kind=(
                self._definition_group_kind if definition_group_kind is _UNSET else definition_group_kind
            ),
            **options,
        )

    def _layer_key(self, data: "TriggerFlowRuntimeData"):
        return ".".join(data._layer_marks) if data._layer_marks else "__root__"

    def _root_block_data(self):
        current = self._block_data
        while current.outer_block is not None:
            current = current.outer_block
        return current

    def _current_definition_parent_group(self):
        if self._definition_group_id is None or self._definition_group_kind is None:
            return None, None
        return (
            self._block_data.data.get("definition_outer_group_id"),
            self._block_data.data.get("definition_outer_group_kind"),
        )

    def _event_signal(self, trigger_event: str, *, role: str | None = None):
        return self._blue_print.make_signal("event", trigger_event, role=role)

    def _resolve_definition_signal(
        self,
        trigger_type: Literal["event", "runtime_data", "flow_data"],
        trigger_event: str | TriggerFlowChunk,
    ):
        if isinstance(trigger_event, TriggerFlowChunk):
            if trigger_type != "event":
                raise TypeError("Can not use chunk as trigger event when trigger type is not 'event'.")
            return self._event_signal(trigger_event.trigger)
        if trigger_type == "event" and isinstance(trigger_event, str) and trigger_event in self._blue_print.chunks:
            return self._event_signal(self._blue_print.chunks[trigger_event].trigger)
        return self._blue_print.make_signal(trigger_type, str(trigger_event))

    @overload
    def when(
        self,
        trigger_or_triggers: str | TriggerFlowChunk,
        *,
        mode: Literal["and", "or", "simple_or"] = "and",
    ) -> Self: ...

    @overload
    def when(
        self,
        trigger_or_triggers: dict[
            Literal["event"],
            str | TriggerFlowChunk | list[str | TriggerFlowChunk],
        ],
        *,
        mode: Literal["and", "or", "simple_or"] = "and",
    ) -> Self: ...

    @overload
    def when(
        self,
        trigger_or_triggers: dict[
            Literal["runtime_data", "flow_data", "collect"],
            str | list[str],
        ],
        *,
        mode: Literal["and", "or", "simple_or"] = "and",
    ) -> Self: ...

    def when(
        self,
        trigger_or_triggers: (
            str
            | TriggerFlowChunk
            | dict[
                Literal["event"],
                str | TriggerFlowChunk | list[str | TriggerFlowChunk],
            ]
            | dict[
                Literal["runtime_data", "flow_data", "collect"],
                str | list[str],
            ]
        ),
        *,
        mode: Literal["and", "or", "simple_or"] = "and",
    ):
        if isinstance(trigger_or_triggers, TriggerFlowChunk):
            trigger_or_triggers = trigger_or_triggers.trigger
        if isinstance(trigger_or_triggers, str):
            if trigger_or_triggers in self._blue_print.chunks:
                trigger = self._blue_print.chunks[trigger_or_triggers].trigger
            else:
                trigger = trigger_or_triggers
            return self._new(
                trigger_event=trigger,
                trigger_type="event",
                blue_print=self._blue_print,
                block_data=TriggerFlowBlockData(
                    outer_block=None,
                ),
                definition_signals=[self._event_signal(trigger)],
                definition_group_id=None,
                definition_group_kind=None,
            )
        values: dict[Literal["event", "runtime_data", "flow_data", "collect"], dict[str, Any]] = {}
        definition_signals: list[dict[str, Any]] = []
        trigger_count = 0
        current_trigger_type = "event"
        current_trigger_event = ""
        for trigger_type, trigger_event_or_events in trigger_or_triggers.items():
            if trigger_type not in values:
                values[trigger_type] = {}
            if isinstance(trigger_event_or_events, TriggerFlowChunk):
                if trigger_type == "event":
                    trigger_event_or_events = trigger_event_or_events.trigger
                else:
                    raise TypeError("Can not use chunk as trigger event when trigger type is not 'event'.")
            if trigger_type == "collect":
                trigger_type = "event"
                if isinstance(trigger_event_or_events, str):
                    trigger_event_or_events = f"Collect-{ trigger_event_or_events }"
                else:
                    trigger_event_or_events = [f"Collect-{ trigger_event }" for trigger_event in trigger_event_or_events]
            if isinstance(trigger_event_or_events, str):
                values[trigger_type][trigger_event_or_events] = EMPTY
                definition_signals.append(self._resolve_definition_signal(trigger_type, trigger_event_or_events))
                current_trigger_type = trigger_type
                current_trigger_event = trigger_event_or_events
                trigger_count += 1
            else:
                for trigger_event in trigger_event_or_events:
                    if isinstance(trigger_event, TriggerFlowChunk):
                        trigger_event = trigger_event.trigger
                    values[trigger_type][trigger_event] = EMPTY
                    definition_signals.append(self._resolve_definition_signal(trigger_type, trigger_event))
                    current_trigger_type = trigger_type
                    current_trigger_event = trigger_event
                    trigger_count += 1

        if trigger_count == 1:
            return self._new(
                trigger_event=current_trigger_event,
                trigger_type=current_trigger_type,
                blue_print=self._blue_print,
                block_data=TriggerFlowBlockData(
                    outer_block=None,
                ),
                definition_signals=definition_signals,
                definition_group_id=None,
                definition_group_kind=None,
            )

        when_id = uuid.uuid4().hex
        when_trigger = f"When-{ when_id }"
        values_template = copy.deepcopy(values)

        async def wait_trigger(data: "TriggerFlowRuntimeData"):
            match mode:
                case "or" | "simple_or":
                    await data.async_emit(
                        when_trigger,
                        (
                            data.value
                            if mode == "simple_or"
                            else (data.trigger_type, data.trigger_event, data.value)
                        ),
                        _layer_marks=data._layer_marks.copy(),
                    )
                case "and":
                    state_key = f"when_states.{ when_id }.{ self._layer_key(data) }"
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
                        when_trigger,
                        state,
                        _layer_marks=data._layer_marks.copy(),
                    )
                    del data._system_runtime_data[state_key]

        for trigger_type, trigger_event_dict in values.items():
            for trigger_event in trigger_event_dict.keys():
                self._blue_print.add_handler(
                    trigger_type,  # type: ignore[arg-type]
                    trigger_event,
                    wait_trigger,
                )

        self._blue_print.definition.add_operator(
            id=f"when-{ when_id }",
            kind="signal_gate",
            name=f"when:{ when_id }",
            listen_signals=definition_signals,
            emit_signals=[self._event_signal(when_trigger, role="continuation")],
            options={"mode": mode},
        )

        return self._new(
            trigger_event=when_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=TriggerFlowBlockData(
                outer_block=None,
            ),
            definition_signals=[self._event_signal(when_trigger)],
            definition_group_id=None,
            definition_group_kind=None,
        )

    def to(
        self,
        chunk: "TriggerFlowChunk | TriggerFlowHandler | TriggerFlow | str | tuple[str, TriggerFlowHandler]",
        side_branch: bool = False,
        name: str | None = None,
    ):
        from ..TriggerFlow import TriggerFlow

        if isinstance(chunk, TriggerFlow):
            return self.to_sub_flow(
                chunk,
                side_branch=side_branch,
                name=name,
            )
        if isinstance(chunk, str):
            if chunk in self._blue_print.chunks:
                chunk = self._blue_print.chunks[chunk]
            else:
                raise NotImplementedError(f"Cannot find chunk named '{ chunk }'")
        elif isinstance(chunk, tuple):
            chunk_name = chunk[0]
            chunk_func = chunk[1]
            chunk = self._flow_chunk(chunk_name)(chunk_func)
        else:
            if callable(chunk):
                chunk = self._flow_chunk(chunk) if name is None else self._flow_chunk(name)(chunk)
        assert isinstance(chunk, TriggerFlowChunk)
        parent_group_id, parent_group_kind = self._current_definition_parent_group()
        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            chunk.async_call,
        )
        self._blue_print.attach_chunk(
            chunk,
            self._definition_signals,
            group_id=self._definition_group_id,
            group_kind=self._definition_group_kind,
            parent_group_id=parent_group_id,
            parent_group_kind=parent_group_kind,
        )
        return self._new(
            trigger_event=chunk.trigger if not side_branch else self.trigger_event,
            trigger_type=self.trigger_type,
            blue_print=self._blue_print,
            block_data=self._block_data,
            definition_signals=[self._event_signal(chunk.trigger)] if not side_branch else self._definition_signals,
            definition_group_id=self._definition_group_id,
            definition_group_kind=self._definition_group_kind,
            **self._options,
        )

    def to_sub_flow(
        self,
        trigger_flow: "TriggerFlow",
        *,
        side_branch: bool = False,
        name: str | None = None,
        capture: "TriggerFlowSubFlowCapture | None" = None,
        write_back: "TriggerFlowSubFlowWriteBack | None" = None,
        concurrency: int | None = None,
    ):
        parent_group_id, parent_group_kind = self._current_definition_parent_group()
        operator = self._blue_print.attach_sub_flow(
            trigger_flow,
            self._definition_signals,
            name=name,
            capture=capture,
            write_back=write_back,
            concurrency=concurrency,
            group_id=self._definition_group_id,
            group_kind=self._definition_group_kind,
            parent_group_id=parent_group_id,
            parent_group_kind=parent_group_kind,
        )
        emit_signal = operator["emit_signals"][0]
        return self._new(
            trigger_event=emit_signal["trigger_event"] if not side_branch else self.trigger_event,
            trigger_type="event" if not side_branch else self.trigger_type,
            blue_print=self._blue_print,
            block_data=self._block_data,
            definition_signals=[emit_signal] if not side_branch else self._definition_signals,
            definition_group_id=self._definition_group_id,
            definition_group_kind=self._definition_group_kind,
            **self._options,
        )

    def side_branch(
        self,
        chunk: "TriggerFlowChunk | TriggerFlowHandler",
        *,
        name: str | None = None,
    ):
        return self.to(
            chunk,
            side_branch=True,
            name=name,
        )

    def batch(
        self,
        *chunks: "TriggerFlowChunk | TriggerFlowHandler | tuple[str, TriggerFlowHandler]",
        side_branch: bool = False,
        concurrency: int | None = None,
    ):
        batch_id = uuid.uuid4().hex
        batch_trigger = f"Batch-{ batch_id }"
        results_template: dict[str, Any] = {}
        triggers_template: dict[str, bool] = {}
        trigger_to_chunk_name = {}
        branch_input_signals: list[dict[str, Any]] = []
        branch_output_signals: list[dict[str, Any]] = []
        result_keys: dict[str, str] = {}

        async def wait_all_chunks(data: "TriggerFlowRuntimeData"):
            if data.event not in trigger_to_chunk_name:
                return
            layer_key = self._layer_key(data)
            state_key = f"batch_states.{ batch_id }.{ layer_key }"
            state = data._system_runtime_data.get(state_key)
            if not isinstance(state, dict):
                state = {
                    "results": copy.deepcopy(results_template),
                    "triggers": triggers_template.copy(),
                }
            state["results"][trigger_to_chunk_name[data.event]] = data.value
            state["triggers"][data.event] = True
            data._system_runtime_data.set(state_key, state)
            for done in state["triggers"].values():
                if done is False:
                    return
            await data.async_emit(
                batch_trigger,
                state["results"],
                _layer_marks=data._layer_marks.copy(),
            )
            del data._system_runtime_data[state_key]

        for chunk in chunks:
            if isinstance(chunk, tuple):
                chunk_name = chunk[0]
                chunk_func = chunk[1]
                chunk = self._flow_chunk(chunk_name)(chunk_func)
            else:
                if callable(chunk):
                    chunk = self._flow_chunk(chunk)
            typed_chunk = cast(TriggerFlowChunk, chunk)
            triggers_template[typed_chunk.trigger] = False
            trigger_to_chunk_name[typed_chunk.trigger] = typed_chunk.name
            results_template[typed_chunk.name] = None

            branch_input_event = f"Batch-{ batch_id }-Input-{ typed_chunk.id }"
            branch_input_signal = self._event_signal(branch_input_event)
            branch_output_signal = self._event_signal(typed_chunk.trigger)
            branch_input_signals.append(branch_input_signal)
            branch_output_signals.append(branch_output_signal)
            result_keys[branch_output_signal["id"]] = typed_chunk.name

            if concurrency is None or concurrency <= 0:
                handler = typed_chunk.async_call
            else:

                def make_handler(bound_chunk: TriggerFlowChunk):
                    async def handler(data: "TriggerFlowRuntimeData"):
                        semaphore_key = f"batch_semaphores.{ batch_id }"
                        semaphore = data._system_runtime_data.get(semaphore_key, inherit=False)
                        if not isinstance(semaphore, Semaphore):
                            semaphore = Semaphore(concurrency)
                            data._system_runtime_data.set(semaphore_key, semaphore)
                        async with semaphore:
                            return await bound_chunk.async_call(data)

                    return handler

                handler = make_handler(typed_chunk)

            self._blue_print.add_handler(
                self.trigger_type,
                self.trigger_event,
                handler,
            )
            self._blue_print.add_event_handler(typed_chunk.trigger, wait_all_chunks)
            self._blue_print.attach_chunk(
                typed_chunk,
                [branch_input_signal],
                group_id=batch_id,
                group_kind="batch",
                parent_group_id=self._definition_group_id,
                parent_group_kind=self._definition_group_kind,
            )

        self._blue_print.definition.add_operator(
            id=f"batch-fanout-{ batch_id }",
            kind="batch_fanout",
            name=f"batch:{ batch_id }",
            listen_signals=self._definition_signals,
            emit_signals=branch_input_signals,
            options={"concurrency": concurrency},
            group_id=batch_id,
            group_kind="batch",
            parent_group_id=self._definition_group_id,
            parent_group_kind=self._definition_group_kind,
        )
        self._blue_print.definition.add_operator(
            id=f"batch-collect-{ batch_id }",
            kind="batch_collect",
            name=f"batch_collect:{ batch_id }",
            listen_signals=branch_output_signals,
            emit_signals=[self._event_signal(batch_trigger, role="continuation")],
            options={"result_keys": result_keys},
            group_id=batch_id,
            group_kind="batch",
            parent_group_id=self._definition_group_id,
            parent_group_kind=self._definition_group_kind,
        )

        return self._new(
            trigger_event=batch_trigger if not side_branch else self.trigger_event,
            blue_print=self._blue_print,
            block_data=self._block_data,
            definition_signals=[self._event_signal(batch_trigger)] if not side_branch else self._definition_signals,
            definition_group_id=self._definition_group_id,
            definition_group_kind=self._definition_group_kind,
            **self._options,
        )

    def collect(
        self,
        collection_name: str,
        branch_id: str | None = None,
        *,
        mode: Literal["filled_and_update", "filled_then_empty"] = "filled_and_update",
    ):
        root_block = self._root_block_data()
        if "_collect_configs" not in root_block.data:
            root_block.data["_collect_configs"] = {}
        collect_configs = root_block.data["_collect_configs"]
        if collection_name not in collect_configs:
            collect_configs[collection_name] = {
                "collect_id": uuid.uuid4().hex,
                "branch_ids": [],
                "definition_operator_ids": [],
            }
        collection_config = collect_configs[collection_name]

        branch_id = branch_id if branch_id is not None else uuid.uuid4().hex
        if branch_id not in collection_config["branch_ids"]:
            collection_config["branch_ids"].append(branch_id)

        collect_id = collection_config["collect_id"]
        collect_trigger = f"Collect-{ collection_name }"

        async def collect_branches(data: "TriggerFlowRuntimeData"):
            branch_ids = list(collection_config["branch_ids"])
            layer_key = self._layer_key(data)
            state_key = f"collect_states.{ collect_id }.{ layer_key }"
            state = data._system_runtime_data.get(state_key)
            if not isinstance(state, dict):
                state = {configured_branch_id: EMPTY for configured_branch_id in branch_ids}
            state[branch_id] = data.value
            data._system_runtime_data.set(state_key, state)

            for configured_branch_id in branch_ids:
                if state.get(configured_branch_id, EMPTY) is EMPTY:
                    return

            collected = {configured_branch_id: state[configured_branch_id] for configured_branch_id in branch_ids}
            await data.async_emit(
                collect_trigger,
                collected,
                _layer_marks=data._layer_marks.copy(),
            )
            if mode == "filled_then_empty":
                del data._system_runtime_data[state_key]

        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            collect_branches,
        )

        operator_id = f"collect-{ collect_id }-{ branch_id }"
        self._blue_print.definition.add_operator(
            id=operator_id,
            kind="collect_branch",
            name=f"collect:{ collection_name }",
            listen_signals=self._definition_signals,
            emit_signals=[self._event_signal(collect_trigger, role="continuation")],
            options={
                "collection_name": collection_name,
                "collect_id": collect_id,
                "branch_id": branch_id,
                "branch_ids": list(collection_config["branch_ids"]),
                "mode": mode,
            },
            group_id=collect_id,
            group_kind="collect",
            parent_group_id=self._definition_group_id,
            parent_group_kind=self._definition_group_kind,
        )
        collection_config["definition_operator_ids"].append(operator_id)
        for definition_operator_id in collection_config["definition_operator_ids"]:
            operator = self._blue_print.definition.get_operator(definition_operator_id)
            operator["options"]["branch_ids"] = list(collection_config["branch_ids"])

        return self._new(
            trigger_event=collect_trigger,
            blue_print=self._blue_print,
            block_data=self._block_data,
            definition_signals=[self._event_signal(collect_trigger)],
            definition_group_id=self._definition_group_id,
            definition_group_kind=self._definition_group_kind,
            **self._options,
        )

    def end(self):
        async def set_default_result(data: "TriggerFlowRuntimeData"):
            result = data._system_runtime_data.get("result")
            if result is EMPTY:
                data.set_result(data.value)
            else:
                result_ready = data._system_runtime_data.get("result_ready")
                if isinstance(result_ready, Event):
                    result_ready.set()

        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            set_default_result,
        )
        self._blue_print.definition.add_operator(
            id=f"result-{ uuid.uuid4().hex }",
            kind="result_sink",
            name="result",
            listen_signals=self._definition_signals,
        )
        return self._new(
            trigger_event=self.trigger_event,
            trigger_type=self.trigger_type,
            blue_print=self._blue_print,
            block_data=self._block_data,
            definition_signals=self._definition_signals,
            definition_group_id=self._definition_group_id,
            definition_group_kind=self._definition_group_kind,
            **self._options,
        )

    def ____(
        self,
        *args,
        log_info: bool = False,
        print_info: bool = False,
        show_value: bool = False,
        **kwargs,
    ):
        """
        Separator for chain expression.
        Do nothing but return self.
        """
        if log_info or print_info or show_value:

            async def runtime_output(data: "TriggerFlowRuntimeData"):
                from agently.base import async_system_message

                message = {}
                annotations = list(args) if args else []
                annotations.extend([f"{k}:{v}" for k, v in kwargs.items()])
                if annotations:
                    message["ANNOTATIONS"] = "\t".join(annotations)
                if show_value:
                    message["VALUE"] = data.value
                if log_info:
                    await async_system_message(
                        "TRIGGER_FLOW",
                        message,
                        data.settings,
                    )
                if print_info:
                    print(*message.values())

            self.side_branch(runtime_output)

        return self
