import asyncio
from random import randint
from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


async def echo(data: TriggerFlowEventData):
    num = randint(0, 100) / 100
    print(f"wait { num }s: { data.value }")
    await asyncio.sleep(num)
    return f"wait { num }s: { data.value }"


flow.batch(
    ("echo_1", echo),
    ("echo_2", echo),
    ("echo_3", echo),
    ("echo_4", echo),
).end()
execution = flow.create_execution()
result = execution.start("Agently")
print(result)
