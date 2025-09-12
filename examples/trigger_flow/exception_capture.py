from agently import TriggerFlow, TriggerFlowEventData


async def throw_exception(data: TriggerFlowEventData):
    raise RuntimeError(f"Test Exception")


flow = TriggerFlow()

flow.to(throw_exception).end()


try:
    flow.start()
except RuntimeError as e:
    print("Captured:", e)
except:
    print("Captured unexpected exception.")
