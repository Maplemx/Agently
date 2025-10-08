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


from typing import Literal

from agently.utils import LazyImport


class Search:

    def __init__(
        self,
        proxy: str | None = None,
        timeout: int | None = None,
        backend: (
            Literal["auto", "bing", "duckduckgo", "yahoo", "google", "mullvad_google", "yandex", "wikipedia"] | None
        ) = "auto",
        search_backend: (
            Literal["auto", "bing", "duckduckgo", "yahoo", "google", "mullvad_google", "yandex", "wikipedia"] | None
        ) = None,
        news_backend: Literal["auto", "bing", "duckduckgo", "yahoo"] | None = None,
    ):
        LazyImport.import_package("ddgs")
        from ddgs import DDGS

        self.proxy = proxy
        self.timeout = timeout
        self.ddgs = DDGS(proxy=self.proxy, timeout=self.timeout)
        self.backends = {
            "search": search_backend if search_backend is not None else backend,
            "news": news_backend if news_backend is not None else backend,
        }

    async def search(
        self,
        query: str,
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = 10,
    ) -> list[dict[str, str]]:
        """
        General search from the internet. The most common search tool to be used.

        Args:
            query: text search query.
            timelimit: d, w, m, y. Defaults to None.
            max_results: maximum number of results. Defaults to 10.

        Returns:
            List of dictionaries with search results.
        """
        return self.ddgs.text(
            query=query,
            timelimit=timelimit,
            max_results=max_results,
            backend=self.backends.get("search", "auto"),
        )

    async def search_news(
        self,
        query: str,
        timelimit: Literal["d", "w", "m"] | None = None,
        max_results: int | None = 10,
    ):
        """
        News search from the internet. A tool to search recent news and stories of the query keywords.

        Args:
            query: news search query.
            timelimit: d, w, m. Defaults to None.
            max_results: maximum number of results. Defaults to 10.

        Returns:
            List of dictionaries with news search results.
        """
        return self.ddgs.news(
            query=query,
            timelimit=timelimit,
            max_results=max_results,
            backend=self.backends.get("news", "auto"),
        )

    async def search_wikipedia(
        self,
        query: str,
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = 10,
    ):
        """
        Search only from wikipedia.

        Args:
            query: text search query.
            timelimit: d, w, m, y. Defaults to None.
            max_results: maximum number of results. Defaults to 10.

        Returns:
            List of dictionaries with search results.
        """
        return self.ddgs.text(
            query=query,
            timelimit=timelimit,
            max_results=max_results,
            backend="wikipedia",
        )

    async def search_arxiv(
        self,
        query: str,
        max_results: int | None = 10,
    ):
        LazyImport.import_package("httpx")
        LazyImport.import_package("feedparser")
        from httpx import AsyncClient
        import feedparser

        url = f"https://export.arxiv.org/api/query?search_query=all:{ query }&max_results={ max_results }"

        async with AsyncClient(
            proxy=self.proxy,
            timeout=self.timeout,
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP Error: { response.status_code } { response.text }")
            feed = feedparser.parse(response.text)
            if isinstance(feed.feed, dict):
                result = {
                    "feed_title": feed.feed.get("title"),
                    "updated": feed.feed.get("updated"),
                    "entries": [],
                }
            else:
                result = {
                    "entries": [],
                }
            for entry in feed.entries:
                result["entries"].append(
                    {
                        "title": entry.get("title"),
                        "summary": entry.get("summary"),
                        "published": entry.get("published"),
                        "updated": entry.get("updated"),
                        "authors": [author.name for author in entry.authors],
                        "links": [{"href": link.href, "rel": link.rel, "type": link.type} for link in entry.links],
                    }
                )
            return result
