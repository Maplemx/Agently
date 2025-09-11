import uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agently.types.trigger_flow import TriggerFlowHandler, TriggerFlowEventData

from agently.utils import FunctionShifter


class TriggerFlowChunk:
    def __init__(
        self,
        handler: "TriggerFlowHandler",
        *,
        name: str | None = None,
    ):
        self.name = name if name is not None else uuid.uuid4().hex
        self._handler = handler
        self.trigger = f"Chunk[{ handler.__name__ }]-{ self.name }"

    async def async_call(self, data: "TriggerFlowEventData"):
        result = await FunctionShifter.asyncify(self._handler)(data)
        await data.async_emit(self.trigger, result)
        return result

    def call(self, data: "TriggerFlowEventData"):
        result = FunctionShifter.syncify(self._handler)(data)
        data.emit(self.trigger, result)
        return result
