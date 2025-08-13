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

from typing import TYPE_CHECKING

from agently.types.plugins import EventHooker

if TYPE_CHECKING:
    from agently.types.data.event import EventMessage, EventStatus


class PureLoggerHooker(EventHooker):
    name = "PureLoggerHooker"
    events = ["message", "log"]

    _status_mapping: dict["EventStatus", str] = {
        "": "",
        "INIT": "▶️",
        "DOING": "🔨",
        "PENDING": "🕘",
        "SUCCESS": "✅",
        "FAILED": "❌",
        "UNKNOWN": "😶",
    }

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    @staticmethod
    async def handler(message: "EventMessage"):
        from agently.base import logger

        match message.level:
            case "DEBUG":
                log = logger.debug
            case "INFO":
                log = logger.info
            case "WARNING":
                log = logger.warning
            case "ERROR":
                log = logger.error
            case "CRITICAL":
                log = logger.critical
        log(
            f"{ PureLoggerHooker._status_mapping[message.status] + ' ' if message.status in PureLoggerHooker._status_mapping else message.status  + ' ' }"
            f"[{ message.module_name }] "
            f"{ message.content}"
        )
