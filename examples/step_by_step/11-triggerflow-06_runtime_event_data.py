from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow RuntimeEventData: data, emit, and layers
def runtime_event_data_demo():
    # Idea: inspect event metadata and emit a custom event in-flow.
    # Flow: to(inspect_event) -> emit(CustomEvent) -> when(CustomEvent)
    # Expect: prints a custom event payload and returns event details.
    flow = TriggerFlow()

    async def inspect_event(data: TriggerFlowEventData):
        # RuntimeEventData provides:
        # - trigger_event / trigger_type / value
        # - runtime_data accessors (execution-scoped)
        # - emit / async_emit to trigger custom events
        # - layer_marks for nested branches
        data.set_runtime_data("seen_event", data.trigger_event)
        await data.async_emit("CustomEvent", {"from": data.trigger_event, "value": data.value})
        return {
            "event": data.trigger_event,
            "type": data.trigger_type,
            "value": data.value,
            "runtime": data.get_runtime_data("seen_event"),
            "layer": data.layer_mark,
        }

    flow.to(inspect_event).end()
    flow.when("CustomEvent").to(lambda d: print("[custom]", d.value))

    result = flow.start("hello")
    print(result)


# runtime_event_data_demo()
