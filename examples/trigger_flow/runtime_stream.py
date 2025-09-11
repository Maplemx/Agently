import asyncio
from agently import TriggerFlow, TriggerFlowEventData

flow = TriggerFlow()


async def say_hello(data: TriggerFlowEventData):
    await asyncio.sleep(0.3)
    await data.async_put(f"Hello, { data.value }")
    return data.value


async def say_bye(data: TriggerFlowEventData):
    await asyncio.sleep(0.3)
    await data.async_put(f"Bye, { data.value }")
    return data.value


async def stop_streaming(data: TriggerFlowEventData):
    await data.async_stop_stream()
    return data.value


flow.to(say_hello).to(say_bye).to(stop_streaming)
execution = flow.create_execution()
stream = execution.get_runtime_stream(initial_value="Agently")
for item in stream:
    print(item)
