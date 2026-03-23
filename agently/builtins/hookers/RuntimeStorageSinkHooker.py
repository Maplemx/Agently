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

import json
from typing import TYPE_CHECKING, Any

from agently.types.plugins import EventHooker
from agently.utils import DataFormatter

if TYPE_CHECKING:
    from agently.types.data import RuntimeEvent


def _stringify_payload(payload: Any) -> str:
    if payload is None:
        return ""
    sanitized = DataFormatter.sanitize(payload)
    try:
        return json.dumps(sanitized, ensure_ascii=False)
    except TypeError:
        return str(sanitized)


class RuntimeStorageSinkHooker(EventHooker):
    name = "RuntimeStorageSinkHooker"
    event_types = None

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    @staticmethod
    async def handler(event: "RuntimeEvent"):
        from agently.base import logger

        match event.level:
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

        content = event.message
        if content is None and event.error is not None:
            content = event.error.message
        if content is None:
            content = _stringify_payload(event.payload)
        run_label = f" [run={ event.run.run_id }]" if event.run is not None else ""
        log(f"[{ event.source }] [{ event.event_type }]{ run_label } { content or '' }".rstrip())
