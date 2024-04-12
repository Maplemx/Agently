#ABC = Abstract Base Class
from abc import ABC, abstractmethod

class ToolABC(ABC):
    def __init__(self, tool_manager: object):
        self.tool_manager = tool_manager

    def export(self):
        return {
            "<tool_name>": {
                "desc": "<tool_desc>",
                "args": {
                    "<arg_1>": ("<arg_type>", "<arg_desc>"),
                },
                "func": callable,
            },
        }