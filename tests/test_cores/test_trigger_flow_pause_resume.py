import asyncio

import pytest

from agently import TriggerFlow, TriggerFlowRuntimeData


@pytest.mark.asyncio
async def test_trigger_flow_pause_continue_with_saved_interrupt():
    flow = TriggerFlow()

    async def ask_feedback(data: TriggerFlowRuntimeData):
        data.set_runtime_data("draft", {"topic": data.value})
        return await data.async_pause_for(
            type="human_input",
            payload={"question": "approve?"},
            resume_event="UserFeedback",
        )

    async def finalize(data: TriggerFlowRuntimeData):
        return {
            "draft": data.get_runtime_data("draft"),
            "feedback": data.value,
        }

    flow.to(ask_feedback)
    flow.when("UserFeedback").to(finalize).end()

    execution = await flow.async_start_execution("pricing", wait_for_result=False)
    pending_interrupts = execution.get_pending_interrupts()

    assert execution.get_status() == "waiting"
    assert len(pending_interrupts) == 1

    interrupt_id, interrupt = next(iter(pending_interrupts.items()))
    assert interrupt["resume_event"] == "UserFeedback"

    restored_execution = flow.create_execution()
    restored_execution.load(execution.save())

    assert restored_execution.get_status() == "waiting"
    assert interrupt_id in restored_execution.get_pending_interrupts()

    await restored_execution.async_continue_with(interrupt_id, {"approved": True})
    result = await restored_execution.async_get_result(timeout=1)

    assert restored_execution.get_status() == "completed"
    assert result == {
        "draft": {"topic": "pricing"},
        "feedback": {"approved": True},
    }


@pytest.mark.asyncio
async def test_trigger_flow_when_and_state_is_isolated_per_execution():
    flow = TriggerFlow()
    flow.when({"event": ["A", "B"]}, mode="and").to(lambda data: data.value).end()

    execution_1 = flow.create_execution()
    execution_2 = flow.create_execution()

    await execution_1.async_emit("A", "execution-1-a")
    await execution_2.async_emit("B", "execution-2-b")

    with pytest.warns(UserWarning):
        assert await execution_1.async_get_result(timeout=0.01) is None
    with pytest.warns(UserWarning):
        assert await execution_2.async_get_result(timeout=0.01) is None

    await execution_1.async_emit("B", "execution-1-b")
    await execution_2.async_emit("A", "execution-2-a")

    result_1 = await execution_1.async_get_result(timeout=1)
    result_2 = await execution_2.async_get_result(timeout=1)

    assert result_1 == {
        "event": {
            "A": "execution-1-a",
            "B": "execution-1-b",
        }
    }
    assert result_2 == {
        "event": {
            "A": "execution-2-a",
            "B": "execution-2-b",
        }
    }


@pytest.mark.asyncio
async def test_trigger_flow_batch_state_is_isolated_per_execution():
    flow = TriggerFlow()

    async def left(data: TriggerFlowRuntimeData):
        await asyncio.sleep(0.01)
        return {"left": data.value}

    async def right(data: TriggerFlowRuntimeData):
        await asyncio.sleep(0.01)
        return {"right": data.value}

    flow.batch(left, right).to(lambda data: data.value).end()

    execution_1 = flow.create_execution()
    execution_2 = flow.create_execution()

    await asyncio.gather(
        execution_1.async_start("first", wait_for_result=False),
        execution_2.async_start("second", wait_for_result=False),
    )

    result_1 = await execution_1.async_get_result(timeout=1)
    result_2 = await execution_2.async_get_result(timeout=1)

    assert result_1 == {
        "left": {"left": "first"},
        "right": {"right": "first"},
    }
    assert result_2 == {
        "left": {"left": "second"},
        "right": {"right": "second"},
    }
