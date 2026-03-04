import pytest
import json

from agently import Agently
from agently.builtins.plugins.ModelRequester.OpenAICompatible import OpenAICompatible


def test_session_extension_activate_and_override_chat_history():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-test")
    assert agent.activated_session is not None

    agent.add_chat_history({"role": "user", "content": "hello"})

    assert len(agent.activated_session.full_context) == 1
    assert agent.activated_session.full_context[0].content == "hello"
    assert len(agent.activated_session.context_window) == 1

    prompt_chat_history = agent.agent_prompt.get("chat_history")
    assert isinstance(prompt_chat_history, list)
    assert len(prompt_chat_history) == 1


def test_session_extension_clean_context_window():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-test-clean")
    assert agent.activated_session is not None

    agent.add_chat_history({"role": "user", "content": "hello"})
    agent.clean_context_window()

    assert len(agent.activated_session.context_window) == 0
    assert agent.agent_prompt.get("chat_history") == []


def test_session_extension_deactivate_cleans_chat_history():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-test-deactivate")
    assert agent.activated_session is not None

    agent.add_chat_history({"role": "user", "content": "hello"})
    assert len(agent.agent_prompt.get("chat_history", [])) == 1

    agent.deactivate_session()

    assert agent.activated_session is None
    assert agent.agent_prompt.get("chat_history") == []


@pytest.mark.asyncio
async def test_session_extension_request_prefix_syncs_context_window():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-test-prefix")
    assert agent.activated_session is not None

    agent.add_chat_history({"role": "user", "content": "from-session"})
    prompt = agent.request_prompt
    prompt.set("chat_history", [{"role": "assistant", "content": "stale"}])

    await agent._session_request_prefix(prompt, agent.settings)

    synced_history = prompt.get("chat_history")
    assert isinstance(synced_history, list)
    assert len(synced_history) == 1
    assert synced_history[0].content == "from-session"


@pytest.mark.asyncio
async def test_session_extension_finally_default_recording():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-finally-default")
    assert agent.activated_session is not None

    prompt = agent.request_prompt
    prompt.set("input", "hello")

    class DummyResult:
        def __init__(self, prompt):
            self.prompt = prompt

        async def async_get_data(self):
            return {"answer": "world", "score": 10}

    result = DummyResult(prompt)
    expected_user_content = str(prompt.to_text())

    await agent._session_finally(result, agent.settings)  # type: ignore[arg-type]

    history = agent.activated_session.full_context
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == expected_user_content
    assert history[1].role == "assistant"
    assert "answer: world" in str(history[1].content)
    assert "score: 10" in str(history[1].content)


@pytest.mark.asyncio
async def test_session_extension_finally_recording_with_keys():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-finally-keys")
    assert agent.activated_session is not None

    agent.system("base-system", always=True)
    agent.set_settings("session.input_keys", ["city", ".agent.system", "input.code"])
    agent.set_settings("session.reply_keys", ["answer.text", "score"])

    prompt = agent.request_prompt
    prompt.set(
        "input",
        {
            "city": "Shanghai",
            "code": 200,
            "ignored": True,
        },
    )

    class DummyResult:
        def __init__(self, prompt):
            self.prompt = prompt

        async def async_get_data(self):
            return {"answer": {"text": "done"}, "score": 99, "ignored": "x"}

    await agent._session_finally(DummyResult(prompt), agent.settings)  # type: ignore[arg-type]

    history = agent.activated_session.full_context
    assert len(history) == 2
    assert history[0].role == "user"
    assert "[city]:" in str(history[0].content)
    assert "Shanghai" in str(history[0].content)
    assert "[.agent.system]:" in str(history[0].content)
    assert "base-system" in str(history[0].content)
    assert "[input.code]:" in str(history[0].content)
    assert "200" in str(history[0].content)

    assert history[1].role == "assistant"
    assert "[answer.text]:" in str(history[1].content)
    assert "done" in str(history[1].content)
    assert "[score]:" in str(history[1].content)
    assert "99" in str(history[1].content)


def test_session_extension_finally_runs_after_result_ready(monkeypatch):
    async def fake_request_model(self, request_data):
        yield "message", json.dumps(
            {
                "id": "mock-id",
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": "hello",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        )
        yield "message", "[DONE]"

    monkeypatch.setattr(OpenAICompatible, "request_model", fake_request_model)

    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-finally-ready")
    assert agent.activated_session is not None

    list(agent.input("hello").get_generator(type="delta"))

    history = agent.activated_session.full_context
    assert len(history) == 2
    assert history[0].role == "user"
    assert "hello" in str(history[0].content)
    assert history[1].role == "assistant"
    assert "hello" in str(history[1].content)


@pytest.mark.asyncio
async def test_session_extension_register_analysis_and_resize_handler():
    agent = Agently.create_agent()
    agent.activate_session(session_id="session-extension-custom-resize")
    assert agent.activated_session is not None

    called = {"analysis": 0, "resize": 0}

    async def analysis_handler(full_context, context_window, memo, session_settings):
        _ = (full_context, memo, session_settings)
        called["analysis"] += 1
        if len(context_window) > 0:
            return "drop_window"
        return None

    async def resize_handler(full_context, context_window, memo, session_settings):
        _ = (context_window, session_settings)
        called["resize"] += 1
        return full_context, [], memo

    agent.register_session_analysis_handler(analysis_handler)
    agent.register_session_resize_handler("drop_window", resize_handler)

    agent.add_chat_history({"role": "user", "content": "hello"})

    assert called["analysis"] >= 1
    assert called["resize"] >= 1
    assert agent.activated_session.context_window == []


def test_session_extension_register_resize_handler_rejects_empty_strategy():
    agent = Agently.create_agent()
    with pytest.raises(ValueError):
        agent.register_session_resize_handler("", lambda *_: None)  # type: ignore
