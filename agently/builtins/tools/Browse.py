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


from agently.utils import LazyImport


class Browse:

    def __init__(
        self,
        proxy: str | None = None,
        timeout: int | None = None,
        headers: dict[str, str] | None = None,
    ):
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

    async def browse(self, url: str):
        """
        Fetch webpage content from target URL.

        Args:
            url <str>: Target URL.

        Returns:
            Content string from the target webpage.
        """
        import re
        from httpx import AsyncClient
        from bs4 import BeautifulSoup, Tag

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
                # find text in p, list, pre (github code), td
                chunks = soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "pre", "td"])
                for chunk in chunks:
                    if isinstance(chunk, Tag):
                        if chunk.name.startswith("h"):
                            content += "#" * int(chunk.name[-1]) + " " + chunk.get_text() + "\n"
                        else:
                            text = chunk.get_text()
                            if text and text != "":
                                content += text + "\n"
                # find text in div that class=content
                divs = soup.find_all("div", class_="content")
                if divs:
                    for div in divs:
                        if isinstance(divs, Tag):
                            chunks_with_text = divs.find_all(text=True)
                            for chunk in chunks_with_text:
                                if isinstance(chunk, str) and chunk.strip():
                                    content += chunk.strip() + "\n"
                content = re.sub(r"\n+", "\n", content)
                if content:
                    return content
                else:
                    return f"Can not fetch any content from { url }!"
        except Exception as e:
            return f"Can not browse '{ url }'.\tError: { str(e) }"
