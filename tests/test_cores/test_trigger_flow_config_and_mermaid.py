import pytest
from typing import Any, cast
from pydantic import BaseModel

from agently import TriggerFlow, TriggerFlowRuntimeData


def _operator_by_kind(config: dict, kind: str):
    return [operator for operator in config["operators"] if operator["kind"] == kind]


def _operator_ids(config: dict):
    return {operator["id"] for operator in config["operators"]}


class ContractConfigInput(BaseModel):
    topic: str


class ContractConfigStream(BaseModel):
    stage: str


class ContractConfigResult(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_trigger_flow_config_round_trip_with_inspected_chunk_handler():
    flow = TriggerFlow(name="inspectable-flow")

    async def double(data: TriggerFlowRuntimeData):
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


def test_trigger_flow_config_and_mermaid_include_contract_metadata():
    flow = TriggerFlow(name="contract-config-flow").set_contract(
        initial_input=ContractConfigInput,
        stream=ContractConfigStream,
        result=ContractConfigResult,
        meta={"domain": "qa"},
    )

    async def worker(data: TriggerFlowRuntimeData[Any, ContractConfigStream, ContractConfigResult]):
        data.put(ContractConfigStream(stage="working"))
        data.set_result(ContractConfigResult(answer=data.value.topic.upper()))

    flow.to(worker).end()

    config = flow.get_flow_config()
    mermaid = flow.to_mermaid(mode="detailed")

    assert config["contract"]["initial_input"]["label"] == "ContractConfigInput"
    assert config["contract"]["stream"]["label"] == "ContractConfigStream"
    assert config["contract"]["result"]["label"] == "ContractConfigResult"
    assert config["contract"]["initial_input"]["schema"]["type"] == "object"
    assert config["contract"]["meta"] == {"domain": "qa"}
    assert config["contract"]["system_stream"]["interrupt"]["label"] == "TriggerFlowInterruptEvent"
    assert config["contract"]["system_stream"]["interrupt"]["schema"]["properties"]["type"]["const"] == "interrupt"
    assert "contract" in mermaid
    assert "input: ContractConfigInput" in mermaid
    assert "stream: ContractConfigStream" in mermaid
    assert "result: ContractConfigResult" in mermaid
    assert "meta: domain" in mermaid
    assert "system: interrupt" in mermaid

    restored = TriggerFlow()
    restored.register_chunk_handler(worker)
    restored.load_flow_config(config)

    assert restored.get_flow_config()["contract"] == config["contract"]
    assert "ContractConfigInput" in restored.to_mermaid(mode="detailed")


@pytest.mark.asyncio
async def test_trigger_flow_batch_round_trip_and_mermaid():
    flow = TriggerFlow(name="batch-flow")

    async def left(data: TriggerFlowRuntimeData):
        return data.value + 1

    async def right(data: TriggerFlowRuntimeData):
        return data.value + 10

    async def combine(data: TriggerFlowRuntimeData):
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

    async def scale(data: TriggerFlowRuntimeData):
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

    def is_even(data: TriggerFlowRuntimeData):
        return data.value % 2 == 0

    async def even_branch(data: TriggerFlowRuntimeData):
        return "even"

    async def odd_branch(data: TriggerFlowRuntimeData):
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

    async def yes(data: TriggerFlowRuntimeData):
        return "yes"

    async def no(data: TriggerFlowRuntimeData):
        return "no"

    flow.if_condition(lambda data: bool(data.value)).to(yes).else_condition().to(no).end_condition().end()

    mermaid = flow.to_mermaid(mode="detailed")
    assert "<lambda>" in mermaid

    with pytest.raises(ValueError, match="non-serializable condition"):
        flow.get_flow_config()


def test_trigger_flow_mermaid_shows_external_signal_and_declared_emit():
    flow = TriggerFlow(name="mermaid-signals")

    async def notify(data: TriggerFlowRuntimeData):
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


def test_trigger_flow_mermaid_simplified_shows_if_condition_internal_nodes():
    flow = TriggerFlow(name="if-condition-mermaid")

    async def prepare(data: TriggerFlowRuntimeData):
        return {"score": data.value}

    def is_a(data: TriggerFlowRuntimeData):
        return data.value["score"] >= 90

    def is_b(data: TriggerFlowRuntimeData):
        return data.value["score"] >= 80

    async def grade_a(data: TriggerFlowRuntimeData):
        return "A"

    async def grade_b(data: TriggerFlowRuntimeData):
        return "B"

    async def grade_c(data: TriggerFlowRuntimeData):
        return "C"

    async def finalize(data: TriggerFlowRuntimeData):
        return f"grade:{ data.value }"

    (
        flow.to(prepare)
        .if_condition(is_a)
        .to(grade_a)
        .elif_condition(is_b)
        .to(grade_b)
        .else_condition()
        .to(grade_c)
        .end_condition()
        .to(finalize)
        .end()
    )

    mermaid = flow.to_mermaid()
    config = flow.get_flow_config()
    finalize_operator = next(
        operator
        for operator in config["operators"]
        if operator["kind"] == "chunk" and operator["name"] == "finalize"
    )

    assert "subgraph" in mermaid
    assert "grade_a" in mermaid
    assert "grade_b" in mermaid
    assert "grade_c" in mermaid
    assert "finalize" in mermaid
    assert "case" in mermaid
    assert "else" in mermaid
    assert "--> group_" not in mermaid
    assert finalize_operator["group_id"] is None


def test_trigger_flow_mermaid_simplified_shows_nested_for_each_subflows():
    flow = TriggerFlow(name="nested-for-mermaid")

    async def outer_items(data: TriggerFlowRuntimeData):
        return [data.value, data.value + 1]

    async def middle_items(data: TriggerFlowRuntimeData):
        return [data.value, data.value * 10]

    async def leaf_items(data: TriggerFlowRuntimeData):
        return [f"{ data.value }-a", f"{ data.value }-b"]

    async def render_leaf(data: TriggerFlowRuntimeData):
        return data.value

    async def finalize(data: TriggerFlowRuntimeData):
        return data.value

    (
        flow.to(outer_items)
        .for_each()
        .to(middle_items)
        .for_each()
        .to(leaf_items)
        .for_each()
        .to(render_leaf)
        .end_for_each()
        .end_for_each()
        .end_for_each()
        .to(finalize)
        .end()
    )

    mermaid = flow.to_mermaid()
    config = flow.get_flow_config()
    finalize_operator = next(
        operator
        for operator in config["operators"]
        if operator["kind"] == "chunk" and operator["name"] == "finalize"
    )

    assert mermaid.count("subgraph ") >= 3
    assert "outer_items" in mermaid
    assert "middle_items" in mermaid
    assert "leaf_items" in mermaid
    assert "render_leaf" in mermaid
    assert "finalize" in mermaid
    assert "for each collect" in mermaid
    assert "--> group_" not in mermaid
    assert finalize_operator["group_id"] is None


@pytest.mark.asyncio
async def test_trigger_flow_sub_flow_round_trip_and_runtime():
    child_flow = TriggerFlow(name="child-flow")

    async def child_prepare(data: TriggerFlowRuntimeData):
        return data.value * 2

    async def child_finalize(data: TriggerFlowRuntimeData):
        return data.value + 1

    child_flow.to(child_prepare).to(child_finalize).end()

    parent_flow = TriggerFlow(name="parent-flow")

    async def parent_prepare(data: TriggerFlowRuntimeData):
        return data.value + 3

    async def parent_finalize(data: TriggerFlowRuntimeData):
        return data.value * 5

    parent_flow.to(parent_prepare).to_sub_flow(child_flow).to(parent_finalize).end()

    assert await parent_flow.async_start(2) == 55

    config = parent_flow.get_flow_config()
    assert _operator_by_kind(config, "sub_flow")

    restored = TriggerFlow()
    restored.register_chunk_handler(parent_prepare)
    restored.register_chunk_handler(parent_finalize)
    restored.register_chunk_handler(child_prepare)
    restored.register_chunk_handler(child_finalize)
    restored.load_flow_config(config)

    assert await restored.async_start(2) == 55


@pytest.mark.asyncio
async def test_trigger_flow_sub_flow_capture_and_write_back_round_trip():
    child_flow = TriggerFlow(name="child-bindings-flow")

    async def child_collect(data: TriggerFlowRuntimeData):
        return {
            "received": data.value,
            "draft": data.get_runtime_data("draft"),
            "topic": data.get_flow_data("topic"),
            "logger": data.require_resource("logger"),
        }

    child_flow.to(child_collect).end()

    parent_flow = TriggerFlow(name="parent-bindings-flow")

    async def parent_prepare(data: TriggerFlowRuntimeData):
        data.set_runtime_data("draft", {"headline": data.value})
        data.set_flow_data("topic", "sub-flow")
        data.set_resource("logger", "main-logger")
        return {"payload": data.value, "skip": True}

    async def parent_finalize(data: TriggerFlowRuntimeData):
        return {
            "value": data.value,
            "stored": data.get_runtime_data("subflow"),
            "latest_topic": data.get_flow_data("latest_topic"),
        }

    parent_flow.to(parent_prepare).to_sub_flow(
        child_flow,
        capture={
            "input": "value.payload",
            "runtime_data": {
                "draft": "runtime_data.draft",
            },
            "flow_data": {
                "topic": "flow_data.topic",
            },
            "resources": {
                "logger": "resources.logger",
            },
        },
        write_back={
            "value": "result.received",
            "runtime_data": {
                "subflow": "result",
            },
            "flow_data": {
                "latest_topic": "result.topic",
            },
        },
    ).to(parent_finalize).end()

    expected = {
        "value": "news",
        "stored": {
            "received": "news",
            "draft": {"headline": "news"},
            "topic": "sub-flow",
            "logger": "main-logger",
        },
        "latest_topic": "sub-flow",
    }

    assert await parent_flow.async_start("news") == expected

    config = parent_flow.get_flow_config()
    sub_flow_operator = _operator_by_kind(config, "sub_flow")[0]
    assert sub_flow_operator["options"]["capture"]["input"] == "value.payload"
    assert sub_flow_operator["options"]["write_back"]["value"] == "result.received"

    restored = TriggerFlow()
    restored.register_chunk_handler(parent_prepare)
    restored.register_chunk_handler(parent_finalize)
    restored.register_chunk_handler(child_collect)
    restored.load_flow_config(config)

    assert await restored.async_start("news") == expected


@pytest.mark.asyncio
async def test_trigger_flow_sub_flow_uses_isolated_child_flow_state():
    child_flow = TriggerFlow(name="child-isolated-flow")

    async def child_increment(data: TriggerFlowRuntimeData):
        next_count = data.get_flow_data("count", 0) + 1
        data.set_flow_data("count", next_count)
        return next_count

    child_flow.to(child_increment).end()

    parent_flow = TriggerFlow(name="parent-isolated-flow")
    parent_flow.to(child_flow).end()

    assert await parent_flow.async_start("first") == 1
    assert await parent_flow.async_start("second") == 1
    assert child_flow.get_flow_data("count") is None


@pytest.mark.asyncio
async def test_trigger_flow_sub_flow_bridges_child_runtime_stream():
    child_flow = TriggerFlow(name="child-stream-flow")

    async def child_emit(data: TriggerFlowRuntimeData):
        await data.async_put_into_stream({"scope": "child", "value": data.value})
        await data.async_stop_stream()
        return data.value + 1

    child_flow.to(child_emit).end()

    parent_flow = TriggerFlow(name="parent-stream-flow")

    async def parent_finalize(data: TriggerFlowRuntimeData):
        await data.async_put_into_stream({"scope": "parent", "value": data.value})
        await data.async_stop_stream()
        return data.value

    parent_flow.to(child_flow).to(parent_finalize).end()

    execution = await parent_flow.async_start_execution(2, wait_for_result=False)
    runtime_stream = execution.get_async_runtime_stream(timeout=1)
    items = [item async for item in runtime_stream]

    assert items == [
        {"scope": "child", "value": 2},
        {"scope": "parent", "value": 3},
    ]
    assert await execution.async_get_result(timeout=1) == 3


def test_trigger_flow_sub_flow_rejects_invalid_capture_and_write_back_specs():
    child_flow = TriggerFlow(name="child-invalid-spec")

    async def child_identity(data: TriggerFlowRuntimeData):
        return data.value

    child_flow.to(child_identity).end()

    parent_flow = TriggerFlow(name="parent-invalid-spec")

    with pytest.raises(TypeError, match="scope 'runtime_data' only accepts key-path mappings"):
        parent_flow.to_sub_flow(
            child_flow,
            capture=cast(Any, {
                "runtime_data": "runtime_data",
            }),
        )

    with pytest.raises(ValueError, match="source scope 'value' is not supported"):
        parent_flow.to_sub_flow(
            child_flow,
            write_back={
                "value": "value",
            },
        )


@pytest.mark.asyncio
async def test_trigger_flow_sub_flow_rejects_child_pause_resume():
    child_flow = TriggerFlow(name="child-pause-flow")

    async def child_pause(data: TriggerFlowRuntimeData):
        return await data.async_pause_for(
            type="human_input",
            payload={"question": "continue?"},
            resume_event="ResumeChild",
        )

    child_flow.to(child_pause).end()

    parent_flow = TriggerFlow(name="parent-pause-flow")
    parent_flow.to(child_flow).end()

    with pytest.raises(NotImplementedError, match="pause/resume"):
        await parent_flow.async_start("topic")


def test_trigger_flow_mermaid_shows_sub_flow_box_and_nested_flow():
    child_flow = TriggerFlow(name="child-mermaid-flow")

    async def child_step_one(data: TriggerFlowRuntimeData):
        return data.value + 1

    async def child_step_two(data: TriggerFlowRuntimeData):
        return data.value * 2

    child_flow.to(child_step_one).to(child_step_two).end()

    parent_flow = TriggerFlow(name="parent-mermaid-flow")

    async def parent_prepare(data: TriggerFlowRuntimeData):
        return data.value

    async def parent_finalize(data: TriggerFlowRuntimeData):
        return data.value

    parent_flow.to(parent_prepare).to(child_flow).to(parent_finalize).end()

    mermaid = parent_flow.to_mermaid()

    assert "subgraph subflow_" in mermaid
    assert "style subflow_" in mermaid
    assert "fill:#F6F8FB" in mermaid
    assert "child_step_one" in mermaid
    assert "child_step_two" in mermaid
    assert "parent_prepare" in mermaid
    assert "parent_finalize" in mermaid


@pytest.mark.asyncio
async def test_trigger_flow_repeated_internal_helper_names_do_not_conflict():
    flow = TriggerFlow(name="internal-helper-dup")
    flow.to(lambda data: data.value).____("first", print_info=True).____("second", print_info=True).end()

    result = await flow.async_start("ok")
    assert result == "ok"


def test_trigger_flow_import_fails_without_registered_handler():
    flow = TriggerFlow(name="strict-load")

    async def named_handler(data: TriggerFlowRuntimeData):
        return data.value

    flow.to(named_handler).end()
    config = flow.get_flow_config()

    restored = TriggerFlow()
    with pytest.raises(ValueError, match="not registered"):
        restored.load_flow_config(config)


def test_trigger_flow_load_flow_config_respects_replace_flag():
    first_flow = TriggerFlow(name="first-flow")

    async def first(data: TriggerFlowRuntimeData):
        return data.value + 1

    first_flow.to(first).end()
    first_config = first_flow.get_flow_config()

    second_flow = TriggerFlow(name="second-flow")

    async def second(data: TriggerFlowRuntimeData):
        return data.value * 2

    second_flow.when("UserSignal").to(second).end()
    second_config = second_flow.get_flow_config()

    restored = TriggerFlow()
    restored.register_chunk_handler(first)
    restored.register_chunk_handler(second)

    restored.load_flow_config(first_config, replace=False)
    restored.load_flow_config(second_config, replace=False)
    merged_config = restored.get_flow_config()

    assert merged_config["name"] == first_config["name"]
    assert _operator_ids(first_config).issubset(_operator_ids(merged_config))
    assert _operator_ids(second_config).issubset(_operator_ids(merged_config))
    assert len(merged_config["operators"]) == len(first_config["operators"]) + len(second_config["operators"])

    restored.load_flow_config(second_config, replace=True)
    replaced_config = restored.get_flow_config()

    assert replaced_config["name"] == second_config["name"]
    assert _operator_ids(replaced_config) == _operator_ids(second_config)


def test_trigger_flow_load_json_flow_respects_replace_flag():
    first_flow = TriggerFlow(name="first-json-flow")

    async def first_json(data: TriggerFlowRuntimeData):
        return data.value + 1

    first_flow.to(first_json).end()
    first_json_content = first_flow.get_json_flow()
    first_config = first_flow.get_flow_config()

    second_flow = TriggerFlow(name="second-json-flow")

    async def second_json(data: TriggerFlowRuntimeData):
        return data.value * 2

    second_flow.when("UserSignal").to(second_json).end()
    second_json_content = second_flow.get_json_flow()
    second_config = second_flow.get_flow_config()

    restored = TriggerFlow()
    restored.register_chunk_handler(first_json)
    restored.register_chunk_handler(second_json)

    restored.load_json_flow(first_json_content, replace=False)
    restored.load_json_flow(second_json_content, replace=False)
    merged_config = restored.get_flow_config()

    assert merged_config["name"] == first_config["name"]
    assert _operator_ids(first_config).issubset(_operator_ids(merged_config))
    assert _operator_ids(second_config).issubset(_operator_ids(merged_config))
    assert len(merged_config["operators"]) == len(first_config["operators"]) + len(second_config["operators"])

    restored.load_json_flow(second_json_content, replace=True)
    replaced_config = restored.get_flow_config()

    assert replaced_config["name"] == second_config["name"]
    assert _operator_ids(replaced_config) == _operator_ids(second_config)


def test_trigger_flow_load_yaml_flow_respects_replace_flag():
    first_flow = TriggerFlow(name="first-yaml-flow")

    async def first_yaml(data: TriggerFlowRuntimeData):
        return data.value + 1

    first_flow.to(first_yaml).end()
    first_yaml_content = first_flow.get_yaml_flow()
    first_config = first_flow.get_flow_config()

    second_flow = TriggerFlow(name="second-yaml-flow")

    async def second_yaml(data: TriggerFlowRuntimeData):
        return data.value * 2

    second_flow.when("UserSignal").to(second_yaml).end()
    second_yaml_content = second_flow.get_yaml_flow()
    second_config = second_flow.get_flow_config()

    restored = TriggerFlow()
    restored.register_chunk_handler(first_yaml)
    restored.register_chunk_handler(second_yaml)

    restored.load_yaml_flow(first_yaml_content, replace=False)
    restored.load_yaml_flow(second_yaml_content, replace=False)
    merged_config = restored.get_flow_config()

    assert merged_config["name"] == first_config["name"]
    assert _operator_ids(first_config).issubset(_operator_ids(merged_config))
    assert _operator_ids(second_config).issubset(_operator_ids(merged_config))
    assert len(merged_config["operators"]) == len(first_config["operators"]) + len(second_config["operators"])

    restored.load_yaml_flow(second_yaml_content, replace=True)
    replaced_config = restored.get_flow_config()

    assert replaced_config["name"] == second_config["name"]
    assert _operator_ids(replaced_config) == _operator_ids(second_config)
