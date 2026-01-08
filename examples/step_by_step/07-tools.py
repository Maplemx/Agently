import asyncio

from agently import Agently
from agently.builtins.tools import Search, Browse

agent = Agently.create_agent()

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


## Tools in Agently
def builtin_tools():
    # Built-in tools: Search / Browse.
    # Search supports proxy for network access.
    ## Notice: always update ddgs package to latest version first to ensure the quality of search results
    search = Search(
        proxy="http://127.0.0.1:55758",
        region="us-en",
        backend="google",
    )
    browse = Browse()
    agent.use_tools([search.search, search.search_news, browse.browse])
    result = agent.input("What is Agently AI Framework in Github?").start()
    print(result)


# builtin_tools()


## Tool Functions with Decorator
def tool_func_decorator():
    # Register a Python function as a tool with @agent.tool_func.
    @agent.tool_func
    def add(a: int, b: int) -> int:
        return a + b

    agent.use_tools(add)
    result = agent.input("Calculate 345 + 678 using the tool.").start()
    print(result)


# tool_func_decorator()


## Advanced: Trace Tool Calls from Result (extra)
def tool_call_trace():
    # Tool calls happen inside the agent request, so the model can decide when to call tools.
    # The tool call records are stored in response.result.full_result_data["extra"].
    search = Search(
        proxy="http://127.0.0.1:55758",
        region="us-en",
        backend="google",
    )
    agent.use_tools([search.search, search.search_news])
    response = agent.input("Search for Agently AI Framework and summarize key points.").get_response()
    result = response.result.get_data()
    extra = response.result.full_result_data.get("extra", {})
    print(result)
    print("[extra]", extra)


# tool_call_trace()


## Multi-Stage Tooling: Search -> Decide -> Browse -> Summarize
def multi_stage_search_browse_summarize():
    # Stage 1: allow Search tools only, let the model pick candidate URLs.
    search = Search(
        proxy="http://127.0.0.1:55758",
        region="us-en",
        backend="google",
    )
    agent.use_tools([search.search, search.search_news])
    response = (
        agent.input("Search for Agently AI Framework and list 3 best URLs to read (only URLs).")
        .output({"urls": [(str, "URL")]})
        .get_response()
    )
    stage1 = response.result.get_data()
    urls = stage1.get("urls", []) if isinstance(stage1, dict) else []
    urls = [u for u in urls if isinstance(u, str)]
    urls = urls[:3]
    print("[stage1 urls]", urls)

    # Stage 2: browse the selected URLs concurrently.
    browse = Browse()

    async def browse_all():
        tasks = [browse.browse(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [{"url": url, "content": content} for url, content in zip(urls, results)]

    pages = asyncio.run(browse_all())

    # Stage 3: summarize based on the browsed content.
    agent.use_tools([])
    response = (
        agent.input({"task": "Summarize key points from the sources.", "sources": pages})
        .output(
            {
                "summary": (str, "Short summary of the sources"),
                "sources": [
                    {
                        "url": (str, "Source URL"),
                        "notes": (str, "Key notes from this page"),
                    }
                ],
            }
        )
        .get_response()
    )
    stage3 = response.result.get_data()
    print("[stage3 summary]", stage3)


# multi_stage_search_browse_summarize()
