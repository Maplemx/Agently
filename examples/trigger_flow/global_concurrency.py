import asyncio
from agently import TriggerFlow, TriggerFlowEventData


async def handle(data: TriggerFlowEventData):
    print(f"Hi, { data.value }")
    await asyncio.sleep(2)
    return f"handled: { data.value }"


flow = TriggerFlow()
flow.batch(
    ("a", handle),
    ("b", handle),
    ("c", handle),
    ("d", handle),
).end()

execution = flow.create_execution(concurrency=2)
result = execution.start("hello")
print(result)
