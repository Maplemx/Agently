from typing import cast
from agently import TriggerFlow, TriggerFlowRuntimeData


## TriggerFlow Runtime Resources: inject runtime-only dependencies and restore after load
def triggerflow_runtime_resources_demo():
    # Idea: keep serializable state in runtime_data, but inject runtime-only tools
    # and services through flow/execution resources.
    # Flow: START -> prepare -> pause_for -> save/load -> continue_with -> finalize
    # Expect: restored execution uses re-injected search tool and shared logger.
    class SimpleLogger:
        def info(self, message: str):
            print(f"[logger] {message}")

    def search_tool(query: str):
        return [
            {"title": f"{query} - result 1"},
            {"title": f"{query} - result 2"},
        ]

    flow = TriggerFlow()
    flow.update_runtime_resources(logger=SimpleLogger())

    async def prepare(data: TriggerFlowRuntimeData):
        query = str(data.value).strip()
        data.state.set("request", {"query": query})
        cast(SimpleLogger, data.require_resource("logger")).info(f"prepared request for: {query}")
        return await data.async_pause_for(
            type="human_input",
            payload={"question": f"search news for '{query}'?"},
            resume_event="UserFeedback",
        )

    async def finalize(data: TriggerFlowRuntimeData):
        request = data.state.get("request") or {}
        logger = cast(SimpleLogger, data.require_resource("logger"))
        search = data.require_resource("search_tool")
        assert search
        feedback = data.value if isinstance(data.value, dict) else {}
        results = search(str(request.get("query") or ""))
        logger.info(f"searched {len(results)} items")
        return {
            "request": request,
            "feedback": feedback,
            "results": results,
        }

    flow.to(prepare)
    flow.when("UserFeedback").to(finalize).end()

    execution = flow.start_execution("AI chips", wait_for_result=False)
    saved_state = execution.save()

    restored = flow.create_execution(runtime_resources={"search_tool": search_tool})
    restored.load(saved_state)

    interrupt_id = next(iter(restored.get_pending_interrupts()))
    restored.continue_with(interrupt_id, {"approved": True})

    print(restored.get_result(timeout=5))


# triggerflow_runtime_resources_demo()
