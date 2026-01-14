from typing import Protocol

from agently.types.data import ToolInfo


class BuiltInTool(Protocol):
    tool_info_list: list[ToolInfo]
