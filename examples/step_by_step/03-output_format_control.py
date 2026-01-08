from agently import Agently

agent = Agently.create_agent()

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


## Agently-Styled Output Data Format Control
def agently_output_format_control():
    result = (
        agent.input("Please explain recursion")
        # With Agently, you can control structured data output easily.
        # Output data format control can be much more stable than other develop frameworks and this control ability can work without the dependency of model ability support or parameter like 'response_format' from API server provider.
        # This is framework ability without model reliance for real!
        .output(
            # You can use a structured data to specific the output structure you want
            {
                # use Tuple[<type>, <output specific description of this part>] to specific output content you want at the leaf points
                "thinking": (str, "Think about how you would answer this question?"),
                "explanation": (str, "Concept explanation"),
                # Nested type definition supported
                "example_codes": ([(str, "Example code")], "Provide at least 2 example codes"),
                "practices": (
                    # Specific as many layers as you pleased
                    [
                        {
                            "question": (str, "Practice question"),
                            "answer": (str, "Reference answer"),
                        }
                    ],
                    "Provide at least 2 practice questions, ensure they are different from the example codes",
                ),
            }
        ).start(
            ## You can use parameter `ensure_keys` to enhance output control
            # You can use dot style path to define a deeper-level path
            ensure_keys=["practices[*].question", "practices[*].answer"],
            # You can switch key path style in 'dot' and 'slash'("final/steps")
            key_style="dot",  # default: "dot"
            # You can customize max retries
            max_retries=1,  # default: 3
            # You can control whether to raise exception if can not ensure all keys in model generation or just ignore it and return the value of the last try.
            raise_ensure_failure=False,  # default: True
        )
    )
    [
        print("[Question]:\n", item["question"], "\n\n[Answer]:\n", item["answer"], "\n\n=======\n\n")
        for item in result["practices"]
    ]


# agently_output_format_control()


## Output Order Matters for CoT-like Control
def output_order_cot_control():
    result = (
        agent.input("Where can I find the release dates for Dark Souls 3 and GTA6 and buy/pre-order them?").output(
            {
                "info_list": [
                    {
                        "topic": (str, "Which game/subject this info is about"),
                        "key_fact": (str, "Key fact needed to answer the question"),
                        "is_known": (bool, "Whether you are confident about this key fact"),
                    }
                ],
                "sure_info": (str, "Only explain the key facts you are confident about"),
                "uncertain": (str, "List the key facts you are not confident about"),
            }
        )
        # Order matters:
        # 1) First generate "info_list" to enumerate knowledge and certainty.
        # 2) Then derive "sure_info" and "uncertain" based on that list.
        # This encourages the model to separate confident vs. uncertain facts.
        # If you swap the order, the model may answer directly and skip the control step.
        .start(
            ensure_keys=["info_list[*].topic", "info_list[*].key_fact", "info_list[*].is_known"],
            key_style="dot",
            max_retries=1,
            raise_ensure_failure=False,
        )
    )
    # Use ensure_keys to protect "info_list" completeness when later fields depend on it.
    print(result)


# output_order_cot_control()


## Role-Thinking + Self-Critique (Second Example)
def role_thinking_self_critique():
    result = (
        agent.input(
            {
                "target": "enter a cave blocked by a huge boulder",
                "items": ["spoon", "chopsticks"],
            }
        ).output(
            {
                "action": (str, "Propose the boldest way to complete {target} using {items}"),
                "can_do": (bool, "Use common sense to judge if {action} is feasible"),
                "can_do_explain": (str, "If {can_do} is false, explain why"),
                "fixed_action": (
                    str,
                    "If {can_do} is false, revise the plan using {items} and {can_do_explain}",
                ),
            }
        )
        # Order matters:
        # action -> can_do -> can_do_explain -> fixed_action
        # This keeps the critique and revision grounded on the proposed action.
        .start(
            ensure_keys=["action", "can_do", "fixed_action"],
            key_style="dot",
            max_retries=1,
            raise_ensure_failure=False,
        )
    )
    print(result)


# role_thinking_self_critique()
