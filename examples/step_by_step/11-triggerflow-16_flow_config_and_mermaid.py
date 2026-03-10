from pathlib import Path

from agently import TriggerFlow, TriggerFlowEventData


ASSET_DIR = Path(__file__).with_name("11-triggerflow-16_assets")
JSON_PATH = ASSET_DIR / "approval_flow.json"
YAML_PATH = ASSET_DIR / "approval_flow.yaml"
SIMPLIFIED_MERMAID_PATH = ASSET_DIR / "approval_flow_simplified.mmd"
DETAILED_MERMAID_PATH = ASSET_DIR / "approval_flow_detailed.mmd"


async def collect_request(data: TriggerFlowEventData):
    request_context = {
        "topic": data.value,
        "status": "waiting_feedback",
    }
    data.set_runtime_data("request_context", request_context)
    return request_context


async def finalize_request(data: TriggerFlowEventData):
    request_context = data.get_runtime_data("request_context") or {}
    return {
        "topic": request_context.get("topic"),
        "status": "done",
        "feedback": data.value,
    }


def register_handlers(flow: TriggerFlow):
    flow.register_chunk_handler(collect_request)
    flow.register_chunk_handler(finalize_request)
    return flow


def build_flow() -> TriggerFlow:
    flow = TriggerFlow(name="step-by-step-approval-flow")
    register_handlers(flow)

    collect_request_chunk = flow.chunk("collect_request")(collect_request)
    finalize_request_chunk = flow.chunk("finalize_request")(finalize_request)
    collect_request_chunk.declare_emits("ApprovalRequest")

    flow.to(collect_request_chunk)
    flow.when("UserFeedback").to(finalize_request_chunk).end()
    return flow


def export_assets(flow: TriggerFlow):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    flow.get_json_flow(JSON_PATH)
    flow.get_yaml_flow(YAML_PATH)
    SIMPLIFIED_MERMAID_PATH.write_text(flow.to_mermaid(mode="simplified"), encoding="utf-8")
    DETAILED_MERMAID_PATH.write_text(flow.to_mermaid(mode="detailed"), encoding="utf-8")

    print("Exported assets:")
    print(" -", JSON_PATH)
    print(" -", YAML_PATH)
    print(" -", SIMPLIFIED_MERMAID_PATH)
    print(" -", DETAILED_MERMAID_PATH)


## TriggerFlow Flow Config + Mermaid: export simple assets and load them back
def triggerflow_flow_config_and_mermaid_demo():
    # Idea: name your handlers, export JSON / YAML / Mermaid, then reload with
    # registered handlers to prove the config is executable.
    # Flow: collect_request -> wait UserFeedback -> finalize_request
    # Expect: source flow, JSON flow, and YAML flow all print the same shape result.
    source_flow = build_flow()
    export_assets(source_flow)

    execution = source_flow.start_execution("Refund order #A1001", wait_for_result=False)
    execution.emit("UserFeedback", {"approved": True})
    print("\n=== Source Flow ===")
    print(execution.get_result(timeout=5))

    json_flow = TriggerFlow()
    register_handlers(json_flow)
    json_flow.load_json_flow(JSON_PATH)
    json_execution = json_flow.start_execution("Refund order #A1002", wait_for_result=False)
    json_execution.emit("UserFeedback", {"approved": False})
    print("\n=== JSON Loaded Flow ===")
    print(json_execution.get_result(timeout=5))

    yaml_flow = TriggerFlow()
    register_handlers(yaml_flow)
    yaml_flow.load_yaml_flow(YAML_PATH)
    yaml_execution = yaml_flow.start_execution("Refund order #A1003", wait_for_result=False)
    yaml_execution.emit("UserFeedback", {"approved": True, "note": "Valid receipt"})
    print("\n=== YAML Loaded Flow ===")
    print(yaml_execution.get_result(timeout=5))


# triggerflow_flow_config_and_mermaid_demo()
