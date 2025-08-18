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


@agent.tool_func
async def add(a: int, b: int) -> int:
    """
    Get result of `a(int)` add `b(int)`
    """
    await asyncio.sleep(1)
    print(a, "+", b, "=", a + b)
    return a + b


result = agent.input("34643523+52131231=? Use tool to calculate!").use_tool(add).start()
print(result)
