# Copyright 2023-2026 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

import uuid
import asyncio
from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowEventData

from .BaseProcess import TriggerFlowBaseProcess
from agently.types.data import EMPTY
from agently.types.trigger_flow import TriggerFlowBlockData
from agently.utils import RuntimeDataNamespace


class TriggerFlowForEachProcess(TriggerFlowBaseProcess):
    def for_each(self, *, concurrency: int | None = None):
        for_each_id = uuid.uuid4().hex
        for_each_block_data = TriggerFlowBlockData(
            outer_block=self._block_data,
            data={
                "for_each_id": for_each_id,
                "definition_outer_group_id": self._definition_group_id,
                "definition_outer_group_kind": self._definition_group_kind,
            },
        )
        send_item_trigger = f"ForEach-{ for_each_id }-Send"

        async def send_items(data: "TriggerFlowEventData"):
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
                return item_id, layer_marks, item

            async def emit_item(item, layer_marks):
                if concurrency is None or concurrency <= 0:
                    await data.async_emit(
                        send_item_trigger,
                        item,
                        layer_marks,
                    )
                else:
                    semaphore_key = f"for_each_semaphores.{ for_each_id }"
                    semaphore = data._system_runtime_data.get(semaphore_key, inherit=False)
                    if not isinstance(semaphore, asyncio.Semaphore):
                        semaphore = asyncio.Semaphore(concurrency)
                        data._system_runtime_data.set(semaphore_key, semaphore)
                    async with semaphore:
                        await data.async_emit(
                            send_item_trigger,
                            item,
                            layer_marks,
                        )

            if not isinstance(data.value, str) and isinstance(data.value, Sequence):
                items = list(data.value)
                for item in items:
                    _, layer_marks, item_value = prepare_item(item)
                    send_tasks.append(emit_item(item_value, layer_marks))
                await asyncio.gather(*send_tasks)
            else:
                _, layer_marks, item_value = prepare_item(data.value)
                await emit_item(item_value, layer_marks)

        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            send_items,
        )
        self._blue_print.definition.add_operator(
            id=f"for_each-split-{ for_each_id }",
            kind="for_each_split",
            name=f"for_each:{ for_each_id }",
            listen_signals=self._definition_signals,
            emit_signals=[self._event_signal(send_item_trigger, role="continuation")],
            options={"concurrency": concurrency},
            group_id=for_each_id,
            group_kind="for_each",
        )

        return self._new(
            trigger_event=send_item_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=for_each_block_data,
            definition_signals=[self._event_signal(send_item_trigger)],
            definition_group_id=for_each_id,
            definition_group_kind="for_each",
        )

    def end_for_each(self):
        if "for_each_id" not in self._block_data.data:
            raise NotImplementedError("Cannot use .end_for_each() without .for_each().")

        for_each_id = self._block_data.data["for_each_id"]
        end_for_each_trigger = f"ForEach-{ for_each_id }-End"

        async def collect_results(data: "TriggerFlowEventData"):
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
                    end_for_each_trigger,
                    list(for_each_results[for_each_instance_id].values()),
                    data._layer_marks.copy(),
                )
                for_each_results.delete(for_each_instance_id)

        self._blue_print.add_handler(
            self.trigger_type,
            self.trigger_event,
            collect_results,
        )
        self._blue_print.definition.add_operator(
            id=f"for_each-collect-{ for_each_id }",
            kind="for_each_collect",
            name=f"for_each_collect:{ for_each_id }",
            listen_signals=self._definition_signals,
            emit_signals=[self._event_signal(end_for_each_trigger, role="continuation")],
            group_id=for_each_id,
            group_kind="for_each",
        )

        outer_block = self._block_data.outer_block
        block_data = outer_block if outer_block is not None else TriggerFlowBlockData()

        return self._new(
            trigger_event=end_for_each_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=block_data,
            definition_signals=[self._event_signal(end_for_each_trigger)],
            definition_group_id=self._block_data.data.get("definition_outer_group_id"),
            definition_group_kind=self._block_data.data.get("definition_outer_group_kind"),
        )
