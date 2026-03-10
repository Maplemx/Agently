from agently import TriggerFlow, TriggerFlowRuntimeData


async def throw_exception(data: TriggerFlowRuntimeData):
    raise RuntimeError(f"Test Exception")


flow = TriggerFlow()

flow.to(throw_exception).end()


try:
    flow.start()
except RuntimeError as e:
    print("Captured:", e)
except:
    print("Captured unexpected exception.")
