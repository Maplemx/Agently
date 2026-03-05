import json
from pathlib import Path

import yaml
import json5

from agently import Agently


def test_prompt_to_json_yaml_prompt_returns_string():
    agent = Agently.create_agent()
    agent.input("hello").instruct("say hi")

    json_content = agent.request_prompt.to_json_prompt()
    yaml_content = agent.request_prompt.to_yaml_prompt()

    json_data = json.loads(json_content)
    yaml_data = yaml.safe_load(yaml_content)
    assert json_data["input"] == "hello"
    assert yaml_data["input"] == "hello"


def test_get_json_yaml_prompt_save_to_file(tmp_path: Path):
    agent = Agently.create_agent()
    agent.input("demo input").instruct("demo instruct")

    json_path = tmp_path / "configured_prompt.json"
    yaml_path = tmp_path / "configured_prompt.yaml"

    json_prompt = agent.get_json_prompt(save_to=json_path)
    yaml_prompt = agent.get_yaml_prompt(save_to=yaml_path)

    assert json_path.exists()
    assert yaml_path.exists()
    assert json_path.read_text(encoding="utf-8") == json_prompt
    assert yaml_path.read_text(encoding="utf-8") == yaml_prompt

    json_data = json5.loads(json_prompt)
    yaml_data = yaml.safe_load(yaml_prompt)
    assert isinstance(json_data, dict)
    assert json_data[".request"]["input"] == "demo input"
    assert yaml_data[".request"]["input"] == "demo input"
