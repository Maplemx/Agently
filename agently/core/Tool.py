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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, cast
from typing_extensions import TypedDict

from agently.utils import Settings, SettingsNamespace, FunctionShifter
from .TriggerFlow import TriggerFlow

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.types.plugins import ToolManager
    from agently.core import PluginManager


class ToolCommand(TypedDict, total=False):
    purpose: str
    tool_name: str
    tool_kwargs: dict[str, Any]
    todo_suggestion: str
    next: str


class ToolPlanDecision(TypedDict, total=False):
    next_action: str
    use_tool: bool
    next: str
    execution_commands: list[ToolCommand]
    tool_command: ToolCommand
    tool_commands: list[ToolCommand]


class ToolExecutionRecord(TypedDict, total=False):
    purpose: str
    tool_name: str
    kwargs: dict[str, Any]
    todo_suggestion: str
    next: str
    success: bool
    result: Any
    error: str


ToolPlanAnalysisHandler = Callable[
    [
        "Prompt",
        "Settings",
        list[dict[str, Any]],
        list[ToolExecutionRecord],
        list[ToolExecutionRecord],
        int,
        int | None,
        str,
    ],
    ToolPlanDecision | Awaitable[ToolPlanDecision],
]

StandardToolPlanAnalysisHandler = Callable[
    [
        "Prompt",
        "Settings",
        list[dict[str, Any]],
        list[ToolExecutionRecord],
        list[ToolExecutionRecord],
        int,
        int | None,
        str,
    ],
    Awaitable[ToolPlanDecision],
]

ToolExecutionHandler = Callable[
    [
        list[ToolCommand],
        "Settings",
        Callable[[str, dict[str, Any]], Awaitable[Any]],
        list[ToolExecutionRecord],
        int,
        int | None,
        str,
    ],
    list[ToolExecutionRecord] | Awaitable[list[ToolExecutionRecord]],
]

StandardToolExecutionHandler = Callable[
    [
        list[ToolCommand],
        "Settings",
        Callable[[str, dict[str, Any]], Awaitable[Any]],
        list[ToolExecutionRecord],
        int,
        int | None,
        str,
    ],
    Awaitable[list[ToolExecutionRecord]],
]


class Tool:
    TOOL_RESULT_QUOTE_NOTICE = (
        "NOTICE: MUST QUOTE KEY INFO OR MARK SOURCE (PREFER URL INCLUDED) FROM {action_results} "
        "IN REPLY IF YOU USE {action_results} TO IMPROVE REPLY!"
    )

    def __init__(
        self,
        plugin_manager: "PluginManager",
        parent_settings: "Settings",
    ):
        self.plugin_manager = plugin_manager
        self.settings = Settings(
            name="Tool-Settings",
            parent=parent_settings,
        )
        self.tool_settings = SettingsNamespace(self.settings, "tool")
        self.tool_settings.setdefault("loop.max_rounds", 5)
        self.tool_settings.setdefault("loop.concurrency", None)
        self.tool_settings.setdefault("loop.timeout", None)

        ToolManagerPlugin = cast(
            type["ToolManager"],
            plugin_manager.get_plugin(
                "ToolManager",
                str(self.settings["plugins.ToolManager.activate"]),
            ),
        )
        self.tool_manager = ToolManagerPlugin(self.settings)
        self.register = self.tool_manager.register
        self.tag = self.tool_manager.tag
        self.tool_func = self.tool_manager.tool_func
        self.get_tool_info = self.tool_manager.get_tool_info
        self.get_tool_list = self.tool_manager.get_tool_list
        self.get_tool_func = self.tool_manager.get_tool_func
        self.call_tool = self.tool_manager.call_tool
        self.async_call_tool = self.tool_manager.async_call_tool
        self.use_mcp = self.tool_manager.use_mcp
        self.async_use_mcp = self.tool_manager.async_use_mcp

        self._plan_analysis_handler: "StandardToolPlanAnalysisHandler | None" = None
        self._tool_execution_handler: "StandardToolExecutionHandler | None" = None

        self.plan_and_execute = FunctionShifter.syncify(self.async_plan_and_execute)

    def set_loop_options(
        self,
        *,
        max_rounds: int | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ):
        if max_rounds is not None:
            if not isinstance(max_rounds, int) or max_rounds < 0:
                raise ValueError("max_rounds must be an integer >= 0.")
            self.tool_settings.set("loop.max_rounds", max_rounds)
        if concurrency is not None:
            if not isinstance(concurrency, int) or concurrency <= 0:
                raise ValueError("concurrency must be an integer > 0.")
            self.tool_settings.set("loop.concurrency", concurrency)
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError("timeout must be a number > 0.")
            self.tool_settings.set("loop.timeout", float(timeout))
        return self

    def register_plan_analysis_handler(self, handler: "ToolPlanAnalysisHandler | None"):
        if handler is None:
            self._plan_analysis_handler = None
        else:
            self._plan_analysis_handler = FunctionShifter.asyncify(handler)
        return self

    def register_tool_execution_handler(self, handler: "ToolExecutionHandler | None"):
        if handler is None:
            self._tool_execution_handler = None
        else:
            self._tool_execution_handler = FunctionShifter.asyncify(handler)
        return self

    @staticmethod
    def is_execution_error_result(result: Any):
        if not isinstance(result, str):
            return False
        stripped = result.strip()
        return stripped.startswith("Error:") or stripped.startswith("Can not find tool named")

    @staticmethod
    def _normalize_tool_command(command: Any, *, fallback_next: str | None = None) -> "ToolCommand | None":
        if not isinstance(command, dict):
            return None

        tool_name = command.get("tool_name")
        if not isinstance(tool_name, str) or tool_name.strip() == "":
            return None

        purpose = command.get("purpose")
        if not isinstance(purpose, str) or purpose.strip() == "":
            purpose = f"Use {tool_name}"

        tool_kwargs = command.get("tool_kwargs", {})
        if not isinstance(tool_kwargs, dict):
            tool_kwargs = {}

        command_next = command.get("todo_suggestion")
        if not isinstance(command_next, str) or command_next.strip() == "":
            command_next = command.get("next")
        if not isinstance(command_next, str) or command_next.strip() == "":
            command_next = fallback_next if isinstance(fallback_next, str) and fallback_next.strip() != "" else ""

        return {
            "purpose": purpose,
            "tool_name": tool_name,
            "tool_kwargs": tool_kwargs,
            "todo_suggestion": command_next,
            "next": command_next,
        }

    def _normalize_plan_decision(self, decision: Any) -> "ToolPlanDecision":
        if not isinstance(decision, dict):
            return {
                "next_action": "response",
                "use_tool": False,
                "next": "",
                "tool_commands": [],
            }

        fallback_next = decision.get("todo_suggestion")
        if not isinstance(fallback_next, str):
            fallback_next = decision.get("next")
        if not isinstance(fallback_next, str):
            fallback_next = ""

        tool_commands: list[ToolCommand] = []
        command_key: str | None = None
        for key in ("execution_commands", "tool_commands"):
            if isinstance(decision.get(key), list):
                command_key = key
                break
        if command_key:
            for command in decision[command_key]:
                tool_command = self._normalize_tool_command(command, fallback_next=fallback_next)
                if tool_command is not None:
                    tool_commands.append(tool_command)

        if len(tool_commands) == 0 and "tool_command" in decision:
            tool_command = self._normalize_tool_command(decision.get("tool_command"), fallback_next=fallback_next)
            if tool_command is not None:
                tool_commands.append(tool_command)

        next_action = decision.get("next_action")
        if not isinstance(next_action, str) or next_action.strip() == "":
            next_action = "execute" if len(tool_commands) > 0 else "response"
        next_action = next_action.lower()
        if next_action not in {"execute", "response"}:
            next_action = "execute" if len(tool_commands) > 0 else "response"

        use_tool = decision.get("use_tool")
        if isinstance(use_tool, bool):
            final_use_tool = use_tool and len(tool_commands) > 0 and next_action == "execute"
        else:
            final_use_tool = len(tool_commands) > 0 and next_action == "execute"

        if not final_use_tool:
            tool_commands = []
            next_action = "response"

        return {
            "next_action": next_action,
            "use_tool": final_use_tool,
            "next": fallback_next,
            "execution_commands": tool_commands,
            "tool_commands": tool_commands,
        }

    def _normalize_execution_record(
        self, record: Any, command: "ToolCommand | None", index: int
    ) -> "ToolExecutionRecord":
        if command is None:
            command = {}

        fallback_tool_name = str(command.get("tool_name", ""))
        fallback_kwargs = command.get("tool_kwargs", {})
        if not isinstance(fallback_kwargs, dict):
            fallback_kwargs = {}
        fallback_purpose = str(command.get("purpose", f"tool_call_{ index + 1 }"))
        fallback_next = str(command.get("todo_suggestion", command.get("next", "")))

        if isinstance(record, dict):
            tool_name = record.get("tool_name", fallback_tool_name)
            if not isinstance(tool_name, str):
                tool_name = fallback_tool_name

            kwargs = record.get("kwargs", fallback_kwargs)
            if not isinstance(kwargs, dict):
                kwargs = fallback_kwargs

            purpose = record.get("purpose", fallback_purpose)
            if not isinstance(purpose, str):
                purpose = fallback_purpose

            next_step = record.get("todo_suggestion", record.get("next", fallback_next))
            if not isinstance(next_step, str):
                next_step = fallback_next

            result = record.get("result")
            error = record.get("error", "")
            if not isinstance(error, str):
                error = str(error)

            success = record.get("success")
            if not isinstance(success, bool):
                success = error == "" and not self.is_execution_error_result(result)

            if not success and error == "":
                error = str(result) if result is not None else "Tool execution failed."

            return {
                "purpose": purpose,
                "tool_name": tool_name,
                "kwargs": dict(kwargs),
                "todo_suggestion": next_step,
                "next": next_step,
                "success": success,
                "result": result,
                "error": error,
            }

        result = record
        success = not self.is_execution_error_result(result)
        return {
            "purpose": fallback_purpose,
            "tool_name": fallback_tool_name,
            "kwargs": dict(fallback_kwargs),
            "todo_suggestion": fallback_next,
            "next": fallback_next,
            "success": success,
            "result": result,
            "error": "" if success else str(result),
        }

    def _normalize_execution_records(
        self,
        records: Any,
        commands: list["ToolCommand"],
    ) -> list["ToolExecutionRecord"]:
        if not isinstance(records, list):
            return []

        normalized: list[ToolExecutionRecord] = []
        for index, record in enumerate(records):
            command = commands[index] if index < len(commands) else None
            normalized.append(self._normalize_execution_record(record, command, index))
        return normalized

    @staticmethod
    def to_action_results(records: list["ToolExecutionRecord"]):
        action_results: dict[str, Any] = {}
        used_keys: set[str] = set()

        for index, record in enumerate(records):
            purpose = record.get("purpose")
            if not isinstance(purpose, str) or purpose.strip() == "":
                purpose = f"tool_call_{ index + 1 }"

            key = purpose
            suffix = 2
            while key in used_keys:
                key = f"{ purpose } ({ suffix })"
                suffix += 1

            used_keys.add(key)
            if record.get("success"):
                action_results[key] = record.get("result")
            else:
                action_results[key] = {
                    "error": record.get("error", "Tool execution failed."),
                    "result": record.get("result"),
                }

        return action_results

    @staticmethod
    def _should_continue(
        decision: "ToolPlanDecision",
        *,
        round_index: int,
        max_rounds: int | None,
    ):
        if isinstance(max_rounds, int) and max_rounds >= 0 and round_index >= max_rounds:
            return False
        if decision.get("next_action") != "execute":
            return False
        if decision.get("use_tool") is not True:
            return False
        commands = decision.get("tool_commands")
        return isinstance(commands, list) and len(commands) > 0

    async def async_plan_and_execute(
        self,
        *,
        prompt: "Prompt",
        settings: "Settings",
        tool_list: list[dict[str, Any]],
        agent_name: str = "Manual",
        plan_analysis_handler: "ToolPlanAnalysisHandler | None" = None,
        tool_execution_handler: "ToolExecutionHandler | None" = None,
        max_rounds: int | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ) -> list["ToolExecutionRecord"]:
        if len(tool_list) == 0:
            return []

        if plan_analysis_handler:
            standard_plan_handler = FunctionShifter.asyncify(plan_analysis_handler)
        elif self._plan_analysis_handler:
            standard_plan_handler = FunctionShifter.asyncify(self._plan_analysis_handler)
        else:
            raise RuntimeError("[Agently Tool] Tool plan analysis handler is required.")

        if tool_execution_handler:
            standard_execution_handler = FunctionShifter.asyncify(tool_execution_handler)
        elif self._tool_execution_handler:
            standard_execution_handler = FunctionShifter.asyncify(self._tool_execution_handler)
        else:
            raise RuntimeError("[Agently Tool] Tool execution handler is required.")

        if max_rounds is None:
            max_rounds = self.tool_settings.get("loop.max_rounds", 5)  # type: ignore
        if concurrency is None:
            concurrency = self.tool_settings.get("loop.concurrency", None)  # type: ignore
        if timeout is None:
            timeout = self.tool_settings.get("loop.timeout", None)  # type: ignore

        if not isinstance(max_rounds, int) or max_rounds < 0:
            max_rounds = 5
        if not isinstance(concurrency, int) or concurrency <= 0:
            concurrency = None
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            timeout = None

        flow = TriggerFlow(name=f"tool-loop-{ agent_name }")

        async def initialize_loop(data):
            data.set_runtime_data("done_plans", [])
            data.set_runtime_data("last_round_records", [])
            data.set_runtime_data("round_index", 0)
            await data.async_emit("PLAN", None)
            return None

        async def plan_step(data):
            round_index = data.get_runtime_data("round_index", 0)
            if not isinstance(round_index, int):
                round_index = 0
            done_plans = data.get_runtime_data("done_plans", [])
            if not isinstance(done_plans, list):
                done_plans = []
            last_round_records = data.get_runtime_data("last_round_records", [])
            if not isinstance(last_round_records, list):
                last_round_records = []

            decision = self._normalize_plan_decision(
                await standard_plan_handler(
                    prompt,
                    settings,
                    tool_list,
                    done_plans,
                    last_round_records,
                    round_index,
                    max_rounds,
                    agent_name,
                )
            )
            if self._should_continue(decision, round_index=round_index, max_rounds=max_rounds):
                await data.async_emit("EXECUTE", decision.get("tool_commands", []))
            else:
                await data.async_emit("DONE", done_plans)
            return decision

        async def execute_step(data):
            tool_commands = data.value if isinstance(data.value, list) else []
            round_index = data.get_runtime_data("round_index", 0)
            if not isinstance(round_index, int):
                round_index = 0
            done_plans = data.get_runtime_data("done_plans", [])
            if not isinstance(done_plans, list):
                done_plans = []

            records = self._normalize_execution_records(
                await standard_execution_handler(
                    tool_commands,
                    settings,
                    self.async_call_tool,
                    done_plans,
                    round_index,
                    concurrency,
                    agent_name,
                ),
                tool_commands,
            )

            done_plans.extend(records)
            data.set_runtime_data("done_plans", done_plans)
            data.set_runtime_data("last_round_records", records)
            data.set_runtime_data("round_index", round_index + 1)
            await data.async_emit("PLAN", None)
            return records

        flow.to(initialize_loop)
        flow.when("PLAN").to(plan_step)
        flow.when("EXECUTE").to(execute_step)
        flow.when("DONE").to(lambda data: data.value).end()

        result = await flow.async_start(
            wait_for_result=True,
            timeout=timeout,
        )
        if not isinstance(result, list):
            return []
        return [self._normalize_execution_record(record, None, index) for index, record in enumerate(result)]
