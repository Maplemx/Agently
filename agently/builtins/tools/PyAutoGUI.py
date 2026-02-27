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

import os
import platform
import time
from typing import Any

from agently.types.plugins import BuiltInTool
from agently.utils import LazyImport


class PyAutoGUI(BuiltInTool):
    def __init__(
        self,
        *,
        pause: float = 0.05,
        fail_safe: bool = True,
    ):
        self.tool_info_list = [
            {
                "name": "pyautogui_open_url",
                "desc": "Use keyboard automation to open {url} in the focused browser.",
                "kwargs": {
                    "url": ("str", "Target URL"),
                    "new_tab": ("bool", "Open a new browser tab first"),
                    "wait_seconds": ("float", "Seconds to wait after opening URL"),
                    "dry_run": ("bool", "Only return planned actions"),
                },
                "func": self.open_url,
            }
        ]

        LazyImport.import_package("pyautogui")
        self.pause = pause
        self.fail_safe = fail_safe

    async def open_url(
        self,
        url: str,
        new_tab: bool = True,
        wait_seconds: float = 1.5,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Open URL in currently focused browser with keyboard shortcuts.

        Args:
            url: URL to type.
            new_tab: Whether to create a new tab before opening URL.
            wait_seconds: Seconds to wait after pressing Enter.
            dry_run: Return actions without controlling keyboard/mouse.

        Returns:
            Dictionary with execution status and metadata.
        """
        import pyautogui

        os_name = platform.system()
        modifier = "command" if os_name == "Darwin" else "ctrl"
        actions = []
        if new_tab:
            actions.append(f"{modifier}+t")
        actions.append(f"{modifier}+l")
        actions.extend([f"type:{url}", "press:enter"])

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "platform": os_name,
                "actions": actions,
            }

        if os_name == "Linux" and not os.environ.get("DISPLAY"):
            return {
                "ok": False,
                "error": "DISPLAY is not set. GUI session is required for PyAutoGUI.",
            }

        pyautogui.PAUSE = self.pause
        pyautogui.FAILSAFE = self.fail_safe

        try:
            if new_tab:
                pyautogui.hotkey(modifier, "t")
            pyautogui.hotkey(modifier, "l")
            pyautogui.typewrite(url, interval=0.01)
            pyautogui.press("enter")
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            return {
                "ok": True,
                "dry_run": False,
                "platform": os_name,
                "url": url,
            }
        except Exception as e:
            return {
                "ok": False,
                "dry_run": False,
                "platform": os_name,
                "url": url,
                "error": str(e),
            }
