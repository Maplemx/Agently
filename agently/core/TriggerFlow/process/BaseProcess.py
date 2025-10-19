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


import uuid
from asyncio import Event
from threading import Lock

from typing import Any, Literal, TYPE_CHECKING, overload
from typing_extensions import Self


if TYPE_CHECKING:
    from agently.core.TriggerFlow import TriggerFlowBluePrint
    from agently.types.trigger_flow import TriggerFlowHandler, TriggerFlowEventData

from agently.core.TriggerFlow.Chunk import TriggerFlowChunk
from agently.types.data import EMPTY
from agently.types.trigger_flow import TriggerFlowBlockData


class TriggerFlowBaseProcess:
    def __init__(
        self,
        *,
        trigger_event: str,
        blue_print: "TriggerFlowBluePrint",
        block_data: "TriggerFlowBlockData",
        trigger_type: Literal["event", "runtime_data", "flow_data"] = "event",
        **options,
    ):
        self.trigger_event = trigger_event
        self.trigger_type: Literal["event", "runtime_data", "flow_data"] = trigger_type
        self._blue_print = blue_print
        self._block_data = block_data
        self._options = options

    def _new(
        self,
        trigger_event: str,
        blue_print: "TriggerFlowBluePrint",
        block_data: "TriggerFlowBlockData",
        trigger_type: Literal["event", "runtime_data", "flow_data"] = "event",
        **options,
    ):
        return type(self)(
            trigger_event=trigger_event,
            trigger_type=trigger_type,
            blue_print=blue_print,
            block_data=block_data,
            **options,
        )

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
            return self._new(
                trigger_event=trigger_or_triggers,
                trigger_type="event",
                blue_print=self._blue_print,
                block_data=TriggerFlowBlockData(
                    outer_block=None,
                ),
            )
        else:
            values: dict[Literal["event", "runtime_data", "flow_data", "collect"], dict[str, Any]] = {}
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
                        raise TypeError(f"Can not use chunk as trigger event when trigger type is not 'event'.")
                if trigger_type == "collect":
                    trigger_type = "event"
                    if isinstance(trigger_event_or_events, str):
                        trigger_event_or_events = f"Collect-{ trigger_event_or_events }"
                    else:
                        trigger_events = []
                        for trigger_event in trigger_event_or_events:
                            trigger_events.append(f"Collect-{ trigger_event }")
                        trigger_event_or_events = trigger_events
                if isinstance(trigger_event_or_events, str):
                    values[trigger_type][trigger_event_or_events] = EMPTY
                    current_trigger_type = trigger_type
                    current_trigger_event = trigger_event_or_events
                    trigger_count += 1
                else:
                    for trigger_event in trigger_event_or_events:
                        if isinstance(trigger_event, TriggerFlowChunk):
                            trigger_event = trigger_event.trigger
                        values[trigger_type][trigger_event] = EMPTY
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
                )

            when_trigger = f"When-{ uuid.uuid4().hex }"

            async def wait_trigger(data: "TriggerFlowEventData"):
                match mode:
                    case "or" | "simple_or":
                        await data.async_emit(
                            when_trigger,
                            (
                                data.value
                                if mode == "simple_or"
                                else (data.trigger_type, data.trigger_event, data.value)
                            ),
                            layer_marks=data.layer_marks.copy(),
                        )
                    case "and":
                        if data.trigger_type in values and data.trigger_event in values[trigger_type]:  # type: ignore
                            values[data.trigger_type][data.trigger_event] = data.value
                        for trigger_event_dict in values.values():
                            for event_value in trigger_event_dict.values():
                                if event_value is EMPTY:
                                    return

                        await data.async_emit(
                            when_trigger,
                            values,
                            layer_marks=data.layer_marks.copy(),
                        )

            for trigger_type, trigger_event_dict in values.items():
                for trigger_event in trigger_event_dict.keys():
                    self._blue_print.add_handler(
                        trigger_type,  # type: ignore
                        trigger_event,
                        wait_trigger,
                    )

            return self._new(
                trigger_event=when_trigger,
                trigger_type="event",
                blue_print=self._blue_print,
                block_data=TriggerFlowBlockData(
                    outer_block=None,
                ),
            )

    def to(
        self,
        chunk: "TriggerFlowChunk | TriggerFlowHandler | str",
        side_branch: bool = False,
    ):
        if isinstance(chunk, str):
            if chunk in self._blue_print.chunks:
                chunk = self._blue_print.chunks[chunk]
            else:
                raise NotImplementedError(f"Cannot find chunk named '{ chunk }'")
        chunk = TriggerFlowChunk(chunk) if callable(chunk) else chunk
        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            chunk.async_call,
        )
        return self._new(
            trigger_event=chunk.trigger if not side_branch else self.trigger_event,
            trigger_type=self.trigger_type,
            blue_print=self._blue_print,
            block_data=self._block_data,
            **self._options,
        )

    def side_branch(self, chunk: "TriggerFlowChunk | TriggerFlowHandler"):
        return self.to(chunk, side_branch=True)

    def batch(
        self,
        *chunks: "TriggerFlowChunk | TriggerFlowHandler",
        side_branch: bool = False,
    ):
        batch_trigger = f"Batch-{ uuid.uuid4().hex }"
        results = {}
        chunks_to_wait = {}

        async def wait_all_chunks(data: "TriggerFlowEventData"):
            if data.event in chunks_to_wait:
                results[data.event] = data.value
                chunks_to_wait[data.event] = True
            for done in chunks_to_wait.values():
                if done is False:
                    return
            await data.async_emit(
                batch_trigger,
                results,
                layer_marks=data.layer_marks.copy(),
            )

        for chunk in chunks:
            chunk = TriggerFlowChunk(chunk) if callable(chunk) else chunk
            chunks_to_wait[chunk.name] = False
            self._blue_print.add_handler(
                self.trigger_type,
                self.trigger_event,
                chunk.async_call,
            )
            self._blue_print.add_event_handler(chunk.trigger, wait_all_chunks)

        return self._new(
            trigger_event=batch_trigger if not side_branch else self.trigger_event,
            blue_print=self._blue_print,
            block_data=self._block_data,
            **self._options,
        )

    def collect(
        self,
        collection_name: str,
        branch_id: str | None = None,
        *,
        mode: Literal["filled_and_update", "filled_then_empty"] = "filled_and_update",
    ):
        branch_id = branch_id if branch_id is not None else uuid.uuid4().hex
        collect_trigger = f"Collect-{ collection_name }"
        with Lock():
            self._block_data.global_data.set(f"collections.{ collection_name }.{ branch_id }", EMPTY)

        async def collect_branches(data: "TriggerFlowEventData"):
            self._block_data.global_data.set(f"collections.{ collection_name }.{ branch_id }", data.value)
            for value in self._block_data.global_data.get(f"collections.{ collection_name}", {}).values():
                if value is EMPTY:
                    return

            if mode == "filled_and_update":
                await data.async_emit(
                    collect_trigger,
                    self._block_data.global_data.get(f"collections.{ collection_name}"),
                    layer_marks=data.layer_marks.copy(),
                )
            elif mode == "filled_then_empty":
                await data.async_emit(
                    collect_trigger,
                    self._block_data.global_data.get(f"collections.{ collection_name}"),
                    layer_marks=data.layer_marks.copy(),
                )
                del self._block_data.global_data[f"collections.{ collection_name}"]

        self.to(collect_branches)

        return self._new(
            trigger_event=collect_trigger,
            blue_print=self._blue_print,
            block_data=self._block_data,
            **self._options,
        )

    def end(self):
        async def set_default_result(data: "TriggerFlowEventData"):
            result = data._system_runtime_data.get("result")
            if result is EMPTY:
                data._system_runtime_data.set("result", data.value)
            result_ready = data._system_runtime_data.get("result_ready")
            if isinstance(result_ready, Event):
                result_ready.set()

        return self.to(set_default_result)

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

            async def runtime_output(data: "TriggerFlowEventData"):
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
