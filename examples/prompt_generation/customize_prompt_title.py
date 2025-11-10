from agently import Agently

agent = Agently.create_agent()

agent.set_settings(
    "prompt.prompt_title_mapping",
    {
        "system": "通用提示",
        "developer": "开发者指令",
        "chat_history": "对话记录",
        "info": "相关信息",
        "tools": "工具信息",
        "action_results": "行动结果记录",
        "instruct": "处理规则",
        "examples": "举例",
        "input": "输入",
        "output": "输出",
        "output_requirement": "输出要求",
    },
)

user_input = "Hello"
welcome_words = {
    "Hello": "Welcome word in English",
    "你好": "Welcome word in Chinese",
    "こんにちは": "Welcome word in Japanese",
    "Bonjour": "Welcome word in French",
    "Hola": "Welcome word in Spanish",
}

(
    agent.input({"user_input": user_input})
    .info(welcome_words)
    .instruct(
        [
            "Judge user's region according {user_input}",
            "Use {info} to help",
        ]
    )
    .output(
        {
            "why": (str, "explanation"),
            "user_region": (str,),
        }
    )
)

print(agent.prompt.to_messages()[0]["content"])
print("==================")
print(agent.prompt.to_text())
