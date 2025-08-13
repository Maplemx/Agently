from typing import Literal, Callable

from agently.utils import RuntimeData


class ExtensionHandlers(RuntimeData):
    def append(self, key: Literal["prefixes", "suffixes"] | str, value: tuple[str, Callable]):
        super().append(key, value)
