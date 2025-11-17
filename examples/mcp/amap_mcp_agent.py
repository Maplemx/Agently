from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import os
import asyncio
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", True)

agent = Agently.create_agent()


async def main():
    result = (
        await agent.use_mcp(f"https://mcp.amap.com/mcp?key={ os.environ.get('AMAP_API_KEY') }")
        .input("What's the weather like in Shanghai today?")
        .async_start()
    )
    print(result)


asyncio.run(main())
