from typing import Literal, Callable, TypeAlias
from typing_extensions import TypedDict, NotRequired
from pydantic import AnyUrl
from httpx import Auth, AsyncClient

ArgumentDesc: TypeAlias = type | str | tuple[str | type, str]
KwargsType: TypeAlias = dict[str, ArgumentDesc]
ReturnType: TypeAlias = KwargsType | ArgumentDesc | dict[str, "ReturnType"] | list["ReturnType"]


class MCPConfig(TypedDict):
    type: Literal["sse", "http", "stdio"]
    command: NotRequired[str]
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]
    cwd: NotRequired[str]
    keep_alive: NotRequired[bool]
    timeout: NotRequired[int]
    url: NotRequired[str | AnyUrl]
    headers: NotRequired[dict[str, str]]
    auth: NotRequired[Auth | str]
    sse_read_timeout: NotRequired[float | int]
    httpx_client_factory: NotRequired[Callable[[], AsyncClient]]


class MCPConfigs(TypedDict):
    mcpServers: dict[str, MCPConfig]
