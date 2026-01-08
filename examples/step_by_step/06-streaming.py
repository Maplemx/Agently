from agently import Agently

agent = Agently.create_agent()

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


## Streaming Output Basics
def basic_delta_streaming():
    # Agently provides delta streaming to show partial output early,
    # so users don't stare at a blank screen.
    gen = agent.input("Give me a short speech about recursion.").get_generator(type="delta")
    for delta in gen:
        print(delta, end="", flush=True)
    print()


# basic_delta_streaming()


## Instant / Streaming-Parse for Structured Output
def instant_structured_streaming():
    # Agently provides instant streaming for structured output.
    # Stream nodes as they are generated, no need to wait for the whole response.
    # Great for dashboards, partial rendering, or realtime UI updates.
    # Two typical scenes:
    # 1) In chat UIs, some content is for users while other nodes drive functions,
    #    special UI cards, or animations without being shown directly.
    # 2) In complex workflows (e.g., planning multiple tasks), you can trigger
    #    downstream work as soon as one task is generated, instead of waiting
    #    for the full plan.
    gen = (
        agent.input("Explain recursion with a short definition and two tips.")
        .output(
            {
                "definition": (str, "Short definition"),
                "tips": [(str, "Short tip")],
            }
        )
        .get_generator(type="instant")
    )
    current_path = None
    change_path = False
    for data in gen:
        if current_path != data.path:
            current_path = data.path
            change_path = True
        else:
            change_path = False
        if data.wildcard_path == "tips[*]":
            if change_path:
                index = data.path.split("[", 1)[1].split("]", 1)[0]
                print(f"\nTip {int(index) + 1}: ", end="", flush=True)
            if data.delta:
                print(data.delta, end="", flush=True)
        if data.path == "definition":
            if change_path:
                print("\nDefinition: ", end="", flush=True)
            if data.delta:
                print(data.delta, end="", flush=True)
    print()


# instant_structured_streaming()


## Specific Event Streaming
def specific_event_streaming():
    # Agently provides specific-event streaming so you can pick only the events you care about
    # (delta / tool_calls / reasoning).
    gen = agent.input("Tell me a short story about recursion.").get_generator(type="specific")
    current_event = None
    for event, data in gen:
        if event in ("reasoning_delta", "delta"):
            if current_event != event:
                current_event = event
                label = "reasoning" if event == "reasoning_delta" else "answer"
                print(f"\n[{label}] ", end="", flush=True)
            print(data, end="", flush=True)
        elif event == "tool_calls":
            print("\n[tool_calls]", data)
    print()


specific_event_streaming()


## Async Variants
async def async_streaming():
    # Agently also provides async streaming for higher concurrency workloads.
    gen = agent.input("Give three recursion tips.").get_async_generator(type="delta")
    async for delta in gen:
        print(delta, end="", flush=True)
    print()


# async def main():
#     await async_streaming()
