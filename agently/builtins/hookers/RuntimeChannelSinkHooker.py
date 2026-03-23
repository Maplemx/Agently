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

from typing import TYPE_CHECKING

from agently.types.plugins import EventHooker

if TYPE_CHECKING:
    from agently.types.data import RuntimeEvent

class RuntimeChannelSinkHooker(EventHooker):
    name = "RuntimeChannelSinkHooker"
    event_types = None
    _buffer: list["RuntimeEvent"] = []

    @staticmethod
    def _on_register():
        RuntimeChannelSinkHooker._buffer.clear()

    @staticmethod
    def _on_unregister():
        RuntimeChannelSinkHooker._buffer.clear()

    @staticmethod
    def read_buffer():
        return list(RuntimeChannelSinkHooker._buffer)

    @staticmethod
    def drain_buffer():
        buffered = list(RuntimeChannelSinkHooker._buffer)
        RuntimeChannelSinkHooker._buffer.clear()
        return buffered

    @staticmethod
    async def handler(event: "RuntimeEvent"):
        RuntimeChannelSinkHooker._buffer.append(event.model_copy(deep=True))
