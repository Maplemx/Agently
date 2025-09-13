from agently import Agently, TriggerFlow

flow = TriggerFlow()


@flow.chunk
async def user_input(_):
    return input("Say 'STOP' to exit: ")


(
    flow.to(user_input)
    .____()
    .match()
    .case("STOP")
    .to(lambda _: print("👋 bye~"))
    .to(lambda data: data.get_runtime_data("results"))
    .end()
    .case_else()
    .to(
        lambda data: data.append_runtime_data(
            "results",
            data.value,
            emit=False,
        )
    )
    .to(user_input)
    .end_match()
    .____()
)

results = flow.start()
print(results)
