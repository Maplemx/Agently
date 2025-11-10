import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

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
        .get_async_generator(type="delta")
    )

    async for delta in async_generator:
        print(delta, end="")


# asyncio.run(basic_delta())


async def async_instant():
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
        .get_async_generator(type="instant")
    )

    current_path = None
    change_path = False
    async for data in async_generator:
        if current_path != data.path:
            current_path = data.path
            change_path = True
        else:
            change_path = False
        if data.wildcard_path == "practices[*].question":
            if data.delta:
                print(data.delta, end="", flush=True)
        if data.wildcard_path == "practices[*].answer":
            if change_path:
                print()
            if data.delta:
                print(data.delta, end="", flush=True)


# asyncio.run(async_instant())


def instant():
    agent = Agently.create_agent()
    generator = (
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
        .get_generator(type="instant")
    )

    current_path = None
    change_path = False
    for data in generator:
        if current_path != data.path:
            current_path = data.path
            change_path = True
        else:
            change_path = False
        if data.wildcard_path == "practices[*].question":
            if data.delta:
                print(data.delta, end="", flush=True)
        if data.wildcard_path == "practices[*].answer":
            if change_path:
                print()
            if data.delta:
                print(data.delta, end="", flush=True)


instant()
