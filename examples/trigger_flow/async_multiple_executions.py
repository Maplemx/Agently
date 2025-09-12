import asyncio
from random import randint

from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


async def task(data: TriggerFlowEventData):
    print(f"No.{ data.value } START")
    await asyncio.sleep(randint(1, 5))
    print(f"No.{ data.value } DONE")


(flow.to(task).end())


async def main():
    tasks = []
    for i in range(10):
        tasks.append(asyncio.create_task(flow.async_start(i)))
    await asyncio.gather(*tasks)


asyncio.run(main())
