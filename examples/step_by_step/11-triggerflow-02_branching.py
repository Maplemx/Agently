from agently import TriggerFlow, TriggerFlowEventData


## TriggerFlow Branching: when()
def triggerflow_when_demo():
    # Idea: gate execution until multiple runtime signals appear.
    # Flow: set runtime_data -> when(and) / when(simple_or)
    # Expect: prints "[when or]" then "[when both]".
    flow = TriggerFlow()

    async def set_runtime(data: TriggerFlowEventData):
        data.set_runtime_data("flag", "ready")
        return "runtime done"

    async def set_runtime_phase(data: TriggerFlowEventData):
        data.set_runtime_data("phase", "ready")
        return "runtime phase done"

    flow.to(set_runtime).to(set_runtime_phase).end()

    # Wait for both runtime_data values (execution-scoped)
    flow.when({"runtime_data": ["flag", "phase"]}, mode="and").to(lambda data: print("[when both]", data.value))

    # Simple OR mode (value only)
    flow.when({"runtime_data": ["flag", "other"]}, mode="simple_or").to(lambda data: print("[when or]", data.value))

    flow.start(wait_for_result=False)


# triggerflow_when_demo()


## TriggerFlow Branching: if_condition / elif / else
def triggerflow_if_condition_demo():
    # Idea: map a score to grade using if/elif/else.
    # Flow: score -> if/elif/else -> print grade
    # Expect: prints "[grade] B".
    flow = TriggerFlow()

    (
        flow.to(lambda _: {"score": 82})
        .if_condition(lambda data: data.value["score"] >= 90)
        .to(lambda _: "A")
        .elif_condition(lambda data: data.value["score"] >= 80)
        .to(lambda _: "B")
        .else_condition()
        .to(lambda _: "C")
        .end_condition()
        .to(lambda data: print("[grade]", data.value))
        .end()
    )

    flow.start(wait_for_result=False)


# triggerflow_if_condition_demo()


## TriggerFlow Branching: match_case
def triggerflow_match_demo():
    # Idea: route fixed values through match/case.
    # Flow: value -> match/case -> print priority
    # Expect: prints "[match result] priority: medium".
    flow = TriggerFlow()

    (
        flow.to(lambda _: "medium")
        .match()
        .case("low")
        .to(lambda _: "priority: low")
        .case("medium")
        .to(lambda _: "priority: medium")
        .case("high")
        .to(lambda _: "priority: high")
        .case_else()
        .to(lambda _: "priority: unknown")
        .end_match()
        .to(lambda data: print("[match result]", data.value))
        .end()
    )

    flow.start(wait_for_result=False)


# triggerflow_match_demo()


## TriggerFlow Branching: complex flow with when + if_condition + match_case
def triggerflow_complex_branching_demo():
    # Idea: combine when/if/match in one flow to show interplay.
    # Flow: prepare runtime -> if review -> when ready -> match urgency
    # Expect: prints "[review]", "[when ready]", "[action]".
    flow = TriggerFlow()

    async def prepare(data: TriggerFlowEventData):
        data.set_runtime_data("task", "summarize")
        data.set_runtime_data("urgency", "high")
        data.set_runtime_data("score", 78)
        return {"task": "summarize", "urgency": "high", "score": 78}

    (
        flow.to(prepare)
        .if_condition(lambda data: data.value["score"] >= 85)
        .to(lambda _: "skip review")
        .else_condition()
        .to(lambda _: "needs review")
        .end_condition()
        .to(lambda data: print("[review]", data.value))
        .end()
    )

    flow.when({"runtime_data": ["task", "urgency"]}, mode="and").to(lambda data: print("[when ready]", data.value))

    (
        flow.to(lambda _: "high")
        .match()
        .case("low")
        .to(lambda _: "queue later")
        .case("high")
        .to(lambda _: "run now")
        .case_else()
        .to(lambda _: "queue")
        .end_match()
        .to(lambda data: print("[action]", data.value))
        .end()
    )

    flow.start(wait_for_result=False)


# triggerflow_complex_branching_demo()
