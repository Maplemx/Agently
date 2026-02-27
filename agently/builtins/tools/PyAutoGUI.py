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
import json
import re
import subprocess
import time
import unicodedata
import webbrowser
from typing import Any, Literal

from agently.types.plugins import BuiltInTool
from agently.utils import LazyImport

_URL_PUNCT_TRANSLATION = str.maketrans(
    {
        "。": ".",
        "，": ",",
        "；": ";",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "《": "<",
        "》": ">",
        "「": '"',
        "」": '"',
        "『": '"',
        "』": '"',
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "、": "/",
    }
)


class PyAutoGUI(BuiltInTool):
    def __init__(
        self,
        *,
        pause: float = 0.05,
        fail_safe: bool = True,
        new_tab: bool = True,
        wait_seconds: float = 1.5,
        dry_run: bool = True,
        type_interval: float = 0.01,
        open_mode: Literal["hotkey", "system"] = "hotkey",
        activate_browser: bool = False,
        browser_app: str | None = None,
        activate_wait_seconds: float = 0.4,
        read_wait_seconds: float = 0.4,
        max_content_length: int = 24000,
        response_mode: Literal["markdown", "text"] = "markdown",
    ):
        self.tool_info_list = [
            {
                "name": "pyautogui_open_url",
                "desc": "Open {url} with keyboard automation or system browser open (configured by tool settings).",
                "kwargs": {
                    "url": ("str", "Target URL"),
                },
                "func": self.open_url,
            },
            {
                "name": "pyautogui_read_active_tab",
                "desc": "Read URL, title and visible text from the active tab of the configured browser.",
                "kwargs": {},
                "func": self.read_active_tab,
            },
            {
                "name": "pyautogui_open_and_read_url",
                "desc": "Open {url} in browser and then read active tab content in the same browser session.",
                "kwargs": {
                    "url": ("str", "Target URL"),
                },
                "func": self.open_and_read_url,
            },
        ]

        self.pause = pause
        self.fail_safe = fail_safe
        self.new_tab = new_tab
        self.wait_seconds = wait_seconds
        self.dry_run = dry_run
        self.type_interval = type_interval
        self.open_mode = open_mode
        self.activate_browser = activate_browser
        self.browser_app = browser_app
        self.activate_wait_seconds = activate_wait_seconds
        self.read_wait_seconds = read_wait_seconds
        self.max_content_length = max_content_length
        self.response_mode = response_mode

        if self.open_mode == "hotkey":
            LazyImport.import_package("pyautogui")

    def _activate_browser(self, os_name: str) -> str | None:
        if not self.activate_browser:
            return None
        app = (self.browser_app or "").strip()
        try:
            if os_name == "Darwin":
                target = app or "Google Chrome"
                subprocess.run(
                    ["osascript", "-e", f'tell application "{target}" to activate'],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if self.activate_wait_seconds > 0:
                    time.sleep(self.activate_wait_seconds)
                return target
            if os_name == "Windows" and app:
                subprocess.run(
                    f'start "" "{app}"',
                    shell=True,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if self.activate_wait_seconds > 0:
                    time.sleep(self.activate_wait_seconds)
                return app
            if os_name == "Linux" and app:
                subprocess.Popen(
                    [app],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if self.activate_wait_seconds > 0:
                    time.sleep(self.activate_wait_seconds)
                return app
        except Exception:
            return None
        return None

    def _normalize_url(self, url: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(url or "")).strip()
        normalized = normalized.translate(_URL_PUNCT_TRANSLATION)
        normalized = normalized.replace("\u3000", " ")
        normalized = re.sub(r"[\r\n\t]+", "", normalized)
        normalized = normalized.strip(' "\'`')
        normalized = re.sub(r"[,;:!?]+$", "", normalized)
        return normalized

    def _normalize_content(self, content: str) -> str:
        normalized = str(content or "").replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if self.max_content_length > 0 and len(normalized) > self.max_content_length:
            return f"{normalized[:self.max_content_length]}..."
        return normalized

    def _resolve_browser_app(self, os_name: str) -> str:
        if self.browser_app and self.browser_app.strip():
            return self.browser_app.strip()
        if os_name == "Darwin":
            return "Google Chrome"
        return ""

    def _build_read_javascript(self) -> str:
        if self.response_mode == "text":
            return (
                "JSON.stringify({"
                "url: location.href || '',"
                "title: document.title || '',"
                "content: ((document.body && document.body.innerText) || '')"
                "})"
            )
        return (
            "(() => {"
            "const root = document.body ? document.body.cloneNode(true) : null;"
            "if (root) {"
            "root.querySelectorAll('script,style,noscript,svg').forEach((el) => el.remove());"
            "root.querySelectorAll('a[href]').forEach((a) => {"
            "const href = a.href || '';"
            "const text = (a.textContent || '').trim().replace(/\\s+/g, ' ');"
            "const markdownLink = text ? '[' + text + '](' + href + ')' : href;"
            "a.replaceWith(document.createTextNode(markdownLink));"
            "});"
            "}"
            "const content = root ? (root.innerText || '') : '';"
            "return JSON.stringify({"
            "url: location.href || '',"
            "title: document.title || '',"
            "content: content"
            "});"
            "})()"
        )

    def _build_darwin_read_script(self, browser_app: str) -> list[str]:
        javascript = self._build_read_javascript()
        javascript_escaped = javascript.replace("\\", "\\\\").replace('"', '\\"')
        return [
            f'tell application "{browser_app}"',
            '    if (count of windows) is 0 then return ""',
            "    set _tab to active tab of front window",
            f'    set _json to execute _tab javascript "{javascript_escaped}"',
            "    return _json",
            "end tell",
        ]

    def _run_osascript(self, script_lines: list[str]) -> tuple[int, str, str]:
        cmd = ["osascript"]
        for line in script_lines:
            cmd.extend(["-e", line])
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    async def open_url(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Open URL in a real browser with configured mode.

        Args:
            url: URL to type.
            Behavior is configured at class initialization.

        Returns:
            Dictionary with execution status and metadata.
        """
        requested_url = str(url or "")
        url = self._normalize_url(requested_url)
        os_name = platform.system()
        actions = []
        if self.activate_browser:
            actions.append(f"activate:{self.browser_app or 'default-browser'}")
        if self.open_mode == "system":
            actions.append(f"system_open:{url}")
        else:
            modifier = "command" if os_name == "Darwin" else "ctrl"
            if self.new_tab:
                actions.append(f"{modifier}+t")
            actions.append(f"{modifier}+l")
            actions.extend([f"type:{url}", "press:enter"])

        if self.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "platform": os_name,
                "open_mode": self.open_mode,
                "requested_url": requested_url,
                "url": url,
                "actions": actions,
            }

        if self.open_mode == "hotkey" and os_name == "Linux" and not os.environ.get("DISPLAY"):
            return {
                "ok": False,
                "error": "DISPLAY is not set. GUI session is required for PyAutoGUI.",
            }

        activated = self._activate_browser(os_name)

        try:
            if self.open_mode == "system":
                opened = bool(webbrowser.open_new_tab(url))
                if self.wait_seconds > 0:
                    time.sleep(self.wait_seconds)
                return {
                    "ok": opened,
                    "dry_run": False,
                    "platform": os_name,
                    "open_mode": self.open_mode,
                    "activated_browser": activated,
                    "requested_url": requested_url,
                    "url": url,
                }

            import pyautogui

            modifier = "command" if os_name == "Darwin" else "ctrl"
            pyautogui.PAUSE = self.pause
            pyautogui.FAILSAFE = self.fail_safe
            if self.new_tab:
                pyautogui.hotkey(modifier, "t")
            pyautogui.hotkey(modifier, "l")
            pyautogui.typewrite(url, interval=self.type_interval)
            pyautogui.press("enter")
            if self.wait_seconds > 0:
                time.sleep(self.wait_seconds)
            return {
                "ok": True,
                "dry_run": False,
                "platform": os_name,
                "open_mode": self.open_mode,
                "activated_browser": activated,
                "requested_url": requested_url,
                "url": url,
            }
        except Exception as e:
            hint = ""
            if os_name == "Darwin":
                hint = (
                    "Grant Accessibility and Input Monitoring permissions to your terminal app "
                    "(System Settings > Privacy & Security)."
                )
            return {
                "ok": False,
                "dry_run": False,
                "platform": os_name,
                "open_mode": self.open_mode,
                "requested_url": requested_url,
                "url": url,
                "error": str(e),
                "hint": hint,
            }

    async def read_active_tab(self) -> dict[str, Any]:
        """
        Read URL/title/visible content from active browser tab in the current user session.
        """
        os_name = platform.system()
        browser_app = self._resolve_browser_app(os_name)

        if self.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "platform": os_name,
                "browser_app": browser_app,
                "action": "read_active_tab",
            }

        if self.read_wait_seconds > 0:
            time.sleep(self.read_wait_seconds)

        if os_name != "Darwin":
            return {
                "ok": False,
                "platform": os_name,
                "browser_app": browser_app,
                "error": "read_active_tab currently supports macOS (Darwin) only.",
            }

        try:
            returncode, stdout, stderr = self._run_osascript(self._build_darwin_read_script(browser_app))
            if returncode != 0:
                return {
                    "ok": False,
                    "platform": os_name,
                    "browser_app": browser_app,
                    "error": (stderr or stdout or "AppleScript read failed").strip(),
                }
            if not stdout:
                return {
                    "ok": False,
                    "platform": os_name,
                    "browser_app": browser_app,
                    "error": "No active browser tab content returned.",
                }
            try:
                payload = json.loads(stdout)
            except Exception:
                return {
                    "ok": False,
                    "platform": os_name,
                    "browser_app": browser_app,
                    "error": "Failed to parse active tab content payload.",
                    "raw": stdout[:400],
                }

            tab_url = self._normalize_url(payload.get("url", ""))
            title = str(payload.get("title", "") or "").strip()
            content = self._normalize_content(str(payload.get("content", "") or ""))
            return {
                "ok": True,
                "platform": os_name,
                "browser_app": browser_app,
                "content_format": self.response_mode,
                "url": tab_url,
                "title": title,
                "content": content,
                "status": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "platform": os_name,
                "browser_app": browser_app,
                "error": str(e),
                "hint": (
                    "Grant Automation permission to your terminal for controlling browser apps "
                    "(System Settings > Privacy & Security > Automation)."
                ),
            }

    async def open_and_read_url(self, url: str) -> dict[str, Any]:
        """
        Open URL first, then read active tab content from the same browser session.
        """
        open_result = await self.open_url(url=url)
        if not isinstance(open_result, dict) or not open_result.get("ok"):
            return {
                "ok": False,
                "step": "open_url",
                "open_result": open_result,
            }
        read_result = await self.read_active_tab()
        if not isinstance(read_result, dict):
            return {
                "ok": False,
                "step": "read_active_tab",
                "open_result": open_result,
                "read_result": read_result,
            }
        read_result["requested_url"] = str(url or "")
        read_result["normalized_requested_url"] = self._normalize_url(str(url or ""))
        read_result["open_result"] = open_result
        return read_result
