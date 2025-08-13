import pytest

import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from typing import cast
from agently import Agently
from agently.utils import SerializableRuntimeDataNamespace
from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
    OpenAICompatible,
    ModelRequesterSettings,
)


@pytest.mark.asyncio
async def test_main():
    request_settings = cast(
        ModelRequesterSettings,
        SerializableRuntimeDataNamespace(Agently.settings, "plugins.ModelRequester.OpenAICompatible"),
    )
    # request_settings["base_url"] = os.environ["DEEPSEEK_BASE_URL"]
    # request_settings["model"] = os.environ["DEEPSEEK_DEFAULT_MODEL"]
    # request_settings["model_type"] = "chat"
    # request_settings["auth"] = os.environ["DEEPSEEK_API_KEY"]
    prompt = Agently.create_prompt()

    openai_compatible = OpenAICompatible(
        prompt,
        Agently.settings,
    )

    try:
        prompt.set("input", "ni hao")
        request_data = openai_compatible.generate_request_data()
        request_response = openai_compatible.request_model(request_data)
        response = openai_compatible.broadcast_response(request_response)
        async for event, message in response:
            print(event, message)
    except Exception as e:
        # in case HTTP 401 Unauthorized when provide invalid API key
        # ERROR logging will be shown in console
        raise e
