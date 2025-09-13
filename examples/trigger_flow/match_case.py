from agently import Agently, TriggerFlow

Agently.set_settings("runtime.show_trigger_flow_log", False)

# Match Case
flow_1 = TriggerFlow()

(
    flow_1.to(lambda _: 3)
    .match()
    .case(1)
    .to(lambda _: "It is One!")
    .case(lambda data: data.value == 2)
    .to(lambda _: "It is Two!")
    .case_else()
    .to(lambda _: "I don't know!")
    .end_match()
    .to(lambda data: print(data.value))
)

flow_1.start(wait_for_result=False)

# For Each - Match Case
flow_2 = TriggerFlow()

(
    flow_2.to(lambda _: [1, "2", ["Agently"]])
    .for_each(with_index=True)
    .match()
    .case(lambda data: data.value[1] == 1)
    .to(lambda _: "OK")
    .case_else()
    .to(lambda _: "Not OK")
    .end_match()
    .end_for_each()
    .to(lambda data: print(data.value))
)

flow_2.start(wait_for_result=False)

# If Condition (Simplify)
flow_3 = TriggerFlow()

(
    flow_3.to(lambda _: 1)
    .if_condition(1)
    .to(lambda _: 2)
    # .____() will do nothing but return self
    # You can use it to beautify your chain expression
    # You can also use arguments to comment or mark
    .____("nested if condition start")
    # nested if condition
    .if_condition(1)
    .to(lambda _: "1.OK 2.OK")
    .else_condition()
    .to(lambda _: "1.OK 2.Not OK")
    .end_condition()
    # end nested if condition
    .____("nested if condition end")
    .elif_condition(2)
    .to(lambda _: "Emm...")
    .else_condition()
    .to(lambda _: "Not OK")
    .end_condition()
    .to(lambda data: print(data.value))
)

flow_3.start(wait_for_result=False)

# No Else
flow_4 = TriggerFlow()

(
    flow_4.to(lambda _: 1)
    .match()
    .case(2)
    .to(lambda _: 2)
    .case(3)
    .to(lambda _: 3)
    .end_match()
    .to(lambda data: print(data.value))
)

flow_4.start(wait_for_result=False)

flow_5 = TriggerFlow()

(
    flow_5.to(lambda _: 1)
    .if_condition(2)
    .to(lambda _: print("Got 2"))
    .end_condition()
    .to(lambda data: print(data.value))
    .end()
)

flow_5.start(wait_for_result=False)

# Hit All
flow_6 = TriggerFlow()

(
    flow_6.to(lambda _: 1)
    .match(mode="hit_all")
    .case(1)
    .to(lambda _: print("here"))
    .case(lambda data: data.value < 2)
    .to(lambda _: print("also here"))
    .end_match()
)

flow_6.start(wait_for_result=False)
