import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from agently import Agently

Agently.set_debug_console("ON")

Agently.set_settings("response.streaming_parse", True)

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": os.environ["DEEPSEEK_BASE_URL"],
        "model": os.environ["DEEPSEEK_DEFAULT_MODEL"],
        "model_type": "chat",
        "auth": os.environ["DEEPSEEK_API_KEY"],
    },
)

agent = Agently.create_agent()

agent.set_agent_prompt("system", "You're the cutest cat in the world")

agent.request.set_prompt("input", "Hi~")


streaming_parse_generator = agent.output(
    {
        "thinking": ("str",),
        "actions": [("str",)],
        "say": ("str",),
    }
).get_generator(content="instant")

messenger = Agently.event_center.create_messenger(
    "Customize Output",
    base_meta={
        "table_name": "Kitty Response",
        "row_id": 0,
    },
)

actions = []

for data in streaming_parse_generator:
    if data.path in ("thinking", "say"):
        messenger.to_console({f"${data.path}": data.delta})
    if data.path.startswith("actions["):
        index = data.path[8:-1]
        if data.is_complete:
            actions.append((index, data.value))
            messenger.to_console(
                {
                    "actions": "\n\n".join([f"{item[0]}. {item[1]}" for item in actions]),
                }
            )
