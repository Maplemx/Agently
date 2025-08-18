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


from typing import (
    Any,
    Literal,
    Callable,
    Coroutine,
    TYPE_CHECKING,
    Protocol,
    TypeVar,
    ParamSpec,
)
from agently.types.plugins import AgentlyPlugin

if TYPE_CHECKING:
    from agently.utils import Settings
    from agently.types.data import KwargsType, ReturnType, MCPConfigs

P = ParamSpec("P")
R = TypeVar("R")


class ToolManager(AgentlyPlugin, Protocol):
    name: str
    settings: "Settings"
    DEFAULT_SETTINGS: dict[str, Any] = {}

    def __init__(
        self,
        settings: "Settings",
    ): ...

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    def register(
        self,
        *,
        name: str,
        desc: str | None,
        kwargs: "KwargsType | None",
        func: Callable,
        returns: "ReturnType | None" = None,
        tags: str | list[str] | None = None,
    ): ...

    def tag(self, tool_names: str | list[str], tags: str | list[str]): ...

    def tool_func(
        self,
        func: Callable[P, R],
    ) -> Callable[P, R]: ...

    def get_tool_info(self, tags: str | list[str] | None = None) -> dict[str, dict[str, Any]]: ...

    def get_tool_list(self, tags: str | list[str] | None = None) -> list[dict[str, Any]]: ...

    def get_tool_func(
        self,
        name: str,
        *,
        shift: Literal["sync", "async"] | None = None,
    ) -> Callable[..., Coroutine] | Callable[..., Any] | None: ...

    def call_tool(self, name: str, kwargs: dict[str, Any]) -> Any: ...

    async def async_call_tool(self, name: str, kwargs: dict[str, Any]) -> Any: ...

    async def async_use_mcp(self, transport: "MCPConfigs | str | Any", *, tags: str | list[str] | None = None): ...

    def use_mcp(self, transport: "MCPConfigs | str | Any", *, tags: str | list[str] | None = None): ...
