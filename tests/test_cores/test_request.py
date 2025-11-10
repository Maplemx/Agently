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
from agently.utils import SerializableRuntimeDataNamespace
from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
    ModelRequesterSettings,
)


@pytest.mark.asyncio
async def test_single_request():
    request = ModelRequest(
        Agently.plugin_manager,
        parent_settings=Agently.settings,
    )
    request_settings = cast(
        ModelRequesterSettings,
        SerializableRuntimeDataNamespace(
            Agently.settings,
            "plugins.ModelRequester.OpenAICompatible",
        ),
    )
    request_settings["base_url"] = os.environ["DEEPSEEK_BASE_URL"]
    request_settings["model"] = os.environ["DEEPSEEK_DEFAULT_MODEL"]
    request_settings["model_type"] = "chat"
    request_settings["auth"] = os.environ["DEEPSEEK_API_KEY"]

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
        SerializableRuntimeDataNamespace(
            Agently.settings,
            "plugins.ModelRequester.OpenAICompatible",
        ),
    )

    request_settings["base_url"] = os.environ["DEEPSEEK_BASE_URL"]
    request_settings["model"] = os.environ["DEEPSEEK_DEFAULT_MODEL"]
    request_settings["model_type"] = "chat"
    request_settings["auth"] = os.environ["DEEPSEEK_API_KEY"]

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
