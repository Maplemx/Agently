import time
from typing import TYPE_CHECKING
import pytest
from agently import Agently

if TYPE_CHECKING:
    from agently.types.data.event import EventMessage


@pytest.mark.asyncio
async def test_async_event_messenger():
    module_messenger = Agently.event_center.create_messenger("Async Test")

    saved_message = None

    async def throw_content(message: "EventMessage"):
        nonlocal saved_message
        saved_message = message.content

    Agently.event_center.register_hook("log", throw_content)

    await module_messenger.async_info("Hello", status="SUCCESS")
    assert saved_message == "Hello"
    with pytest.raises(RuntimeError):
        await module_messenger.async_error("Something Wrong", status="FAILED")
        assert saved_message == "Something Wrong"


def test_sync_event_messenger():
    module_messenger = Agently.event_center.create_messenger("Test")

    saved_message = None

    def throw_content(message: "EventMessage"):
        print(">>>>>>>>>>>", message)
        nonlocal saved_message
        saved_message = message.content

    Agently.event_center.register_hook("log", throw_content)

    module_messenger.info("Bye", status="UNKNOWN")
    assert saved_message == "Bye"
    with pytest.raises(RuntimeError):
        module_messenger.critical("Something Really Bad", status="❗️")
        assert saved_message == "Something Really Bad"
