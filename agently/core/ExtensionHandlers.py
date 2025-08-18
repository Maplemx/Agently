from typing import Any, Literal, Callable, TYPE_CHECKING, overload

from agently.utils import RuntimeData

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.utils import Settings
    from agently.types.data import AgentlyModelResponseEvent, AgentlyModelResult


class ExtensionHandlers(RuntimeData):
    @overload
    def append(self, key: Literal["prefixes"] | str, value: "Callable[[Prompt, Settings], Any]"): ...
    @overload
    def append(
        self,
        key: Literal["base_suffixes"],
        value: "Callable[[AgentlyModelResult], Any]",
    ): ...
    @overload
    def append(
        self,
        key: Literal["broadcast_suffixes"],
        value: "Callable[[AgentlyModelResponseEvent, Any, AgentlyModelResult], Any]",
        *,
        event: "AgentlyModelResponseEvent",
    ): ...
    def append(
        self,
        key: Literal["prefixes", "base_suffixes", "broadcast_suffixes"] | str,
        value: Callable,
        *,
        event: str | None = None,
    ):
        match key:
            case "broadcast_suffixes":
                super().append(f"{ key }.{ event }", value)
            case _:
                super().append(key, value)
