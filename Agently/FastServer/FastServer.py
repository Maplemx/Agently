from typing import Union, Literal
from Agently.Agent import Agent
from Agently.Workflow import Workflow

class FastServer:
    #def __init__(self, type: Literal["mcp", "websocket", "sse", "http"]):
    def __init__(self, type: Literal["mcp"]):
        if type == "mcp":
            from .builtins import MCPServerHandler as ServerHandler
        elif type == "websocket":
            from .builtins import WebSocketServerHandler as ServerHandler
        elif type == "sse":
            from .builtins import SSEServerHandler as ServerHandler
        elif type == "http":
            from .builtins import HTTPServerHandler as ServerHandler
        else:
            raise TypeError(f"[Agently FastServer] Can not support type '{ type }.'")
        self._server_handler = ServerHandler()
        self.serve = self._server_handler.serve