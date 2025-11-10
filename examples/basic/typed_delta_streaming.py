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

gen = (
    agent.input("What's the weather like today in New York?")
    .options(
        {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current temperature for provided coordinates in celsius.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                            },
                            "required": ["latitude", "longitude"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                }
            ]
        }
    )
    .get_generator(type="typed_delta")
)

for event, content in gen:
    if event == "delta":
        print(content, end="", flush=True)
    if event == "tool_calls":
        print("\n<tool_calls>\n", content, "\n</tool_calls>")

print("")
