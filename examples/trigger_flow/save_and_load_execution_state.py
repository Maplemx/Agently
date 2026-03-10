from pathlib import Path

from agently import TriggerFlow, TriggerFlowRuntimeData


flow = TriggerFlow()


@flow.chunk
async def prepare_request(data: TriggerFlowRuntimeData):
    # Save context that should survive process restart.
    data.set_runtime_data(
        "request_context",
        {
            "topic": data.value,
            "status": "waiting_feedback",
        },
    )
    print("[prepare]", data.get_runtime_data("request_context"))
    return "WAITING_FOR_USER_FEEDBACK"


@flow.chunk
async def resume_with_feedback(data: TriggerFlowRuntimeData):
    context = data.get_runtime_data("request_context")
    return {
        "topic": context.get("topic") if isinstance(context, dict) else None,
        "feedback": data.value,
        "status": "done",
    }


flow.to(prepare_request)
flow.when("UserFeedback").to(resume_with_feedback).end()


print("=== Step 1: start execution and save checkpoint to file ===")
execution = flow.start_execution("refund order #A1001", wait_for_result=False)
state_file = Path(__file__).with_name("execution_state_checkpoint.json")
execution.save(state_file)
print(f"saved state file: {state_file}")


print("\n=== Step 2: simulate restart and restore execution ===")
restored_execution = flow.create_execution()
restored_execution.load(state_file)
restored_execution.emit(
    "UserFeedback",
    {
        "approved": True,
        "note": "Customer uploaded a valid receipt.",
    },
)


print("\n=== Step 3: continue flow and get result ===")
result = restored_execution.get_result(timeout=5)
print(result)
state_file.unlink(missing_ok=True)
