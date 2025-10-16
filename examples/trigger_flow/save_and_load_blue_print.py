from agently import TriggerFlow, TriggerFlowEventData

flow_1 = TriggerFlow()


@flow_1.chunk
async def say_hello(data: TriggerFlowEventData):
    print("Hello,", data.value)
    return data.value


@flow_1.chunk
async def say_bye(data: TriggerFlowEventData):
    print("Bye,", data.value)
    return data.value


flow_1.to(say_hello).to(say_bye).end()

flow_2 = TriggerFlow(blue_print=flow_1.save_blue_print())

flow_2.when(flow_2.chunks["say_bye"]).to(lambda _: print("One more thing only in flow 2!"))

flow_1.start("World")
flow_2.start("Agently")
