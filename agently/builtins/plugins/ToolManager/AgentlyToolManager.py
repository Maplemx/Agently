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

from agently.utils import SettingsNamespace, DataFormatter, FunctionShifter

if TYPE_CHECKING:
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType

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
        desc: str,
        kwargs: "KwargsType",
        func: Callable[..., Any],
        returns: "ReturnType | None" = None,
        tags: str | list[str] | None = None,
    ):
        self.tool_funcs.update({name: func})
        self.tool_info.update(
            {
                name: {
                    "name": name,
                    "desc": desc,
                    "kwargs": kwargs,
                }
            }
        )
        if returns is not None:
            self.tool_info[name].update({"return": returns})
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
        return func(**kwargs)

    async def async_call_tool(self, name: str, kwargs: dict[str, Any]) -> Any:
        func = self.get_tool_func(name)
        if func is None:
            return f"Can not find tool named '{ name }'"
        func = FunctionShifter.asyncify(func)
        return await func(**kwargs)
