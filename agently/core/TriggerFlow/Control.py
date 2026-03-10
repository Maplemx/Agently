from typing import Any


TRIGGER_FLOW_STATUS_CREATED = "created"
TRIGGER_FLOW_STATUS_RUNNING = "running"
TRIGGER_FLOW_STATUS_WAITING = "waiting"
TRIGGER_FLOW_STATUS_COMPLETED = "completed"
TRIGGER_FLOW_STATUS_FAILED = "failed"
TRIGGER_FLOW_STATUS_CANCELLED = "cancelled"


class TriggerFlowPauseSignal(dict[str, Any]):
    def __init__(self, interrupt: dict[str, Any]):
        super().__init__(interrupt)
        self.interrupt = interrupt
