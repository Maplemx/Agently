import pytest

from agently import TriggerFlow, TriggerFlowEventData


def _operator_by_kind(config: dict, kind: str):
    return [operator for operator in config["operators"] if operator["kind"] == kind]


@pytest.mark.asyncio
async def test_trigger_flow_config_round_trip_with_inspected_chunk_handler():
    flow = TriggerFlow(name="inspectable-flow")

    async def double(data: TriggerFlowEventData):
        return data.value * 2

    flow.to(double).end()
    config = flow.get_flow_config()
    chunk_operator = _operator_by_kind(config, "chunk")[0]
    json_content = flow.get_json_flow()

    assert chunk_operator["handler_ref"]["kind"] == "inspected"
    assert chunk_operator["handler_ref"]["name"] == "double"

    restored = TriggerFlow()
    restored.register_chunk_handler(double)
    restored.load_json_flow(json_content)

    result = await restored.async_start(3)
    assert result == 6


@pytest.mark.asyncio
async def test_trigger_flow_batch_round_trip_and_mermaid():
    flow = TriggerFlow(name="batch-flow")

    async def left(data: TriggerFlowEventData):
        return data.value + 1

    async def right(data: TriggerFlowEventData):
        return data.value + 10

    async def combine(data: TriggerFlowEventData):
        return data.value["left"] + data.value["right"]

    flow.batch(left, right).to(combine).end()
    config = flow.get_flow_config()
    mermaid = flow.to_mermaid()

    assert "batch" in mermaid
    assert _operator_by_kind(config, "batch_fanout")
    assert _operator_by_kind(config, "batch_collect")

    restored = TriggerFlow()
    restored.register_chunk_handler(left)
    restored.register_chunk_handler(right)
    restored.register_chunk_handler(combine)
    restored.load_flow_config(config)

    result = await restored.async_start(5)
    assert result == 21


@pytest.mark.asyncio
async def test_trigger_flow_for_each_round_trip():
    flow = TriggerFlow(name="for-each-flow")

    async def scale(data: TriggerFlowEventData):
        return data.value * 3

    flow.for_each().to(scale).end_for_each().end()
    yaml_content = flow.get_yaml_flow()

    restored = TriggerFlow()
    restored.register_chunk_handler(scale)
    restored.load_yaml_flow(yaml_content)

    result = await restored.async_start([1, 2, 3])
    assert result == [3, 6, 9]


@pytest.mark.asyncio
async def test_trigger_flow_match_round_trip():
    flow = TriggerFlow(name="match-flow")

    def is_even(data: TriggerFlowEventData):
        return data.value % 2 == 0

    async def even_branch(data: TriggerFlowEventData):
        return "even"

    async def odd_branch(data: TriggerFlowEventData):
        return "odd"

    flow.match().case(is_even).to(even_branch).case_else().to(odd_branch).end_match().end()
    config = flow.get_flow_config()

    restored = TriggerFlow()
    restored.register_condition_handler(is_even)
    restored.register_chunk_handler(even_branch)
    restored.register_chunk_handler(odd_branch)
    restored.load_flow_config(config)

    assert await restored.async_start(4) == "even"
    assert await restored.async_start(5) == "odd"


@pytest.mark.asyncio
async def test_trigger_flow_pause_round_trip_after_import():
    flow = TriggerFlow(name="pause-flow")

    async def ask_feedback(data: TriggerFlowEventData):
        data.set_runtime_data("draft", {"topic": data.value})
        return await data.async_pause_for(
            type="human_input",
            payload={"question": "approve?"},
            resume_event="UserFeedback",
        )

    async def finalize(data: TriggerFlowEventData):
        return {
            "draft": data.get_runtime_data("draft"),
            "feedback": data.value,
        }

    flow.to(ask_feedback)
    flow.when("UserFeedback").to(finalize).end()
    config = flow.get_flow_config()

    restored = TriggerFlow()
    restored.register_chunk_handler(ask_feedback)
    restored.register_chunk_handler(finalize)
    restored.load_flow_config(config)

    execution = await restored.async_start_execution("pricing", wait_for_result=False)
    pending_interrupts = execution.get_pending_interrupts()
    interrupt_id = next(iter(pending_interrupts))

    await execution.async_continue_with(interrupt_id, {"approved": True})
    result = await execution.async_get_result(timeout=1)

    assert result == {
        "draft": {"topic": "pricing"},
        "feedback": {"approved": True},
    }


def test_trigger_flow_mermaid_allows_lambda_chunk_but_export_rejects_it():
    flow = TriggerFlow(name="lambda-chunk-flow")
    flow.to(lambda data: data.value).end()

    mermaid = flow.to_mermaid(mode="detailed")
    assert "<lambda>" in mermaid

    with pytest.raises(ValueError, match="non-serializable handler"):
        flow.get_flow_config()


def test_trigger_flow_mermaid_allows_lambda_condition_but_export_rejects_it():
    flow = TriggerFlow(name="lambda-condition-flow")

    async def yes(data: TriggerFlowEventData):
        return "yes"

    async def no(data: TriggerFlowEventData):
        return "no"

    flow.if_condition(lambda data: bool(data.value)).to(yes).else_condition().to(no).end_condition().end()

    mermaid = flow.to_mermaid(mode="detailed")
    assert "<lambda>" in mermaid

    with pytest.raises(ValueError, match="non-serializable condition"):
        flow.get_flow_config()


def test_trigger_flow_mermaid_shows_external_signal_and_declared_emit():
    flow = TriggerFlow(name="mermaid-signals")

    async def notify(data: TriggerFlowEventData):
        return data.value

    chunk = flow.chunk("notify")(notify)
    chunk.declare_emits("Alert")

    flow.to(chunk)
    flow.when("UserFeedback").to(chunk).end()

    mermaid = flow.to_mermaid()
    config = flow.get_flow_config()
    chunk_operator = _operator_by_kind(config, "chunk")[0]

    assert "UserFeedback" in mermaid
    assert "Alert" in mermaid
    assert any(signal.get("role") == "declared_emit" and signal["trigger_event"] == "Alert" for signal in chunk_operator["emit_signals"])


@pytest.mark.asyncio
async def test_trigger_flow_repeated_internal_helper_names_do_not_conflict():
    flow = TriggerFlow(name="internal-helper-dup")
    flow.to(lambda data: data.value).____("first", print_info=True).____("second", print_info=True).end()

    result = await flow.async_start("ok")
    assert result == "ok"


def test_trigger_flow_import_fails_without_registered_handler():
    flow = TriggerFlow(name="strict-load")

    async def named_handler(data: TriggerFlowEventData):
        return data.value

    flow.to(named_handler).end()
    config = flow.get_flow_config()

    restored = TriggerFlow()
    with pytest.raises(ValueError, match="not registered"):
        restored.load_flow_config(config)
