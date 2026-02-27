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

from pathlib import Path
from typing import Any, Literal

from agently.types.plugins import BuiltInTool
from agently.utils import LazyImport


class Playwright(BuiltInTool):
    def __init__(
        self,
        *,
        headless: bool = True,
        timeout: int = 30000,
        proxy: str | None = None,
        user_agent: str | None = None,
    ):
        self.tool_info_list = [
            {
                "name": "playwright_open",
                "desc": "Open {url} in a browser with Playwright and return rendered page info.",
                "kwargs": {
                    "url": ("str", "Target URL"),
                    "wait_until": ("str", "Navigation wait strategy"),
                    "timeout": ("int | None", "Timeout in milliseconds"),
                    "max_text_length": ("int", "Max body text length in return result"),
                    "screenshot_path": ("str | None", "Optional screenshot output path"),
                },
                "func": self.open,
            }
        ]
        LazyImport.import_package("playwright")
        self.headless = headless
        self.timeout = timeout
        self.proxy = proxy
        self.user_agent = user_agent

    async def open(
        self,
        url: str,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "domcontentloaded",
        timeout: int | None = None,
        max_text_length: int = 4000,
        screenshot_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Open a URL with Playwright and collect rendered page details.

        Args:
            url: Target URL.
            wait_until: Playwright wait strategy.
            timeout: Timeout in milliseconds; defaults to tool timeout.
            max_text_length: Max length of returned body text.
            screenshot_path: Save screenshot when provided.

        Returns:
            Dictionary with page status, final URL, title and text.
        """
        from playwright.async_api import async_playwright

        page_timeout = timeout if timeout is not None else self.timeout
        screenshot_output = None

        try:
            async with async_playwright() as playwright:
                launch_kwargs: dict[str, Any] = {
                    "headless": self.headless,
                }
                if self.proxy:
                    launch_kwargs["proxy"] = {"server": self.proxy}
                browser = await playwright.chromium.launch(**launch_kwargs)
                try:
                    context_kwargs = {}
                    if self.user_agent:
                        context_kwargs["user_agent"] = self.user_agent
                    context = await browser.new_context(**context_kwargs)
                    page = await context.new_page()
                    response = await page.goto(url, wait_until=wait_until, timeout=page_timeout)
                    title = await page.title()
                    body_text = await page.locator("body").inner_text(timeout=page_timeout)
                    body_text = " ".join(body_text.split())
                    if max_text_length > 0 and len(body_text) > max_text_length:
                        body_text = f"{body_text[:max_text_length]}..."

                    if screenshot_path:
                        screenshot_output = Path(screenshot_path).expanduser().resolve()
                        screenshot_output.parent.mkdir(parents=True, exist_ok=True)
                        await page.screenshot(path=str(screenshot_output), full_page=True)

                    return {
                        "ok": True,
                        "requested_url": url,
                        "url": page.url,
                        "status": response.status if response else None,
                        "title": title,
                        "text": body_text,
                        "screenshot_path": str(screenshot_output) if screenshot_output else None,
                    }
                finally:
                    await browser.close()
        except Exception as e:
            return {
                "ok": False,
                "requested_url": url,
                "error": str(e),
            }
