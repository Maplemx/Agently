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

from typing import TYPE_CHECKING, Any
from typing_extensions import TypedDict

from pydantic import BaseModel, field_validator, model_validator


class AgentlyRequestDataDict(TypedDict):
    client_options: dict[str, Any]
    headers: dict[str, str]
    data: dict[str, Any]
    request_options: dict[str, Any]
    request_url: str


class AgentlyRequestData(BaseModel):
    client_options: dict[str, Any]
    headers: dict[str, str]
    data: dict[str, Any]
    request_options: dict[str, Any]
    request_url: str
    stream: bool | None = None

    @field_validator("headers")
    @classmethod
    def fix_headers(cls, value: dict[str, str]):
        value.update({"Connection": "close"})
        return value

    @model_validator(mode="after")
    def fix_request_options(self):
        if "stream" not in self.request_options or self.request_options["stream"] is None:
            self.request_options["stream"] = True
            self.stream = True
        else:
            self.request_options["stream"] = bool(self.request_options["stream"])
            self.stream = self.request_options["stream"]
        return self

    @field_validator("stream")
    @classmethod
    def fix_stream(cls, _: bool | None):
        if cls.request_options["stream"] == True:
            return True
        else:
            return False
