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


import warnings

from typing import Any, Callable, TYPE_CHECKING, TypeVar, ParamSpec

from agently.utils import FunctionShifter
from agently.core import BaseAgent

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.core.Tool import ToolCommand, ToolExecutionRecord
    from agently.types.data import KwargsType, ReturnType, MCPConfigs, AgentlyModelResult

from agently.base import tool

P = ParamSpec("P")
R = TypeVar("R")


class ToolExtension(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tool = tool
        self.tool_func = self.tool.tool_func

        self.use_tool = self.use_tools
        self.use_mcp = FunctionShifter.syncify(self.async_use_mcp)

        self.settings.setdefault("tool.loop.max_rounds", 5, inherit=True)
        self.settings.setdefault("tool.loop.concurrency", None, inherit=True)
        self.settings.setdefault("tool.loop.timeout", None, inherit=True)
        self.settings.setdefault("tool.loop.enabled", True, inherit=True)

        self.__tool_logs: list[ToolExecutionRecord] = []

        self.extension_handlers.append("request_prefixes", self.__request_prefix)
        self.extension_handlers.append("broadcast_prefixes", self.__broadcast_prefix)

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
        self.tool.register_plan_analysis_handler(handler)
        return self

    def register_tool_execution_handler(self, handler):
        self.tool.register_tool_execution_handler(handler)
        return self

    async def async_generate_tool_command(
        self,
        prompt: "Prompt | None" = None,
        *,
        done_plans: list["ToolExecutionRecord"] | None = None,
        last_round_records: list["ToolExecutionRecord"] | None = None,
        round_index: int = 0,
        max_rounds: int | None = None,
    ) -> list["ToolCommand"]:
        target_prompt = prompt if prompt is not None else self.request.prompt
        tool_list = self.tool.get_tool_list(tags=[f"agent-{ self.name }"])
        return await self.tool.async_generate_tool_command(
            prompt=target_prompt,
            settings=self.settings,
            tool_list=tool_list,
            agent_name=self.name,
            done_plans=done_plans,
            last_round_records=last_round_records,
            round_index=round_index,
            max_rounds=max_rounds,
        )

    def generate_tool_command(
        self,
        prompt: "Prompt | None" = None,
        *,
        done_plans: list["ToolExecutionRecord"] | None = None,
        last_round_records: list["ToolExecutionRecord"] | None = None,
        round_index: int = 0,
        max_rounds: int | None = None,
    ) -> list["ToolCommand"]:
        return FunctionShifter.syncify(self.async_generate_tool_command)(
            prompt=prompt,
            done_plans=done_plans,
            last_round_records=last_round_records,
            round_index=round_index,
            max_rounds=max_rounds,
        )

    async def async_must_call(
        self,
        prompt: "Prompt | None" = None,
        *,
        done_plans: list["ToolExecutionRecord"] | None = None,
        last_round_records: list["ToolExecutionRecord"] | None = None,
        round_index: int = 0,
        max_rounds: int | None = None,
    ) -> list["ToolCommand"]:
        warnings.warn(
            "Method .async_must_call() is deprecated and will be removed in future version, "
            "please use .async_generate_tool_command() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.async_generate_tool_command(
            prompt=prompt,
            done_plans=done_plans,
            last_round_records=last_round_records,
            round_index=round_index,
            max_rounds=max_rounds,
        )

    def must_call(
        self,
        prompt: "Prompt | None" = None,
        *,
        done_plans: list["ToolExecutionRecord"] | None = None,
        last_round_records: list["ToolExecutionRecord"] | None = None,
        round_index: int = 0,
        max_rounds: int | None = None,
    ) -> list["ToolCommand"]:
        warnings.warn(
            "Method .must_call() is deprecated and will be removed in future version, "
            "please use .generate_tool_command() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.generate_tool_command(
            prompt=prompt,
            done_plans=done_plans,
            last_round_records=last_round_records,
            round_index=round_index,
            max_rounds=max_rounds,
        )

    async def __request_prefix(self, prompt: "Prompt", _settings):
        settings = _settings if _settings is not None else self.settings
        self.__tool_logs = []
        if settings.get("tool.loop.enabled", True) is not True:
            return

        tool_list = self.tool.get_tool_list(tags=[f"agent-{ self.name }"])
        if len(tool_list) == 0:
            return

        records = await self.tool.async_plan_and_execute(
            prompt=prompt,
            settings=settings,
            tool_list=tool_list,
            agent_name=self.name,
            max_rounds=settings.get("tool.loop.max_rounds", 5),  # type: ignore
            concurrency=settings.get("tool.loop.concurrency", None),  # type: ignore
            timeout=settings.get("tool.loop.timeout", None),  # type: ignore
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
        self.__tool_logs = []
