from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Side Branch + ____ separator
def triggerflow_side_branch_demo():
    # Idea: run a side branch without blocking the main path.
    # Flow: main -> ____ separator -> side_branch -> end
    # Expect: prints side branch output and main result.
    flow = TriggerFlow()

    async def main_task(data: TriggerFlowEventData):
        return f"main: {data.value}"

    async def side_task(data: TriggerFlowEventData):
        print(f"[side] {data.value}")
        return "side done"

    (
        flow.to(main_task)
        .____(print_info=True, show_value=True)
        .side_branch(side_task)
        .to(lambda d: print("[main]", d.value))
        .end()
    )

    flow.start("hello")


# triggerflow_side_branch_demo()
