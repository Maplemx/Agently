import json
from pathlib import Path

import pytest

from agently import TriggerFlow, TriggerFlowRuntimeData


def test_trigger_flow_sync_start_returns_result_or_none_by_wait_flag():
    flow = TriggerFlow()
    flow.to(lambda data: {"value": data.value}).end()

    assert flow.start("ok") == {"value": "ok"}
    assert flow.start("ok", wait_for_result=False) is None

    execution = flow.create_execution()
    assert execution.start("ok") == {"value": "ok"}

    another_execution = flow.create_execution()
    assert another_execution.start("ok", wait_for_result=False) is None


@pytest.mark.asyncio
async def test_trigger_flow_execution_save_and_load_then_continue():
    flow = TriggerFlow()

    async def init(data: TriggerFlowRuntimeData):
        data.set_runtime_data("draft", {"topic": "pricing"})
        data.set_flow_data("global_flag", True)
        return "waiting"

    async def finalize(data: TriggerFlowRuntimeData):
        return {
            "feedback": data.value,
            "draft": data.get_runtime_data("draft"),
            "global_flag": data.get_flow_data("global_flag"),
        }

    flow.to(init)
    flow.when("UserFeedback").to(finalize).end()

    execution = await flow.async_start_execution("start", wait_for_result=False)
    saved_state = execution.save()
    json.dumps(saved_state)
    assert "version" not in saved_state

    restored_execution = flow.create_execution()
    restored_execution.load(saved_state)
    await restored_execution.async_emit("UserFeedback", {"approve": True})
    result = await restored_execution.async_get_result(timeout=1)

    assert result == {
        "feedback": {"approve": True},
        "draft": {"topic": "pricing"},
        "global_flag": True,
    }


@pytest.mark.asyncio
async def test_trigger_flow_execution_load_from_json_string():
    flow = TriggerFlow()

    async def setup(data: TriggerFlowRuntimeData):
        data.set_runtime_data("checkpoint", {"step": 2})
        return data.value

    flow.to(setup).end()
    execution = await flow.async_start_execution("ok", wait_for_result=False)
    saved_state = execution.save()

    restored_execution = flow.create_execution()
    restored_execution.load(json.dumps(saved_state))

    assert restored_execution.get_runtime_data("checkpoint") == {"step": 2}


@pytest.mark.asyncio
async def test_trigger_flow_execution_load_restore_ready_result():
    flow = TriggerFlow()
    flow.to(lambda data: data.value).end()

    execution = flow.create_execution()
    execution.set_result({"done": True})
    saved_state = execution.save()

    restored_execution = flow.create_execution()
    restored_execution.load(saved_state)
    result = await restored_execution.async_get_result(timeout=0.01)

    assert result == {"done": True}


@pytest.mark.asyncio
async def test_trigger_flow_execution_save_to_json_file_and_load_from_file(tmp_path: Path):
    flow = TriggerFlow()
    flow.to(lambda data: data.value).end()

    execution = flow.create_execution()
    execution.set_runtime_data("checkpoint", {"step": 1})
    json_path = tmp_path / "execution_state.json"

    saved_state = execution.save(json_path)
    assert json_path.exists()
    assert isinstance(saved_state, dict)

    restored_execution = flow.create_execution()
    restored_execution.load(json_path)
    assert restored_execution.get_runtime_data("checkpoint") == {"step": 1}


@pytest.mark.asyncio
async def test_trigger_flow_execution_save_to_yaml_file_and_load_from_file(tmp_path: Path):
    flow = TriggerFlow()
    flow.to(lambda data: data.value).end()

    execution = flow.create_execution()
    execution.set_runtime_data("checkpoint", {"step": 2})
    yaml_path = tmp_path / "execution_state.yaml"

    execution.save(yaml_path)
    assert yaml_path.exists()

    restored_execution = flow.create_execution()
    restored_execution.load(yaml_path)
    assert restored_execution.get_runtime_data("checkpoint") == {"step": 2}
