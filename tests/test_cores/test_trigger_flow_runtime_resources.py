import json

import pytest

from agently import TriggerFlow, TriggerFlowEventData, TriggerFlowRuntimeData


def test_trigger_flow_runtime_data_alias_is_exported():
    assert TriggerFlowRuntimeData is TriggerFlowEventData


@pytest.mark.asyncio
async def test_trigger_flow_runtime_data_namespaces_and_flow_resources():
    flow = TriggerFlow()
    flow.update_runtime_resources(logger="flow-logger")

    async def prepare(data: TriggerFlowRuntimeData):
        data.state.set("draft", {"topic": data.value})
        data.flow_state.set("shared_flag", True)
        return {
            "draft": data.state.get("draft"),
            "shared_flag": data.flow_state.get("shared_flag"),
            "logger": data.require_resource("logger"),
        }

    flow.to(prepare).end()
    result = await flow.async_start("pricing")

    assert result == {
        "draft": {"topic": "pricing"},
        "shared_flag": True,
        "logger": "flow-logger",
    }


@pytest.mark.asyncio
async def test_trigger_flow_execution_resources_override_flow_defaults():
    flow = TriggerFlow()
    flow.update_runtime_resources(tool_name="flow-tool")

    async def inspect_resource(data: TriggerFlowRuntimeData):
        return data.require_resource("tool_name")

    flow.to(inspect_resource).end()

    assert await flow.async_start("start") == "flow-tool"
    assert await flow.async_start("start", runtime_resources={"tool_name": "execution-tool"}) == "execution-tool"


@pytest.mark.asyncio
async def test_trigger_flow_runtime_data_set_resource_is_execution_scoped():
    flow = TriggerFlow()

    async def remember(data: TriggerFlowRuntimeData):
        data.set_resource("token", data.value)
        return data.value

    async def read_token(data: TriggerFlowRuntimeData):
        return data.require_resource("token")

    flow.to(remember).to(read_token).end()

    execution = flow.create_execution()
    await execution.async_start("alpha", wait_for_result=False)
    result = await execution.async_get_result(timeout=1)

    assert result == "alpha"

    another_execution = flow.create_execution()
    with pytest.raises(KeyError, match="missing required runtime resource"):
        another_execution.require_runtime_resource("token")


@pytest.mark.asyncio
async def test_trigger_flow_execution_save_records_resource_keys_only():
    flow = TriggerFlow()
    flow.update_runtime_resources(flow_tool=object())

    async def passthrough(data: TriggerFlowRuntimeData):
        return data.value

    flow.to(passthrough).end()
    execution = flow.create_execution(runtime_resources={"execution_logger": object()})
    await execution.async_start("ok", wait_for_result=False)
    state = execution.save()

    assert sorted(state["resource_keys"]) == ["execution_logger", "flow_tool"]
    assert "runtime_resources" not in state
    json.dumps(state)


@pytest.mark.asyncio
async def test_trigger_flow_execution_load_requires_reinjecting_runtime_resources():
    flow = TriggerFlow()

    async def ask_feedback(data: TriggerFlowRuntimeData):
        return await data.async_pause_for(
            type="human_input",
            payload={"question": "continue?"},
            resume_event="Resume",
        )

    async def finalize(data: TriggerFlowRuntimeData):
        service = data.require_resource("resume_service")
        return service(data.value)

    flow.to(ask_feedback)
    flow.when("Resume").to(finalize).end()

    execution = await flow.async_start_execution("topic", wait_for_result=False)
    interrupt_id = next(iter(execution.get_pending_interrupts()))
    saved_state = execution.save()

    missing_resource_execution = flow.create_execution()
    missing_resource_execution.load(saved_state)
    with pytest.raises(KeyError, match="missing required runtime resource"):
        await missing_resource_execution.async_continue_with(interrupt_id, {"approved": True})

    restored_execution = flow.create_execution()
    restored_execution.load(
        saved_state,
        runtime_resources={
            "resume_service": lambda payload: {
                "approved": payload["approved"],
                "source": "resource",
            }
        },
    )
    await restored_execution.async_continue_with(interrupt_id, {"approved": True})
    result = await restored_execution.async_get_result(timeout=1)

    assert result == {
        "approved": True,
        "source": "resource",
    }


@pytest.mark.asyncio
async def test_trigger_flow_condition_handler_can_use_runtime_resources():
    flow = TriggerFlow()

    def should_take_left(data: TriggerFlowRuntimeData):
        return bool(data.require_resource("take_left"))

    async def left(data: TriggerFlowRuntimeData):
        return "left"

    async def right(data: TriggerFlowRuntimeData):
        return "right"

    flow.if_condition(should_take_left).to(left).else_condition().to(right).end_condition().end()

    assert await flow.async_start("x", runtime_resources={"take_left": True}) == "left"
    assert await flow.async_start("x", runtime_resources={"take_left": False}) == "right"


@pytest.mark.asyncio
async def test_trigger_flow_config_round_trip_with_runtime_resources():
    flow = TriggerFlow(name="runtime-resources-config")

    async def render(data: TriggerFlowRuntimeData):
        renderer = data.require_resource("renderer")
        return renderer(data.value)

    flow.to(render).end()
    config = flow.get_flow_config()

    assert "renderer" not in json.dumps(config)

    restored = TriggerFlow()
    restored.register_chunk_handler(render)
    restored.load_flow_config(config)

    result = await restored.async_start(
        "hello",
        runtime_resources={"renderer": lambda value: value.upper()},
    )
    assert result == "HELLO"
