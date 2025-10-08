import asyncio
from agently.builtins.tools import Search

search = Search(proxy="http://127.0.0.1:7890")


async def directly_search():
    results = await search.search("attention is all you need")
    print("[SEARCH]:")
    print(results)

    results = await search.search_news("attention is all you need")
    print("[NEWS]:")
    print(results)

    results = await search.search_wikipedia("attention is all you need")
    print("[WIKIPEDIA]:")
    print(results)

    results = await search.search_arxiv("attention is all you need")
    print("[ARXIV]:")
    print(results)


# asyncio.run(directly_search())

import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": os.environ["DEEPSEEK_BASE_URL"],
        "model": os.environ["DEEPSEEK_DEFAULT_MODEL"],
        "model_type": "chat",
        "auth": os.environ["DEEPSEEK_API_KEY"],
    },
)

agent = Agently.create_agent()

agent.use_tools(
    [
        search.search,
        search.search_news,
        search.search_arxiv,
    ]
)

response = agent.input("Search news about language model applications.").get_response()
print(response.result.get_result())
print(response.result.full_result_data["extra"])
