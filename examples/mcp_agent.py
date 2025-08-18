import asyncio
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
)

agent = Agently.create_agent()


async def main():
    result = await agent.use_mcp("cal_mcp_server.py").input("333+546=？").async_start()
    print(result)


asyncio.run(main())
