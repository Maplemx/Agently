from agently import TriggerFlow, TriggerFlowRuntimeData


## TriggerFlow Runtime Stream Lifecycle: normal stop and timeout stop
def triggerflow_runtime_stream_stop_demo():
    # Idea: runtime stream is independent from flow result.
    # Flow: put_into_stream -> stop_stream
    flow = TriggerFlow()

    async def stream_steps(data: TriggerFlowRuntimeData):
        data.put_into_stream("step-1")
        data.put_into_stream("step-2")
        data.stop_stream()
        return "done"

    flow.to(stream_steps)

    for event in flow.get_runtime_stream("start", timeout=None):
        print("[stream]", event)


# triggerflow_runtime_stream_stop_demo()


def triggerflow_runtime_stream_timeout_demo():
    # Idea: if stop_stream() is not called, runtime stream can end by timeout.
    flow = TriggerFlow()

    async def stream_slow(data: TriggerFlowRuntimeData):
        data.put_into_stream("tick")
        return "done"

    flow.to(stream_slow)

    for event in flow.get_runtime_stream("start", timeout=0.5):
        print("[stream]", event)


# triggerflow_runtime_stream_timeout_demo()
