import asyncio
from pathlib import Path

from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
)

agent = Agently.create_agent()


## MCP: use a local MCP server (stdio)
async def mcp_stdio_demo():
    mcp_path = Path(__file__).parents[1] / "mcp" / "cal_mcp_server.py"
    result = await agent.use_mcp(str(mcp_path)).input("333+546=?").async_start()
    print(result)


asyncio.run(mcp_stdio_demo())
