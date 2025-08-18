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
