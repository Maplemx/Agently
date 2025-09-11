from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


async def say_hello(data: TriggerFlowEventData):
    print(f"Hello, { data.value }")
    return data.value


async def say_bye(data: TriggerFlowEventData):
    print(f"Bye, { data.value }")
    return data.value


flow.to(say_hello).to(say_bye)
execution = flow.create_execution()
result = execution.start("Agently")
