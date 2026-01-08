from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", True)

agent = Agently.create_agent()

ensured_data_object = (
    agent.input(
        # Change the integer from "Now 'control' is 2" to see what happen
        "How to develop an independent game? You MUST use the key name 'final.results' instead of the key name 'final.steps' IF value of the key 'control' > 1. Now 'control' is 1."
    )
    .output(
        {
            "control": (int,),
            "final": {
                "steps": [(str,)],
            },
            "resources": [
                {
                    "title": (str,),
                    "link": (str,),
                }
            ],
        }
    )
    .get_data_object(
        # You can use dot style path to define a deeper-level path
        # Use wildcard to ensure each item in a list has required fields.
        ensure_keys=["final.steps", "resources[*].title", "resources[*].link"],
        # You can switch key path style in 'dot' and 'slash'("final/steps")
        key_style="dot",  # default: "dot"
        # You can customize max retries
        max_retries=1,  # default: 3
        # You can control whether to raise exception if can not ensure
        # all keys in model generation or just ignore it and return the value
        # of the last try.
        raise_ensure_failure=False,  # default: True
    )
)
print(ensured_data_object)
print(ensured_data_object.final)  # type: ignore
print(ensured_data_object.final.steps)  # type: ignore
# use type: ignore since ensure_data_object is a runtime created data model
