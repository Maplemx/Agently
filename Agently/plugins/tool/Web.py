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
        try:
            request_options = {}
            if proxy:
                if proxy.startswith("http:"):
                    request_options.update({ "proxies": { "http": proxy } })
                elif proxy.startswith("https:"):
                    request_options.update({ "proxies": { "https": proxy } })
            request_options.update({ "headers": { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"} })
            page_response = requests.get(url, **request_options)
            soup = BeautifulSoup(page_response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            texts = [p.get_text() for p in paragraphs]
            page_content = '\n'.join(texts)
            if page_content and page_content != "":
                return page_content
            else:
                return f"Can not get content from url: { url }"
        except Exception as e:
            if retry_times < 3:
                return self.browse(url, retry_times = retry_times + 1, proxy = proxy)
            else:
                return f"Can not get content from url: { url }\nError: { str(e) }"

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