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
    Mapping,
    Sequence,
    Annotated,
)
from typing_extensions import TypedDict, NotRequired
from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
    PlainValidator,
    Field,
    TypeAdapter,
)


class AttachmentMessageContent(BaseModel):
    type: str

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def suffix(self) -> "AttachmentMessageContent":
        if not hasattr(self, self.type):
            setattr(self, self.type, None)
        return self


class TextMessageContent(BaseModel):
    type: Literal["text"]
    text: str


ChatMessageContent = TextMessageContent | AttachmentMessageContent

ChatMessageContentAdapter = TypeAdapter(Annotated[ChatMessageContent, Field(union_mode="left_to_right")])


class ChatMessage(BaseModel):
    role: str = "user"
    content: str | list[dict[str, Any] | ChatMessageContent]

    model_config = ConfigDict(extra="allow")


def validate_chat_history(chat_history) -> list[ChatMessage]:
    if chat_history is None:
        return []
    if isinstance(chat_history, dict):
        return [ChatMessage(**chat_history)]
    if isinstance(chat_history, list):
        new_chat_history = []
        for message in chat_history:
            if isinstance(message, ChatMessage):
                new_chat_history.append(message)
            elif isinstance(message, dict):
                new_chat_history.append(ChatMessage(**message))
            else:
                new_chat_history.append(ChatMessage(content=str(message)))
        return new_chat_history
    return [ChatMessage(content=str(chat_history))]


def validate_attachment(attachment) -> list[ChatMessageContent]:
    if attachment is None:
        return []
    if isinstance(attachment, dict):
        return [ChatMessageContentAdapter.validate_python(attachment)]
    if isinstance(attachment, list):
        attachment_contents = []
        for content in attachment:
            if isinstance(content, ChatMessageContent):
                attachment_contents.append(content)
            elif isinstance(content, dict):
                attachment_contents.append(ChatMessageContentAdapter.validate_python(content))
            else:
                attachment_contents.append(
                    ChatMessageContentAdapter.validate_python(
                        {
                            "type": "text",
                            "text": str(content),
                        }
                    )
                )
        return attachment_contents
    return [
        ChatMessageContentAdapter.validate_python(
            {
                "type": "text",
                "text": str(attachment),
            }
        )
    ]


OutputFormat = Literal["markdown", "text", "json"]
PromptStandardSlot = Literal[
    "system",
    "developer",
    "chat_history",
    "info",
    "tools",
    "action_results",
    "instruct",
    "examples",
    "input",
    "attachment",
    "output",
    "output_format",
    "options",
]


class ToolMeta(TypedDict):
    name: str
    desc: str
    kwargs: dict[str, Any]
    returns: NotRequired[Any]


class PromptModel(BaseModel):
    system: Any = None
    developer: Any = None
    chat_history: Annotated[list[ChatMessage], PlainValidator(validate_chat_history)] = []
    info: Any = None
    tools: list[ToolMeta] | None = None
    action_results: Any = None
    instruct: Any = None
    examples: Any = None
    input: Any = None
    attachment: Annotated[list[ChatMessageContent], PlainValidator(validate_attachment)] = []
    output: Any = None
    output_format: OutputFormat | Any = None
    options: dict[str, Any] = {}

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def set_output_format(self) -> "PromptModel":
        if self.output_format is None:
            if not isinstance(self.output, str) and isinstance(self.output, (Mapping, Sequence)):
                self.output_format = "json"
            elif isinstance(self.output, type):
                if self.output == str:
                    self.output = None
                    self.output_format = "markdown"
                else:
                    self.output = {"value": (self.output,), "reply": (str, "Reply according the result value")}
                    self.output_format = "json"
            else:
                self.output_format = "markdown"
        if not isinstance(self.output_format, str):
            self.output_format = str(self.output_format)
        return self
