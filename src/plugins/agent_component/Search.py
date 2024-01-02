from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace
from duckduckgo_search import DDGS

class Search(ComponentABC):
    def __init__(self, agent):
        self.agent = agent
        self.is_debug = self.agent.settings.get_trace_back("is_debug")
        self.settings = RuntimeCtxNamespace("plugin_settings.agent_component.Search", self.agent.settings)

    def __exec_search(self, keywords: str, options:dict={}):
        result = []
        search_kwargs = {}
        proxy = self.agent.settings.get_trace_back("proxy")
        if proxy:
            search_kwargs["proxies"] = proxy
        #else:
            #if self.is_debug:
                #print("[No Proxy for Search] That may cause http request error in some areas. If request error occured, please use .set_proxy('<Your Proxy Address>') or .set_settings('proxy', '<Your Proxy Address>') to set a proxy.")
        if "max_results" not in options:
            options.update({ "max_results": self.settings.get_trace_back("max_result_count", 5) })
        with DDGS(**search_kwargs) as ddgs:
            for r in ddgs.text(
                keywords,
                **options
            ):
                result.append(r)
        return result

    def use_search(self):
        self.agent.toggle_component("Search", True)
        return self.agent

    def set_max_results(self, max_result_count: int):
        self.settings.set("max_result_count", max_result_count)
        return self.agent

    def set_max_result_length(self, max_result_length: int):
        self.settings.set("max_result_length", max_result_length)
        return self.agent

    def switch_mode(self, mode: int):
        if mode in (0, 1):
            self.mode = mode
        return self.agent

    def _prefix(self):
        request = self.agent.worker_request
        if self.is_debug:
            print("[Agent Component] Searching: Start search judgement...")
        result = request\
            .input(self.agent.request.request_runtime_ctx.get("prompt")["input"])\
            .output({
                "certain_of_direct_answer": ("Boolean", "if you are cretain that you can answer {input} directly, return true, else false."),
                "keywords": (
                    "String",
                    "- split keywords by space.\n- if do not have one remains {keywords} as ""\n- if you want to search a definition, use the format '{keywords}' to make sure the exact search\n - if you want to search multiple times, split each search by '|'"
                ),
            })\
            .start()
        if not result["certain_of_direct_answer"]:
            search_result_dict = {}
            max_result_length = self.settings.get("max_result_length", 1000)
            result_length = 0
            keywords_list = result["keywords"].split("|")
            for keywords in keywords_list:
                if self.is_debug:
                    print(f"[Agent Component] Searching: { keywords }")
                search_result_dict.update({ keywords: [] })
                for search_result in self.__exec_search(keywords):
                    search_result = f"{ search_result['title'] }: { search_result['body'] }"
                    search_result_dict[keywords].append(search_result)
                    result_length += len(search_result)
                    if result_length > max_result_length:
                        break
                if self.is_debug:
                    print(f"[Agent Component] Search Result: { keywords }\n{ search_result_dict[keywords] }")
            if len(search_result_dict.keys()) > 0:
                return { "information": { "search results": search_result_dict }, "instruction": "answer according {information}" }
            else:
                return None
        else:
            return None

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "use_search": { "func": self.use_search },
            },
        }

def export():
    return ("Search", Search)