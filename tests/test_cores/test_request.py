import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

import pytest
import asyncio
from asyncio import Task
from contextlib import suppress
from typing import AsyncGenerator, cast

from agently import Agently
from agently.core.ModelRequest import ModelRequest
from agently.utils import SerializableStateDataNamespace
from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
    ModelRequesterSettings,
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def configure_ollama(request_settings: ModelRequesterSettings):
    request_settings["base_url"] = OLLAMA_BASE_URL
    request_settings["model"] = OLLAMA_MODEL
    request_settings["model_type"] = "chat"
    request_settings["auth"] = None


@pytest.mark.asyncio
async def test_single_request():
    request = ModelRequest(
        Agently.plugin_manager,
        parent_settings=Agently.settings,
    )
    request_settings = cast(
        ModelRequesterSettings,
        SerializableStateDataNamespace(
            Agently.settings,
            "plugins.ModelRequester.OpenAICompatible",
        ),
    )
    configure_ollama(request_settings)

    request.prompt["input"] = "你是谁"

    async for delta in request.get_async_generator(type="delta"):
        print(delta)


@pytest.mark.asyncio
async def test_multiple_responses_independent_consumption():
    request = ModelRequest(
        Agently.plugin_manager,
        parent_settings=Agently.settings,
    )
    request_settings = cast(
        ModelRequesterSettings,
        SerializableStateDataNamespace(
            Agently.settings,
            "plugins.ModelRequester.OpenAICompatible",
        ),
    )

    configure_ollama(request_settings)

    prompts = ["Hello, how are you?", "Hello again!", "Who are you?"]
    responses = []

    for prompt_text in prompts:
        request.prompt.set("input", prompt_text)
        request.prompt.set(
            "output",
            {
                "thinking": (str,),
                "reply": ([str],),
            },
        )
        responses.append(request.get_response())

    async def consume_response(response):
        async for data in response.get_async_generator(content="delta"):
            print(f"[{id(response)}]: {data}")

    tasks: list[Task] = [asyncio.create_task(consume_response(resp)) for resp in responses]

    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
