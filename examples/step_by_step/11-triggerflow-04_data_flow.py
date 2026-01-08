from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Data Flow: runtime_data + collect
def triggerflow_data_flow():
    # Idea: share execution-scoped data across branches and collect results.
    # Flow: set_runtime + set_runtime_context -> collect -> when(runtime_data)
    # Expect: prints "[when runtime]" then two collect outputs.
    flow = TriggerFlow()

    async def set_runtime(data: TriggerFlowEventData):
        data.set_runtime_data("user_id", "u-001")
        return "runtime ok"

    async def set_runtime_context(data: TriggerFlowEventData):
        data.set_runtime_data("env", "prod")
        return "runtime context ok"

    # collect waits for multiple branches to fill values
    (
        flow.to(set_runtime)
        .collect("done", "r1", mode="filled_then_empty")
        .to(lambda data: print("[collect runtime]", data.value))
    )
    (
        flow.to(set_runtime_context)
        .collect("done", "r2", mode="filled_then_empty")
        .to(lambda data: print("[collect runtime context]", data.value))
        .end()
    )

    # when: wait for runtime_data signal
    flow.when({"runtime_data": "user_id"}).to(lambda data: print("[when runtime]", data.value))

    flow.start()


# triggerflow_data_flow()
