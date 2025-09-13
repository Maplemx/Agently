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
import asyncio

from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowEventData

from agently.types.trigger_flow import TriggerFlowBlockData
from .BaseProcess import TriggerFlowBaseProcess


class TriggerFlowForEachProcess(TriggerFlowBaseProcess):
    def for_each(self, *, with_index: bool = False):
        for_each_block_data = TriggerFlowBlockData(
            outer_block=self._block_data,
        )
        for_each_id = uuid.uuid4().hex
        for_each_block_data.data["for_each_id"] = for_each_id
        send_items_trigger = f"ForEach-{ for_each_id }-Send"

        async def send_for_each_items(data: "TriggerFlowEventData"):
            if not isinstance(data.value, str) and isinstance(data.value, Sequence):
                data._system_runtime_data.set(
                    f"ForEach-{ for_each_id }.len",
                    len(data.value),
                )
                await asyncio.gather(
                    *(
                        [
                            data.async_emit(
                                send_items_trigger,
                                (index, item) if with_index else item,
                            )
                            for index, item in enumerate(data.value)
                        ]
                    )
                )
            else:
                data._system_runtime_data.set(f"ForEach-{ for_each_id }.len", 1)
                await data.async_emit(send_items_trigger, data.value)

        self.to(send_for_each_items)

        return self._new(
            trigger_event=send_items_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=for_each_block_data,
        )

    def end_for_each(self, *, sort_by_index: bool = False):
        if "for_each_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .case() before .match().")
        for_each_id = self._block_data.data["for_each_id"]
        self._results = []
        end_task_trigger = f"ForEach-{ for_each_id }-End"

        async def collect_for_each_results(data: "TriggerFlowEventData"):
            if sort_by_index:
                try:
                    index, result = data.value
                    self._results.append((index, result))
                except:
                    raise ValueError(
                        f"Return tuple(index, value) to .end_for_each() process if you want to use `sort_by_index`."
                    )
            else:
                result = data.value
                self._results.append(result)

            if len(self._results) == data._system_runtime_data[f"ForEach-{ for_each_id }.len"]:
                if sort_by_index:
                    self._results = [
                        value
                        for _, value in sorted(
                            self._results,
                            key=lambda results: results[0],
                        )
                    ]
                await data.async_emit(end_task_trigger, self._results)
                del data._system_runtime_data[f"ForEach-{ for_each_id }"]

        self.to(collect_for_each_results)

        outer_block = self._block_data.outer_block
        block_data = (
            outer_block
            if outer_block is not None
            else TriggerFlowBlockData(
                outer_block=None,
            )
        )

        return self._new(
            trigger_event=end_task_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=block_data,
        )
