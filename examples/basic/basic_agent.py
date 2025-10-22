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
        "api_key": os.environ["QIANFAN_API_KEY"],
    },
)


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
