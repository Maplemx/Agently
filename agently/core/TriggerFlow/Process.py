from .process import (
    TriggerFlowBaseProcess,
    TriggerFlowForEachProcess,
    TriggerFlowMatchCaseProcess,
)


class TriggerFlowProcess(
    TriggerFlowForEachProcess,
    TriggerFlowMatchCaseProcess,
    TriggerFlowBaseProcess,
): ...
