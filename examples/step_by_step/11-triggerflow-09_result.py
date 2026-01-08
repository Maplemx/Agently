from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Result: set_result to control output
def triggerflow_set_result_demo():
    # Idea: control the final output explicitly with set_result().
    # Flow: start_execution -> async work -> set_result -> await result
    # Expect: prints "final answer: done".
    flow = TriggerFlow()

    async def worker(data: TriggerFlowEventData):
        return f"work({data.value})"

    flow.to(worker).end()

    execution = flow.start_execution("task-1", wait_for_result=False)
    execution.set_result("final answer: done")
    result = execution.get_result()
    print(result)


# triggerflow_set_result_demo()
