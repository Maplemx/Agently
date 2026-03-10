from pathlib import Path

from agently import TriggerFlow, TriggerFlowRuntimeData


ASSET_DIR = Path(__file__).with_name("exported_flow_assets")


def build_flow() -> TriggerFlow:
    flow = TriggerFlow(name="approval-request-demo")

    @flow.chunk("collect_request")
    async def collect_request(data: TriggerFlowRuntimeData):
        request_context = {
            "topic": data.value,
            "status": "waiting_feedback",
        }
        data.set_runtime_data("request_context", request_context)
        return request_context

    @flow.chunk("finalize_request")
    async def finalize_request(data: TriggerFlowRuntimeData):
        request_context = data.get_runtime_data("request_context") or {}
        return {
            "topic": request_context.get("topic"),
            "status": "done",
            "feedback": data.value,
        }

    flow.chunks["collect_request"].declare_emits("ApprovalRequest")

    flow.to("collect_request")
    flow.when("UserFeedback").to("finalize_request").end()
    return flow


def export_assets(flow: TriggerFlow):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    simplified_mermaid_path = ASSET_DIR / "approval_request_simplified.mmd"
    detailed_mermaid_path = ASSET_DIR / "approval_request_detailed.mmd"
    json_path = ASSET_DIR / "approval_request_flow.json"
    yaml_path = ASSET_DIR / "approval_request_flow.yaml"

    simplified_mermaid_path.write_text(flow.to_mermaid(mode="simplified"), encoding="utf-8")
    detailed_mermaid_path.write_text(flow.to_mermaid(mode="detailed"), encoding="utf-8")
    flow.get_json_flow(json_path)
    flow.get_yaml_flow(yaml_path)

    print("Exported files:")
    print(" -", simplified_mermaid_path)
    print(" -", detailed_mermaid_path)
    print(" -", json_path)
    print(" -", yaml_path)


flow = build_flow()
export_assets(flow)

execution = flow.start_execution("Refund order #A1001", wait_for_result=False)
execution.emit(
    "UserFeedback",
    {
        "approved": True,
        "note": "Customer uploaded a valid receipt.",
    },
)
print("Execution result:")
print(execution.get_result(timeout=5))
