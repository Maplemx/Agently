import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import asyncio

from agently import Agently

Agently.set_settings("response.streaming_parse", True)

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

agent.set_agent_prompt("system", "You're the cutest cat in the world")

agent.request.set_prompt("input", "Hi~")


async def run():
    streaming_parse_generator = agent.output(
        {
            "thinking": ("str",),
            "actions": [("str",)],
            "say": ("str",),
        }
    ).get_async_generator("instant")

    thinking_status = False
    actions_status = False
    last_actions_index = ""
    current_actions_index = ""
    say_status = False

    async for data in streaming_parse_generator:
        if data.path == "thinking":
            if not thinking_status:
                print("[Think]:")
                thinking_status = True
            if data.delta:
                print(data.delta, end="", flush=True)
        if data.path.startswith("actions["):
            if not actions_status:
                print()
                print("[Actions]:")
                actions_status = True
            current_actions_index = data.path[8:-1]
            if current_actions_index != last_actions_index:
                print()
                print("- ", end="", flush=True)
                last_actions_index = current_actions_index
            if data.delta:
                print(data.delta, end="", flush=True)
        if data.path == "say":
            if not say_status:
                print("\n\n")
                print("[Say]:")
                say_status = True
            if data.delta:
                print(data.delta, end="", flush=True)


asyncio.run(run())
