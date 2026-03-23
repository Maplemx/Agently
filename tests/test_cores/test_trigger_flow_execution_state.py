import json
from pathlib import Path

import pytest

from agently import Agently, TriggerFlow, TriggerFlowRuntimeData
from agently.types.data import RunContext


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


def test_trigger_flow_execution_save_and_load_preserves_run_context():
    flow = TriggerFlow(name="persisted-lineage-flow")
    parent_run = RunContext.create(
        run_kind="request",
        agent_id="agent-1",
        agent_name="tester",
        session_id="session-1",
    )

    execution = flow.create_execution(parent_run_context=parent_run)
    saved_state = execution.save()

    assert saved_state["run_context"]["run_id"] == execution.run_context.run_id
    assert saved_state["run_context"]["parent_run_id"] == parent_run.run_id
    assert saved_state["run_context"]["root_run_id"] == parent_run.root_run_id

    restored_execution = flow.create_execution()
    restored_execution.load(saved_state)

    assert restored_execution.id == execution.id
    assert restored_execution.run_context.run_id == execution.run_context.run_id
    assert restored_execution.run_context.parent_run_id == parent_run.run_id
    assert restored_execution.run_context.root_run_id == parent_run.root_run_id
    assert restored_execution.run_context.execution_id == execution.id
    assert restored_execution.run_context.agent_id == "agent-1"
    assert restored_execution.run_context.agent_name == "tester"
    assert restored_execution.run_context.session_id == "session-1"


def test_trigger_flow_start_propagates_parent_run_context():
    flow = TriggerFlow(name="start-parent-lineage")
    flow.to(lambda data: data.value).end()

    parent_run = RunContext.create(
        run_kind="request",
        agent_id="agent-sync",
        agent_name="sync-owner",
        session_id="sync-session",
    )
    captured = []

    def capture(event):
        if event.event_type == "workflow.execution_started" and event.run is not None:
            captured.append(event)

    hook_name = "test_trigger_flow_start_propagates_parent_run_context.capture"
    Agently.event_center.register_hook(capture, event_types="workflow.execution_started", hook_name=hook_name)
    try:
        assert flow.start("ok", parent_run_context=parent_run) == "ok"
    finally:
        Agently.event_center.unregister_hook(hook_name)

    assert len(captured) == 1
    event = captured[0]
    assert event.run.parent_run_id == parent_run.run_id
    assert event.run.root_run_id == parent_run.root_run_id
    assert event.run.agent_id == "agent-sync"
    assert event.run.agent_name == "sync-owner"
    assert event.run.session_id == "sync-session"


@pytest.mark.asyncio
async def test_trigger_flow_runtime_stream_propagates_parent_run_context():
    flow = TriggerFlow(name="stream-parent-lineage")

    async def stream_once(data: TriggerFlowRuntimeData):
        await data.async_put_into_stream({"value": data.value})
        await data.async_stop_stream()
        return data.value

    flow.to(stream_once).end()

    parent_run = RunContext.create(
        run_kind="request",
        agent_id="agent-stream",
        agent_name="stream-owner",
        session_id="stream-session",
    )
    captured = []

    async def capture(event):
        if event.event_type == "workflow.execution_started" and event.run is not None:
            captured.append(event)

    hook_name = "test_trigger_flow_runtime_stream_propagates_parent_run_context.capture"
    Agently.event_center.register_hook(capture, event_types="workflow.execution_started", hook_name=hook_name)
    try:
        items = [item async for item in flow.get_async_runtime_stream("topic", parent_run_context=parent_run, timeout=1)]
    finally:
        Agently.event_center.unregister_hook(hook_name)

    assert items == [{"value": "topic"}]
    assert len(captured) == 1
    event = captured[0]
    assert event.run.parent_run_id == parent_run.run_id
    assert event.run.root_run_id == parent_run.root_run_id
    assert event.run.agent_id == "agent-stream"
    assert event.run.agent_name == "stream-owner"
    assert event.run.session_id == "stream-session"
