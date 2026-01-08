from agently import Agently

agent = Agently.create_agent()

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


## Basic Prompt Methods
def basic_prompt_methods():
    # .set_agent_prompt() will cache prompt in agent instance and reuse prompt in every future request until it is changed or removed
    agent.set_agent_prompt("system", "You are a useful assistant.")
    # .set_request_prompt() will only use prompt in next request.
    # Request prompt will be erased when response instance of next request is created
    agent.set_request_prompt("input", "Hello")

    print(agent.start())  # Have response
    print(agent.start())  # Raise error because of missing core prompt

    # reset prompt
    agent.agent_prompt.clear()
    agent.request_prompt.clear()


# basic_prompt_methods()


## Request instance
def request_instance():
    # If you don't want to use an agent instance which may contain more functions and extensions but just want to use Agently to request model, you can use request instance only
    # In fact every agent instance contains a request instance inside to execute model request tasks
    # Request instances can inherit global settings and have instance settings on their own too
    request = Agently.create_request()
    # In request instance .set_prompt() is the basic method to set prompt because there's no agent instance outside anymore of course.
    result = request.set_prompt("input", "Hi").start()
    print(result)


# request_instance()


## What happen when .start() or .get_data()?
def what_happen_when_start():
    # In fact, .start() or .get_data() will create a response instance to storage a snapshot of all runtime information for this request first
    # If any response consume command is given to the response instance, the actual model request start and save all result to a result instance inside the response instance.
    # So the actual behaviors are like these:
    agent.input("hi")
    response = agent.get_response()
    result_data = response.result.get_data()
    # You can get different content from result and the request will not be restarted again
    # Different contents will be stored in result instance when the request is finished.
    result_meta = response.result.get_meta()
    print(result_data)
    print(result_meta)
    # You can also use methods like response.get_data() for short
    # It's the same as response.result.get_data()

    ## Notice
    # If you wonder what methods that agent instance, request instance and response instance provide for short, I highly recommend checking codes in 'agently/core/Agent.py' and 'agently/core/ModelRequest.py'


# what_happen_when_start()


## Chaining Methods Support
def chaining_methods_support():
    result = (
        agent.set_request_prompt(
            "input",
            "hello",
        )
        .set_request_prompt(
            "output",
            "your reply",
        )
        .start()
    )
    print(result)


# chaining_methods_support()


## Basically, You can set almost any serializable data as prompt in Agently
def any_data_as_prompt():
    question_list = [
        "How are you?",
        "Who are you?",
    ]
    role_info = {
        "name": "Alice Agently",
        "role": "Assistant who can help you learning Agently.",
        "fields_can_talks": [
            {
                "filed": "Agently Related",
                "examples": [
                    "How to develop with Agently?",
                    "How does Agently work?",
                    "How can I use Agently to request model?",
                ],
            },
            "Programming learning",
        ],  # Nested data supported
    }
    result = (
        agent.set_request_prompt(
            "input",
            question_list,
        )
        .set_request_prompt(
            "info",
            role_info,
        )
        .start()
    )
    print(result)


# any_data_as_prompt()


## Prompt Slots
def prompt_slots():
    # Every different setting of prompt is a prompt slot.
    # The first parameter of .set_agent_prompt() and .set_request_prompt() is the title of this prompt slot.
    # In fact you can use any title as prompt slot title but using these suggested prompt title may help Agently understand what these prompts mean to do and handle them more properly:
    # "system",
    # "developer",
    # "info",
    # "tools",
    # "action_results",
    # "instruct",
    # "examples",
    # "input",
    # "attachment",
    # "output",
    # "output_format",
    # "options"
    # "chat_history", ! Notice: chat_history is a special prompt slot which allows message list only
    agent.set_request_prompt("input", "Is v3 or v4 is Agently's latest version?")
    agent.set_request_prompt("agently_latest_version", "4.0.6.11")
    print(agent.start())


# prompt_slots()


## Placeholder Mappings
def placeholder_mappings():
    # You can use ${<variable name>} in almost every position in prompt data as long as that position support string value
    result = (
        agent.set_request_prompt(
            "input",
            "My question is ${question}",
            mappings={
                "question": "Who're you?",
            },
        )
        .set_request_prompt(
            "info",
            {"${role_settings}": {"${name_key}": "${name_value}"}},
            mappings={
                "role_settings": "角色设置",
                "name_key": "名称",
                "name_value": "Alice Agently",
            },
        )
        .start()
    )
    print(result)
    # Placeholder can be very useful to prompt template management, configure-prompt, i18n, etc.


# placeholder_mappings()


## Quick Prompt Methods
def quick_prompt_methods():
    # Agent instance and Request instance provide quick prompt methods for developers. These methods were used more often than .set_agent_prompt() and .set_request_prompt() in real cases.
    result = (
        agent.role(
            "You're a useful assistant named ${assistant_name}.",
            # set `always=True` if you want to set this prompt as an agent prompt
            always=True,
            # you can use placeholder mapping in quick prompt methods too
            mappings={
                "assistant_name": "Alice Agently",
            },
        )
        .input("What's your name?")
        .start()
    )
    print(result)
    # Quick prompt method list:
    # .system()
    # .rule()
    # .role()
    # .user_info()
    # .input()
    # .info()
    # .instruct()
    # .examples()
    # .output()
    # .options() ! notice: .options() is a special method to set temp model request options parameters for this request / this agent
    # .attachment() ! notice: .attachment() is a special method for VLM file attachment
    # .set_chat_history() / .add_chat_history() / .reset_chat_history()
    #
    # Highly recommend to check code in codes in 'agently/core/Agent.py' and 'agently/core/ModelRequest.py' to dive deeper.


# quick_prompt_methods()
