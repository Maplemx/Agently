import asyncio
from pathlib import Path
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

mcp_path = Path(__file__).parent / "cal_mcp_server.py"
mcp_path_str = str(mcp_path.resolve())


async def main():
    result = await agent.use_mcp(mcp_path_str).input("333+546=？").async_start()
    print(result)


asyncio.run(main())
