from agently import TriggerFlow

flow = TriggerFlow()

(
    flow.to(("get_user_input", lambda _: input("USER:")))
    .side_branch(lambda data: print(data.value))
    .if_condition("#exit")
    .end()
    .else_condition()
    .to("get_user_input")
    .end_condition()
)

flow.start()
