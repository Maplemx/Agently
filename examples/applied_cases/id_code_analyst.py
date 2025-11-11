# Background:
# In our daily operations, business teams often need to validate and parse item codes, logistics codes, and other identifiers according to specific rules.
# For the business teams, these parsing rules may change over time and can only be expressed in natural language.
# For the engineering teams, translating and implementing these rules every time results in long delivery cycles and low sense of accomplishment, resembling routine or tedious tasks.

# However, as is well known, large language models are not particularly adept at handling fine-grained numerical details.

# Can we leverage large language models to carry out this process, understand the business team’s requirements, and produce accurate results? Certainly — the following is our proposed solution.

from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", False)

agent = Agently.create_agent()

code_string = "21553270020250017013_001"

rule = """
Extract various parameters from the user-provided code:
1. Code length
2. Characters from position 6 to 9
3. First character of the code
4. Whether it contains an underscore (boolean)
"""

plan = (
    agent.input(
        {
            "code_string": code_string,
            "rule": rule,
        }
    )
    .instruct(
        "Based on the requirements in {rule}, provide a method plan to extract relevant information from {code_string}",
    )
    .output(
        {
            "output_keys": {
                "<output_key_name>": (str, "The meaning/purpose of this output key"),
                "...": "...",
            },
            "output_method_dict": (
                {
                    "<output_key_name>": (
                        str,
                        "Python code method to obtain the corresponding value using {code_string} as input",
                    ),
                }
            ),
        }
    )
    .start()
)

results = {}

print("PLAN:\n", plan)

for key, expr in plan["output_method_dict"].items():
    results[plan["output_keys"][key]] = eval(expr.strip(), None, {"code_string": code_string})

print("\nRESULT:\n", results)

# PLAN:
#  {'output_keys': {'code_length': 'The length of the provided code string', 'chars_6_to_9': 'Characters from position 6 to 9 in the code string', 'first_char': 'First character of the code string', 'contains_underscore': 'Whether the code contains an underscore (boolean)'}, 'output_method_dict': {'code_length': 'len(code_string)', 'chars_6_to_9': 'code_string[5:9]', 'first_char': 'code_string[0]', 'contains_underscore': '("_" in code_string)'}}

# RESULT:
#  {'The length of the provided code string': 24, 'Characters from position 6 to 9 in the code string': '2700', 'First character of the code string': '2', 'Whether the code contains an underscore (boolean)': True}
