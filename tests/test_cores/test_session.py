import pytest

from agently.core.Session import Session
from agently.types.plugins import MemoResizeDecision
from agently.types.data import ChatMessage
from agently.utils import Settings


@pytest.mark.asyncio
async def test_default_policy_triggers_on_text_length():
    session = Session()
    session.set_settings("session.resize.max_messages_text_length", 10)
    session.set_settings("session.resize.max_keep_messages_count", None)
    session.set_settings("session.resize.every_n_turns", 10_000)
    session.set_resize_handlers("deep", lambda f, c, m, s: (f, c, m))

    session.append_message({"role": "user", "content": "01234567890123456789"})
    session.append_message({"role": "assistant", "content": "x"})

    decision = await session.async_judge_resize()
    assert decision is not None
    assert "reason" in decision
    assert decision["reason"] == "max_messages_text_length"
    assert decision["type"] == "deep"


@pytest.mark.asyncio
async def test_default_policy_triggers_on_max_keep_messages_count():
    session = Session()
    session.set_settings("session.resize.max_messages_text_length", 1_000_000)
    session.set_settings("session.resize.max_keep_messages_count", 2)
    session.set_settings("session.resize.every_n_turns", 10_000)
    session.set_resize_handlers("lite", lambda f, c, m, s: (f, c, m))

    session.append_message({"role": "user", "content": "a"})
    session.append_message({"role": "assistant", "content": "b"})
    session.append_message({"role": "user", "content": "c"})

    decision = await session.async_judge_resize()
    assert decision is not None
    assert "reason" in decision
    assert decision["reason"] == "max_keep_messages_count"
    assert decision["type"] == "lite"


@pytest.mark.asyncio
async def test_default_policy_triggers_on_turns():
    session = Session()
    session.set_settings("session.resize.max_messages_text_length", 1_000_000)
    session.set_settings("session.resize.max_keep_messages_count", None)
    session.set_settings("session.resize.every_n_turns", 1)
    session.set_resize_handlers("lite", lambda f, c, m, s: (f, c, m))

    session.append_message({"role": "user", "content": "hi"})
    session.append_message({"role": "assistant", "content": "a"})

    decision = await session.async_judge_resize()
    assert decision is not None
    assert "reason" in decision
    assert decision["reason"] == "every_n_turns"
    assert decision["type"] == "lite"


@pytest.mark.asyncio
async def test_default_policy_disabled():
    session = Session()
    session.set_settings("session.resize.max_messages_text_length", 0)
    session.set_settings("session.resize.max_keep_messages_count", None)
    session.set_settings("session.resize.every_n_turns", 0)
    session.set_resize_handlers("lite", lambda f, c, m, s: (f, c, m))
    session.set_resize_handlers("deep", lambda f, c, m, s: (f, c, m))

    session.append_message({"role": "user", "content": "hi"})
    session.append_message({"role": "assistant", "content": "a"})

    decision = await session.async_judge_resize()
    assert decision is None


@pytest.mark.asyncio
async def test_sync_handler_override():
    session = Session()

    def policy_handler(
        full_chat_history: list[ChatMessage],
        current_chat_history: list[ChatMessage],
        settings: Settings,
    ) -> MemoResizeDecision:
        return {"type": "lite", "reason": "manual"}

    def resize_handler(
        full_chat_history: list[ChatMessage],
        current_chat_history: list[ChatMessage],
        memo: dict,
        settings: Settings,
    ):
        memo = {"handler": "sync"}
        return full_chat_history, current_chat_history[:1], memo

    session.set_policy_handler(policy_handler)
    session.set_resize_handlers("lite", resize_handler)  # type: ignore
    session.append_message({"role": "user", "content": "a"})
    session.append_message({"role": "assistant", "content": "b"})
    await session.async_resize()
    assert session.memo["handler"] == "sync"
    assert len(session.current_chat_history) == 1


@pytest.mark.asyncio
async def test_async_handler_override():
    session = Session()

    async def policy_handler(
        full_chat_history: list[ChatMessage],
        current_chat_history: list[ChatMessage],
        settings: Settings,
    ) -> MemoResizeDecision:
        return {"type": "deep", "reason": "manual"}

    async def resize_handler(
        full_chat_history: list[ChatMessage],
        current_chat_history: list[ChatMessage],
        memo: dict,
        settings: Settings,
    ):
        memo = {"handler": "async"}
        return full_chat_history, current_chat_history[:1], memo

    session.set_policy_handler(policy_handler)
    session.set_resize_handlers("deep", resize_handler)  # type: ignore
    session.append_message({"role": "user", "content": "a"})
    session.append_message({"role": "assistant", "content": "b"})
    await session.async_resize()
    assert session.memo["handler"] == "async"
    assert len(session.current_chat_history) == 1
