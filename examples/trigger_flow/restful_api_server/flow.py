from agently import TriggerFlow, TriggerFlowEventData


async def init(data: TriggerFlowEventData):
    data.set_runtime_data("init", data.value)
    return data.value


def dump_flow():
    flow = TriggerFlow()

    (
        flow.to(init)
        .batch(
            ("first", lambda data: data.value),
            ("second", lambda data: data.value * 2),
            ("third", lambda data: data.value * 3),
        )
        .side_branch(lambda data: print(data.value))
        .to(
            lambda data: {
                "group_1": data.value["first"],
                "group_2": data.value["second"] + data.value["third"],
                "init": data.get_runtime_data("init", None),
            }
        )
        .end()
    )
    return flow
