from agently import TriggerFlow, TriggerFlowBluePrint

# You can create an independent blue print
blue_print = TriggerFlowBluePrint(name="MyBluePrint")

blue_print.add_event_handler("test", lambda data: print("event:test", data.value))
blue_print.add_flow_data_handler(
    "test",
    lambda data: print(
        f"execution:{ data.execution_id }",
        "flow_data:test",
        data.value,
        flush=True,
    ),
)
blue_print.add_runtime_data_handler(
    "test",
    lambda data: print(
        f"execution:{ data.execution_id }",
        "runtime_data:test",
        data.value,
        flush=True,
    ),
)

# load blue print to flow
flow = TriggerFlow(blue_print=blue_print)

# create multiple executions
execution_1 = flow.create_execution()
execution_1.emit("test", "hello")
execution_1.set_flow_data("test", "world")
execution_1.set_runtime_data("test", "Agently")

execution_2 = flow.create_execution()
execution_2.emit("test", "hello again")
# execution_2 change flow data will trigger execution_1's flow data handler, too.
execution_2.set_flow_data("test", "world again")
execution_2.set_runtime_data("test", "Agently again")

# flow.set_flow_data() will trigger both executions
flow.set_flow_data("test", "all change")
# after remove execution_2, only execution_1 will be triggered
flow.remove_execution(execution_2)
flow.set_flow_data("test", "only execution_1")
