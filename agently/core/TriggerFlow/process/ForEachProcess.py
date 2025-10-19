# Copyright 2023-2025 AgentEra(Agently.Tech)
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

from agently.core.TriggerFlow.process import TriggerFlowBaseProcess
from agently.types.data import EMPTY
from agently.types.trigger_flow import TriggerFlowBlockData
from agently.utils import RuntimeDataNamespace


class TriggerFlowForEachProcess(TriggerFlowBaseProcess):
    def for_each(self):
        for_each_id = uuid.uuid4().hex
        for_each_block_data = TriggerFlowBlockData(
            outer_block=self._block_data,
            data={
                "for_each_id": for_each_id,
            },
        )
        send_item_trigger = f"ForEach-{ for_each_id }-Send"

        async def send_items(data: "TriggerFlowEventData"):
            data.layer_in()
            for_each_instance_id = data.layer_mark
            assert for_each_instance_id is not None

            send_tasks = []
            if not isinstance(data.value, str) and isinstance(data.value, Sequence):
                items = list(data.value)
                for item in items:
                    data.layer_in()
                    item_id = data.layer_mark
                    assert item_id is not None
                    data._system_runtime_data.set(f"for_each_results.{ for_each_instance_id }.{ item_id }", EMPTY)
                    send_tasks.append(
                        data.async_emit(
                            send_item_trigger,
                            item,
                            data.layer_marks.copy(),
                        )
                    )
                    data.layer_out()
                await asyncio.gather(*send_tasks)
            else:
                data.layer_in()
                item_id = data.layer_mark
                assert item_id is not None
                data._system_runtime_data.set(f"for_each_results.{ for_each_instance_id }.{ item_id }", EMPTY)
                await data.async_emit(
                    send_item_trigger,
                    data.value,
                    data.layer_marks.copy(),
                )
                data.layer_out()

        self.to(send_items)

        return self._new(
            trigger_event=send_item_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=for_each_block_data,
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

                # double out to restore upper for each id and item id
                data.layer_out()
                data.layer_out()

                await data.async_emit(
                    end_for_each_trigger,
                    list(for_each_results[for_each_instance_id].values()),
                    data.layer_marks.copy(),
                )
                for_each_results.delete(for_each_instance_id)

        self.to(collect_results)

        outer_block = self._block_data.outer_block
        block_data = outer_block if outer_block is not None else TriggerFlowBlockData()

        return self._new(
            trigger_event=end_for_each_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=block_data,
        )
