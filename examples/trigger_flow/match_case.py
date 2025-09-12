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
    .else_case()
    .to(lambda _: "I don't know!")
    .end_match()
    .to(lambda data: print(data.value))
)

execution_1 = flow_1.create_execution()
execution_1.start()

# For Each - Match Case
flow_2 = TriggerFlow()

(
    flow_2.to(lambda _: [1, "2", ["Agently"]])
    .for_each(with_index=True)
    .match()
    .case(lambda data: data.value[1] == 1)
    .to(lambda _: "OK")
    .else_case()
    .to(lambda _: "Not OK")
    .end_match()
    .end_for_each()
    .to(lambda data: print(data.value))
)

execution_2 = flow_2.create_execution()
execution_2.start()

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

execution_3 = flow_3.create_execution()
execution_3.start()
