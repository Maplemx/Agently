from agently import TriggerFlow, TriggerFlowRuntimeData


## TriggerFlow Basics: chunks, to(), end(), start()
def triggerflow_basics():
    # Idea: build the smallest flow and see data pass through one node.
    # Flow: START -> greet -> END
    # Expect: prints "Hello, Agently"
    flow = TriggerFlow()

    async def greet(data: TriggerFlowRuntimeData):
        return f"Hello, {data.value}"

    flow.to(greet).end()
    result = flow.start("Agently")
    print(result)


# triggerflow_basics()
