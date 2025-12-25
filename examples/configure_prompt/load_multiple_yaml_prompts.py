from pathlib import Path
from agently import Agently

agent = Agently.create_agent()

agent.load_yaml_prompt(
    Path(__file__).parent / "multiple_yaml_prompts.yaml",
    prompt_key_path="prompt_1",
)
print(agent.get_prompt_text())
