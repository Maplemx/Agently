from pathlib import Path

from agently import TriggerFlow, TriggerFlowRuntimeData


ASSET_DIR = Path(__file__).with_name("12-auto_loop_config_assets")
JSON_PATH = ASSET_DIR / "auto_loop_flow.json"
YAML_PATH = ASSET_DIR / "auto_loop_flow.yaml"
MERMAID_PATH = ASSET_DIR / "auto_loop_flow.mmd"


def tool_knowledge_base(topic: str):
    knowledge = {
        "capital_of_france": "Paris is the capital of France.",
        "capital_of_japan": "Tokyo is the capital of Japan.",
    }
    return knowledge.get(topic, f"No knowledge for topic: {topic}")


def tool_calculator(expression: str):
    results = {
        "2+2": 4,
        "2 + 2": 4,
        "3*7": 21,
        "3 * 7": 21,
    }
    return results.get(expression.strip(), f"Unsupported expression: {expression}")


def is_final_action(data: TriggerFlowRuntimeData):
    return isinstance(data.value, dict) and data.value.get("type") == "final"


async def prepare_context(data: TriggerFlowRuntimeData):
    question = str(data.value)
    data.set_runtime_data("question", question)
    data.set_runtime_data("done_plans", [])
    data.set_runtime_data("step", 0)
    data.set_runtime_data("memo", [])
    return {"question": question}


async def make_next_plan(data: TriggerFlowRuntimeData):
    question = str(data.get_runtime_data("question", ""))
    lower_question = question.lower()
    step = int(data.get_runtime_data("step", 0) or 0)
    done_plans = data.get_runtime_data("done_plans", [])

    data.set_runtime_data("step", step + 1)

    if step >= 3:
        action = {
            "type": "final",
            "reply": "Planning stopped after reaching the max step limit.",
        }
    elif done_plans:
        last_plan = done_plans[-1]
        action = {
            "type": "final",
            "reply": last_plan["result"],
        }
    elif "capital" in lower_question and "france" in lower_question:
        action = {
            "type": "tool",
            "reply": "",
            "tool_using": {
                "tool_name": "knowledge_base",
                "purpose": "Find the capital of France.",
                "kwargs": {"topic": "capital_of_france"},
            },
        }
    elif "capital" in lower_question and "japan" in lower_question:
        action = {
            "type": "tool",
            "reply": "",
            "tool_using": {
                "tool_name": "knowledge_base",
                "purpose": "Find the capital of Japan.",
                "kwargs": {"topic": "capital_of_japan"},
            },
        }
    elif "2+2" in lower_question or "2 + 2" in lower_question:
        action = {
            "type": "tool",
            "reply": "",
            "tool_using": {
                "tool_name": "calculator",
                "purpose": "Calculate the simple math expression.",
                "kwargs": {"expression": "2 + 2"},
            },
        }
    else:
        action = {
            "type": "final",
            "reply": f"Direct answer: {question}",
        }

    await data.async_emit("Plan", action)
    return action


async def use_tool(data: TriggerFlowRuntimeData):
    tool_using = data.value["tool_using"]
    tool_name = str(tool_using["tool_name"]).lower()

    if tool_name == "knowledge_base":
        result = tool_knowledge_base(**tool_using["kwargs"])
    elif tool_name == "calculator":
        result = str(tool_calculator(**tool_using["kwargs"]))
    else:
        result = f"Unknown tool: {tool_name}"

    done_plans = data.get_runtime_data("done_plans", [])
    done_plans.append(
        {
            "tool_name": tool_name,
            "purpose": tool_using["purpose"],
            "result": result,
        }
    )
    data.set_runtime_data("done_plans", done_plans)
    return {"type": "tool_done", "result": result}


async def update_memo(data: TriggerFlowRuntimeData):
    memo = data.get_runtime_data("memo", [])
    question = str(data.get_runtime_data("question", ""))
    if "short" in question.lower():
        memo.append("preference: short answers")
        data.set_runtime_data("memo", memo)
    return data.value


async def reply(data: TriggerFlowRuntimeData):
    result = {
        "question": data.get_runtime_data("question"),
        "reply": data.value["reply"],
        "done_plans": data.get_runtime_data("done_plans", []),
        "memo": data.get_runtime_data("memo", []),
    }
    data.set_result(result)
    return result


def register_auto_loop_handlers(flow: TriggerFlow):
    flow.register_chunk_handler(prepare_context)
    flow.register_chunk_handler(make_next_plan)
    flow.register_chunk_handler(use_tool)
    flow.register_chunk_handler(update_memo)
    flow.register_chunk_handler(reply)
    flow.register_condition_handler(is_final_action)
    return flow


def build_auto_loop_flow() -> TriggerFlow:
    flow = TriggerFlow(name="config-auto-loop-demo")
    register_auto_loop_handlers(flow)

    prepare_context_chunk = flow.chunk("prepare_context")(prepare_context)
    make_next_plan_chunk = flow.chunk("make_next_plan")(make_next_plan)
    use_tool_chunk = flow.chunk("use_tool")(use_tool)
    update_memo_chunk = flow.chunk("update_memo")(update_memo)
    reply_chunk = flow.chunk("reply")(reply)

    make_next_plan_chunk.declare_emits("Plan")

    flow.to(prepare_context_chunk).to(make_next_plan_chunk)
    (
        flow.when("Plan")
        .if_condition(is_final_action)
        .to(update_memo_chunk)
        .to(reply_chunk)
        .else_condition()
        .to(use_tool_chunk)
        .to(make_next_plan_chunk)
        .end_condition()
    )

    return flow


def export_assets(flow: TriggerFlow):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    flow.get_json_flow(JSON_PATH)
    flow.get_yaml_flow(YAML_PATH)
    MERMAID_PATH.write_text(flow.to_mermaid(mode="simplified"), encoding="utf-8")

    print("Exported assets:")
    print(" -", JSON_PATH)
    print(" -", YAML_PATH)
    print(" -", MERMAID_PATH)


def load_flow_from_json() -> TriggerFlow:
    flow = TriggerFlow()
    register_auto_loop_handlers(flow)
    flow.load_json_flow(JSON_PATH)
    return flow


def load_flow_from_yaml() -> TriggerFlow:
    flow = TriggerFlow()
    register_auto_loop_handlers(flow)
    flow.load_yaml_flow(YAML_PATH)
    return flow


## Auto Loop Config Export / Import: build once, export config, load again
def triggerflow_auto_loop_config_export_import_demo():
    # Idea: keep the kernel signal-driven, but export a declarative flow config
    # for reuse in JSON / YAML, then reload the flow with registered handlers.
    # Flow: prepare_context -> make_next_plan -> Plan -> use_tool/reply
    # Expect: source flow, JSON flow, and YAML flow all produce valid results.
    source_flow = build_auto_loop_flow()
    export_assets(source_flow)

    print("\n=== Source Flow ===")
    print(source_flow.start("Please answer short: what is the capital of France?"))

    json_flow = load_flow_from_json()
    print("\n=== JSON Loaded Flow ===")
    print(json_flow.start("Please answer short: what is the capital of Japan?"))

    yaml_flow = load_flow_from_yaml()
    print("\n=== YAML Loaded Flow ===")
    print(yaml_flow.start("Please calculate 2 + 2"))


# triggerflow_auto_loop_config_export_import_demo()
