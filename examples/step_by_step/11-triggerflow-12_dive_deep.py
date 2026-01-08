from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Dive Deep: start/stop mechanics and result control
# This chapter is explanatory code with tiny runnable snippets.
# Read the comments first, then uncomment the calls if needed.


def dive_deep_start_and_result():
    # Idea: understand what start() waits for and how result is decided.
    # Key rules:
    # 1) start(wait_for_result=True) waits for "result_ready".
    # 2) end() sets a default result from the current chain value.
    # 3) set_result() sets result explicitly (public API).
    # 4) when() branches do NOT set result unless you add end() on that branch.
    #
    # Flow: main chain -> end() => result
    # Expect: result becomes the final value of the main chain.
    flow = TriggerFlow()

    async def work(data: TriggerFlowEventData):
        return f"work({data.value})"

    flow.to(work).end()
    result = flow.start("task")
    print(result)


# dive_deep_start_and_result()


def dive_deep_set_result():
    # Idea: take control of result when the flow is event-driven.
    # Flow: start_execution -> manual set_result -> get_result
    # Expect: prints "manual result".
    flow = TriggerFlow()
    flow.to(lambda d: d.value).end()

    execution = flow.start_execution("ignored", wait_for_result=False)
    execution.set_result("manual result")
    print(execution.get_result())


# dive_deep_set_result()


def dive_deep_runtime_stream():
    # Idea: runtime stream is independent of result.
    # Flow: put_into_stream -> stop_stream -> (no end required)
    # Expect: prints stream events; flow can keep running until stop_stream().
    flow = TriggerFlow()

    async def stream_steps(data: TriggerFlowEventData):
        data.put_into_stream("step-1")
        data.put_into_stream("step-2")
        data.stop_stream()
        return "done"

    flow.to(stream_steps)

    for event in flow.get_runtime_stream("start", timeout=None):
        print("[stream]", event)


# dive_deep_runtime_stream()


def dive_deep_when_branch_no_result():
    # Idea: when() branches do not set result by default.
    # Flow: emit -> when -> (no end on when)
    # Expect: start(wait_for_result=True) would timeout unless you set_result/end.
    flow = TriggerFlow()

    async def emit_event(data: TriggerFlowEventData):
        await data.async_emit("Ping", "pong")
        return "emitted"

    flow.to(emit_event)
    flow.when("Ping").to(lambda d: print("[ping]", d.value))
    flow.start(wait_for_result=False)


# dive_deep_when_branch_no_result()


def dive_deep_timeout_and_stream_stop():
    # Idea: show timeout vs stop_stream in runtime stream.
    # Flow: put_into_stream -> no stop_stream -> timeout => warn
    # Expect: stream prints, then timeout warning if timeout is small.
    flow = TriggerFlow()

    async def stream_slow(data: TriggerFlowEventData):
        data.put_into_stream("tick")
        return "done"

    flow.to(stream_slow)

    for event in flow.get_runtime_stream("start", timeout=0.5):
        print("[stream]", event)


# dive_deep_timeout_and_stream_stop()
