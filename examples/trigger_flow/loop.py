from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


@flow.chunk
async def user_input(data: TriggerFlowEventData):
    return input("Say 'STOP' to exit: ")


(flow.to(user_input).match().case("STOP").end().else_case().to(user_input).end_match())

flow.start()
