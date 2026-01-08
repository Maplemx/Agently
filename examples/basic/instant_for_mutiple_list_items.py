from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", False)

agent = Agently.create_agent()

instant_generator = (
    agent.input("How to develop an independent game?")
    .output(
        {
            "steps": [(str,)],
        }
    )
    .get_generator(type="instant")
)

for data in instant_generator:
    if data.wildcard_path == "steps[*]":
        print(data.path, data.indexes, data.value, data.full_data)
