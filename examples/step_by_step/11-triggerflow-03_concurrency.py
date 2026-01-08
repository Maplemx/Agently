import asyncio
from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Concurrency: batch + for_each
def triggerflow_concurrency():
    # Idea: show concurrency limits for batch and for_each.
    # Flow: batch(echo, concurrency=2) -> print, then for_each(list, concurrency=2) -> print
    # Expect: outputs two results with interleaved timing.
    flow = TriggerFlow()

    async def echo(data: TriggerFlowEventData):
        await asyncio.sleep(0.1)
        return f"echo: {data.value}"

    # batch: run chunks in parallel with a concurrency limit
    flow.batch(
        ("a", echo),
        ("b", echo),
        ("c", echo),
        concurrency=2,
    ).end()

    result = flow.start("hello")
    print(result)

    # for_each: process list items with concurrency control
    flow_2 = TriggerFlow()
    (
        flow_2.to(lambda _: [1, 2, 3, 4])
        .for_each(concurrency=2)
        .to(echo)
        .end_for_each()
        .end()
    )
    result_2 = flow_2.start()
    print(result_2)


# triggerflow_concurrency()
