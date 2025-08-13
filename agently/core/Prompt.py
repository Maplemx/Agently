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

from typing import Any, Literal, TYPE_CHECKING, cast, overload

from agently.utils import RuntimeData, Settings

if TYPE_CHECKING:
    from agently.types.data.prompt import ChatMessage, PromptStandardSlot
    from agently.types.plugins import PromptGenerator
    from agently.core import PluginManager


class Prompt(RuntimeData):
    """
    Represents a hierarchical, structured prompt container in the Agently framework.

    The `Prompt` class is designed to manage, organize, and transform prompt data for various
    components within the Agently framework. Prompts can be composed and inherited, allowing
    complex prompt structures to be built from simpler ones, supporting multi-level prompt
    composition for different agents, tools, or workflow steps.

    Core responsibilities:
    - Inherit and manage prompt data using a tree-like structure, supporting parent-child relationships.
    - Enforce and organize prompt content according to a unified set of standard slots
      (see `PromptModel` in `prompt.py`), such as `input`, `info`, `instruct`, `output`, etc.
    - Integrate with the plugin system to allow flexible prompt formatting and validation logic.
    - Provide unified methods for converting prompt data into:
        * Plain text (`to_text`) and message list (`to_messages`) formats, following Agently's internal standards,
          not tied to any specific LLM API. (If LLM APIs require further adaptation, this is handled elsewhere.)
        * A strongly-typed Pydantic prompt model (`to_prompt_model`) for internal validation, normalization,
          and value correction.
        * A dynamic Pydantic output model (`to_output_model`) for validating and parsing model outputs
          according to the prompt's output requirements.

    Usage:
    - Used throughout the framework to represent prompts for agents, tools, or other components.
    - Supports prompt inheritance and composition for complex workflows.
    - Ensures prompt data is always accessible in standardized, validated, and convertible forms.

    Args:
        plugin_manager (PluginManager): The plugin manager for loading prompt generator plugins.
        parent_settings (SerializableRuntimeData): Parent settings for prompt configuration.
        prompt_dict (dict[str, Any] | None): Initial prompt data.
        parent_prompt (Prompt | None): Optional parent prompt for data inheritance.
        name (str | None): Optional name for the prompt instance.

    Attributes:
        settings (SerializableRuntimeData): Prompt-specific settings, inheriting from parent settings.
        prompt_generator (PromptGenerator): The active prompt generator plugin instance.
        to_text (Callable): Convert prompt data to plain text (PromptGenerator plugin provide convert standard).
        to_messages (Callable): Convert prompt data to message list (PromptGenerator plugin provide convert standard).
        to_prompt_model (Callable): Convert prompt data to a strongly-typed Pydantic model.
        to_output_model (Callable): Dynamically generate a Pydantic model for output validation.
    """

    def __init__(
        self,
        plugin_manager: "PluginManager",
        parent_settings: Settings,
        *,
        prompt_dict: dict[str, Any] | None = None,
        parent_prompt: "Prompt | None" = None,
        name: str | None = None,
    ):
        super().__init__(prompt_dict, parent=parent_prompt, name=name)
        self.settings = Settings(
            name="Prompt-Settings",
            parent=parent_settings,
        )
        PromptGeneratorPlugin = cast(
            type["PromptGenerator"],
            plugin_manager.get_plugin(
                "PromptGenerator",
                str(self.settings["plugins.PromptGenerator.activate"]),
            ),
        )
        self.prompt_generator = PromptGeneratorPlugin(self, self.settings)
        self.to_text = self.prompt_generator.to_text
        self.to_messages = self.prompt_generator.to_messages
        self.to_prompt_object = self.prompt_generator.to_prompt_object
        self.to_output_model = self.prompt_generator.to_output_model

    @overload
    def set(
        self, key: Literal["chat_history"], value: "dict[str, str | dict[str, Any]] | list[ChatMessage] | ChatMessage"
    ): ...

    @overload
    def set(self, key: "PromptStandardSlot | str", value: Any): ...

    def set(self, key: "PromptStandardSlot | str", value: Any):
        super().set(key, value)

    def update(self, new: "dict[PromptStandardSlot | str, Any]"):
        super().update(new)

    def append(self, key: "PromptStandardSlot | str", value: Any):
        super().append(key, value)

    def get(self, key: "PromptStandardSlot | None" = None, default: Any | None = None, inherit: bool = True):
        return super().get(key, default=default, inherit=inherit)
