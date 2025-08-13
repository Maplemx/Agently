from typing import Any
import pytest
from agently import Agently
from agently.core import PluginManager


def test_plugin_manager():
    plugin_manager = PluginManager(Agently.settings)
    assert plugin_manager.get_plugin_list() == {}

    from agently.types.plugins import PromptGenerator

    class TestPromptGenerator(PromptGenerator):
        name = "Test"

        def to_text(self, *args, **kwargs) -> str:
            return "OK"

        def to_messages(self, *args, **kwargs) -> list[dict[str, Any]]:
            return []

    plugin_manager.register("PromptGenerator", TestPromptGenerator, activate=False)

    assert plugin_manager.get_plugin_list() == {"PromptGenerator": ["Test"]}
    assert plugin_manager.get_plugin("PromptGenerator", "Test") == TestPromptGenerator


if __name__ == "__main__":
    test_plugin_manager()
