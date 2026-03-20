import pytest

import os
from dotenv import find_dotenv, load_dotenv

import agently

load_dotenv(find_dotenv())

from typing import TYPE_CHECKING, cast

from agently import Agently
from agently.core import ModelRequest
from agently.utils import SerializableStateDataNamespace

if TYPE_CHECKING:
    from agently.builtins.plugins.ModelRequester.OpenAICompatible import ModelRequesterSettings

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def configure_ollama(request_settings: "ModelRequesterSettings"):
    request_settings["base_url"] = OLLAMA_BASE_URL
    request_settings["model"] = OLLAMA_MODEL
    request_settings["model_type"] = "chat"
    request_settings["auth"] = None


def test_model_request():
    Agently.set_settings("response.streaming_parse", True)
    Agently.set_settings("response.streaming_parse_path_style", "slash")
    request = ModelRequest(
        Agently.plugin_manager,
        parent_settings=Agently.settings,
    )
    request_settings = cast(
        "ModelRequesterSettings",
        SerializableStateDataNamespace(Agently.settings, "plugins.ModelRequester.OpenAICompatible"),
    )
    configure_ollama(request_settings)
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
    for parsed in response.get_generator(type="instant"):
        # print(parsed)
        results.append(parsed)
    assert results[0].value is not None
    assert len(results) > 0
