import os
from agently import Agently

current_dir = os.path.dirname(os.path.abspath(__file__))
json_prompt_path = os.path.join(current_dir, "json_prompt.json")

agent = Agently.create_agent()
agent.load_json_prompt(
    json_prompt_path,
    mappings={
        "in_value_placeholder": "IN VALUE!",
        "key_name_placeholder": "KEY_NAME",
        "only_value_placeholder": [
            "THIS",
            "IS",
            "ONLY",
            "VALUE",
            "PLACEHOLDER",
        ],
    },
)
print("AGENT PROMPT:", agent.prompt.get())
print("REQUEST PROMPT:", agent.request.prompt.get(inherit=False))
