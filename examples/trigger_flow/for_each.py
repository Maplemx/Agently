import asyncio
import random
from agently import TriggerFlow, TriggerFlowEventData

flow_1 = TriggerFlow()

(flow_1.for_each().to(lambda data: print(data.value)))

execution_1 = flow_1.create_execution()
execution_1.start(
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

flow_2 = TriggerFlow()


async def send_list(_):
    return [
        1,
        "2",
        {"index": 3, "value": "OK"},
        (4, "Agently"),
    ]


async def handle(data: TriggerFlowEventData):
    await asyncio.sleep(random.randint(0, 100) / 100)
    return data.value


(
    flow_2.to(send_list)
    .for_each(with_index=True)  # Turn on/off to send item index in event data
    .to(handle)
    .end_for_each(sort_by_index=True)  # Turn on/off sort
    .to(lambda data: print(data.value))
)

execution_2 = flow_2.create_execution()
execution_2.start()
