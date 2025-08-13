from typing import Any, Callable, TYPE_CHECKING, TypeVar, ParamSpec
from typing_extensions import Self

from agently.utils import Settings
from agently.core import ModelRequest, BaseAgent

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType

from agently.base import tool

P = ParamSpec("P")
R = TypeVar("R")


class ToolExtension(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool = tool
        self.tool_func = self.tool.tool_func

        self.use_tool = self.use_tools
        self.extension_handlers.append("prefixes", ("tool_prefix", self._prefix))

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

    async def _prefix(self, prompt: "Prompt", settings: "Settings"):
        tool_judgement_request = ModelRequest(
            self.plugin_manager,
            parent_settings=self.settings,
            request_name="Tool Judgement",
        )
        tool_judgement_request.set_prompt("input", prompt.get("input"))
        tool_judgement_request.set_prompt("tools", self.tool.get_tool_list(tags=[f"agent-{ self.name }"]))
        tool_judgement_request.set_prompt(
            "instruct", "Judge if you need to use tool in {tools} to collect information for responding {input}?"
        )
        tool_judgement_request.set_prompt(
            "output",
            {
                "use_tool": (bool,),
                "tool_command": {
                    "purpose": (str, "Why and what result you want to use tool to collect?"),
                    "tool_name": (str, "Must in {tools.[].name}"),
                    "tool_kwargs": (dict, "kwargs dict as {tools.[].kwargs} of {tool_name}"),
                },
            },
        )
        tool_judgement_result = await tool_judgement_request.async_get_result()
        if tool_judgement_result["use_tool"] is True:
            tool_command = tool_judgement_result["tool_command"]
            prompt.set(
                "action_results",
                {
                    tool_command["purpose"]: await self.tool.async_call_tool(
                        tool_command["tool_name"],
                        tool_command["tool_kwargs"],
                    ),
                },
            )
