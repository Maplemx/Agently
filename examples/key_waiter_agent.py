import asyncio

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

# Get specific key before all generation completed
(
    agent.input("34643523+52131231=? Use tool to calculate!").output(
        {
            "thinking": (str,),
            "result": (float,),
            "reply": (str,),
        }
    )
)

reply = agent.get_key_result("thinking")
print(reply)

# Get specific keys from generator before generation completed
(
    agent.input("34643523+52131231=? Use tool to calculate!").output(
        {
            "thinking": (str,),
            "result": (float,),
            "reply": (str,),
        }
    )
)

gen = agent.wait_keys(["thinking", "reply"])
for event, data in gen:
    print(event, data)

# Use handlers to handle different specific keys
(
    agent.input("34643523+52131231=? Use tool to calculate!")
    .output(
        {
            "thinking": (str,),
            "result": (float,),
            "reply": (str,),
        }
    )
    .when_key("thinking", lambda result: print("🤔:", result))
    .when_key("result", lambda result: print("✅:", result))
    .when_key("reply", lambda result: print("⏩:", result))
    .start_waiter()
)
