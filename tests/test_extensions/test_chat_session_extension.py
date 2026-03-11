import warnings

from agently import Agently
from agently.builtins.agent_extensions import ChatSessionExtension


def _create_chat_session_extension():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ChatSessionExtension(Agently.plugin_manager, parent_settings=Agently.settings)


def test_chat_session_extension_record_input_paths_replace_and_clean():
    agent = _create_chat_session_extension()

    agent.set_record_input_paths("input.city")
    agent.set_record_input_paths("input.code")
    assert agent.settings.get("record_input_paths", inherit=False) == [("input.code", None)]

    agent.clean_record_input_paths()
    assert agent.settings.get("record_input_paths", inherit=False) == []


def test_chat_session_extension_record_output_paths_replace_and_clean():
    agent = _create_chat_session_extension()

    agent.set_record_output_paths("answer.text")
    agent.set_record_output_paths("score")
    assert agent.settings.get("record_output_paths", inherit=False) == ["score"]

    agent.clean_record_output_paths()
    assert agent.settings.get("record_output_paths", inherit=False) == []
