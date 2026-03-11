import pytest

import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from typing import cast
from agently import Agently
from agently.core.Prompt import Prompt
from agently.utils import SerializableRuntimeDataNamespace
from agently.utils import Settings
from agently.builtins.plugins.ModelRequester.OpenAICompatible import (
    OpenAICompatible,
    ModelRequesterSettings,
)
import agently.builtins.plugins.ModelRequester.OpenAICompatible as openai_module

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def build_plugin(config: dict, prompt_values: dict | None = None):
    settings = Settings(parent=Agently.settings)
    settings.update({"plugins": {"ModelRequester": {"OpenAICompatible": config}}})
    prompt = Prompt(plugin_manager=Agently.plugin_manager, parent_settings=settings)
    for key, value in (prompt_values or {}).items():
        prompt.set(key, value)
    return OpenAICompatible(prompt, settings)


def generate_request(config: dict, prompt_values: dict | None = None):
    return build_plugin(config, prompt_values).generate_request_data().model_dump()


async def capture_request_headers(monkeypatch: pytest.MonkeyPatch, config: dict, prompt_values: dict | None = None):
    captured: dict = {}

    class FakeResponse:
        status_code = 200
        content = b'{"ok": true}'
        text = content.decode()
        headers = {"Content-Type": "application/json"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.headers = {}
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = dict(self.headers if headers is None else headers)
            return FakeResponse()

        async def aclose(self):
            return None

    monkeypatch.setattr(openai_module, "AsyncClient", FakeAsyncClient)
    plugin = build_plugin(config, prompt_values)
    request_data = plugin.generate_request_data()
    async for _event, _payload in plugin.request_model(request_data):
        pass
    return captured


@pytest.mark.asyncio
async def test_main():
    request_settings = cast(
        ModelRequesterSettings,
        SerializableRuntimeDataNamespace(Agently.settings, "plugins.ModelRequester.OpenAICompatible"),
    )
    request_settings["base_url"] = OLLAMA_BASE_URL
    request_settings["model"] = OLLAMA_MODEL
    request_settings["model_type"] = "chat"
    request_settings["auth"] = None
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
        raise e


def test_plugin_root_options_are_treated_as_request_options():
    request = generate_request(
        {
            "base_url": "https://api.example.com/v1",
            "model": "m1",
            "options": {"temperature": 0.7, "top_p": 0.9},
        },
        {"input": "hello"},
    )

    assert request["request_options"] == {"temperature": 0.7, "top_p": 0.9, "model": "m1", "stream": True}


def test_request_options_override_legacy_plugin_root_options():
    request = generate_request(
        {
            "base_url": "https://api.example.com/v1",
            "model": "m1",
            "options": {"temperature": 0.7, "top_p": 0.9},
            "request_options": {"temperature": 0.2},
        },
        {"input": "hello", "options": {"top_p": 0.5}},
    )

    assert request["request_options"] == {"temperature": 0.2, "top_p": 0.5, "model": "m1", "stream": True}


@pytest.mark.asyncio
async def test_auth_headers_are_preserved_in_outgoing_request(monkeypatch: pytest.MonkeyPatch):
    captured = await capture_request_headers(
        monkeypatch,
        {
            "base_url": "https://api.example.com/v1",
            "model": "m1",
            "stream": False,
            "auth": {"headers": {"Authorization": "Custom ABC", "X-Test": "1"}},
        },
        {"input": "hello"},
    )

    assert captured["headers"]["Authorization"] == "Custom ABC"
    assert captured["headers"]["X-Test"] == "1"


@pytest.mark.asyncio
async def test_auth_headers_are_kept_when_api_key_sets_authorization(monkeypatch: pytest.MonkeyPatch):
    captured = await capture_request_headers(
        monkeypatch,
        {
            "base_url": "https://api.example.com/v1",
            "model": "m1",
            "stream": False,
            "api_key": "KEY2",
            "auth": {"headers": {"X-Test": "1"}},
        },
        {"input": "hello"},
    )

    assert captured["headers"]["Authorization"] == "Bearer KEY2"
    assert captured["headers"]["X-Test"] == "1"
