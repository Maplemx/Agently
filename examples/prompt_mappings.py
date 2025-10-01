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

user_input = "How are you today?"
role = "A teacher for kids that 3 years old."


async def main():
    agent = Agently.create_agent()
    result = (
        agent.input(
            "Acting as ${role} to response: ${user_input}",
            mappings={
                "user_input": user_input,
                "role": role,
            },
        )
        .output({"reply": (str, "role reply only")})
        .start()
    )
    print(result["reply"])


asyncio.run(main())
