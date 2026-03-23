import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import asyncio

from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", True)


async def main():
    agent = Agently.create_agent()
    result = (
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
        .start()
    )
    print("Thinking", result["thinking"])
    print("Example Codes", result["example_codes"])
    print("Practices", result["practices"])


asyncio.run(main())
