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

from typing import Any, Protocol, AsyncGenerator, TYPE_CHECKING
from .base import AgentlyPlugin

if TYPE_CHECKING:
    from agently.core import Prompt
    from agently.utils import Settings
    from agently.types.data import AgentlyResponseGenerator, AgentlyRequestData


class ModelRequester(AgentlyPlugin, Protocol):
    """
    **[Agently Plugin] Model Requester**

    The ModelRequester plugin is responsible for bridging standardized prompt data with model APIs,
    including request data generation, model invocation, and response streaming/broadcasting.

    Core functionalities include:
    - Generate request data adapted to the target model API based on the prompt and plugin settings.
    - Asynchronously send requests to the model, supporting both streaming and non-streaming responses.
    - Process and broadcast model responses, standardizing output for downstream plugin chains.

    This plugin standardizes the model request workflow, decouples prompt structure from model API details,
    and improves framework flexibility and extensibility.

    Main methods:
    - `generate_request_data`: Generate request data for the model API based on prompt and settings.
    - `request_model`: Send the model request and return an async generator for streaming responses.
    - `broadcast_response`: Process and broadcast the response stream in a standardized format.

    Recommended usage:
    - Plugin developers can inherit from this protocol to implement custom model request logic.
    - Framework users can call different models via a unified interface, abstracting away API differences.
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
        Initialize the ModelRequester plugin.

        Args:
            prompt (Prompt): The associated Prompt instance.
            settings (Settings): Plugin settings, supporting hierarchical inheritance.
        """
        ...

    @staticmethod
    def _on_register(): ...

    @staticmethod
    def _on_unregister(): ...

    def generate_request_data(self) -> "AgentlyRequestData":
        """
        Generate request data required by the model API.

        Returns:
            AgentlyRequestData: Agently standardized request data adapted to the target model API.
        """
        ...

    def request_model(self, request_data: "AgentlyRequestData") -> AsyncGenerator[tuple[str, Any], None]:
        """
        Send the model request and return an async generator for streaming responses.

        Args:
            request_data (SerializableData): The generated request data.

        Returns:
            AsyncGenerator: The model response stream, format depends on implementation.
        """
        ...

    def broadcast_response(self, response_generator: AsyncGenerator) -> "AgentlyResponseGenerator":
        """
        Process and broadcast the model response stream in a standardized format.

        Args:
            response_generator (AsyncGenerator): The model response stream.

        Returns:
            AsyncGenerator[AgentlyModelResponseMessage, None]: Standardized response message stream.
        """
        ...
