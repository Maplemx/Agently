from agently import TriggerFlow, TriggerFlowRuntimeData

flow = TriggerFlow()


async def say_hello(data: TriggerFlowRuntimeData):
    print(f"Hello, { data.value }")
    return data.value


async def say_bye(data: TriggerFlowRuntimeData):
    print(f"Bye, { data.value }")
    return data.value


flow.to(say_hello).to(say_bye).end()
execution = flow.create_execution()
result = execution.start("Agently")
