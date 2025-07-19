import pytest
from agently import Agently


@pytest.mark.asyncio
async def test_settings():
    Agently.set_settings("test", "test")
    assert Agently.settings["test"] == "test"
