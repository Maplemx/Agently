import pytest
import asyncio
from textwrap import indent

from itertools import repeat

from agently.core.Session import Session


@pytest.mark.asyncio
async def test_one_message_session():
    session = Session()
    assert isinstance(session.id, str)
    assert session._auto_resize is True
    assert session.session_settings.get("max_length", None) is None
    session.session_settings.set("max_length", 100)
    await session.async_add_chat_history({"role": "user", "content": "hi" * 100})
    assert len(session.context_window[-1].content) == 100


@pytest.mark.asyncio
async def test_multi_messages_session():
    session = Session()
    assert isinstance(session.id, str)
    assert session._auto_resize is True
    assert session.session_settings.get("max_length", None) is None
    session.session_settings.set("max_length", 100)
    await session.async_add_chat_history([{"role": "user", "content": "hi"} for _ in repeat(None, 100)])
    total_length = 0
    for message in session.context_window:
        total_length += len(str(message.model_dump()))
    max_length = session.session_settings.get("max_length")
    assert isinstance(max_length, int)
    assert total_length <= max_length
    assert len(session.context_window) > 0


def test_session_json_export_and_load():
    session = Session(id="session-1", auto_resize=False)
    session.session_settings.set("max_length", 123)
    session.add_chat_history(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
    )

    json_data = session.get_json_session()
    loaded = Session(auto_resize=True)
    loaded.load_json_session(json_data)

    assert loaded.id == "session-1"
    assert loaded.session_settings.get("max_length") == 123
    assert len(loaded.full_context) == 2
    assert len(loaded.context_window) == 2


def test_session_yaml_export_and_load_by_path():
    session = Session(id="session-2", auto_resize=False)
    session.add_chat_history({"role": "user", "content": "content-from-yaml"})

    yaml_data = session.get_yaml_session()
    wrapped_yaml_data = f"payload:\n  session:\n{indent(yaml_data, '    ')}"

    loaded = Session(auto_resize=True)
    loaded.load_yaml_session(wrapped_yaml_data, session_key_path="payload.session")

    assert loaded.id == "session-2"
    assert len(loaded.context_window) == 1
    assert loaded.context_window[0].content == "content-from-yaml"


@pytest.mark.asyncio
async def test_session_legacy_execution_aliases():
    session = Session(auto_resize=False)
    await session.async_add_chat_history({"role": "user", "content": "hello"})

    async def execution_handler(full_context, context_window, memo, session_settings):
        _ = (full_context, context_window, session_settings)
        return None, [], memo

    with pytest.warns(DeprecationWarning):
        session.register_execution_handlers("legacy_drop", execution_handler)

    assert "legacy_drop" in session._resize_handlers
    assert "legacy_drop" in session._execution_handlers

    with pytest.warns(DeprecationWarning):
        await session.async_execute_strategy("legacy_drop")
    assert len(session.context_window) == 0
