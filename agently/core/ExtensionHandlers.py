from typing import Any, Literal, Callable, TYPE_CHECKING, overload

from agently.utils import RuntimeData

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.utils import Settings
    from agently.types.data import AgentlyModelResponseEvent


class ExtensionHandlers(RuntimeData):
    @overload
    def append(self, key: Literal["prefixes"] | str, value: "Callable[[Prompt, Settings], Any]"): ...
    @overload
    def append(
        self,
        key: Literal["suffixes"] | str,
        value: "Callable[[AgentlyModelResponseEvent, Any], Any]",
    ): ...
    def append(self, key: Literal["prefixes", "suffixes"] | str, value: Callable):
        super().append(key, value)
