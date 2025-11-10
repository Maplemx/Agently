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

import yaml

from typing import (
    Any,
    List,
    Mapping,
    Sequence,
    Annotated,
    TYPE_CHECKING,
    get_origin,
    get_args,
    cast,
)
from pydantic import (
    PlainValidator,
    TypeAdapter,
    Field,
    create_model,
)

from agently.types.plugins import PromptGenerator
from agently.types.data import PromptModel, ChatMessageContent, TextMessageContent
from agently.utils import SettingsNamespace, DataFormatter

if TYPE_CHECKING:
    from pydantic import BaseModel
    from agently.core import Prompt
    from agently.utils import Settings


class AgentlyPromptGenerator(PromptGenerator):
    name = "AgentlyPromptGenerator"

    DEFAULT_SETTINGS = {}

    def __init__(
        self,
        prompt: "Prompt",
        settings: "Settings",
    ):
        from agently.base import event_center

        self.prompt = prompt
        self.settings = settings
        self.plugin_settings = SettingsNamespace(self.settings, f"plugins.PromptGenerator.{ self.name }")
        self._messenger = event_center.create_messenger(self.name)

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    def _check_prompt_all_empty(self, prompt_object: PromptModel):
        # If prompt is customized, skip the check
        if prompt_object.model_extra:
            return
        # Check standard prompt keys
        fields_to_check = ["input", "info", "instruct", "output", "attachment"]
        all_empty = all(getattr(prompt_object, field) in (None, "", [], {}) for field in fields_to_check)
        if all_empty:
            self._messenger.error(
                KeyError(
                    "Prompt requires at least one of 'input', 'info', 'instruct', 'output', 'attachment' or customize extra prompt keys to be provided."
                )
            )

    def _generate_json_output_prompt(
        self,
        output: Any,
        layer: int = 0,
    ) -> str:
        indent = "  " * layer
        next_indent = "  " * (layer + 1)

        if isinstance(output, dict):
            if not output:
                return "{}"
            lines = ["{"]
            items = list(output.items())
            for i, (key, value) in enumerate(items):
                value_str = self._generate_json_output_prompt(value, layer + 1)
                desc_str = ""
                if isinstance(value, tuple) and len(value) > 1:
                    desc_str = " //"
                    if len(value) >= 2 and value[1]:
                        desc_str += f" {value[1]}"
                comma = "," if i < len(items) - 1 else ""
                lines.append(f'{next_indent}"{key}": {value_str}{comma}{desc_str}')
            lines.append(f"{indent}}}")
            return "\n".join(lines)

        if isinstance(output, (list, set)):
            if not output:
                return "[]"
            lines = ["["]
            items = list(output)
            for i, item in enumerate(items):
                item_str = self._generate_json_output_prompt(item, layer + 1)
                desc_str = ""
                if isinstance(item, tuple) and len(item) > 1 and item[1]:
                    desc_str += f" // {item[1]}"
                if i < len(items):
                    lines.append(f"{next_indent}{item_str},{desc_str}")
            lines.append(f"{next_indent}...")
            lines.append(f"{indent}]")
            return "\n".join(lines)

        if isinstance(output, tuple) and len(output) >= 1:
            if isinstance(output[0], (dict, list, set)):
                return self._generate_json_output_prompt(output[0], layer + 1)
            return f"<{str(output[0])}>"

        if isinstance(output, type):
            return f"<{type(output).__name__}>"

        return f"<{str(output)}>"

    def _generate_yaml_prompt_list(self, title: str, prompt_part: Any) -> list[str]:
        sanitized_part = DataFormatter.sanitize(prompt_part)
        return [
            f"[{ title }]:",
            (
                str(sanitized_part)
                if isinstance(sanitized_part, (str, int, float, bool)) or sanitized_part is None
                else yaml.safe_dump(sanitized_part, allow_unicode=True)
            ),
            "",
        ]

    def _generate_main_prompt(self, prompt_object: PromptModel):
        prompt_title_mapping = cast(dict[str, str], self.settings.get("prompt.prompt_title_mapping", {}))
        prompt_text_list = []
        # tools
        if prompt_object.tools and isinstance(prompt_object.tools, list):
            prompt_text_list.append(f"[{ prompt_title_mapping.get('tools', 'TOOLS') }]:")
            for tool_info in prompt_object.tools:
                if isinstance(tool_info, dict):
                    prompt_text_list.append("[")
                    for key, value in tool_info.items():
                        if key in ("kwargs", "returns"):
                            prompt_text_list.append(
                                f"{ key }: {self._generate_json_output_prompt(DataFormatter.sanitize(value))}"
                            )
                        else:
                            prompt_text_list.append(f"{ key }: { value }")
                    prompt_text_list.append("]")

        # action_results
        if prompt_object.action_results:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'action_results',
                            'ACTION RESULTS',
                        )
                    ),
                    prompt_object.action_results,
                )
            )

        # info
        if prompt_object.info:
            prompt_text_list.append(f"[{ prompt_title_mapping.get('info', 'INFO') }]:")
            if isinstance(prompt_object.info, Mapping):
                for title, content in prompt_object.info.items():
                    prompt_text_list.append(f"- { title }: { DataFormatter.sanitize(content) }")
            elif isinstance(prompt_object.info, Sequence) and not isinstance(prompt_object.info, str):
                prompt_text_list.extend(
                    [f"- { DataFormatter.sanitize(info_line) }" for info_line in prompt_object.info]
                )
            else:
                prompt_text_list.append(DataFormatter.sanitize(prompt_object.info))
            prompt_text_list.append("")

        # extra
        if prompt_object.model_extra:
            for title, content in prompt_object.model_extra.items():
                prompt_text_list.extend(self._generate_yaml_prompt_list(title, content))

        # instruct
        if prompt_object.instruct:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'instruct',
                            'INSTRUCT',
                        )
                    ),
                    prompt_object.instruct,
                )
            )

        # examples
        if prompt_object.examples:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'examples',
                            'EXAMPLES',
                        )
                    ),
                    prompt_object.examples,
                )
            )

        # input
        if prompt_object.input:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'input',
                            'INPUT',
                        )
                    ),
                    prompt_object.input,
                )
            )

        # output
        if prompt_object.output:
            match prompt_object.output_format:
                case "json":
                    final_output_dict = {}
                    final_output_dict.update(prompt_object.output)
                    prompt_text_list.extend(
                        [
                            f"[{ prompt_title_mapping.get('output_requirement', 'OUTPUT REQUIREMENT') }]:",
                            "Data Format: JSON",
                            "Data Structure:",
                            self._generate_json_output_prompt(DataFormatter.sanitize(final_output_dict)),
                            "",
                        ]
                    )
                case "markdown":
                    prompt_text_list.extend(
                        [
                            f"[{ prompt_title_mapping.get('output_requirement', 'OUTPUT REQUIREMENT') }]:",
                            "Data Format: markdown text",
                        ]
                    )
                case "text":
                    pass

        prompt_text_list.append(
            f"[{ prompt_title_mapping.get('output', 'OUTPUT') }]:",
        )
        return prompt_text_list

    def _generate_yaml_prompt_message(
        self,
        role: str,
        prompt_part: Any,
        *,
        role_mapping: dict[str, str],
    ) -> dict[str, str]:
        role = str(role_mapping[role]) if role in role_mapping else role
        sanitized_part = DataFormatter.sanitize(prompt_part)
        return {
            "role": role,
            "content": (
                str(sanitized_part)
                if isinstance(sanitized_part, (str, int, float, bool)) or sanitized_part is None
                else yaml.safe_dump(sanitized_part, allow_unicode=True)
            ),
        }

    def to_prompt_object(self) -> PromptModel:
        prompt_object = PromptModel(**self.prompt)
        return prompt_object

    def to_text(
        self,
        *,
        role_mapping: dict[str, str] | None = None,
    ) -> str:
        prompt_object = self.to_prompt_object()
        self._check_prompt_all_empty(prompt_object)

        prompt_text_list = []

        merged_role_mapping = cast(dict[str, str], self.settings.get("prompt.role_mapping", {}))
        prompt_title_mapping = cast(dict[str, str], self.settings.get("prompt.prompt_title_mapping", {}))
        if not isinstance(merged_role_mapping, dict):
            merged_role_mapping = {}

        if isinstance(role_mapping, dict):
            merged_role_mapping.update(role_mapping)

        prompt_text_list.append(
            f"{ (merged_role_mapping['user'] if 'user' in merged_role_mapping else 'user').upper() }:"
        )

        # system & developer
        if prompt_object.system:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'system',
                            'SYSTEM',
                        )
                    ),
                    prompt_object.system,
                )
            )

        if prompt_object.developer:
            prompt_text_list.extend(
                self._generate_yaml_prompt_list(
                    str(
                        prompt_title_mapping.get(
                            'developer',
                            'DEVELOPER DIRECTIONS',
                        )
                    ),
                    prompt_object.developer,
                )
            )

        # chat_history
        if prompt_object.chat_history:
            chat_history_lines = [f"[{ prompt_title_mapping.get('chat_history', 'CHAT HISTORY') }]:"]
            content_adapter = TypeAdapter(ChatMessageContent)
            for message in prompt_object.chat_history:
                role = (
                    merged_role_mapping[message.role]
                    if message.role in merged_role_mapping
                    else (merged_role_mapping["_"] if "_" in merged_role_mapping else message.role)
                )
                content = message.content
                if isinstance(content, dict) and "type" in content:
                    content = [content]
                if isinstance(content, list):
                    content = [content_adapter.validate_python(message_content) for message_content in content]
                    for one_content in content:
                        if one_content.type == "text":
                            chat_history_lines.append(f"[{ role }]:{ str(one_content.text) }")
                        else:
                            self._messenger.warning(
                                f"Skipped content: unable to convert type '{one_content.type}' to text. "
                                f"Content: {one_content.model_dump()}",
                            )
                else:
                    chat_history_lines.append(f"[{ role }]:{ DataFormatter.sanitize(content) }")
            prompt_text_list.extend(chat_history_lines)
            prompt_text_list.append("")

        prompt_text_list.extend(self._generate_main_prompt(prompt_object))
        prompt_text_list.append(
            f"{ (merged_role_mapping['assistant'] if 'assistant' in merged_role_mapping else 'assistant').upper() }:"
        )

        return "\n".join(prompt_text_list)

    def to_messages(
        self,
        *,
        role_mapping: dict[str, str] | None = None,
        rich_content: bool | None = False,
        strict_role_orders: bool | None = True,
    ) -> list[dict[str, Any]]:
        prompt_object = self.to_prompt_object()
        self._check_prompt_all_empty(prompt_object)

        prompt_messages = []

        merged_role_mapping = cast(dict[str, str], self.settings.get("prompt.role_mapping", {}))
        prompt_title_mapping = cast(dict[str, str], self.settings.get("prompt.prompt_title_mapping", {}))

        if not isinstance(merged_role_mapping, dict):
            merged_role_mapping = {}

        if isinstance(role_mapping, dict):
            merged_role_mapping.update(role_mapping)

        # system & developer
        if prompt_object.system:
            prompt_messages.append(
                self._generate_yaml_prompt_message(
                    str(
                        prompt_title_mapping.get(
                            'system',
                            'SYSTEM',
                        )
                    ),
                    prompt_object.system,
                    role_mapping=merged_role_mapping,
                )
            )

        if prompt_object.developer:
            prompt_messages.append(
                self._generate_yaml_prompt_message(
                    str(
                        prompt_title_mapping.get(
                            'developer',
                            'DEVELOPER DIRECTIONS',
                        )
                    ),
                    prompt_object.developer,
                    role_mapping=merged_role_mapping,
                )
            )

        # chat_history
        if prompt_object.chat_history:
            chat_history = []
            content_adapter = TypeAdapter(ChatMessageContent)
            last_role = None
            for message in prompt_object.chat_history:
                role = (
                    merged_role_mapping[message.role]
                    if message.role in merged_role_mapping
                    else (merged_role_mapping["_"] if "_" in merged_role_mapping else message.role)
                )
                origin_content = message.content
                content = None
                if isinstance(origin_content, dict) and "type" in origin_content:
                    origin_content = [origin_content]
                elif not isinstance(origin_content, list):
                    origin_content = [{"type": "text", "text": str(origin_content)}]
                content = [
                    content_adapter.validate_python(message_content).model_dump() for message_content in origin_content
                ]
                # strict role orders
                if strict_role_orders:
                    if role == last_role:
                        chat_history[-1]["content"].extend(content)
                    else:
                        chat_history.append({"role": role, "content": content})
                else:
                    chat_history.append({"role": role, "content": content})
                # update last_role
                last_role = role
            # check first and last role in chat history
            if strict_role_orders:
                if chat_history[0]["role"] != "user":
                    chat_history.insert(
                        0,
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"[{ prompt_title_mapping.get('chat_history', 'CHAT HISTORY') }]",
                                }
                            ],
                        },
                    )
                if chat_history[-1]["role"] != "assistant":
                    chat_history.append(
                        {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "[User continue input]"}],
                        }
                    )

            # simplify rich content
            if rich_content is False:
                simplified_chat_history = []
                for message in chat_history:
                    origin_content = message["content"]
                    content = []
                    if isinstance(origin_content, str):
                        content.append(origin_content)
                    elif isinstance(origin_content, Sequence):
                        for one_content in origin_content:
                            if "type" in one_content and one_content["type"] == "text":
                                content.append(one_content["text"])
                            elif "type" in one_content:
                                self._messenger.warning(
                                    f"Skipped content: unable to convert type '{ one_content['type'] }' to chat message when `rich_content` == False. "
                                    f"Content: {one_content}",
                                )

                    content = "\n\n".join(content)
                    simplified_chat_history.append(
                        {
                            "role": message["role"],
                            "content": content,
                        }
                    )
                chat_history = simplified_chat_history.copy()

            prompt_messages.extend(chat_history)

        # special occasion: only input
        if (
            prompt_object.input
            and not prompt_object.tools
            and not prompt_object.action_results
            and not prompt_object.info
            and not prompt_object.instruct
            and not prompt_object.output
            and not prompt_object.model_extra
            and not prompt_object.attachment
        ):
            role = merged_role_mapping["user"] if "user" in merged_role_mapping else "user"
            prompt_messages.append({"role": role, "content": DataFormatter.sanitize(prompt_object.input)})
        # special occasion: only attachment
        elif (
            prompt_object.attachment
            and not prompt_object.input
            and not prompt_object.tools
            and not prompt_object.action_results
            and not prompt_object.info
            and not prompt_object.instruct
            and not prompt_object.output
            and not prompt_object.model_extra
        ):
            role = merged_role_mapping["user"] if "user" in merged_role_mapping else "user"
            if rich_content:
                prompt_messages.append(
                    {
                        "role": role,
                        "content": [content.model_dump() for content in prompt_object.attachment],
                    }
                )
            else:
                for one_content in prompt_object.attachment:
                    if one_content.type == "text" and isinstance(one_content, TextMessageContent):
                        prompt_messages.append(
                            {
                                "role": role,
                                "content": one_content.text,
                            }
                        )
                    else:
                        self._messenger.warning(
                            f"Skipped content: unable to put attachment content into prompt messages when `rich_content` == False\n"
                            f"Content: {str(one_content.model_dump())}"
                        )
        else:
            role = merged_role_mapping["user"] if "user" in merged_role_mapping else "user"
            # attachment message
            if rich_content:
                user_message_content = []
                # main prompt content (info, instruct, input, output)
                user_message_content.append(
                    {
                        "type": "text",
                        "text": "\n".join(self._generate_main_prompt(prompt_object)),
                    }
                )
                # extend attachment content
                if prompt_object.attachment:
                    user_message_content.extend([content.model_dump() for content in prompt_object.attachment])
                prompt_messages.append(
                    {
                        "role": role,
                        "content": user_message_content,
                    }
                )
            # simple message
            else:
                # main prompt content (info, instruct, input, output)
                user_message_content = self._generate_main_prompt(prompt_object)
                # extend attachment content
                if prompt_object.attachment:
                    for one_content in prompt_object.attachment:
                        if one_content.type == "text" and isinstance(one_content, TextMessageContent):
                            prompt_messages.append(
                                {
                                    "role": role,
                                    "content": one_content.text,
                                }
                            )
                        else:
                            self._messenger.warning(
                                f"Skipped content: unable to put attachment content into prompt messages when `rich_content` == False\n"
                                f"Content: {str(one_content.model_dump())}"
                            )
                prompt_messages.append({"role": role, "content": "\n".join(user_message_content)})

        return prompt_messages

    def _generate_output_model(self, name: str, schema: Mapping[str, Any] | Sequence[Any]) -> Any:
        fields = {}
        validators = {}

        def ensure_list_and_cast(v: Any, target_type: type):
            if not isinstance(v, list):
                v = [v]
            return [
                (target_type(item) if target_type is not Any and not isinstance(item, target_type) else item)
                for item in v
            ]

        if isinstance(schema, Mapping):
            for field_name, field_type_schema in schema.items():
                field_type = Any
                field_desc = None
                default_value = None
                if isinstance(field_type_schema, str):
                    field_desc = field_type_schema
                elif isinstance(field_type_schema, Mapping):
                    field_type = self._generate_output_model(f"{ name }_{ field_name.capitalize() }", field_type_schema)
                elif isinstance(field_type_schema, tuple):
                    value_type = field_type_schema[0] if len(field_type_schema) > 0 else Any
                    desc = field_type_schema[1] if len(field_type_schema) > 1 else ""
                    default_value = field_type_schema[2] if len(field_type_schema) > 2 else None
                    if isinstance(value_type, type) or get_origin(value_type) is not None:
                        field_type = value_type
                        field_desc = desc
                    else:
                        field_desc = f"type: { value_type }; desc: { desc }"
                elif isinstance(field_type_schema, Sequence):
                    field_type = self._generate_output_model(
                        f"{ name }_{ field_name.capitalize() }",
                        list(field_type_schema),
                    )
                elif isinstance(field_type_schema, type) or get_origin(field_type_schema) is not None:
                    field_type = field_type_schema | None
                else:
                    field_desc = str(field_type_schema)
                if get_origin(field_type) in (list, List):
                    elem_type = cast(
                        type,
                        get_args(field_type)[0] if get_args(field_type) else Any,
                    )

                    fields.update(
                        {
                            field_name: (
                                Annotated[
                                    field_type,
                                    PlainValidator(lambda value: ensure_list_and_cast(value, elem_type)),
                                ],
                                Field(default_value, description=field_desc),
                            )
                        }
                    )
                else:
                    fields.update(
                        {
                            field_name: (
                                field_type,
                                Field(default_value, description=field_desc),
                            )
                        }
                    )

            return create_model(name, **fields, **validators)
        else:
            item_type = Any
            if len(schema) > 0:
                origin_item = schema[0]
                if isinstance(origin_item, str):
                    item_type = Any
                elif isinstance(origin_item, Mapping):
                    item_type = self._generate_output_model(f"{ name }_List", origin_item)
                elif isinstance(origin_item, tuple):
                    value_type = origin_item[0] if len(origin_item) > 0 else Any
                    desc = origin_item[1] if len(origin_item) > 1 else ""
                    if isinstance(value_type, type) or get_origin(value_type) is not None:
                        item_type = value_type
                    else:
                        item_type = Any
                elif isinstance(origin_item, Sequence):
                    item_type = self._generate_output_model(f"{ name }_List", list(origin_item))
                elif isinstance(origin_item, type) or get_origin(origin_item) is not None:
                    item_type = origin_item
                else:
                    item_type = Any
            else:
                item_type = Any

            return Annotated[
                list[item_type | None] | None,
                PlainValidator(lambda v: ensure_list_and_cast(v, cast(type, item_type))),
            ]

    def to_output_model(self) -> type["BaseModel"]:
        prompt_object = self.to_prompt_object()
        output_prompt = prompt_object.output

        if not isinstance(output_prompt, (Mapping, Sequence)) or isinstance(output_prompt, str):
            self._messenger.error(
                TypeError(f"Unable to generator output model because the output is not a structure data.")
            )

        if isinstance(output_prompt, Mapping):
            return self._generate_output_model(
                "AgentlyOutput",
                DataFormatter.sanitize(output_prompt, remain_type=True),
            )
        else:
            return self._generate_output_model(
                "AgentlyOutput",
                {"list": DataFormatter.sanitize(output_prompt, remain_type=True)},
            )
