from agently import Agently, TriggerFlow

flow = TriggerFlow()

(
    flow.to(lambda _: range(0, 2))
    .for_each()
    .to(lambda _: range(0, 2))
    .for_each()
    .to(lambda _: ["Hello", "Agently"])
    .for_each()
    .to(lambda data: data.value)
    # Print line "Hello" and line "Agently" (2 * 2) times
    # in async parallel orders (random orders)
    .____("INNER LAYER RESULT:", print_info=True, show_value=True)
    .end_for_each()
    # Print ["Hello", "Agently"] (2 * 2) times
    .____("MIDDLE LAYER RESULT:", print_info=True, show_value=True)
    .end_for_each()
    # Get ["Hello", "Agently"], ["Hello", "Agently"] 2 times for each loop
    # so print [["Hello", "Agently"], ["Hello", "Agently"]] 2 times
    .____("OUTER LAYER RESULT:", print_info=True, show_value=True)
    .end_for_each()
    # Get [["Hello", "Agently"], ["Hello", "Agently"]] 2 times for each loop
    # so print [[["Hello", "Agently"], ["Hello", "Agently"]], [["Hello", "Agently"], ["Hello", "Agently"]]]
    .____("FINAL RESULT:", print_info=True, show_value=True)
    .end()
)

result = flow.start()
# Get final result from .end() chunk
print(result)
