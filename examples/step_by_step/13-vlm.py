from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "https://qianfan.baidubce.com/v2",
        "model": "ernie-4.5-turbo-vl",
        "auth": "<QianFan-API-Key>",
        "options": {
            "temperature": 0.7,
        },
    },
).set_settings("debug", True)

agent = Agently.create_agent()

result = agent.attachment(
    [
        {"type": "text", "text": "What's this？"},
        {
            "type": "image_url",
            "image_url": {"url": "https://cdn.deepseek.com/logo.png?x-image-process=image%2Fresize%2Cw_1920"},
        },
    ],
).start()

print(result)
