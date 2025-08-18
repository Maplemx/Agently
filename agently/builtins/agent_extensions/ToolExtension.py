# Copyright 2023-2025 AgentEra(Agently.Tech)
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


from typing import Any, Callable, TYPE_CHECKING, TypeVar, ParamSpec

from agently.utils import Settings, FunctionShifter
from agently.core import ModelRequest, BaseAgent

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType, MCPConfigs, AgentlyModelResult

from agently.base import tool

P = ParamSpec("P")
R = TypeVar("R")


class ToolExtension(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from agently.base import event_center

        self.tool = tool
        self.tool_func = self.tool.tool_func

        self.use_tool = self.use_tools
        self.use_mcp = FunctionShifter.syncify(self.async_use_mcp)

        self.__tool_log = None
        self.__messenger = event_center.create_messenger("Agently Tool")

        self.extension_handlers.append("prefixes", self.__prefix)
        self.extension_handlers.append("base_suffixes", self.__base_suffix)

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
                names.append(tool.__name__)
        self.tool.tag(names, f"agent-{ self.name }")
        return self

    async def async_use_mcp(self, transport: "MCPConfigs | str | Any"):
        await self.tool.async_use_mcp(transport, tags=[f"agent-{ self.name }"])
        return self

    async def __prefix(self, prompt: "Prompt", settings: "Settings"):
        tool_list = self.tool.get_tool_list(tags=[f"agent-{ self.name }"])
        if tool_list:
            tool_judgement_request = ModelRequest(
                self.plugin_manager,
                parent_settings=self.settings,
                agent_name=self.name,
            )
            tool_judgement_request.set_prompt("input", prompt.get("input"))
            tool_judgement_request.set_prompt("extra instruction", prompt.get("instruct"))
            tool_judgement_request.set_prompt("tools", tool_list)
            tool_judgement_request.set_prompt(
                "instruct", "Judge if you need to use tool in {tools} to collect information for responding {input}?"
            )
            tool_judgement_request.set_prompt(
                "output",
                {
                    "use_tool": (bool,),
                    "tool_command": {
                        "purpose": (
                            str,
                            "Simple words to conclude why/what result you want to use tool to collect?",
                        ),
                        "tool_name": (str, "Must in {tools.[].name}"),
                        "tool_kwargs": (dict, "kwargs dict as {tools.[].kwargs} of {tool_name}"),
                    },
                },
            )
            tool_judgement_result = tool_judgement_request.get_async_generator(content="instant")
            async for instant in tool_judgement_result:
                if instant.path == "use_tool" and instant.is_complete:
                    if instant.value is False:
                        return
                if instant.path == "tool_command" and instant.is_complete:
                    tool_command = instant.value
                    tool_result = await self.tool.async_call_tool(
                        tool_command["tool_name"],
                        tool_command["tool_kwargs"],
                    )
                    prompt.set(
                        "action_results",
                        {
                            tool_command["purpose"]: tool_result,
                        },
                    )
                    self.__tool_log = {
                        "tool_name": tool_command["tool_name"],
                        "kwargs": tool_command["tool_kwargs"],
                        "purpose": tool_command["purpose"],
                        "result": tool_result,
                    }

    async def __base_suffix(self, full_result_data: "AgentlyModelResult"):
        if self.__tool_log is not None:
            yield "tool", self.__tool_log
            if "extra" not in full_result_data:
                full_result_data["extra"] = {}
            if isinstance(full_result_data["extra"], dict) and "tool_logs" not in full_result_data["extra"]:
                full_result_data["extra"]["tool_logs"] = []
            if (
                "extra" in full_result_data
                and isinstance(full_result_data["extra"], dict)
                and "tool_logs" in full_result_data["extra"]
            ):
                full_result_data["extra"]["tool_logs"].append(self.__tool_log)
            if self.settings.get("runtime.show_tool_logs"):
                await self.__messenger.async_info(
                    "\n" + "\n".join([f"{ key }: { value }" for key, value in self.__tool_log.items()])
                )
            self.__tool_log = None
