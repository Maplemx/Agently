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

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowEventData
    from agently.types.data import SerializableValue

from agently.types.trigger_flow import TriggerFlowBlockData
from agently.utils import FunctionShifter
from .BaseProcess import TriggerFlowBaseProcess

TriggerFlowCaseHandler = Callable[["TriggerFlowEventData"], bool]


class TriggerFlowMatchCaseProcess(TriggerFlowBaseProcess):
    def match(self):
        case_block_data = TriggerFlowBlockData(
            outer_block=self._block_data,
        )
        match_id = uuid.uuid4().hex
        case_block_data.data.update(
            {
                "match_id": match_id,
                "else_trigger": f"Match-{ match_id }-Else",
                "end_trigger": f"Match-{ match_id }-End",
                "is_first_case": True,
                "branch_ends": [],
                "cases": [],
            }
        )

        if "branch_trigger_event" not in case_block_data.data:
            case_block_data.data["branch_trigger_event"] = self.trigger_event

        return self._new(
            trigger_event=self.trigger_event,
            trigger_type=self.trigger_type,
            blue_print=self._blue_print,
            block_data=case_block_data,
        )

    def case(self, condition: "TriggerFlowCaseHandler | SerializableValue"):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .case() before .match().")

        match_id = self._block_data.data["match_id"]

        is_first_case = self._block_data.data["is_first_case"]
        if is_first_case:
            self._block_data.data["is_first_case"] = False
        else:
            self._block_data.data["branch_ends"].append(self.trigger_event)

        case_trigger = f"Match-{ match_id }-Case-{ uuid.uuid4().hex }"
        self._block_data.data["cases"].append(case_trigger)

        async def check_condition(data: "TriggerFlowEventData"):
            if callable(condition):
                result = await FunctionShifter.asyncify(condition)(data)
                if result:
                    await data.async_emit(
                        case_trigger,
                        data.value,
                    )
                else:
                    data.append_runtime_data(
                        f"$TF.{ match_id }.failed_cases",
                        case_trigger,
                    )
            else:
                if data.value == condition:
                    await data.async_emit(
                        case_trigger,
                        data.value,
                    )
                else:
                    data.append_runtime_data(
                        f"$TF.{ match_id }.failed_cases",
                        case_trigger,
                    )

        self._blue_print.add_event_handler(
            self._block_data.data["branch_trigger_event"],
            check_condition,
        )

        return self._new(
            trigger_event=case_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=self._block_data,
        )

    def else_case(self):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .case() before .match().")
        match_id = self._block_data.data["match_id"]
        is_first_case = self._block_data.data["is_first_case"]
        if is_first_case:
            raise NotImplementedError(f"Cannot use .else_case() before any .case().")
        else:
            self._block_data.data["branch_ends"].append(self.trigger_event)
        else_trigger = self._block_data.data["else_trigger"]

        async def wait_else(data: "TriggerFlowEventData"):
            if len(data.value) >= len(self._block_data.data["cases"]):
                await data.async_emit(
                    else_trigger,
                    data.value,
                )
                data.del_runtime_data(data.event, emit=False)

        self._blue_print.add_runtime_data_handler(
            f"$TF.{ match_id }.failed_cases",
            wait_else,
        )

        return self._new(
            trigger_event=else_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=self._block_data,
        )

    def end_match(self):
        if "match_id" not in self._block_data.data:
            raise NotImplementedError(f"Cannot use .end_match() before .match().")
        end_trigger = self._block_data.data["end_trigger"]
        branch_ends = self._block_data.data["branch_ends"]
        branch_ends.append(self.trigger_event)

        async def collect_branch_result(data: "TriggerFlowEventData"):
            await data.async_emit(
                end_trigger,
                data.value,
            )

        for event in branch_ends:
            self._blue_print.add_event_handler(event, collect_branch_result)

        outer_block = self._block_data.outer_block
        block_data = (
            outer_block
            if outer_block is not None
            else TriggerFlowBlockData(
                outer_block=None,
            )
        )

        return self._new(
            trigger_event=end_trigger,
            trigger_type="event",
            blue_print=self._blue_print,
            block_data=block_data,
        )

    # If Condition
    def if_condition(self, condition: "TriggerFlowCaseHandler | SerializableValue"):
        match_process = self.match()
        case_process = match_process.case(condition)
        return case_process

    elif_condition = case
    else_condition = else_case
    end_condition = end_match
