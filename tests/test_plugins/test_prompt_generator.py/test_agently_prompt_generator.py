import pytest
import rich

from agently.core import Prompt
from agently import Agently


def test_to_prompt_object():
    Agently.set_settings("plugins.PromptGenerator.activate", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.set("input", "OK")
    assert prompt.to_prompt_object().model_dump() == {
        "chat_history": [],
        "system": None,
        "developer": None,
        "tools": None,
        "action_results": None,
        "input": "OK",
        "attachment": [],
        "info": None,
        "instruct": None,
        "output": None,
        "output_format": "markdown",
    }
    prompt.set("user_info", "Nobody")
    assert prompt.to_prompt_object().model_extra == {"user_info": "Nobody"}
    assert prompt.to_prompt_object().model_dump() == {
        "chat_history": [],
        "system": None,
        "developer": None,
        "tools": None,
        "action_results": None,
        "input": "OK",
        "attachment": [],
        "info": None,
        "instruct": None,
        "output": None,
        "output_format": "markdown",
        "user_info": "Nobody",
    }
    prompt["output"] = {"reply": (str, "your reply")}
    assert prompt.to_prompt_object().model_dump() == {
        "chat_history": [],
        "system": None,
        "developer": None,
        "tools": None,
        "action_results": None,
        "input": "OK",
        "attachment": [],
        "info": None,
        "instruct": None,
        "output": {"reply": (str, "your reply")},
        "output_format": "json",  # Be automatically changed by `output`
        "user_info": "Nobody",
    }
    prompt["output_format"] = "yaml"
    assert prompt.to_prompt_object().model_dump() == {
        "chat_history": [],
        "system": None,
        "developer": None,
        "tools": None,
        "action_results": None,
        "input": "OK",
        "attachment": [],
        "info": None,
        "instruct": None,
        "output": {"reply": (str, "your reply")},
        "output_format": "yaml",  # You can modify it manually
        "user_info": "Nobody",
    }

    prompt_2 = Prompt(Agently.plugin_manager, Agently.settings)
    prompt_2["output_format"] = "some random words"
    prompt_2["output"] = [(str, "something")]
    # Should not be infected by `output`
    # because its value has already been set
    assert prompt_2.to_prompt_object().output_format == "some random words"


def test_to_text():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.update(
        {
            "input": "Hello",
            "instruct": "reply something",
            "info": "I'm a human",
            "output": {
                "thinking": (str, "describe how will you plan to reply?"),
                "reply": (str, "your final reply"),
            },
        }
    )
    assert (
        prompt.to_text()
        == """[INFO]:
I'm a human

[INSTRUCT]:
reply something

[INPUT]:
Hello

[OUTPUT REQUIREMENT]:
Data Format: JSON
Data Structure:
{
  "thinking": <str>, // describe how will you plan to reply?
  "reply": <str> // your final reply
}

[OUTPUT]:
[assistant]:"""
    )


def test_to_text_complex():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.update(
        {
            "input": "Hello",
            "instruct": "reply something",
            "info": "I'm a human",
            "output": {
                "thinking": (str, "describe how will you plan to reply?"),
                "reply": (str, "your final reply"),
            },
        }
    )
    prompt.set(
        "chat_history",
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "ni hao",
                    },
                    {
                        "type": "something",
                        "something": "OK",
                    },
                ],
            }
        ],
    )
    assert (
        prompt.to_text()
        == """[CHAT HISTORY]:
[user]:ni hao

[INFO]:
I'm a human

[INSTRUCT]:
reply something

[INPUT]:
Hello

[OUTPUT REQUIREMENT]:
Data Format: JSON
Data Structure:
{
  "thinking": <str>, // describe how will you plan to reply?
  "reply": <str> // your final reply
}

[OUTPUT]:
[assistant]:"""
    )
    # Receive warning when using pytest test_prompt -s


def test_empty_prompt():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    with pytest.raises(
        KeyError,
        match="Prompt requires at least one",
    ):
        prompt.to_text()


def test_message_prompt():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.update(
        {
            "input": "Hello",
            "instruct": "reply something",
            "info": "I'm a human",
            "output": {
                "thinking": (str, "describe how will you plan to reply?"),
                "reply": (str, "your final reply"),
            },
        }
    )
    prompt.set(
        "chat_history",
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "ni hao",
                    },
                    {
                        "type": "something",
                        "something": "OK",
                    },
                ],
            },
            {
                "role": "assistant",
                "content": "hello, what can I help you?",
            },
        ],
    )
    assert prompt.to_messages(rich_content=False) == [
        {"role": "user", "content": "ni hao"},
        {"role": "assistant", "content": "hello, what can I help you?"},
        {
            "role": "user",
            "content": '[INFO]:\nI\'m a human\n\n[INSTRUCT]:\nreply something\n\n[INPUT]:\nHello\n\n[OUTPUT REQUIREMENT]:\nData Format: JSON\nData Structure:\n{\n  "thinking": <str>, // describe how will you plan to reply?\n  "reply": <str> // your final reply\n}\n\n[OUTPUT]:',
        },
    ]
    assert prompt.to_messages(rich_content=True) == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "ni hao"},
                {"type": "something", "something": "OK"},
            ],
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "hello, what can I help you?"},
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": '[INFO]:\nI\'m a human\n\n[INSTRUCT]:\nreply something\n\n[INPUT]:\nHello\n\n[OUTPUT REQUIREMENT]:\nData Format: JSON\nData Structure:\n{\n  "thinking": <str>, // describe how will you plan to reply?\n  "reply": <str> // your final reply\n}\n\n[OUTPUT]:',
                }
            ],
        },
    ]


def test_output_model():
    from typing import Literal
    from pydantic import BaseModel
    from agently.utils import DataFormatter

    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.set(
        "output",
        {
            "thinking": [(str, "Your plan to reply")],
            "reply": (
                Literal[1, 2, 3],
                "Your actually reply",
            ),
            "number": int,
        },
    )
    MyOutputModel = prompt.to_output_model()
    test_data = {"thinking": 1, "number": "123"}
    output = MyOutputModel.model_validate(test_data)
    assert DataFormatter.sanitize(prompt["output"], remain_type=True) == {
        "thinking": [(str, "Your plan to reply")],
        "reply": (
            Literal[1, 2, 3],
            "Your actually reply",
        ),
        "number": int,
    }
    assert output.model_dump()["thinking"] == ["1"]

    prompt.set("output", [(int,)])
    MyOutputModel = prompt.to_output_model()
    test_data = ["456"]
    output: "BaseModel" = MyOutputModel.model_validate({"list": test_data})
    assert output.model_dump()["list"] == [456]


def test_rich_prompt():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.update(
        {
            "attachment": [
                {
                    "type": "text",
                    "text": "你好",
                },
                {
                    "type": "image_url",
                    "image_url": "http://example.com",
                },
            ]
        }
    )
    messages = prompt.to_messages(rich_content=True)
    assert messages[0] == {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "你好",
            },
            {
                "type": "image_url",
                "image_url": "http://example.com",
            },
        ],
    }
    messages = prompt.to_messages()
    assert messages[0] == {
        "role": "user",
        "content": "你好",
    }


def test_strict_role_orders():
    Agently.set_settings("plugins.PromptGenerator.name", "AgentlyPromptGenerator")
    prompt = Prompt(Agently.plugin_manager, Agently.settings)
    prompt.set(
        "chat_history",
        [
            {"role": "assistant", "content": "Hi, how can I help you today?"},
            {"role": "user", "content": "?"},
        ],
    )
    prompt.set("input", "hi")
    messages = prompt.to_messages(rich_content=True, strict_role_orders=True)
    assert messages == [
        {'role': 'user', 'content': [{'type': 'text', 'text': '[Chat History]'}]},
        {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Hi, how can I help you today?'}]},
        {'role': 'user', 'content': [{'type': 'text', 'text': '?'}]},
        {'role': 'assistant', 'content': [{'type': 'text', 'text': '[User continue input]'}]},
        {'role': 'user', 'content': 'hi'},
    ]
    messages = prompt.to_messages(rich_content=False, strict_role_orders=True)
    assert messages == [
        {'role': 'user', 'content': '[Chat History]'},
        {'role': 'assistant', 'content': 'Hi, how can I help you today?'},
        {'role': 'user', 'content': '?'},
        {'role': 'assistant', 'content': '[User continue input]'},
        {'role': 'user', 'content': 'hi'},
    ]
