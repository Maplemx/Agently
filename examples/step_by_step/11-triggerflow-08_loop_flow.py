from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Loop: emit event to re-enter the flow
def loop_flow_demo():
    # Idea: create a loop by emitting the same event until a stop condition.
    # Flow: start_loop -> emit Loop -> loop_step -> emit Loop/LoopEnd
    # Expect: prints "done: 3".
    flow = TriggerFlow()

    async def start_loop(data: TriggerFlowEventData):
        await data.async_emit("Loop", 0)
        return None

    async def loop_step(data: TriggerFlowEventData):
        count = data.value
        if count >= 3:
            await data.async_emit("LoopEnd", count)
            return None
        await data.async_emit("Loop", count + 1)
        return count

    flow.to(start_loop)
    flow.when("Loop").to(loop_step)
    flow.when("LoopEnd").to(lambda d: f"done: {d.value}").end()

    result = flow.start("start")
    print(result)


# loop_flow_demo()
