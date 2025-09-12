from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


async def change_runtime_data(data: TriggerFlowEventData):
    data.set_runtime_data("test", "Hello")
    return


flow.to(change_runtime_data).end()
flow.when("test", type="runtime_data").to(
    lambda data: print("runtime data 'test' change:", data.value),
)

flow.start()
