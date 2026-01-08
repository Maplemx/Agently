from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow emit + when: custom event routing
def emit_when_demo():
    # Idea: use emit + when to fan out work and collect results.
    # Flow: planner emits Plan.Read/Plan.Write -> when listeners -> collect
    # Expect: prints collected results; start() does not return a final value here.
    flow = TriggerFlow()

    async def planner(data: TriggerFlowEventData):
        # emit two custom events for downstream branches
        await data.async_emit("Plan.Read", {"task": "read"})
        await data.async_emit("Plan.Write", {"task": "write"})
        return "plan done"

    async def reader(data: TriggerFlowEventData):
        return f"read: {data.value['task']}"

    async def writer(data: TriggerFlowEventData):
        return f"write: {data.value['task']}"

    # when listens to custom events emitted by planner
    flow.to(planner).end()
    flow.when("Plan.Read").to(reader).collect("plan", "read")
    (
        flow.when("Plan.Write")
        .to(writer)
        .collect("plan", "write")
        .to(lambda d: print("[collect]", d.value))
        .end()
    )

    flow.start("go", wait_for_result=False)


# emit_when_demo()
