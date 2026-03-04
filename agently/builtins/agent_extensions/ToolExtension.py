# Copyright 2023-2026 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import asyncio

from typing import Any, Callable, TYPE_CHECKING, TypeVar, ParamSpec

from agently.utils import FunctionShifter
from agently.core import ModelRequest, BaseAgent

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.core.Tool import ToolCommand, ToolExecutionRecord, ToolPlanDecision
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType, MCPConfigs, AgentlyModelResult

from agently.base import tool

P = ParamSpec("P")
R = TypeVar("R")


class ToolExtension(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from agently.base import async_system_message

        self.tool = tool
        self.tool_func = self.tool.tool_func

        self.use_tool = self.use_tools
        self.use_mcp = FunctionShifter.syncify(self.async_use_mcp)

        self.settings.setdefault("tool.loop.max_rounds", 5, inherit=True)
        self.settings.setdefault("tool.loop.concurrency", None, inherit=True)
        self.settings.setdefault("tool.loop.timeout", None, inherit=True)
        self.settings.setdefault("tool.loop.enabled", True, inherit=True)

        self.__tool_logs: list[ToolExecutionRecord] = []
        self.__tool_plan_analysis_handler = self.__default_tool_plan_analysis_handler
        self.__tool_execution_handler = self.__default_tool_execution_handler

        self.extension_handlers.append("request_prefixes", self.__request_prefix)
        self.extension_handlers.append("broadcast_prefixes", self.__broadcast_prefix)

        self.async_system_message = async_system_message

    def register_tool(
        self,
        *,
        name: str,
        desc: str,
        kwargs: "KwargsType",
        func: Callable,
        returns: "ReturnType | None" = None,
    ):
        self.tool.register(
            name=name,
            desc=desc,
            kwargs=kwargs,
            func=func,
            tags=[f"agent-{ self.name }"],
            returns=returns,
        )
        return self

    def tool_func(self, func: Callable[P, R]) -> Callable[P, R]:
        self.tool.tool_func(func)
        name = func.__name__
        self.tool.tag([name], [f"agent-{ self.name }"])
        return func

    def use_tools(self, tools: Callable | str | list[str | Callable]):
        if isinstance(tools, (str, Callable)):
            tools = [tools]
        names = []
        for tool in tools:
            if isinstance(tool, str):
                names.append(tool)
            else:
                if tool.__name__ not in self.tool.tool_manager.tool_funcs:  # type: ignore
                    self.tool_func(tool)
                names.append(tool.__name__)
        self.tool.tag(names, f"agent-{ self.name }")
        return self

    async def async_use_mcp(self, transport: "MCPConfigs | str | Any"):
        await self.tool.async_use_mcp(transport, tags=[f"agent-{ self.name }"])
        return self

    def set_tool_loop(
        self,
        *,
        enabled: bool | None = None,
        max_rounds: int | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ):
        if enabled is not None:
            self.settings.set("tool.loop.enabled", bool(enabled))
        if max_rounds is not None:
            if not isinstance(max_rounds, int) or max_rounds < 0:
                raise ValueError("max_rounds must be an integer >= 0.")
            self.settings.set("tool.loop.max_rounds", max_rounds)
        if concurrency is not None:
            if not isinstance(concurrency, int) or concurrency <= 0:
                raise ValueError("concurrency must be an integer > 0.")
            self.settings.set("tool.loop.concurrency", concurrency)
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError("timeout must be a number > 0.")
            self.settings.set("tool.loop.timeout", float(timeout))
        return self

    def register_tool_plan_analysis_handler(self, handler):
        self.__tool_plan_analysis_handler = FunctionShifter.asyncify(handler)
        return self

    def register_tool_execution_handler(self, handler):
        self.__tool_execution_handler = FunctionShifter.asyncify(handler)
        return self

    @staticmethod
    def __is_next_action_path(path: Any) -> bool:
        if not isinstance(path, str):
            return False
        normalized = path.strip()
        if normalized.startswith("$"):
            normalized = normalized[1:]
        normalized = normalized.lstrip("./")
        return normalized == "next_action"

    @staticmethod
    async def __try_close_response_stream(response: Any):
        result = getattr(response, "result", None)
        parser = getattr(result, "_response_parser", None)
        consumer = getattr(parser, "_response_consumer", None)
        close = getattr(consumer, "close", None)
        if callable(close):
            maybe_coroutine = close()
            if asyncio.iscoroutine(maybe_coroutine):
                await maybe_coroutine

    async def __default_tool_plan_analysis_handler(
        self,
        prompt: "Prompt",
        settings: "Settings",
        tool_list: list[dict[str, Any]],
        done_plans: list["ToolExecutionRecord"],
        last_round_records: list["ToolExecutionRecord"],
        round_index: int,
        max_rounds: int | None,
        agent_name: str,
    ) -> "ToolPlanDecision":
        tool_plan_request = ModelRequest(
            self.plugin_manager,
            parent_settings=settings,
            agent_name=agent_name,
        )
        tool_plan_request.input(
            {
                "user_input": prompt.get("input"),
                "user_extra_requriement": prompt.get("instruct"),
                "available_tools": tool_list,
            }
        ).info(
            {
                "done_plans": done_plans,
                "last_round_result": last_round_records,
                "round_index": round_index,
                "max_rounds": max_rounds,
            }
        ).instruct(
            [
                "Plan next actions to respond to {input.user_input} with {input.available_tools}.",
                "Decide this round action first via 'next_action': 'execute' or 'response'.",
                "If next_action is 'response', return empty 'execution_commands'.",
                "If next_action is 'execute', return one or more 'execution_commands' for parallel execution.",
                "Each command must include 'todo_suggestion' for next round decision making.",
                "Use {info.done_plans}, {info.last_round_result}, {info.round_index}, and {info.max_rounds} for decision.",
            ]
        ).output(
            {
                "next_action": ("'execute' | 'response'", "This round action decision."),
                "execution_commands": [
                    {
                        "purpose": (str, "What this tool call collects or verifies."),
                        "tool_name": (str, "Must in {input.available_tools.[].name}"),
                        "tool_kwargs": (dict, "kwargs dict as {input.available_tools.[].kwargs} of {tool_name}"),
                        "todo_suggestion": (str, "Suggestion for next round's next_action decision."),
                    }
                ],
            }
        )
        tool_plan_response = tool_plan_request.get_response()
        async for instant in tool_plan_response.get_async_generator(type="instant"):
            if not instant.is_complete:
                continue
            if not self.__is_next_action_path(instant.path):
                continue
            if isinstance(instant.value, str) and instant.value.strip().lower() == "response":
                await self.__try_close_response_stream(tool_plan_response)
                return {
                    "next_action": "response",
                    "use_tool": False,
                    "execution_commands": [],
                }
            break
        result = await tool_plan_response.result.async_get_data()
        return result

    async def __default_tool_execution_handler(
        self,
        tool_commands: list["ToolCommand"],
        _settings: "Settings",
        async_call_tool,
        done_plans: list["ToolExecutionRecord"],
        round_index: int,
        concurrency: int | None,
        agent_name: str,
    ) -> list["ToolExecutionRecord"]:
        _ = (done_plans, round_index, agent_name)
        if len(tool_commands) == 0:
            return []

        semaphore = asyncio.Semaphore(concurrency) if isinstance(concurrency, int) and concurrency > 0 else None

        async def run_command(tool_command: "ToolCommand") -> "ToolExecutionRecord":
            tool_name = str(tool_command.get("tool_name", ""))
            tool_kwargs = tool_command.get("tool_kwargs", {})
            if not isinstance(tool_kwargs, dict):
                tool_kwargs = {}
            purpose = str(tool_command.get("purpose", f"Use {tool_name}"))
            next_step = str(tool_command.get("todo_suggestion", tool_command.get("next", "")))

            async def execute_once() -> "ToolExecutionRecord":
                result = await async_call_tool(tool_name, tool_kwargs)
                success = not self.tool.is_execution_error_result(result)
                return {
                    "purpose": purpose,
                    "tool_name": tool_name,
                    "kwargs": dict(tool_kwargs),
                    "todo_suggestion": next_step,
                    "next": next_step,
                    "success": success,
                    "result": result,
                    "error": "" if success else str(result),
                }

            if semaphore is None:
                return await execute_once()
            async with semaphore:
                return await execute_once()

        return await asyncio.gather(*[run_command(tool_command) for tool_command in tool_commands])

    async def __request_prefix(self, prompt: "Prompt", _):
        self.__tool_logs = []
        if self.settings.get("tool.loop.enabled", True) is not True:
            return

        tool_list = self.tool.get_tool_list(tags=[f"agent-{ self.name }"])
        if len(tool_list) == 0:
            return

        records = await self.tool.async_plan_and_execute(
            prompt=prompt,
            settings=self.settings,
            tool_list=tool_list,
            agent_name=self.name,
            plan_analysis_handler=self.__tool_plan_analysis_handler,
            tool_execution_handler=self.__tool_execution_handler,
            max_rounds=self.settings.get("tool.loop.max_rounds", 5),  # type: ignore
            concurrency=self.settings.get("tool.loop.concurrency", None),  # type: ignore
            timeout=self.settings.get("tool.loop.timeout", None),  # type: ignore
        )

        if len(records) > 0:
            prompt.set("action_results", self.tool.to_action_results(records))
            prompt.set("extra_instruction", self.tool.TOOL_RESULT_QUOTE_NOTICE)
            self.__tool_logs = records

    async def __broadcast_prefix(self, full_result_data: "AgentlyModelResult", _):
        if len(self.__tool_logs) == 0:
            return

        for tool_log in self.__tool_logs:
            yield "tool", tool_log

        if "extra" not in full_result_data:
            full_result_data["extra"] = {}
        if isinstance(full_result_data["extra"], dict) and "tool_logs" not in full_result_data["extra"]:
            full_result_data["extra"]["tool_logs"] = []
        if (
            "extra" in full_result_data
            and isinstance(full_result_data["extra"], dict)
            and "tool_logs" in full_result_data["extra"]
            and isinstance(full_result_data["extra"]["tool_logs"], list)
        ):
            full_result_data["extra"]["tool_logs"].extend(self.__tool_logs)
        if self.settings.get("runtime.show_tool_logs"):
            for tool_log in self.__tool_logs:
                await self.async_system_message(
                    "TOOL",
                    "\n".join(
                        [f"{ key }: { value }" for key, value in tool_log.items()],
                    ),
                )
        self.__tool_logs = []
