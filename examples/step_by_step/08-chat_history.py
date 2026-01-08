from agently import Agently

agent = Agently.create_agent()

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


## Chat History: basic multi-turn management
def chat_history_basic():
    # You can add messages to chat_history to keep multi-turn context.
    agent.set_chat_history(
        [
            {"role": "user", "content": "Hi, who are you?"},
            {"role": "assistant", "content": "I'm an Agently assistant."},
        ]
    )
    result = agent.input("What did I ask you before?").start()
    print(result)

    # You can append new turns, or reset the history.
    # Treat the last answer as a new user message to continue the thread.
    agent.add_chat_history({"role": "user", "content": result})
    follow_up = agent.input("Summarize my last message in one sentence.").start()
    print(follow_up)

    agent.reset_chat_history()


# chat_history_basic()
