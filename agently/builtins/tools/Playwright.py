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
import re
import unicodedata
from urllib.parse import urljoin, urlparse

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


class Playwright(BuiltInTool):
    def __init__(
        self,
        *,
        headless: bool = True,
        timeout: int = 30000,
        proxy: str | None = None,
        user_agent: str | None = None,
        response_mode: Literal["markdown", "text"] = "markdown",
        max_content_length: int = 8000,
        include_links: bool = False,
        max_links: int = 120,
        screenshot_path: str | None = None,
    ):
        self.tool_info_list = [
            {
                "name": "playwright_open",
                "desc": "Open {url} in a browser with Playwright and return rendered page info.",
                "kwargs": {
                    "url": ("str", "Target URL"),
                },
                "func": self.open,
            }
        ]
        LazyImport.import_package("playwright")
        self.headless = headless
        self.timeout = timeout
        self.proxy = proxy
        self.user_agent = user_agent
        self.wait_until: Literal["domcontentloaded"] = "domcontentloaded"
        self.response_mode = response_mode
        self.max_content_length = max_content_length
        self.include_links = include_links
        self.max_links = max_links
        self.screenshot_path = screenshot_path

    def _normalize_url(self, url: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(url or "")).strip()
        normalized = normalized.translate(_URL_PUNCT_TRANSLATION)
        normalized = normalized.replace("\u3000", " ")
        normalized = re.sub(r"[\r\n\t]+", "", normalized)
        normalized = normalized.strip(' "\'`')
        normalized = re.sub(r"[,;:!?]+$", "", normalized)
        return normalized

    async def open(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Open a URL with Playwright and collect rendered page details.

        Args:
            url: Target URL.
            Output and navigation behavior are configured at class initialization.

        Returns:
            Dictionary with page status, final URL and one `content` field.
        """
        from playwright.async_api import async_playwright

        requested_url = str(url or "")
        url = self._normalize_url(requested_url)
        page_timeout = self.timeout
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
                    response = await page.goto(url, wait_until=self.wait_until, timeout=page_timeout)
                    title = await page.title()

                    if self.response_mode == "text":
                        content = await page.locator("body").inner_text(timeout=page_timeout)
                        content = " ".join(content.split())
                    else:
                        content = await page.evaluate(
                            """
                            () => {
                                const root = document.body.cloneNode(true);
                                root.querySelectorAll("script,style,noscript,svg").forEach((el) => el.remove());
                                root.querySelectorAll("a[href]").forEach((a) => {
                                    const href = a.href || "";
                                    const text = (a.textContent || "").trim().replace(/\\s+/g, " ");
                                    const markdownLink = text ? `[${text}](${href})` : href;
                                    a.replaceWith(document.createTextNode(markdownLink));
                                });
                                return (root.innerText || "")
                                    .replace(/\\u00a0/g, " ")
                                    .replace(/[ \\t]+\\n/g, "\\n")
                                    .replace(/\\n{3,}/g, "\\n\\n")
                                    .trim();
                            }
                            """
                        )
                        content = " ".join(str(content).split())
                    if self.max_content_length > 0 and len(content) > self.max_content_length:
                        content = f"{content[:self.max_content_length]}..."

                    links = None
                    if self.include_links:
                        raw_links = await page.eval_on_selector_all(
                            "a[href]",
                            """
                            (elements) => elements.map((item) => ({
                                href: item.getAttribute("href") || "",
                                text: (item.textContent || "").trim(),
                            }))
                            """,
                        )
                        links = []
                        seen_links: set[str] = set()
                        for item in raw_links:
                            if not isinstance(item, dict):
                                continue
                            href = str(item.get("href", "")).strip()
                            if not href or href.startswith("#") or href.lower().startswith("javascript:"):
                                continue
                            absolute_url = urljoin(page.url, href)
                            parsed = urlparse(absolute_url)
                            if parsed.scheme not in ("http", "https"):
                                continue
                            if absolute_url in seen_links:
                                continue
                            seen_links.add(absolute_url)

                            link_text = " ".join(str(item.get("text", "")).split())
                            if self.max_links <= 0 or len(links) < self.max_links:
                                links.append(
                                    {
                                        "url": absolute_url,
                                        "text": link_text,
                                    }
                                )

                    if self.screenshot_path:
                        screenshot_output = Path(self.screenshot_path).expanduser().resolve()
                        screenshot_output.parent.mkdir(parents=True, exist_ok=True)
                        await page.screenshot(path=str(screenshot_output), full_page=True)

                    result = {
                        "ok": True,
                        "requested_url": requested_url,
                        "normalized_url": url,
                        "url": page.url,
                        "status": response.status if response else None,
                        "title": title,
                        "content_format": self.response_mode,
                        "content": content,
                        "screenshot_path": str(screenshot_output) if screenshot_output else None,
                    }
                    if links is not None:
                        result["links"] = links
                    return result
                finally:
                    await browser.close()
        except Exception as e:
            return {
                "ok": False,
                "requested_url": requested_url,
                "normalized_url": url,
                "error": str(e),
            }
