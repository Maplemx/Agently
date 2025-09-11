from agently import Agently, TriggerFlow

Agently.set_settings("runtime.show_trigger_flow_log", False)

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
