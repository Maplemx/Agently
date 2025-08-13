import time
from typing import TYPE_CHECKING
import pytest
from agently import Agently

from agently.core import EventCenter

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


@pytest.mark.asyncio
async def test_messenger():
    ec = EventCenter()

    # 注册一个简单的 console hook，用来打印内容
    def console_hook(message: "EventMessage"):
        print(
            f"[Console Hook] table={message.meta.get('table_name')}, "
            f"row={message.meta.get('row_id')}, content={message.content}"
        )

    ec.register_hook("console", console_hook)

    messenger = ec.create_messenger("TestModule", base_meta={"source": "unit-test"})

    # 同 table，多行输出
    table_name = "TestTable"
    messenger.update_base_meta({"row_id": 1})
    await messenger.async_to_console("第一行数据", table_name=table_name)
    messenger.update_base_meta({"row_id": 2})
    await messenger.async_to_console("第二行数据", table_name=table_name)
    messenger.update_base_meta({"row_id": 3})
    await messenger.async_to_console("第三行数据", table_name=table_name)
