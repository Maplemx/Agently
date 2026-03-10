from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Safe Cycle: bounded loop, pause-resume loop, and external re-entry
def triggerflow_bounded_cycle_demo():
    # Idea: a cycle is safe if every turn has a clear stop condition.
    # Flow: START -> loop_step -> emit Loop -> loop_step ... -> set_result
    # Expect: prints a bounded sequence and final result.
    flow = TriggerFlow()

    async def loop_step(data: TriggerFlowEventData):
        current = int(data.get_runtime_data("count", 0) or 0)
        seen = data.get_runtime_data("seen", []) or []
        seen.append(current)
        data.set_runtime_data("seen", seen, emit=False)

        if current >= 3:
            result = {"mode": "bounded", "seen": seen}
            data.set_result(result)
            return result

        data.set_runtime_data("count", current + 1, emit=False)
        await data.async_emit("Loop", current + 1)
        return current

    flow.to(loop_step)
    flow.when("Loop").to(loop_step)

    print(flow.start("start"))


# triggerflow_bounded_cycle_demo()


def triggerflow_pause_between_turns_demo():
    # Idea: instead of self-spinning, pause after each turn and wait for an external resume.
    # Flow: START -> step -> pause_for -> continue_with -> ResumeLoop -> Loop -> step
    # Expect: prints one interrupt per turn and exits after the scripted replies.
    flow = TriggerFlow()

    async def step(data: TriggerFlowEventData):
        current = int(data.get_runtime_data("count", 0) or 0)
        turns = data.get_runtime_data("turns", []) or []
        turns.append(current)
        data.set_runtime_data("turns", turns, emit=False)

        if current >= 2:
            result = {"mode": "pause_resume", "turns": turns}
            data.set_result(result)
            return result

        return await data.async_pause_for(
            type="human_input",
            payload={"question": f"continue from turn {current}?"},
            resume_event="ResumeLoop",
        )

    async def resume_loop(data: TriggerFlowEventData):
        answer = data.value if isinstance(data.value, dict) else {}
        current = int(data.get_runtime_data("count", 0) or 0)
        if not answer.get("continue", False):
            result = {
                "mode": "pause_resume",
                "turns": data.get_runtime_data("turns", []),
                "stopped_by_user": True,
            }
            data.set_result(result)
            return result

        data.set_runtime_data("count", current + 1, emit=False)
        await data.async_emit("Loop", current + 1)
        return {"continued": current + 1}

    flow.to(step)
    flow.when("Loop").to(step)
    flow.when("ResumeLoop").to(resume_loop)

    execution = flow.start_execution("start", wait_for_result=False)

    scripted_answers = [{"continue": True}, {"continue": True}]
    for answer in scripted_answers:
        pending_interrupts = execution.get_pending_interrupts()
        interrupt_id = next(iter(pending_interrupts))
        print("[interrupt]", pending_interrupts[interrupt_id]["payload"])
        execution.continue_with(interrupt_id, answer)

    print(execution.get_result(timeout=5))


# triggerflow_pause_between_turns_demo()


def triggerflow_external_reentry_demo():
    # Idea: the safest cycle is often not a self-emit loop, but repeated external re-entry.
    # Flow: START -> init, then external Tick events re-enter the same execution.
    # Expect: prints a result only after enough external Tick events arrive.
    flow = TriggerFlow()

    async def init(data: TriggerFlowEventData):
        data.set_runtime_data("total", 0, emit=False)
        return "waiting_for_ticks"

    async def on_tick(data: TriggerFlowEventData):
        total = int(data.get_runtime_data("total", 0) or 0) + int(data.value)
        data.set_runtime_data("total", total, emit=False)
        if total >= 3:
            result = {"mode": "external_reentry", "total": total}
            data.set_result(result)
            return result
        return {"waiting_for_more_ticks": total}

    flow.to(init)
    flow.when("Tick").to(on_tick)

    execution = flow.start_execution("start", wait_for_result=False)
    for delta in [1, 1, 1]:
        execution.emit("Tick", delta)

    print(execution.get_result(timeout=5))


# triggerflow_external_reentry_demo()
