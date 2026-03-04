import pytest

import asyncio
import uuid
from pathlib import Path
from agently import Agently


def test_tool():
    tool = Agently.tool

    tool.register(
        name="test",
        desc="test func",
        kwargs={},
        func=lambda: print("OK"),
    )

    @tool.tool_func
    async def add(a: int, b: int) -> int:
        """
        Get result of `a(int)` add `b(int)`
        """
        await asyncio.sleep(1)
        return a + b

    assert tool.get_tool_info() == {
        "add": {
            "name": "add",
            "desc": "Get result of `a(int)` add `b(int)`",
            "kwargs": {
                "a": (int, ""),
                "b": (int, ""),
            },
            "returns": int,
        },
        "test": {
            "desc": "test func",
            "kwargs": {},
            "name": "test",
        },
    }
    add_tool = tool.get_tool_func("add", shift="sync")
    if add_tool:
        result = add_tool(1, 2)
        assert result == 3


def test_use_mcp():
    tool = Agently.tool

    server_script = Path(__file__).with_name("cal_mcp_server.py")
    tool.use_mcp(str(server_script))

    result = tool.call_tool("add", kwargs={"first_number": 1, "second_number": 2})
    assert result["result"] == 3

    result = tool.call_tool("add", kwargs={"a": 1, "b": 2})
    assert "validation error" in result["error"].lower()
    assert "first_number" in result["error"]
    assert "second_number" in result["error"]


@pytest.mark.asyncio
async def test_tool_plan_execute_loop_with_trigger_flow():
    tool = Agently.tool
    tag = f"tool-loop-test-{ uuid.uuid4().hex }"

    async def add_for_loop_test(a: int, b: int):
        await asyncio.sleep(0.01)
        return a + b

    tool.register(
        name=f"add_for_loop_test_{ uuid.uuid4().hex[:8] }",
        desc="Add two integers for tool loop test.",
        kwargs={"a": (int, ""), "b": (int, "")},
        func=add_for_loop_test,
        tags=[tag],
    )
    tool_name = tool.get_tool_list(tags=[tag])[0]["name"]
    prompt = Agently.create_prompt()
    prompt.set("input", "calculate two additions")

    plan_rounds: list[dict] = []

    async def plan_handler(
        _prompt,
        _settings,
        _tool_list,
        done_plans,
        last_round_records,
        round_index,
        _max_rounds,
        _agent_name,
    ):
        plan_rounds.append(
            {
                "round_index": round_index,
                "done_count": len(done_plans),
                "last_count": len(last_round_records),
            }
        )
        if len(done_plans) == 0:
            return {
                "next_action": "execute",
                "tool_commands": [
                    {
                        "purpose": "calc_1",
                        "tool_name": tool_name,
                        "tool_kwargs": {"a": 1, "b": 2},
                        "next": "continue",
                    },
                    {
                        "purpose": "calc_2",
                        "tool_name": tool_name,
                        "tool_kwargs": {"a": 3, "b": 4},
                        "next": "continue",
                    },
                ],
            }
        return {
            "next_action": "response",
            "next": "enough information",
            "tool_commands": [],
        }

    async def execution_handler(
        tool_commands,
        _settings,
        async_call_tool,
        _done_plans,
        _round_index,
        concurrency,
        _agent_name,
    ):
        semaphore = asyncio.Semaphore(concurrency or len(tool_commands))

        async def run(command):
            async with semaphore:
                result = await async_call_tool(command["tool_name"], command.get("tool_kwargs", {}))
                return {
                    "purpose": command["purpose"],
                    "tool_name": command["tool_name"],
                    "kwargs": command.get("tool_kwargs", {}),
                    "next": command.get("next", ""),
                    "success": True,
                    "result": result,
                    "error": "",
                }

        return await asyncio.gather(*[run(command) for command in tool_commands])

    records = await tool.async_plan_and_execute(
        prompt=prompt,
        settings=Agently.settings,
        tool_list=tool.get_tool_list(tags=[tag]),
        agent_name="tool-loop-test",
        plan_analysis_handler=plan_handler,  # type: ignore
        tool_execution_handler=execution_handler,  # type: ignore
        max_rounds=3,
        concurrency=2,
        timeout=5,
    )

    assert len(records) == 2
    assert {record["result"] if "result" in record else None for record in records} == {3, 7}
    assert plan_rounds[0]["done_count"] == 0
    assert plan_rounds[1]["done_count"] == 2
    assert plan_rounds[1]["last_count"] == 2
