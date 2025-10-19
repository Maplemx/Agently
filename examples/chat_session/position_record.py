# ⚠️ ChatSessionExtension is an experimental extension and may not officially include into Agently default Agent class
# Because the chat history record may become chaos when you try to request a same agent instance at the same time.
# But it works when you can control that only one request and response is happening to the same agent instance and maybe helpful.
# We're trying to figure out other plans to help developers manage chat sessions.

from agently.base import Agent, AgentlyMain
from agently.builtins.agent_extensions import ChatSessionExtension


# Extend Agent with Extension
class ExtendedAgent(ChatSessionExtension, Agent): ...


# Create Agently EntryPoint using Extended Agent Class
Agently = AgentlyMain(AgentType=ExtendedAgent)

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
)


agent = Agently.create_agent()

session_id = agent.activate_chat_session()

# Record key 'user_input' in prompt.input
agent.add_record_input_path("input", "user_input")
# Record key 'reply' in structured output
agent.add_record_output_path("reply")

print(
    "[First Input]:\n",
    agent.input(
        {
            "current_date": "2025-10-19",
            "user_input": "Please help me to take a note: I need to bug some eggs and 1 box of milk from the supermarket today later.",
        }
    )
    .output(
        {
            "think": (str, "How to reply?"),
            "reply": (str,),
        }
    )
    .start(),
)

print(
    "[Response when Chat Session ON]:\n",
    agent.input(
        {
            "current_date": "2025-10-19",
            "user_input": "What did I say earlier?",
        }
    )
    .output(
        {
            "think": (str, "How to reply?"),
            "reply": (str,),
        }
    )
    .start(),
)

agent.stop_chat_session()

print(
    "[Response when Chat Session OFF]:\n",
    agent.input(
        {
            "current_date": "2025-10-19",
            "user_input": "What did I say earlier?",
        }
    )
    .output(
        {
            "think": (str, "How to reply?"),
            "reply": (str,),
        }
    )
    .start(),
)

agent.activate_chat_session(session_id)

print(
    "[Response when Chat Session recovered by ID]:\n",
    agent.input(
        {
            "current_date": "2025-10-19",
            "user_input": "What did I say earlier?",
        }
    )
    .output(
        {
            "think": (str, "How to reply?"),
            "reply": (str,),
        }
    )
    .start(),
)

print(
    "[Chat History]:\n",
    agent.prompt.get("chat_history"),
)
