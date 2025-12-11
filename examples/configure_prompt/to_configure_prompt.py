from agently import Agently

agent = Agently.create_agent()

(
    agent.role(
        "You are an Agently enhanced agent.",
        always=True,
    )
    .info(
        {
            "Agently": "Speed up your AI application development. Official website: https://Agently.tech.",
        },
        always=True,
    )
    .input("Say hello.")
    .instruct(
        [
            "Reply {input} politely.",
        ]
    )
    .output(
        {
            "thinking": (
                [(str, "one step of plan")],
                "plans to response",
            ),
            "reply": (str,),
            "extra": (
                {
                    "worth_to_remember": (
                        bool,
                        "is {input} and {reply} worth to be remembered that not a normal daily chat?",
                    ),
                    "user_emotion_guess": (str, "how do you thinking user's emotion is going to be after {reply}?"),
                },
                "extra info you need to collect and analysis",
            ),
        }
    )
)

yaml_prompt = agent.to_yaml_prompt()
json_prompt = agent.to_json_prompt()

print("[YAML PROMPT]:")
print(yaml_prompt)
print("[JSON PROMPT]:")
print(json_prompt)

agent_2 = Agently.create_agent()

agent_2.load_yaml_prompt(yaml_prompt)
print("[AGENT 2 PROMPT]:")
print(agent_2.get_prompt_text())
