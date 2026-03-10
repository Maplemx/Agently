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


from typing import Any


TRIGGER_FLOW_STATUS_CREATED = "created"
TRIGGER_FLOW_STATUS_RUNNING = "running"
TRIGGER_FLOW_STATUS_WAITING = "waiting"
TRIGGER_FLOW_STATUS_COMPLETED = "completed"
TRIGGER_FLOW_STATUS_FAILED = "failed"
TRIGGER_FLOW_STATUS_CANCELLED = "cancelled"


class TriggerFlowPauseSignal(dict[str, Any]):
    def __init__(self, interrupt: dict[str, Any]):
        super().__init__(interrupt)
        self.interrupt = interrupt
