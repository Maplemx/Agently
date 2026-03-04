import pytest
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import os
import asyncio
import time
import importlib
from types import SimpleNamespace
from agently import Agently
from agently.types.data import StreamingData


def test_tool_extension():
    Agently.set_settings(
        "OpenAICompatible",
        {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:7b",
            "model_type": "chat",
        },
    )

    agent = Agently.create_agent()

    @agent.tool_func
    async def add(a: int, b: int) -> int:
        """
        Get result of `a(int)` add `b(int)`
        """
        await asyncio.sleep(1)
        assert a == 34643523
        return a + b

    result = (
        agent.input("34643523+52131231=? Use tool to calculate!")
        .use_tool(add)
        .output(
            {
                "result": (int,),
            }
        )
        .start()
    )
    assert result["result"] == 86774754


def test_tool_extension_set_tool_loop_config():
    agent = Agently.create_agent()
    agent.set_tool_loop(
        enabled=True,
        max_rounds=3,
        concurrency=2,
        timeout=6.5,
    )
    assert agent.settings.get("tool.loop.enabled") is True
    assert agent.settings.get("tool.loop.max_rounds") == 3
    assert agent.settings.get("tool.loop.concurrency") == 2
    assert agent.settings.get("tool.loop.timeout") == 6.5


@pytest.mark.asyncio
async def test_tool_extension_request_prefix_injects_action_results(monkeypatch):
    agent = Agently.create_agent()
    request = agent.create_request()
    prompt = request.prompt
    prompt.set("input", "test tool loop")

    monkeypatch.setattr(
        agent.tool,
        "get_tool_list",
        lambda tags=None: [
            {"name": "dummy_tool", "desc": "dummy", "kwargs": {}},
        ],
    )

    async def fake_loop(**kwargs):
        _ = kwargs
        return [
            {
                "purpose": "fetch_dummy",
                "tool_name": "dummy_tool",
                "kwargs": {},
                "next": "respond",
                "success": True,
                "result": {"ok": 1},
                "error": "",
            }
        ]

    monkeypatch.setattr(agent.tool, "async_plan_and_execute", fake_loop)

    await agent._ToolExtension__request_prefix(prompt, None)  # type: ignore

    action_results = prompt.get("action_results")
    assert isinstance(action_results, dict)
    assert action_results.get("fetch_dummy") == {"ok": 1}
    assert "extra_instruction" in prompt


@pytest.mark.asyncio
async def test_tool_extension_plan_handler_instant_response_short_circuit(monkeypatch):
    agent = Agently.create_agent()
    request = agent.create_request()
    prompt = request.prompt
    prompt.set("input", "hello")
    prompt.set("instruct", "just answer directly")

    closed = False

    async def fake_close():
        nonlocal closed
        closed = True

    async def fake_async_get_data():
        raise AssertionError("async_get_data should not be called when next_action is response")

    class FakeResponse:
        def __init__(self):
            self.result = SimpleNamespace(
                async_get_data=fake_async_get_data,
                _response_parser=SimpleNamespace(
                    _response_consumer=SimpleNamespace(
                        close=fake_close,
                    )
                ),
            )

        def get_async_generator(self, type=None, **kwargs):
            _ = kwargs
            assert type == "instant"

            async def gen():
                yield StreamingData(
                    path="$.next_action",
                    value="response",
                    is_complete=True,
                )

            return gen()

    class FakeModelRequest:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

        def input(self, *args, **kwargs):
            _ = (args, kwargs)
            return self

        def info(self, *args, **kwargs):
            _ = (args, kwargs)
            return self

        def instruct(self, *args, **kwargs):
            _ = (args, kwargs)
            return self

        def output(self, *args, **kwargs):
            _ = (args, kwargs)
            return self

        def get_response(self):
            return FakeResponse()

    tool_extension_module = importlib.import_module("agently.builtins.agent_extensions.ToolExtension")
    monkeypatch.setattr(tool_extension_module, "ModelRequest", FakeModelRequest)

    decision = await agent._ToolExtension__default_tool_plan_analysis_handler(  # type: ignore
        prompt=prompt,
        settings=agent.settings,
        tool_list=[{"name": "dummy_tool", "desc": "dummy", "kwargs": {}}],
        done_plans=[],
        last_round_records=[],
        round_index=0,
        max_rounds=3,
        agent_name=agent.name,
    )

    assert decision["next_action"] == "response"
    assert decision["use_tool"] is False
    assert decision["execution_commands"] == []
    assert closed is True
