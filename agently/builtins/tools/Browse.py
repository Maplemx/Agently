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

from agently.types.plugins import BuiltInTool
from agently.utils import LazyImport


class Browse(BuiltInTool):
    MAIN_CONTENT_SELECTORS = (
        "[data-agently-main]",
        "main .vp-doc",
        "article .vp-doc",
        ".vp-doc",
        "main article",
        "article",
        "main",
        '[role="main"]',
        "#content",
        ".content",
        ".markdown-body",
    )

    CONTENT_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "td", "th", "blockquote")

    REMOVE_TAGS = ("script", "style", "noscript", "svg", "nav", "aside", "footer", "header", "form")

    NOISE_KEYWORDS = (
        "sidebar",
        "toc",
        "table-of-contents",
        "breadcrumb",
        "pagination",
        "pager",
        "navbar",
        "menu",
        "nav",
        "footer",
        "header",
        "ads",
        "advert",
    )

    def __init__(
        self,
        proxy: str | None = None,
        timeout: int | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.tool_info_list = [
            {
                "name": "browse",
                "desc": "Browse the page at {url}",
                "kwargs": {"url": ("str", "Accessible URL")},
                "func": self.browse,
            }
        ]

        LazyImport.import_package("httpx")
        LazyImport.import_package("bs4", install_name="beautifulsoup4")
        self.proxy = proxy
        self.timeout = timeout
        self.headers = (
            headers
            if headers is not None
            else {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            }
        )

    @staticmethod
    def _build_header_line(level: str, text: str):
        if not level.startswith("h") or len(level) != 2 or not level[1].isdigit():
            return text
        return "#" * int(level[1]) + " " + text

    @classmethod
    def _is_noise_node(cls, node) -> bool:
        class_values = node.get("class", []) if hasattr(node, "get") else []
        if isinstance(class_values, str):
            class_text = class_values.lower()
        elif isinstance(class_values, (list, tuple)):
            class_text = " ".join([str(item).lower() for item in class_values])
        else:
            class_text = ""

        node_id = str(node.get("id", "")).lower() if hasattr(node, "get") else ""
        merged = f"{class_text} {node_id}".strip()
        return any(keyword in merged for keyword in cls.NOISE_KEYWORDS)

    @classmethod
    def _pick_main_root(cls, soup):
        from bs4 import Tag

        for selector in cls.MAIN_CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if isinstance(node, Tag) and node.get_text(strip=True):
                return node
        if isinstance(soup.body, Tag):
            return soup.body
        html_node = soup.find("html")
        if isinstance(html_node, Tag):
            return html_node
        return soup

    @classmethod
    def _collect_text(cls, root):
        import re

        for removable in root.find_all(cls.REMOVE_TAGS):
            removable.decompose()

        for node in root.find_all(True):
            if cls._is_noise_node(node):
                node.decompose()

        content_lines = []
        for chunk in root.find_all(cls.CONTENT_TAGS):
            text = chunk.get_text(" ", strip=True)
            if text == "":
                continue
            if cls._is_noise_node(chunk):
                continue
            if chunk.name and chunk.name.startswith("h"):
                content_lines.append(cls._build_header_line(chunk.name, text))
            else:
                content_lines.append(text)

        normalized_lines: list[str] = []
        prev_line = ""
        for line in content_lines:
            line = re.sub(r"\s+", " ", line).strip()
            if line == "" or line == prev_line:
                continue
            normalized_lines.append(line)
            prev_line = line

        return "\n".join(normalized_lines).strip()

    @classmethod
    def _extract_text_from_soup(cls, soup):
        root = cls._pick_main_root(soup)
        return cls._collect_text(root)

    async def browse(self, url: str):
        """
        Fetch webpage content from target URL.

        Args:
            url <str>: Target URL.

        Returns:
            Content string from the target webpage.
        """
        from httpx import AsyncClient
        from bs4 import BeautifulSoup

        content = ""
        try:
            async with AsyncClient(
                proxy=self.proxy,
                timeout=self.timeout,
            ) as client:
                page = await client.get(url, headers=self.headers)
                if page.status_code == 301 and url.startswith("http:"):
                    url = url.replace("http:", "https:")
                    page = await client.get(url, headers=self.headers)
                soup = BeautifulSoup(page.content, "html.parser")
                content = self._extract_text_from_soup(soup)
                if content:
                    return content
                else:
                    return f"Can not fetch any content from { url }!"
        except Exception as e:
            return f"Can not browse '{ url }'.\tError: { str(e) }"
