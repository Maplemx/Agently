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

from typing import Any, Protocol, TYPE_CHECKING
from .base import AgentlyPlugin

if TYPE_CHECKING:
    from agently.types.data import PromptModel
    from agently.core import Prompt
    from agently.utils import Settings
    from pydantic import BaseModel


class PromptGenerator(AgentlyPlugin, Protocol):
    """
    **[Agently Plugin] Prompt Generator**

    The `PromptGenerator` plugin defines a unified interface for converting structured prompt data into various representations compatible with different LLM APIs or use cases.

    Main responsibilities:
    - Convert structured data into plain text for text completion models.
    - Convert structured data into OpenAI-style message lists for chat models.
    - Convert structured data into a validated `PromptModel`.
    - Dynamically generate a Pydantic `BaseModel` for output validation, based on the prompt’s `output` or `output_format`.

    Benefits:
    - Standardizes prompt formatting across different workflows.
    - Decouples template logic from models.
    - Improves consistency and reusability.

    Usage:
    - Plugin developers should inherit from this protocol to implement custom logic.
    - Framework users can use this interface to support different model types and output formats.
    """

    name: str
    prompt: "Prompt"
    settings: "Settings"
    DEFAULT_SETTINGS: dict[str, Any] = {}

    def __init__(
        self,
        prompt: "Prompt",
        settings: "Settings",
    ):
        """
        Initialize the prompt generator plugin.

        Args:
            prompt (Prompt):
                The associated Prompt instance.
            settings (Settings):
                Settings inherit from upper instances.
        """
        ...

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    def to_text(self, *args, **kwargs) -> str:
        """
        Convert the structured prompt data into a plain text string.

        Typically used for text completion models that accept plain text input.

        Returns:
            str: The formatted prompt as a plain text string.
        """
        ...

    def to_messages(
        self,
        *args,
        rich_content: bool | None = False,
        strict_role_orders: bool | None = True,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Convert the structured prompt data into an OpenAI-style message list.

        Typically used for chat models that expect a list of role-content dictionaries.

        Args:
            rich_content (bool | None): If True, messages can include rich content such as image URLs.
                Example:
                { "role": "user", "content": [
                    { "type": "text", "text": "hello" },
                    { "type": "image_url", "image_url": "http://example.com" }
                ] }

        Returns:
            list[dict[str, Any]]: A message list in the format [{'role': ..., 'content': ...}, ...].
        """
        ...

    def to_prompt_object(self, *args, **kwargs) -> "PromptModel":
        """
        Convert the prompt into a standardized `PromptModel`.

        This includes field normalization, auto-completion of missing fields, and structural validation.

        Returns:
            PromptModel: A validated, structured prompt data model.
        """
        ...

    def to_output_model(self, *args, **kwargs) -> type["BaseModel"]:
        """
        Dynamically generate a Pydantic `BaseModel` for output validation, based on `prompt.output`.

        Useful for validating and parsing structured LLM responses (e.g., JSON or dictionary-like formats).

        Returns:
            type[BaseModel]: A generated Pydantic model for validating the output.
            - For dict outputs: use `BaseModel(**output_result)` to validate.
            - For list outputs: use `BaseModel(list=output_result)` to validate.
        """
        ...
