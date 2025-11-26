from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
)

yaml_prompt = """
$role: You're a cat language expert!
input: The cat said "${cat_words}"
output:
    cat_words:
        $type: str
        $desc: what did the cat said?
    reply:
        $type: str
        $desc: what would you reply?
""".strip()

cat_words = "This is delicious!"

agent = Agently.create_agent()
result = agent.load_yaml_prompt(yaml_prompt, {"cat_words": cat_words}).start()
print(result)
