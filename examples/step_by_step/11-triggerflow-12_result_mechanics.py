from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Result Mechanics: default result, manual result, and branch caveat
def triggerflow_result_basics_demo():
    # Idea: start(wait_for_result=True) waits for result_ready.
    # Flow: main chain -> end() => default result.
    flow = TriggerFlow()

    async def work(data: TriggerFlowEventData):
        return f"work({data.value})"

    flow.to(work).end()
    result = flow.start("task")
    print(result)


# triggerflow_result_basics_demo()


def triggerflow_manual_set_result_demo():
    # Idea: control the final output explicitly in event-driven flows.
    # Flow: start_execution -> set_result -> get_result
    flow = TriggerFlow()
    flow.to(lambda d: d.value).end()

    execution = flow.start_execution("ignored", wait_for_result=False)
    execution.set_result("manual result")
    print(execution.get_result())


# triggerflow_manual_set_result_demo()


def triggerflow_when_branch_without_result_demo():
    # Idea: when() branch does not finalize result unless end()/set_result() is used.
    flow = TriggerFlow()

    async def emit_event(data: TriggerFlowEventData):
        await data.async_emit("Ping", "pong")
        return "emitted"

    flow.to(emit_event)
    flow.when("Ping").to(lambda d: print("[ping]", d.value))
    flow.start(wait_for_result=False)


# triggerflow_when_branch_without_result_demo()
