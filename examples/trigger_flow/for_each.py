import asyncio
import random
from agently import TriggerFlow, TriggerFlowEventData


async def handle(data: TriggerFlowEventData):
    print("START HANDLING:", data.value)
    await asyncio.sleep(random.randint(0, 100) / 100)
    print("FINISH HANDLING:", data.value)
    return data.value


flow_1 = TriggerFlow()

flow_1.for_each().to(handle).end_for_each().to(lambda data: data.value).end()

execution_1 = flow_1.create_execution()
result = execution_1.start(
    [
        1,
        2,
        "a",
        "b",
        [
            1,
            2,
            3,
        ],
        {"say": "hello world"},
    ]
)
print(result)
