from typing import TYPE_CHECKING

import pytest

from agently import Agently
from agently.core import EventCenter

if TYPE_CHECKING:
    from agently.types.data import RuntimeEvent


@pytest.mark.asyncio
async def test_async_runtime_emitter():
    emitter = Agently.event_center.create_emitter("Async Test")
    saved_event = None

    async def capture(event: "RuntimeEvent"):
        nonlocal saved_event
        saved_event = event

    hook_name = "test_async_runtime_emitter.capture"
    Agently.event_center.register_hook(capture, event_types="runtime.info", hook_name=hook_name)
    try:
        await emitter.async_info("Hello")
        assert saved_event is not None
        assert saved_event.message == "Hello"
        assert saved_event.source == "Async Test"
        with pytest.raises(RuntimeError):
            await emitter.async_error("Something Wrong")
    finally:
        Agently.event_center.unregister_hook(hook_name)


def test_sync_runtime_emitter():
    emitter = Agently.event_center.create_emitter("Test", base_meta={"scope": "unit-test"})
    saved_event = None

    def capture(event: "RuntimeEvent"):
        nonlocal saved_event
        saved_event = event

    hook_name = "test_sync_runtime_emitter.capture"
    Agently.event_center.register_hook(capture, event_types="runtime.info", hook_name=hook_name)
    try:
        emitter.info("Bye")
        assert saved_event is not None
        assert saved_event.message == "Bye"
        assert saved_event.meta["scope"] == "unit-test"
        with pytest.raises(RuntimeError):
            emitter.critical("Something Really Bad")
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_event_center_filtering():
    ec = EventCenter()
    captured: list["RuntimeEvent"] = []

    async def allowed_only(event: "RuntimeEvent"):
        captured.append(event)

    ec.register_hook(allowed_only, event_types="custom.allowed", hook_name="allowed_only")
    emitter = ec.create_emitter("TestModule", base_meta={"scope": "unit-test"})

    await emitter.async_emit("custom.allowed", message="first", payload={"row": 1})
    await emitter.async_emit("custom.blocked", message="second")

    assert len(captured) == 1
    assert captured[0].event_type == "custom.allowed"
    assert captured[0].payload == {"row": 1}
    assert captured[0].meta["scope"] == "unit-test"


@pytest.mark.asyncio
async def test_event_center_infers_source_for_emitter_and_direct_emit():
    ec = EventCenter()
    captured: list["RuntimeEvent"] = []

    async def capture(event: "RuntimeEvent"):
        captured.append(event)

    ec.register_hook(capture, hook_name="capture")

    class SourceOwner:
        name = "InferredOwner"

        def build_emitter(self):
            return ec.create_emitter()

        async def emit_directly(self):
            await ec.async_emit({"event_type": "custom.direct", "message": "direct"})

    owner = SourceOwner()
    emitter = owner.build_emitter()
    await emitter.async_emit("custom.emitter", message="via emitter")
    await owner.emit_directly()

    assert len(captured) == 2
    assert captured[0].source == "InferredOwner"
    assert captured[1].source == "InferredOwner"
