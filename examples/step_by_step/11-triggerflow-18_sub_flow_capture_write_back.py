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


async def use_multi_section_mode(data: TriggerFlowRuntimeData):
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info("child flow switched to multi-section mode")
    next_value = dict(data.value) if isinstance(data.value, dict) else {}
    next_value["mode"] = "multi"
    return next_value


async def use_single_section_mode(data: TriggerFlowRuntimeData):
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info("child flow switched to single-section mode")
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
    topic = request_context.get("topic", "unknown")
    section = str(data.value)
    logger = cast(SimpleLogger, data.require_resource("logger"))
    logger.info(f"drafting section '{section}' for '{topic}'")
    await data.async_put_into_stream(
        {
            "scope": "child",
            "section": section,
            "mode": mode,
            "locale": locale,
        }
    )
    return f"[{locale}|{mode}] {section}: {topic}"


async def summarize_child_report(data: TriggerFlowRuntimeData):
    request_context = data.get_runtime_data("request_context") or {}
    sections = list(data.value) if isinstance(data.value, list) else [data.value]
    return {
        "topic": request_context.get("topic"),
        "mode": data.get_runtime_data("mode"),
        "sections": sections,
        "summary": "\n".join(str(section) for section in sections),
    }


async def prepare_request(data: TriggerFlowRuntimeData):
    topic = str(data.value).strip()
    sections = ["summary"] if "brief" in topic.lower() else ["overview", "risks", "actions"]
    request_context = {
        "topic": topic,
        "sections": sections,
    }
    data.set_runtime_data("request_context", request_context)
    data.set_flow_data("locale", "zh-CN")
    return request_context


async def finalize_request(data: TriggerFlowRuntimeData):
    child_report = data.get_runtime_data("child_report") or {}
    await data.async_put_into_stream(
        {
            "scope": "parent",
            "topic": data.get_flow_data("last_topic"),
            "summary": data.value,
        }
    )
    await data.async_stop_stream()
    return {
        "topic": data.get_flow_data("last_topic"),
        "summary": data.value,
        "child_report": child_report,
    }


def build_child_flow() -> TriggerFlow:
    flow = TriggerFlow(name="draft-sections-sub-flow")
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


def build_parent_flow() -> TriggerFlow:
    flow = TriggerFlow(name="parent-sub-flow-demo")
    flow.update_runtime_resources(logger=SimpleLogger())
    child_flow = build_child_flow()

    (
        flow.to(prepare_request)
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


## TriggerFlow Sub Flow: capture, write_back, and runtime stream bridge
def triggerflow_sub_flow_capture_write_back_demo():
    # Idea: treat child flow as an isolated function-like block, explicitly capture
    # the parent snapshot into it, then write the child result back into the parent.
    # Flow: prepare_request -> sub_flow(if + for_each) -> finalize_request
    # Expect: child stream events appear in the parent stream, and child result writes
    # back to parent value/runtime_data/flow_data.
    flow = build_parent_flow()

    print("=== Multi-section request stream ===")
    execution = flow.create_execution()
    for event in execution.get_runtime_stream(initial_value="AI infra weekly", timeout=5):
        print(event)

    print("\n=== Multi-section final result ===")
    print(execution.get_result(timeout=5))

    print("\n=== Single-section final result ===")
    print(flow.start("Brief release note"))


# triggerflow_sub_flow_capture_write_back_demo()
