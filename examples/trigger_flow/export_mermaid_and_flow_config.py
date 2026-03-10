from pathlib import Path
from typing import cast

from agently import TriggerFlow, TriggerFlowRuntimeData


ASSET_DIR = Path(__file__).with_name("exported_sub_flow_assets")


class SimpleLogger:
    def info(self, message: str):
        print(f"[logger] {message}")


def has_multiple_sections(data: TriggerFlowRuntimeData):
    if not isinstance(data.value, dict):
        return False
    sections = data.value.get("sections", [])
    return isinstance(sections, list) and len(sections) > 1


async def collect_request(data: TriggerFlowRuntimeData):
    topic = str(data.value).strip()
    sections = ["summary"] if "brief" in topic.lower() else ["overview", "risks", "actions"]
    request_context = {"topic": topic, "sections": sections}
    data.set_runtime_data("request_context", request_context)
    data.set_flow_data("locale", "zh-CN")
    return request_context


async def use_multi_section_mode(data: TriggerFlowRuntimeData):
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info("multi-section mode")
    next_value = dict(data.value) if isinstance(data.value, dict) else {}
    next_value["mode"] = "multi"
    return next_value


async def use_single_section_mode(data: TriggerFlowRuntimeData):
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info("single-section mode")
    next_value = dict(data.value) if isinstance(data.value, dict) else {}
    next_value["mode"] = "single"
    return next_value


async def list_sections(data: TriggerFlowRuntimeData):
    if not isinstance(data.value, dict):
        return []
    data.set_runtime_data("mode", data.value.get("mode"))
    return data.value.get("sections", [])


async def draft_section(data: TriggerFlowRuntimeData):
    request_context = data.get_runtime_data("request_context") or {}
    locale = data.get_flow_data("locale") or "zh-CN"
    mode = data.get_runtime_data("mode") or "unknown"
    section = str(data.value)
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info(f"drafting {section}")
    return f"[{locale}|{mode}] {section}: {request_context.get('topic')}"


async def summarize_child_report(data: TriggerFlowRuntimeData):
    request_context = data.get_runtime_data("request_context") or {}
    sections = list(data.value) if isinstance(data.value, list) else [data.value]
    return {
        "topic": request_context.get("topic"),
        "mode": data.get_runtime_data("mode"),
        "sections": sections,
        "summary": "\n".join(str(section) for section in sections),
    }


async def finalize_request(data: TriggerFlowRuntimeData):
    return {
        "summary": data.value,
        "child_report": data.get_runtime_data("child_report"),
        "last_topic": data.get_flow_data("last_topic"),
    }


def register_handlers(flow: TriggerFlow):
    flow.register_condition_handler(has_multiple_sections)
    flow.register_chunk_handler(collect_request)
    flow.register_chunk_handler(use_multi_section_mode)
    flow.register_chunk_handler(use_single_section_mode)
    flow.register_chunk_handler(list_sections)
    flow.register_chunk_handler(draft_section)
    flow.register_chunk_handler(summarize_child_report)
    flow.register_chunk_handler(finalize_request)
    return flow


def build_child_flow() -> TriggerFlow:
    flow = TriggerFlow(name="child-review-flow")
    (
        flow.if_condition(has_multiple_sections)
        .to(use_multi_section_mode)
        .else_condition()
        .to(use_single_section_mode)
        .end_condition()
        .to(list_sections)
        .for_each()
        .to(draft_section)
        .end_for_each()
        .to(summarize_child_report)
        .end()
    )
    return flow


def build_flow() -> TriggerFlow:
    flow = TriggerFlow(name="sub-flow-review-demo")
    register_handlers(flow)
    flow.update_runtime_resources(logger=SimpleLogger())
    child_flow = build_child_flow()

    (
        flow.to(collect_request)
        .to_sub_flow(
            child_flow,
            capture={
                "input": "value",
                "runtime_data": {
                    "request_context": "runtime_data.request_context",
                },
                "flow_data": {
                    "locale": "flow_data.locale",
                },
                "resources": {
                    "logger": "resources.logger",
                },
            },
            write_back={
                "value": "result.summary",
                "runtime_data": {
                    "child_report": "result",
                },
                "flow_data": {
                    "last_topic": "result.topic",
                },
            },
        )
        .to(finalize_request)
        .end()
    )
    return flow


def export_assets(flow: TriggerFlow):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    simplified_mermaid_path = ASSET_DIR / "sub_flow_review_simplified.mmd"
    detailed_mermaid_path = ASSET_DIR / "sub_flow_review_detailed.mmd"
    json_path = ASSET_DIR / "sub_flow_review_flow.json"
    yaml_path = ASSET_DIR / "sub_flow_review_flow.yaml"

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

print("\nSource flow result:")
print(flow.start("AI infra weekly"))

json_flow = TriggerFlow()
register_handlers(json_flow)
json_flow.update_runtime_resources(logger=SimpleLogger())
json_flow.load_json_flow(ASSET_DIR / "sub_flow_review_flow.json")
print("\nJSON loaded flow result:")
print(json_flow.start("Brief release note"))
