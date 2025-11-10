import asyncio
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "https://qianfan.baidubce.com/v2",
        "model": "ernie-4.5-turbo-128k",
        "auth": "QianFan API Key",
        "options": {
            "temperature": 0.7,
        },
    },
)

llm = Agently.create_agent()


async def main():
    instant_mode_response = (
        llm.input("Give me 5 computer-related words and 3 color-related phrases and 1 random sentence.")
        .output(
            {
                "words": [(str,)],
                "phrases": {
                    "<color-name>": (str, "phrase"),
                },
                "sentence": (str,),
            }
        )
        .get_async_generator(type="instant")
    )

    async for event in instant_mode_response:
        print(
            event.path,
            "[DONE]" if event.is_complete else "[>>>>]",
            event.value,
        )


asyncio.run(main())
