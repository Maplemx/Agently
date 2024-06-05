import re
from .utils import ToolABC
import time
import httpx
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

class Web(ToolABC):
    def __init__(self, tool_manager: object):
        self.tool_manager = tool_manager

    def search(self, keywords: str, *, options: dict={}, proxy: str=None, type: int=1, no_sleep: bool=False, timelimit: str=None):
        if timelimit:
            options.update({ "timelimit": timelimit })
        results = []
        '''
        results = {
            "origin": [],
            "for_agent": [],
        }
        '''
        search_kwargs = {}
        if proxy:
            search_kwargs["proxies"] = proxy
        if "max_results" not in options:
            options.update({ "max_results": 5 })
        try:
            with DDGS(**search_kwargs) as ddgs:
                if type == 1:
                    for index, result in enumerate(ddgs.text(
                        str(keywords),
                        **options
                    )):
                        results.append({
                            "title": result["title"],
                            "brief": result["body"],
                            "url": result["href"],
                        })
                elif type == 2:
                    for index, result in enumerate(ddgs.news(
                        str(keywords),
                        **options
                    )):
                        results.append({
                            "title": result["title"],
                            "brief": result["body"],
                            "url": result["url"],
                            "source": result["source"],
                            "date": result["date"],
                        })
        except Exception as e:
            results = f"No Result Because: { str(e) }"
        return results

    def search_definition(self, item_name: str, *, options: dict={}, proxy: str=None):
        return self.search(f'whatis { item_name }', options=options, proxy=proxy)

    def search_news(self, keywords: str, *, options: dict={}, proxy: str=None, timelimit: str=None):
        if timelimit:
            options.update({ "timelimit": timelimit })
        if "timelimit" not in options:
            options.update({ "timelimit": "w" })
        if "max_results" not in options:
            options.update({ "max_results": 10 })
        return self.search(keywords, options=options, proxy=proxy, type=2)

    def browse(self, url: str, *, retry_times:int = 0, proxy: str=None):
        content = ""
        try:
            request_options = {
                "headers": { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" }
            }
            if proxy:
                if proxy.startswith("http:"):
                    request_options.update({ "proxies": { "http": proxy } })
                elif proxy.startswith("https:"):
                    request_options.update({ "proxies": { "https": proxy } })
            page = requests.get(
                url,
                **request_options
            )
            soup = BeautifulSoup(page.content, "html.parser")
            # find text in p, list, pre (github code), td
            chunks = soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "pre", "td"])
            for chunk in chunks:
                if chunk.name.startswith("h"):
                    content += "#" * int(chunk.name[-1]) + " " + chunk.get_text() + "\n"
                else:
                    text = chunk.get_text()
                    if text and text != "":
                        content += text + "\n"
            # find text in div that class=content
            divs = soup.find("div", class_="content")
            if divs:
                chunks_with_text = divs.find_all(text=True)
                for chunk in chunks_with_text:
                    if isinstance(chunk, str) and chunk.strip():
                        content += chunk.strip() + "\n"
            content = re.sub(r"\n+", "\n", content)
            return content
        except Exception as e:
            return f"Can not browse '{ url }'.\tError: { str(e) }"

    def export(self):
        return {
            "search": {
                "desc": "search {keywords}.",
                "args": {
                    "keywords": ("String", "[*Required]keywords to search, seperate keywords by ' '."),
                    "options": {
                        "timelimit": ("String | Null", "'d': last day; 'w': this week; 'm': this month;")
                    },
                },
                "func": self.search,
                "require_proxy": True,
            },
            "search_info": {
                "desc": "search information about {keywords}.",
                "args": {
                    "keywords": ("String", "[*Required]keywords to search, seperate keywords by ' '."),
                    "options": {
                        "timelimit": ("String | Null", "'d': last day; 'w': this week; 'm': this month;")
                    },
                },
                "func": self.search,
                "require_proxy": True,
            },
            "search_news": {
                "desc": "search news about {keywords}.",
                "args": {
                    "keywords": ("String", "[*Required]keywords to search, seperate keywords by ' '."),
                    "options": {
                        "timelimit": ("String | Null", "'d': last day; 'w': this week; 'm': this month;")
                    },
                },
                "func": self.search_news,
                "require_proxy": True,
            },
            "search_definition": {
                "desc": "search definition about {item_name}.",
                "args": {
                    "item_name": ("String", "[*Required]item name to find the definition."),
                },
                "func": self.search_definition,
                "require_proxy": True,
            },
            "browse": {
                "desc": "Browse web page by url.",
                "args": {
                    "url": ("String", "[*Required]url to browse.")
                },
                "func": self.browse,
                "require_proxy": True,
            }
        }

def export():
    return ("Web", Web)