from typing import cast

from agently import TriggerFlow, TriggerFlowRuntimeData


class SimpleLogger:
    def info(self, message: str):
        print(f"[logger] {message}")


def has_multiple_sections(data: TriggerFlowRuntimeData):
    if not isinstance(data.value, dict):
        return False
    sections = data.value.get("sections", [])
    return isinstance(sections, list) and len(sections) > 1


async def prepare_request(data: TriggerFlowRuntimeData):
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
    section = str(data.value)
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info(f"drafting {section}")
    await data.async_put_into_stream({"scope": "child", "section": section})
    return f"[{data.get_flow_data('locale')}|{data.get_runtime_data('mode')}] {section}: {request_context.get('topic')}"


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
    await data.async_put_into_stream({"scope": "parent", "summary": data.value})
    await data.async_stop_stream()
    return {
        "summary": data.value,
        "child_report": data.get_runtime_data("child_report"),
        "last_topic": data.get_flow_data("last_topic"),
    }


child_flow = TriggerFlow(name="child-review-flow")
(
    child_flow.if_condition(has_multiple_sections)
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

parent_flow = TriggerFlow(name="parent-review-flow")
parent_flow.update_runtime_resources(logger=SimpleLogger())
(
    parent_flow.to(prepare_request)
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

execution = parent_flow.create_execution()
for item in execution.get_runtime_stream(initial_value="AI infra weekly", timeout=5):
    print(item)

print("\nResult:")
print(execution.get_result(timeout=5))
