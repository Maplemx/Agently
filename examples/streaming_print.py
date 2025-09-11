import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import asyncio

from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": os.environ["QIANFAN_BASE_URL"],
        "model": "ernie-lite-8k",
        "model_type": "chat",
        "auth": os.environ["QIANFAN_API_KEY"],
    },
)


async def basic_delta():
    agent = Agently.create_agent()
    async_generator = (
        agent.input("Please explain recursion")
        .output(
            {
                "thinking": (str, "Think about how you would answer this question?"),
                "explanation": (str, "Concept explanation"),
                "example_codes": ([(str, "Example code")], "Provide at least 2 example codes"),
                "practices": (
                    [
                        {
                            "question": (str, "Practice question"),
                            "answer": (str, "Reference answer"),
                        }
                    ],
                    "Provide at least 2 practice questions, ensure they are different from the example codes",
                ),
            }
        )
        .get_async_generator(content="delta")
    )

    async for delta in async_generator:
        print(delta, end="")


# asyncio.run(basic_delta())


async def instant():
    agent = Agently.create_agent()
    async_generator = (
        agent.input("Please explain recursion")
        .output(
            {
                "thinking": (str, "Think about how you would answer this question?"),
                "explanation": (str, "Concept explanation"),
                "example_codes": ([(str, "Example code")], "Provide at least 2 example codes"),
                "practices": (
                    [
                        {
                            "question": (str, "Practice question"),
                            "answer": (str, "Reference answer"),
                        }
                    ],
                    "Provide at least 2 practice questions, ensure they are different from the example codes",
                ),
            }
        )
        .get_async_generator(content="instant")
    )

    current_path = None
    change_path = False
    async for data in async_generator:
        if current_path != data.path:
            current_path = data.path
            change_path = True
        else:
            change_path = False
        if data.path == "practices[0].question":
            if data.delta:
                print(data.delta, end="")
        if data.path == "practices[0].answer":
            if change_path:
                print()
            if data.delta:
                print(data.delta, end="")


asyncio.run(instant())
