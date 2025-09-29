import asyncio
from random import randint
from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


@flow.chunk
async def change_runtime_data(data: TriggerFlowEventData):
    await asyncio.sleep(randint(0, 100) / 100)
    data.set_runtime_data("test", "Hello")
    return


async def change_another_runtime_data(data: TriggerFlowEventData):
    await asyncio.sleep(randint(0, 100) / 100)
    data.set_runtime_data("test_2", "Bye")
    return


async def change_flow_data(data: TriggerFlowEventData):
    await asyncio.sleep(randint(0, 100) / 100)
    data.set_flow_data("test", "Hello")
    return


async def change_another_flow_data(data: TriggerFlowEventData):
    await asyncio.sleep(randint(0, 100) / 100)
    data.set_flow_data("test_2", "Bye")
    return


# Two parallel processes
flow.to(change_runtime_data).to(change_another_runtime_data).collect("branch_end", "1", mode="filled_then_empty")
(
    flow.to(change_flow_data)
    .to(change_another_flow_data)
    .collect("branch_end", "2", mode="filled_then_empty")
    .to(lambda _: print("All Done"))
    .end()
)

# Wait for chunk done
# Notice: if you want to wait a specific chunk, you need to use @flow.chunk
# to decorate the chunk handler function into a trigger flow chunk
flow.when(change_runtime_data).to(lambda data: print("change runtime data done, but return None:", data.value))

# Wait for runtime data key 'test' change
flow.when({"runtime_data": "test"}).to(
    lambda data: print("runtime data 'test' changed:", data.value),
)

# Wait for flow data key 'test' change
flow.when({"flow_data": "test"}).to(
    lambda data: print("flow data 'test' changed:", data.value),
)

# Wait for runtime data key 'test' and flow data key 'test' change
flow.when(
    {
        "runtime_data": "test",
        "flow_data": "test",
    },
).to(lambda data: print("runtime data 'test' and flow data 'test' both changed:", data.value))

# Wait for all data change
flow.when(
    {
        "runtime_data": ["test", "test_2"],
        "flow_data": ["test", "test_2"],
    },
).to(lambda data: print("all data changed:", data.value))


flow.start()
