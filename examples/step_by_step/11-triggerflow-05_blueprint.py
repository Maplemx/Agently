from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Blueprint: save / load
def triggerflow_blueprint():
    # Idea: export a flow blueprint and reuse it elsewhere.
    # Flow: build -> save_blue_print -> load_blue_print -> start
    # Expect: prints "AGENTLY".
    flow = TriggerFlow()

    async def upper(data: TriggerFlowEventData):
        return str(data.value).upper()

    flow.to(upper).end()

    blueprint = flow.save_blue_print()

    # load the blueprint into a new flow
    flow_2 = TriggerFlow()
    flow_2.load_blue_print(blueprint)

    result = flow_2.start("agently")
    print(result)


# triggerflow_blueprint()
