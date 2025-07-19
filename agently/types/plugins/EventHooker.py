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

from typing import TYPE_CHECKING, Protocol
from agently.types.plugins import AgentlyPlugin

if TYPE_CHECKING:
    from agently.types.data.event import AgentlyEvent, EventMessage


class EventHooker(AgentlyPlugin, Protocol):
    name: str
    events: list["AgentlyEvent"]

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    @staticmethod
    async def handler(message: "EventMessage"): ...
