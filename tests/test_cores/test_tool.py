import pytest

import asyncio
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
    assert "Input validation error" in result["error"]
