import pytest
import json5
from agently.utils import DataFormatter, DataLocator, StreamingJSONCompleter


def run_complete_and_parse(json_str: str, expected_keys: list[str]):
    completer = StreamingJSONCompleter()
    completer.append(json_str)
    completed = completer.complete()
    print("Completed JSON:", completed)
    parsed = json5.loads(completed)
    for key in expected_keys:
        assert key in parsed  # type: ignore
        print("Key:", key, "Value:", parsed[key])  # type: ignore


def test_normal_model_output_extraction_and_completion():
    model_output = '''
    Here is the data you asked:

    ```json
    {
      "name": "Alice",
      "age": 30,
      "skills": ["python", "ML"]
    }
    ```

    Let me know if you want more.
    '''

    json_blocks = DataLocator.locate_all_json(model_output)
    assert len(json_blocks) > 0

    output_prompt_dict = {"name": None, "age": None}
    chosen_json = DataLocator.locate_output_json(model_output, output_prompt_dict)  # type: ignore
    assert chosen_json is not None

    run_complete_and_parse(chosen_json, ["name", "age", "skills"])


def test_edge_cases_multiple_json_and_text():
    model_output = '''
    Some explanation before JSON:

    ```json
    {"incomplete": true,
    '''

    model_output += '''
    "list": [1, 2, 3],
    '''

    model_output += '''
    }
    ```

    And some unrelated text.

    {"other": "object", "number": 42}
    '''

    json_blocks = DataLocator.locate_all_json(model_output)
    assert len(json_blocks) >= 2

    # output_prompt_dict = {"incomplete": None, "list": None}
    output_prompt_dict = {"other": None, "number": None}
    chosen_json = DataLocator.locate_output_json(model_output, output_prompt_dict)  # type: ignore
    assert chosen_json is not None

    # run_complete_and_parse(chosen_json, ["incomplete", "list"])
    run_complete_and_parse(chosen_json, ["other", "number"])

    # Also test last json block separately
    # run_complete_and_parse(json_blocks[-1], ["other", "number"])
    run_complete_and_parse(json_blocks[0], ["incomplete", "list"])


def test_no_json_in_text():
    text = "This is a plain text without any JSON or braces."
    json_blocks = DataLocator.locate_all_json(text)
    assert json_blocks == []

    chosen_json = DataLocator.locate_output_json(text, {"any": None})
    assert chosen_json is None


def test_json_with_nested_and_comments():
    model_output = '''
    Here is nested JSON with comments:

    {
        "user": "Bob", // user name
        "data": {
            /* data start here */
            "scores": [10, 20, 30], /* array of scores */
            "active": true
            /* -*-data end here-*- */
        }
    }
    '''

    json_blocks = DataLocator.locate_all_json(model_output)
    assert len(json_blocks) == 1

    chosen_json = DataLocator.locate_output_json(model_output, {"user": None, "data": None})
    assert chosen_json is not None

    run_complete_and_parse(chosen_json, ["user", "data"])
