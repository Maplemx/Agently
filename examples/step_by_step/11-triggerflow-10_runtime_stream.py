import asyncio
from agently import Agently, TriggerFlow, TriggerFlowEventData


## TriggerFlow Streaming: runtime stream + agent streaming in flow
def triggerflow_runtime_stream_demo():
    # Idea: stream progress updates without waiting for the final result.
    # Flow: put_into_stream steps -> end -> get_runtime_stream
    # Expect: prints stream events as they arrive.
    flow = TriggerFlow()

    async def stream_steps(data: TriggerFlowEventData):
        for i in range(3):
            data.put_into_stream({"step": i + 1, "status": "working"})
            await asyncio.sleep(0.05)
        data.stop_stream()
        return "done"

    flow.to(stream_steps).end()

    for event in flow.get_runtime_stream("start"):
        print("[stream]", event)


# triggerflow_runtime_stream_demo()


def triggerflow_agent_stream_demo():
    # Idea: interactive loop with user input + streamed replies.
    # Flow: input -> emit Loop -> stream reply -> emit Loop
    # Expect: prints streaming tokens for each user query.
    agent = Agently.create_agent()
    agent.set_settings(
        "OpenAICompatible",
        {
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "qwen2.5:7b",
        },
    )

    flow = TriggerFlow()

    async def get_input(data: TriggerFlowEventData):
        try:
            user_input = input("Question (type 'exit' to stop): ").strip()
        except EOFError:
            user_input = "exit"
        if user_input.lower() == "exit":
            data.stop_stream()
            return "exit"
        data.put_into_stream(f"\n[user] {user_input}\n")
        await data.async_emit("UserInput", user_input)
        return "next"

    async def stream_reply(data: TriggerFlowEventData):
        data.put_into_stream("[assistant] ")
        try:
            request = agent.input(data.value)
            async for chunk in request.get_async_generator(type="delta"):
                data.put_into_stream(chunk)
            data.put_into_stream("\n")
            await data.async_emit("Loop", None)
            return None
        except Exception as exc:
            data.put_into_stream(f"\n[error] {exc}\n")
            data.stop_stream()
            return "error"

    # This loop is stream-driven, so we don't set a default result with end().
    flow.to(get_input)
    flow.when("UserInput").to(stream_reply)
    flow.when("Loop").to(get_input)

    for event in flow.get_runtime_stream("start", timeout=None):
        print(event, end="", flush=True)


triggerflow_agent_stream_demo()
