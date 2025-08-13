import pytest

from agently.utils import Settings


def test_settings():
    root_settings = Settings()
    parent_settings = Settings(parent=root_settings)
    child_settings = Settings(parent=parent_settings)
    root_settings.set("test", 1)
    assert child_settings.get() == {"test": 1}
