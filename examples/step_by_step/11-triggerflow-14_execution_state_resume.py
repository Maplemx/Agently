from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Execution State Resume: save and continue later
def triggerflow_save_and_resume_state_demo():
    # Idea: save execution state at waiting point, restore later, then continue.
    # Flow: start_execution(waiting) -> save() -> load() -> emit feedback -> get_result
    flow = TriggerFlow()

    async def prepare(data: TriggerFlowEventData):
        data.set_runtime_data("ticket", {"id": "T-001", "topic": data.value})
        return "waiting"

    async def finalize(data: TriggerFlowEventData):
        return {
            "ticket": data.get_runtime_data("ticket"),
            "feedback": data.value,
        }

    flow.to(prepare)
    flow.when("UserFeedback").to(finalize).end()

    execution = flow.start_execution("refund request", wait_for_result=False)
    state = execution.save()

    restored_execution = flow.create_execution()
    restored_execution.load(state)
    restored_execution.emit("UserFeedback", {"approved": True})
    print(restored_execution.get_result(timeout=5))


# triggerflow_save_and_resume_state_demo()
