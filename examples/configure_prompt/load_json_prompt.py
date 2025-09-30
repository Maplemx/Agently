import os
from agently import Agently

current_dir = os.path.dirname(os.path.abspath(__file__))
json_prompt_path = os.path.join(current_dir, "json_prompt.json")

agent = Agently.create_agent()
agent.load_json_prompt(json_prompt_path)
print("AGENT PROMPT:", agent.prompt.get())
print("REQUEST PROMPT:", agent.request.prompt.get(inherit=False))
