import os
from agently import Agently

current_dir = os.path.dirname(os.path.abspath(__file__))
yaml_prompt_path = os.path.join(current_dir, "yaml_prompt.yaml")

agent = Agently.create_agent()
agent.load_yaml_prompt(yaml_prompt_path)
print("AGENT PROMPT:", agent.prompt.get())
print("REQUEST PROMPT:", agent.request.prompt.get(inherit=False))
