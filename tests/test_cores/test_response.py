import pytest

import os
from dotenv import find_dotenv, load_dotenv

import agently

load_dotenv(find_dotenv())

from typing import TYPE_CHECKING, cast

from agently import Agently
from agently.core import ModelRequest
from agently.utils import SerializableRuntimeDataNamespace

if TYPE_CHECKING:
    from agently.builtins.plugins.ModelRequester.OpenAICompatible import ModelRequesterSettings


def test_model_request():
    Agently.set_settings("response.streaming_parse", True)
    Agently.set_settings("response.streaming_parse_path_style", "slash")
    Agently.set_debug_console("OFF")
    request = ModelRequest(
        Agently.plugin_manager,
        parent_settings=Agently.settings,
    )
    request_settings = cast(
        "ModelRequesterSettings",
        SerializableRuntimeDataNamespace(Agently.settings, "plugins.ModelRequester.OpenAICompatible"),
    )

    request_settings["base_url"] = os.environ["DEEPSEEK_BASE_URL"]
    request_settings["model"] = os.environ["DEEPSEEK_DEFAULT_MODEL"]
    request_settings["model_type"] = "chat"
    request_settings["auth"] = os.environ["DEEPSEEK_API_KEY"]
    request.set_prompt("input", "hello")
    request.set_prompt(
        "output",
        {
            "thinking": (str,),
            "reply": ([str],),
        },
    )
    response = request.get_response()
    results = []
    for parsed in response.get_generator(content="streaming_parse"):
        # print(parsed)
        results.append(parsed)
    assert results[0].value is not None
    assert len(results) > 0
