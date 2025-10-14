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

from typing import Callable, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.data import SerializableValue
    from agently.types.trigger_flow import TriggerFlowEventData

from agently.types.data import EMPTY
from agently.types.trigger_flow import TriggerFlowBlockData
from .BaseProcess import TriggerFlowBaseProcess

TriggerFlowConditionHandler = Callable[["TriggerFlowEventData"], bool]


class TriggerFlowMatchCaseProcess(TriggerFlowBaseProcess):
    def match(self, *, mode: Literal["hit_first", "hit_all"] = "hit_first"):
        match_block_data = TriggerFlowBlockData(
            outer_block=self._block_data,
        )
        match_id = uuid.uuid4().hex
        match_block_data.data.update(
            {
                "match_id": match_id,
                "cases": {},
                "branch_ends": [],
                "is_first_case": True,
                "has_else": False,
            }
        )

        async def match_case(data: "TriggerFlowEventData"):
            data.layer_in()
            matched_count = 0
            tasks = []
            for case_id, condition in match_block_data.data["cases"].items():
                if callable(condition):
                    judgement = condition(data)
                else:
                    judgement = bool(data.value == condition)
                if judgement is True:
                    if mode == "hit_first":
                        await data.async_emit(
                            f"Match-{ match_id }-Case-{ case_id }",
                            data.value,
                            layer_marks=data.layer_marks.copy(),
                        )
                        return
                    elif mode == "hit_all":
                        data.layer_in()
                        matched_count += 1
                        data._system_runtime_data.set(
                            f"match_results.{ data.upper_layer_mark }.{ data.layer_mark }", EMPTY
                        )
                        tasks.append(
                            data.async_emit(
                                f"Match-{ match_id }-Case-{ case_id }",
                                data.value,
                                layer_marks=data.layer_marks.copy(),
                            )
                        )
                        data.layer_out()
            await asyncio.gather(*tasks)
            if matched_count == 0:
                if match_block_data.data["has_else"] is True:
                    await data.async_emit(
                        f"Match-{ match_id }-Else",
                        data.value,
                        layer_marks=data.layer_marks.copy(),
                    )
                else:
                    await data.async_emit(
                        f"Match-{ match_id }-Result",
                        data.value,
                        layer_marks=data.layer_marks.copy(),
                    )

        self.to(match_case)

        return self._new(
            trigger_event=self.trigger_event,
            trigger_type=self.trigger_type,
            blue_print=self._blue_print,
            block_data=match_block_data,
        )

    def case(self, condition: "TriggerFlowConditionHandler | SerializableValue"):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .case() before .match().")

        match_id = self._block_data.data["match_id"]
        case_id = uuid.uuid4().hex
        self._block_data.data["cases"][case_id] = condition

        is_first_case = self._block_data.data["is_first_case"]
        if is_first_case:
            self._block_data.data["is_first_case"] = False
        else:
            if not self.trigger_event.startswith(f"Match-{ match_id }"):
                self._block_data.data["branch_ends"].append(self.trigger_event)

        case_trigger = f"Match-{ match_id }-Case-{ case_id }"
        return self._new(
            trigger_event=case_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=self._block_data,
        )

    def case_else(self):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .case() before .match().")

        self._block_data.data["has_else"] = True
        match_id = self._block_data.data["match_id"]
        is_first_case = self._block_data.data["is_first_case"]
        if is_first_case:
            raise NotImplementedError(f"Cannot use .case_else() before any .case().")
        else:
            if not self.trigger_event.startswith(f"Match-{ match_id }"):
                self._block_data.data["branch_ends"].append(self.trigger_event)

        else_trigger = f"Match-{ match_id }-Else"
        return self._new(
            trigger_event=else_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=self._block_data,
        )

    def end_match(self):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .end_match() before .match().")
        match_id = self._block_data.data["match_id"]
        branch_ends = self._block_data.data["branch_ends"]
        if not self.trigger_event.startswith(f"Match-{ match_id }"):
            branch_ends.append(self.trigger_event)

        async def collect_branch_result(data: "TriggerFlowEventData"):
            match_results = data._system_runtime_data.get(f"match_results.{ data.upper_layer_mark }")
            if match_results:
                if data.layer_mark in match_results:
                    match_results[data.layer_mark] = data.value
                for value in match_results.values():
                    if value is EMPTY:
                        data._system_runtime_data.set(f"match_results.{ data.upper_layer_mark }", match_results)
                        return
                data.layer_out()
                await data.async_emit(
                    f"Match-{ match_id }-Result",
                    list(match_results.values()),
                    layer_marks=data.layer_marks.copy(),
                )
                del data._system_runtime_data[f"match_results.{ data.upper_layer_mark }"]
            else:
                data.layer_out()
                await data.async_emit(
                    f"Match-{ match_id }-Result",
                    data.value,
                    layer_marks=data.layer_marks.copy(),
                )

        for trigger in branch_ends:
            self.when(trigger).to(collect_branch_result)

        outer_block = self._block_data.outer_block
        block_data = (
            outer_block
            if outer_block is not None
            else TriggerFlowBlockData(
                outer_block=None,
            )
        )

        return self._new(
            trigger_event=f"Match-{ match_id }-Result",
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=block_data,
        )

    # If Condition
    def if_condition(self, condition: "TriggerFlowConditionHandler | SerializableValue"):
        return self.match().case(condition)

    elif_condition = case
    else_condition = case_else
    end_condition = end_match
