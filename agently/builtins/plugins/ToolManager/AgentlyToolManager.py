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


import inspect

from typing import (
    Any,
    Literal,
    Callable,
    TYPE_CHECKING,
    Coroutine,
    Annotated,
    TypeVar,
    ParamSpec,
    get_origin,
    get_args,
    get_type_hints,
)
from agently.types.plugins import ToolManager

from agently.utils import (
    SettingsNamespace,
    DataFormatter,
    FunctionShifter,
    LazyImport,
)

if TYPE_CHECKING:
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType, MCPConfigs

P = ParamSpec("P")
R = TypeVar("R")


class AgentlyToolManager(ToolManager):
    name = "AgentlyToolManager"

    DEFAULT_SETTINGS = {}

    def __init__(self, settings: "Settings"):
        from agently.base import event_center

        self.settings = settings
        self.plugin_settings = SettingsNamespace(self.settings, f"plugins.ToolManager.{ self.name }")
        self._messenger = event_center.create_messenger(self.name)

        self.tool_funcs: dict[str, Callable] = {}
        self.tool_info: dict[str, dict[str, Any]] = {}
        self.tag_mappings: dict[str, set[str]] = {}

        self.use_mcp = FunctionShifter.syncify(self.async_use_mcp)

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    def register(
        self,
        *,
        name: str,
        desc: str | None,
        kwargs: "KwargsType | None",
        func: Callable[..., Any],
        returns: "ReturnType | None" = None,
        tags: str | list[str] | None = None,
    ):
        self.tool_funcs.update({name: func})
        self.tool_info.update(
            {
                name: {
                    "name": name,
                    "desc": desc if desc is not None else "",
                    "kwargs": kwargs if kwargs is not None else {},
                }
            }
        )
        if returns is not None:
            self.tool_info[name].update({"returns": returns})
        if tags is None:
            tags = []
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            if tag not in self.tag_mappings:
                self.tag_mappings.update({tag: set()})
            self.tag_mappings[tag].add(name)

    def tag(self, tool_names: str | list[str], tags: str | list[str]):
        if isinstance(tool_names, str):
            tool_names = [tool_names]
        if isinstance(tags, str):
            tags = [tags]

        for tool_name in tool_names:
            if tool_name in self.tool_info:
                for tag in tags:
                    if tag not in self.tag_mappings:
                        self.tag_mappings.update({tag: set()})
                    self.tag_mappings[tag].add(tool_name)
            else:
                self._messenger.error(f"Cannot find tool named '{ tool_name }'")

    def tool_func(self, func: Callable[P, R]) -> Callable[P, R]:
        tool_name = func.__name__
        desc = inspect.getdoc(func) or func.__name__
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        returns = None
        if "return" in type_hints:
            returns = DataFormatter.sanitize(type_hints["return"], remain_type=True)
        kwargs_signature = {}
        for param_name, param in signature.parameters.items():
            annotated_type = param.annotation
            if get_origin(annotated_type) is Annotated:
                base_type, *annotations = get_args(annotated_type)
            else:
                base_type = annotated_type
                annotations = []
            if param.default != inspect.Parameter.empty:
                annotations.append(f"Default: { param.default }")
            kwargs_signature.update({param_name: (base_type, ";".join(annotations))})
        self.register(
            name=tool_name,
            desc=desc,
            kwargs=kwargs_signature,
            func=func,
            returns=returns,
        )
        return func

    def get_tool_info(self, tags: str | list[str] | None = None) -> dict[str, dict[str, Any]]:
        if tags is None:
            return self.tool_info
        if isinstance(tags, str):
            tags = [tags]
        tool_info: dict[str, dict[str, Any]] = {}
        for tag in tags:
            if tag in self.tag_mappings:
                for name in self.tag_mappings[tag]:
                    if name not in tool_info:
                        tool_info.update({name: self.tool_info[name]})
        return tool_info

    def get_tool_list(self, tags: str | list[str] | None = None) -> list[dict[str, Any]]:
        tool_info = self.get_tool_info(tags)
        return list(tool_info.values())

    def get_tool_func(
        self,
        name: str,
        *,
        shift: Literal["sync", "async"] | None = None,
    ) -> Callable[..., Coroutine] | Callable[..., Any] | None:
        tool_func = self.tool_funcs[name] if name in self.tool_funcs else None
        if tool_func is None:
            return None
        match shift:
            case "sync":
                return FunctionShifter.syncify(tool_func)
            case "async":
                return FunctionShifter.asyncify(tool_func)
            case None:
                return tool_func

    def call_tool(self, name: str, kwargs: dict[str, Any]) -> Any:
        func = self.get_tool_func(name)
        if func is None:
            return f"Can not find tool named '{ name }'"
        func = FunctionShifter.syncify(func)
        try:
            return func(**kwargs)
        except Exception as e:
            return f"Error: { e }"

    async def async_call_tool(self, name: str, kwargs: dict[str, Any]) -> Any:
        func = self.get_tool_func(name)
        if func is None:
            return f"Can not find tool named '{ name }'"
        func = FunctionShifter.asyncify(func)
        try:
            return await func(**kwargs)
        except Exception as e:
            return f"Error: { e }"

    def _mcp_tool_func(
        self,
        mcp_tool_name: str,
        transport: "MCPConfigs | str | Any",
    ):
        async def _call_mcp_tool(**kwargs):
            from fastmcp import Client

            async with Client(transport) as client:  # type: ignore
                mcp_result = await client.call_tool(
                    name=mcp_tool_name,
                    arguments=kwargs,
                    raise_on_error=False,
                )
                if mcp_result.is_error:
                    return {"error": mcp_result.content[0].text}  # type: ignore
                else:
                    return mcp_result.structured_content

        return _call_mcp_tool

    async def async_use_mcp(
        self,
        transport: "MCPConfigs | str | Any",
        *,
        tags: str | list[str] | None = None,
    ):
        LazyImport.import_package("fastmcp", version_constraint=">=2.10")
        from fastmcp import Client

        if tags is None:
            tags = []
        if isinstance(tags, str):
            tags = [tags]

        async with Client(transport) as client:  # type: ignore
            tool_list = await client.list_tools()
            for tool in tool_list:
                tool_tags = []
                if hasattr(tool, "_meta") and tool._meta:  # type: ignore
                    tool_tags = tool._meta.get("_fastmcp", {}).get("tags", [])  # type: ignore
                tool_tags.extend(tags)
                self.register(
                    name=tool.name,
                    desc=tool.description,
                    kwargs=DataFormatter.from_schema_to_kwargs_format(tool.inputSchema),
                    returns=DataFormatter.from_schema_to_kwargs_format(tool.outputSchema),
                    func=self._mcp_tool_func(tool.name, transport),
                    tags=tool_tags,
                )
